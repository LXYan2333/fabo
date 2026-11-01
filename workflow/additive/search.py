"""Finite exhaustive grid search; expanded tables never enter the result cache."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import gmpy2 as g
from .model import Grid, storage, row_data
from .qualify import qualify


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def completed_tasks(pool, tasks, capacity):
    """Bounded, work-conserving dispatch; a slow grid cannot stall a batch."""
    tasks = iter(tasks)
    pending = set()
    def refill():
        while len(pending) < capacity:
            task = next(tasks, None)
            if task is None:
                break
            pending.add(pool.submit(candidate, task))
    refill()
    while pending:
        finished, pending = wait(pending, return_when=FIRST_COMPLETED)
        for future in finished:
            yield future.result()
        refill()


def identity(config):
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(Path(__file__).parent.glob('*.py'))}
    return digest(dict(method='additive-materialized-nextup-v1', config=config, sources=sources,
                       python=sys.version.split()[0], gmpy2=g.version(), mpfr=g.mpfr_version(), gmp=g.mp_version()))


def validate(config):
    producer = config.get('producer')
    actual = dict(python=sys.version.split()[0], gmpy2=g.version(), mpfr=g.mpfr_version(), gmp=g.mp_version())
    if producer is not None and producer != actual:
        raise ValueError('producer version mismatch: expected '+str(producer)+'; got '+str(actual))
    if config['error']['metric'] not in ('ulp', 'relative', 'absolute') or not 0 < config['error']['limit'] < float('inf'):
        raise ValueError('invalid error target')
    if not config['requested_ranges'] or any(type(v) is not int or v < 0 for pair in config['requested_ranges'] for v in pair):
        raise ValueError('invalid requested ranges')
    if any(len(pair) != 2 or pair[0] > pair[1] for pair in config['requested_ranges']):
        raise ValueError('invalid requested range')
    if not 1 <= config['minimum_degree'] <= config['maximum_degree'] <= 64:
        raise ValueError('invalid degree limits')
    if config['budget_bytes'] <= 0 or config['screen_subdivisions'] < 1 or config['final_subdivisions'] < 1 or config['refinement_rounds'] < 0:
        raise ValueError('invalid budget or qualification settings')
    if not config['retained_bits'] or not config['spacing_exponents']:
        raise ValueError('empty grid family')
    for b in config['retained_bits']:
        for e in config['spacing_exponents']:
            Grid(b, e, 1, float(config['domain_end']))


def grids(config):
    for b in sorted(set(config['retained_bits'])):
        for e in sorted(set(config['spacing_exponents'])):
            for m in range(1, 2**b+1):
                yield Grid(b, e, m, float(config['domain_end']))


def score(record):
    return (max(record['degrees']), record['storage']['table_bytes'], tuple(record['degrees']),
            record['grid']['b'], record['grid']['e'], record['grid']['m'])


def candidate(task):
    index, grid, config = task
    order_cache = {}
    results = []
    priority = config.get('priority_orders', [4, 8, 12])
    ranges = sorted(config['requested_ranges'], key=lambda r: (priority.index(r[1]) if r[1] in priority else len(priority)+r[1], r[0]))
    for first, last in ranges:
        record = dict(first=first, last=last, grid=grid.metadata())
        minimum = [config['minimum_degree']]*(last-first+1)
        if storage(grid, first, minimum)['table_bytes'] > config['budget_bytes']:
            results.append(dict(record, status='budget_lower_bound'))
            continue
        degrees, evidence = [], []
        for n in range(first, last+1):
            if n not in order_cache:
                failures, selected = [], None
                for p in range(config['minimum_degree'], config['maximum_degree']+1):
                    args = dict(metric=config['error']['metric'], limit=config['error']['limit'])
                    keys = list(dict.fromkeys(grid.keys.start+(len(grid.keys)-1)*i//16 for i in range(17)))
                    result = qualify(grid, n, p, **args, subdivisions=config['screen_subdivisions'], keys=keys)
                    if result['status'] == 'qualified':
                        result = qualify(grid, n, p, **args, subdivisions=config['final_subdivisions'], refinement=config['refinement_rounds'])
                    if result['status'] == 'qualified':
                        selected = (p, dict(result, lower_degree_failures=failures))
                        break
                    failures.append(dict(degree=p, **result))
                    if result['status'] == 'unresolved':
                        break  # Cannot certify a minimum by skipping this degree.
                order_cache[n] = selected, failures
            selected, failures = order_cache[n]
            if selected is None:
                record.update(status='unresolved' if failures[-1]['status'] == 'unresolved' else 'degree_limit',
                              failed_order=n, degree_trials=failures)
                break
            degrees.append(selected[0])
            evidence.append(selected[1])
        else:
            size = storage(grid, first, degrees)
            # Fully materialized rounded coefficients make outputs separable:
            # assembled evaluation has exactly the same per-output DAG.
            record.update(status='qualified' if size['table_bytes'] <= config['budget_bytes'] else 'budget',
                          degrees=degrees, storage=size, qualification=evidence)
        results.append(record)
    return dict(index=index, results=results)


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def payload_rows(record):
    meta = record['grid']
    grid = Grid(meta['b'], meta['e'], meta['m'], float.fromhex(meta['domain_end']))
    first, last = record['first'], record['last']
    highest = record['storage']['highest_reference_order']
    for key in grid.keys:
        hi, codes = row_data(grid.node(key), highest, first, last)
        words = [struct.unpack('<Q', struct.pack('<d', x))[0] for x in hi[first:highest+1]]
        words[0] += 1  # Lowest stored order is never a coefficient for a lower output.
        row = struct.pack('<'+'Q'*len(words), *words)+bytes(codes[first:last+1])
        yield row+bytes(record['storage']['row_bytes']-len(row))


def summarize(folder, run_id, config, records, complete):
    winners, counts = {}, {}
    for item in records:
        for result in item['results']:
            status = result['status']
            counts[status] = counts.get(status, 0)+1
            if status != 'qualified':
                continue
            name = f"{result['first']}-{result['last']}"
            if name not in winners or score(result) < score(winners[name]):
                winners[name] = result
    for record in winners.values():
        checksum = hashlib.sha256()
        for row in payload_rows(record):
            checksum.update(row)
        record['payload_sha256'] = checksum.hexdigest()
        record['minimum_order_prebiased'] = True
        record['window_edges'] = dict(b=record['grid']['b'] in (min(config['retained_bits']), max(config['retained_bits'])),
                                      e=record['grid']['e'] in (min(config['spacing_exponents']), max(config['spacing_exponents'])),
                                      degree=max(record['degrees']) == config['maximum_degree'])
    atomic_json(folder/'summary.json', dict(identity=run_id, complete=complete, counts=counts,
                config=config, winners=winners, minimum_claim='within declared family and sampled policy; unresolved candidates may prevent minimum certification',
                unresolved=counts.get('unresolved', 0)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--shard', type=int, default=0)
    parser.add_argument('--shards', type=int, default=1)
    parser.add_argument('--merge', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    validate(config)
    if args.workers < 1 or not 0 <= args.shard < args.shards:
        parser.error('invalid workers/shard')
    run_id = identity(config)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = args.output/'identity.json'
    if manifest.exists() and json.loads(manifest.read_text())['identity'] != run_id:
        raise ValueError('output belongs to another numerical identity')
    # Each shard has a separate directory; the parent merge owns its own manifest.
    atomic_json(manifest, dict(identity=run_id, config=config))
    journal = args.output/'records.jsonl'
    done = set()
    if journal.exists():
        valid_bytes = 0
        with journal.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    break
                record = json.loads(line)
                if record['index'] in done or record['index'] % args.shards != args.shard:
                    raise ValueError('duplicate grid or incompatible shard assignment')
                done.add(record['index'])
                valid_bytes += len(line)
        # Recover only an interrupted final append, never silently discard a complete record.
        with journal.open('r+b') as stream:
            stream.truncate(valid_bytes)
    if args.merge:
        paths = []
        for shard in range(args.shards):
            directory = args.output/f'shard-{shard}'
            summary = json.loads((directory/'summary.json').read_text())
            if summary['identity'] != run_id or not summary['complete']:
                raise ValueError('incomplete or incompatible shard')
            paths.append(directory/'records.jsonl')
        expected = set(range(sum(1 for _ in grids(config))))
        seen = set()
        def merged_records():
            for path in paths:
                with path.open() as stream:
                    for line in stream:
                        record = json.loads(line)
                        if record['index'] in seen or record['index'] not in expected:
                            raise ValueError('duplicate or unknown grid')
                        seen.add(record['index'])
                        yield record
            if seen != expected:
                raise ValueError('missing grid coverage')
        summarize(args.output, run_id, config, merged_records(), True)
        return
    expected = {i for i, _ in enumerate(grids(config)) if i % args.shards == args.shard}
    if not done <= expected:
        raise ValueError('missing or duplicate grid coverage')
    tasks = ((i, grid, config) for i, grid in enumerate(grids(config)) if i % args.shards == args.shard and i not in done)
    with journal.open('a') as stream, ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in completed_tasks(pool, tasks, args.workers*2):
            stream.write(json.dumps(result, sort_keys=True)+'\n')
            stream.flush()
            done.add(result['index'])
            print(json.dumps(dict(grid=result['index'], completed=len(done), total=len(expected))), flush=True)
    with journal.open() as stream:
        summarize(args.output, run_id, config, (json.loads(line) for line in stream), done == expected)


if __name__ == '__main__':
    main()

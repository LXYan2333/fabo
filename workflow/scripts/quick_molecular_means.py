"""Reduce archived QUICK matrices to differences of five-run means; no QUICK execution."""

import argparse
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path

import numpy as np

if __package__:
    from .molecular_metrics import MatrixMetrics, DEFINITION
    from .record_manifest import write_manifest
else:
    from molecular_metrics import MatrixMetrics, DEFINITION
    from record_manifest import write_manifest

BACKENDS = ('official', 'libintx_gpu', 'vsr', 'gansu', 'fabo_additive')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mean_difference(values, hi, lo):
    # Center before averaging so a sub-ulp mean offset is not lost to hi.
    total = np.zeros_like(hi)
    for value in values:
        if not np.isfinite(value).all():
            raise ValueError('Nonfinite archived output')
        total += (value - hi) - lo
    return total / len(values)


def reduce_case(root, case, identity):
    cid = case['case']['id']
    n = case['dimensions'][0]
    if case['identity'] != identity or case['rounds'] != 5:
        raise ValueError('Case identity/repetitions mismatch')
    reference = root / 'reports' / cid / 'reference-mean'
    layout = json.loads((reference / 'layout.json').read_text())
    if layout['dimensions'] != [2, n, n]:
        raise ValueError('Reference matrix dimensions')
    files = {'hi': reference / 'hi.bin', 'lo': reference / 'lo.bin'}
    hashes = {name: layout['files'][f'{name}.bin'] for name in files}
    result_hashes = {}
    rows = {}
    fixtures = set()
    for backend in BACKENDS:
        energy = []
        for r in range(5):
            folder = root / 'samples' / cid / f'{r:02d}' / backend
            complete = json.loads((folder / 'complete.json').read_text())
            if complete['identity'] != identity or sha(folder / 'result.json') != complete['files']['result.json']:
                raise ValueError('Sample identity/hash mismatch')
            observation = json.loads((folder / 'result.json').read_text())
            if (observation['variant'], observation['round'], observation['case']) != (backend, r, cid):
                raise ValueError('Sample metadata mismatch')
            fixtures.add(observation['fixture_sha256'])
            energy.append(observation['energy_hartree'])
            key = f'{backend}/{r}'
            files[key] = folder / 'outputs.bin'
            hashes[key] = complete['files']['outputs.bin']
            result_hashes[key] = complete['files']['result.json']
        saved = case['variants'][backend]
        if math.fsum(energy) / 5 != saved['energy_mean']:
            raise ValueError('Energy summary mismatch')
        rows[backend] = dict(energy_abs_difference=abs(saved['energy_mean_difference']),
                             fock_max_absolute=0.0, density_max_absolute=0.0)
    if len(fixtures) != 1 or any(p.stat().st_size != 16 * n * n for p in files.values()):
        raise ValueError('Fixture or output size mismatch')
    accumulators = {key: hashlib.sha256() for key in files}
    with ExitStack() as stack:
        streams = {key: stack.enter_context(path.open('rb')) for key, path in files.items()}
        for matrix in ('fock', 'density'):
            metrics = {backend: MatrixMetrics() for backend in BACKENDS}
            for start in range(0, n * n, 262144):
                count = min(262144, n * n - start)
                def read(key):
                    block = streams[key].read(count * 8)
                    if len(block) != count * 8:
                        raise ValueError('Truncated matrix')
                    accumulators[key].update(block)
                    return np.frombuffer(block, dtype='<f8')
                hi, lo = read('hi'), read('lo')
                if not (np.isfinite(hi).all() and np.isfinite(lo).all()):
                    raise ValueError('Nonfinite reference')
                for backend in BACKENDS:
                    delta = mean_difference([read(f'{backend}/{r}') for r in range(5)], hi, lo)
                    metrics[backend].add(delta)
            for backend in BACKENDS:
                values = metrics[backend].finish()
                rows[backend].update({matrix + '_' + name: value for name, value in values.items()})
    if any(h.hexdigest() != hashes[key] for key, h in accumulators.items()):
        raise ValueError('Archived matrix checksum mismatch')
    return dict(case=case['case'], dimensions=n, backends=rows,
                reference_matrix_sd_max=case['reference_matrix_sd_max'],
                reference_energy_sd=case['variants']['reference']['energy_sd'],
                matrix_sha256=hashes, result_sha256=result_hashes,
                reference_layout_sha256=sha(reference / 'layout.json'))


def run(root, output):
    complete = json.loads((root / 'complete.json').read_text())
    if sha(root / 'summary.json') != complete['summary_sha256']:
        raise ValueError('Summary checksum mismatch')
    summary = json.loads((root / 'summary.json').read_text())
    if summary['identity'] != complete['identity'] or len(summary['cases']) != 12:
        raise ValueError('Incomplete run')
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in summary['cases']:
        result = reduce_case(root, case, summary['identity'])
        records.append(result)
        (output / (case['case']['id'] + '.json')).write_text(json.dumps(result, indent=2) + '\n')
        print('Completed', case['case']['id'], flush=True)
    report = dict(identity=summary['identity'], summary_sha256=complete['summary_sha256'],
                  generator_sha256=sha(Path(__file__)), rounds=5,
                  schema=2, metric_definition=DEFINITION,
                  numpy_version=np.__version__, longdouble_bits=np.finfo(np.longdouble).nmant + 1,
                  metrics_source_sha256=sha(Path(__file__).with_name('molecular_metrics.py')),
                  matrix_statistic='maximum and mean absolute elementwise differences of mean(backend)-mean(reference)',
                  cases=records)
    (output / 'molecular-means.json').write_text(json.dumps(report, indent=2) + '\n')
    write_manifest(output / 'molecular-means.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.run, args.output)

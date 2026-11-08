"""Small, deterministic orchestration helpers. Experimental data are immutable."""
import csv
import hashlib
import json
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def save(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temp.replace(path)

def partitions(total, size):
    if total < 1 or size < 1:
        raise ValueError('positive grid and shard sizes required')
    return [(first, min(size, total-first)) for first in range(0,total,size)]

def merge(shards, total):
    first = 0
    rows = {}
    signature = None
    with localcontext() as context:
        context.prec = 80
        for shard in sorted(shards, key=lambda s:s['first']):
            if shard['first'] != first or shard['count'] <= 0:
                raise ValueError('overlapping, empty, or missing shard')
            first += shard['count']
            keys = [(r['id'],r['N'],r['n'],r['metric']) for r in shard['rows']]
            if len(set(keys)) != len(keys) or (signature is not None and set(keys) != signature):
                raise ValueError('duplicate or inconsistent adapter coverage')
            signature = set(keys)
            for key, source in zip(keys, shard['rows']):
                r = rows.setdefault(key, dict(source, count=0, invalid=0, sum_lo='0', sum_hi='0', max_lo='0',max_hi='0'))
                r['count'] += shard['count']; r['invalid'] += source['invalid']
                for field in ('sum_lo','sum_hi'):
                    context.rounding = ROUND_FLOOR if field.endswith('lo') else ROUND_CEILING
                    r[field] = str(Decimal(r[field])+Decimal(source[field]))
                r['max_lo'] = str(max(Decimal(r['max_lo']),Decimal(source['max_lo'])))
                if Decimal(source['max_hi']) >= Decimal(r['max_hi']):
                    r['max_hi'] = source['max_hi']
                    for field in source:
                        if field.startswith('witness_'): r[field]=source[field]
        if first != total:
            raise ValueError('incomplete grid coverage')
        result = list(rows.values())
        # Pool all outputs with equal weight, without discarding invalid values.
        groups = {}
        for r in result:
            key = r['id'],r['N'],r['metric']
            g = groups.setdefault(key, dict(id=r['id'],N=r['N'],n='all',metric=r['metric'],count=0,invalid=0,sum_lo='0',sum_hi='0',max_lo='0',max_hi='0'))
            g['count']+=r['count'];g['invalid']+=r['invalid']
            for field in ('sum_lo','sum_hi'):
                context.rounding = ROUND_FLOOR if field.endswith('lo') else ROUND_CEILING
                g[field]=str(Decimal(g[field])+Decimal(r[field]))
            g['max_lo']=str(max(Decimal(g['max_lo']),Decimal(r['max_lo'])))
            if Decimal(r['max_hi'])>=Decimal(g['max_hi']):
                g['max_hi']=r['max_hi']
                g['witness_n']=r['n']
                for field in r:
                    if field.startswith('witness_'):g[field]=r[field]
        result += list(groups.values())
        for r in result:
            r['status']='nonfinite-output' if r['invalid'] else 'complete'
            for side in ('lo','hi'):
                context.rounding = ROUND_FLOOR if side=='lo' else ROUND_CEILING
                r['mean_'+side]=None if r['invalid'] else str(Decimal(r['sum_'+side])/r['count'])
            if r['invalid']:r['max_lo']=r['max_hi']=None
        return result

def storage(summary, include):
    data = json.loads(Path(summary).read_text())
    if not data['complete']: raise ValueError('incomplete numerical selection')
    result=[]
    for n in range(25):
        w=data['winners'][f'0-{n}'];s=w['storage'];t=w['tail']['storage']
        word_bytes=s['row_bytes'];main=s['table_bytes'];tail=t['table_bytes']
        if main+tail!=w['combined_table_bytes'] or main+tail>data['config']['budget_bytes']:
            raise ValueError('invalid storage accounting')
        # Resolve the public data header and check its model's emitted constants.
        import re
        public=Path(include)/f'fast_boys/models/data_0_{n}.h'
        target=re.search(r'#include "([^"]+)"',public.read_text()).group(1)
        model=(Path(include)/target).with_name('model.h').read_text()
        for field,value in [('table_bytes',main+tail),('row_words',word_bytes//8),('tail_row_count',t['row_count'])]:
            if not re.search(r'\b'+field+r'\s*=\s*'+str(value)+r'\b',model):
                raise ValueError('generated model and numerical storage disagree: '+field)
        rows=w['grid']['row_count']+t['row_count']
        result.append(dict(N=n,main_bytes=main,tail_bytes=tail,total_bytes=main+tail,
            coefficient_bytes=rows*s['coefficient_bytes_per_row'],correction_bytes=rows*s['correction_bytes_per_row'],
            padding_bytes=rows*s['padding_bytes_per_row'],budget_bytes=data['config']['budget_bytes']))
    return result

def csv_write(path, rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,keys);writer.writeheader();writer.writerows(rows)

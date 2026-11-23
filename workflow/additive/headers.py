"""Regenerate a single contiguous main/tail table for each selected model."""
import argparse
import json
from pathlib import Path

from ._frozen_v3 import paired_headers as emitter
from ._frozen_v3.headers import coefficient_word, correction_word, interleaved_rows, validate_record
from .tail import storage as tail_storage

ROOT = Path(__file__).resolve().parents[2]


def generate(summary, output, ranges=None, workers=1):
    if workers < 1:
        raise ValueError('workers must be positive')
    if not summary.get('complete') or summary.get('unresolved', 0):
        raise ValueError('a complete resolved selection is required')
    if summary['config']['error']['metric'] not in ('ulp', 'absolute', 'relative'):
        raise ValueError('unsupported error metric')
    records = summary['winners']
    chosen = sorted(records if ranges is None else ranges)
    if not chosen or any(key not in records for key in chosen):
        raise ValueError('requested range is missing')
    # Validate the whole selection before the identity-bearing writer emits any files.
    for key in chosen:
        r = records[key]
        tail = r.get('tail')
        if not isinstance(tail, dict):
            raise ValueError(f'{key}: combined-table record required; split catalogs are unsupported')
        grid = validate_record(r)
        first, last, degrees = r['first'], r['last'], r['degrees']
        if (key != f'{first}-{last}' or
                (tail['first'], tail['last'], tail['degrees']) != (first, last, degrees)):
            raise ValueError(f'{key}: paired degrees/ranges disagree')
        if tail['storage'] != tail_storage(first, degrees, tail['retained_bits']):
            raise ValueError(f'{key}: tail storage does not match recipe')
        if (grid.domain_end < 1 or tail['minimum_x'] != grid.domain_end or
                tail['storage']['row_bytes'] != r['storage']['row_bytes']):
            raise ValueError(f'{key}: paired layout/seam mismatch')
        if tail['storage']['table_bytes'] + r['storage']['table_bytes'] > summary['config']['budget_bytes']:
            raise ValueError(f'{key}: paired table exceeds combined budget')
    return emitter.generate(summary, Path(output), chosen, workers)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--output',type=Path,required=True,help='generated include root')
    parser.add_argument('--ranges',nargs='+',help='selected keys, e.g. 0-4 0-8 0-12')
    parser.add_argument('--workers',type=int,default=1,help='accepted for CLI compatibility; combined emission is sequential')
    args=parser.parse_args()
    generate(json.loads(args.summary.read_text()),args.output,args.ranges,args.workers)


if __name__=='__main__':
    main()

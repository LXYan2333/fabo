"""Reproduce CPU mean-time charts from the completed fixed-density experiment."""

import argparse
import json
import math
from pathlib import Path
import statistics

from .plot_quick_performance import BASES, digest, render

BACKENDS = (
    ('original', 'Simint original', '#999999'),
    ('libintx', 'LibintX', '#E69F00'),
    ('vsr', 'VSR', '#009E73'),
    ('laikov', 'Laikov', '#CC79A7'),
    ('fabo', 'FABO', '#0072B2'),
)
SYSTEMS = {1: ('water', 'Water', 8), 17: ('uracil', 'Uracil', 1),
           24: ('benzene', 'Benzene', 1), 34: ('pentane', 'Pentane', 1)}


def load_records(root):
    manifest = json.loads((root / 'download-manifest.json').read_text())
    for name, checksum in manifest['files'].items():
        if digest(root / name) != checksum:
            raise ValueError(f'Checksum mismatch: {name}')
    complete = json.loads((root / 'complete.json').read_text())
    for name in ('summary', 'reuse'):
        if digest(root / f'{name}.json') != complete[f'{name}_sha256']:
            raise ValueError(f'Checksum mismatch: {name}')
    config = json.loads((root / 'config.json').read_text())
    if config['rounds'] != 5:
        raise ValueError('Unexpected repetition count')
    cases = json.loads((root / 'selected-cases.json').read_text())
    raw = json.loads((root / 'results.json').read_text())
    summaries = json.loads((root / 'summary.json').read_text())
    if len(raw) != 300 or len(summaries) != 60 or len(cases) != 12:
        raise ValueError('Incomplete coverage')
    if {(c['system'], c['basis']) for c in cases} != {(s, b) for s in SYSTEMS for b in BASES}:
        raise ValueError('Unexpected cases')
    if len({c['id'] for c in cases}) != 12:
        raise ValueError('Duplicate case identifiers')
    rows, used = [], set()
    for case in cases:
        if case['copies'] != SYSTEMS[case['system']][2]:
            raise ValueError('Unexpected stack size')
        fixtures = set()
        for backend, _, _ in BACKENDS:
            samples = [r for r in raw if r['case'] == case['id'] and r['backend'] == backend]
            if len(samples) != 5 or {r['round'] for r in samples} != set(range(5)):
                raise ValueError('Missing or duplicate repetitions')
            times = [float(r['jk_seconds']) for r in samples]
            if not all(math.isfinite(t) and t > 0 for t in times):
                raise ValueError('Invalid timing')
            fixtures.update(r['fixture_sha256'] for r in samples)
            recorded = [r for r in summaries if r['case'] == case['id'] and r['backend'] == backend]
            if len(recorded) != 1 or statistics.median(times) != recorded[0]['jk_seconds']:
                raise ValueError('Raw timings disagree with completed median summary')
            used.add((case['id'], backend))
            rows.append(dict(case=case['id'], system=case['system'], basis=case['basis'],
                             copies=case['copies'], backend=backend,
                             mean_seconds=statistics.mean(times), sd_seconds=statistics.stdev(times),
                             repetitions=5))
        if len(fixtures) != 1:
            raise ValueError('Mismatched initial-state fixtures')
    if {(r['case'], r['backend']) for r in raw} != used:
        raise ValueError('Unexpected measurements')
    return rows


def generate(root, output, tables=None):
    rows = load_records(root)
    tables = tables if tables is not None else output.parent / 'tables'
    render(rows, output, tables=tables, backends=BACKENDS, systems=SYSTEMS, stem='nwchem',
           engine='NWChem--Simint', scope='two-electron Fock-build', figure_prefix='cpu',
           ylabel='Mean two-electron Fock-build time (s)')
    provenance = dict(results_sha256=digest(root / 'results.json'),
                      completion_sha256=digest(root / 'complete.json'),
                      generator_sha256=digest(Path(__file__)),
                      renderer_sha256=digest(Path(__file__).with_name('plot_quick_performance.py')),
                      observations=300, means=60, statistic='arithmetic mean',
                      error_bars='sample standard deviation (ddof=1)',
                      scope='fock_2e; raw jk_seconds', units='seconds')
    (tables / 'results-nwchem-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tables', type=Path, help='Table/data directory (default: tables beside the figure directory)')
    args = parser.parse_args()
    generate(args.records, args.output, args.tables)

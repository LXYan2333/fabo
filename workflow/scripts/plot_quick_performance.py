"""Regenerate mean Fock-build bar charts from completed QUICK observations."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

BACKENDS = (
    ('official', 'QUICK original', '#999999'),
    ('libintx_gpu', 'LibintX', '#E69F00'),
    ('vsr', 'VSR', '#009E73'),
    ('gansu', 'GANSU', '#CC79A7'),
    ('fabo_additive', 'FABO', '#0072B2'),
)
BASES = ('6-31G*', 'def2-SVP', 'cc-pVDZ')
SYSTEMS = {1: ('water', 'Water', 128), 17: ('uracil', 'Uracil', 8),
           24: ('benzene', 'Benzene', 16), 34: ('pentane', 'Pentane', 16)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records(root):
    complete = json.loads((root / 'complete.json').read_text())
    for name, key in (('summary.json', 'summary_sha256'), ('reuse.json', 'reuse_sha256'),
                      ('execution-repair.json', 'execution_repair_sha256')):
        if digest(root / name) != complete[key]:
            raise ValueError(f'Checksum mismatch: {name}')
    summary = json.loads((root / 'summary.json').read_text())
    if summary['identity'] != complete['identity']:
        raise ValueError('Summary identity mismatch')
    rows, seen = [], set()
    for case in summary['cases']:
        info = case['case']
        key = info['system'], info['basis']
        if key in seen or key[0] not in SYSTEMS or key[1] not in BASES:
            raise ValueError('Unexpected or duplicate case')
        seen.add(key)
        if case['identity'] != complete['identity'] or case['rounds'] != 5:
            raise ValueError('Inconsistent case identity or repetition count')
        if info['copies'] != SYSTEMS[key[0]][2]:
            raise ValueError('Unexpected stack size')
        timed = {v for v, r in case['variants'].items() if 'timing' in r}
        if timed != {v for v, _, _ in BACKENDS}:
            raise ValueError('Unexpected timed backend coverage')
        for backend, _, _ in BACKENDS:
            samples = case['variants'][backend]['timing']['fock_seconds']['samples']
            if len(samples) != 5 or not all(math.isfinite(x) and x > 0 for x in samples):
                raise ValueError('Invalid timing samples')
            rows.append(dict(case=info['id'], system=key[0], basis=key[1],
                             copies=info['copies'], backend=backend,
                             mean_seconds=statistics.mean(samples),
                             sd_seconds=statistics.stdev(samples), repetitions=len(samples)))
    if seen != {(s, b) for s in SYSTEMS for b in BASES}:
        raise ValueError('Incomplete molecular coverage')
    return complete['identity'], rows


def timing_table(rows, *, backends=BACKENDS, systems=SYSTEMS, engine='QUICK', scope='full Fock-build', figure_prefix='gpu'):
    by_key = {(r['system'], r['basis'], r['backend']): r for r in rows}
    lines = [
        r'\begin{table*}[tbp]',
        r'\caption{Mean ' + scope + ' times in seconds for every molecular stack, basis set, and timed Boys backend in ' + engine + r'. Each entry is the arithmetic mean of five measurements, reported to three decimal places. Stack sizes are given in parentheses as numbers of dimers. These are the same observations as Fig.~\ref{fig:' + figure_prefix + r'-fock-performance}; the correctly rounded reference is untimed.}',
        r'\label{tab:' + figure_prefix + '-fock-times}',
        r'\begin{ruledtabular}',
        r'\begin{tabular}{llrrrrr}',
        'Dimer stack & Basis & ' + ' & '.join(label for _, label, _ in backends) + r' \\',
        r'\hline',
    ]
    for i, (system, (_, name, copies)) in enumerate(systems.items()):
        if i:
            lines.append(r'\hline')
        for j, basis in enumerate(BASES):
            label = f'{name} ({copies})' if j == 1 else ''
            times = [f"{by_key[system, basis, backend]['mean_seconds']:.3f}" for backend, _, _ in backends]
            lines.append(' & '.join([label, basis, *times]) + r' \\')
    lines.extend([r'\end{tabular}', r'\end{ruledtabular}', r'\end{table*}'])
    return '\n'.join(lines) + '\n'


def render(rows, output, *, tables=None, backends=BACKENDS, systems=SYSTEMS, stem='quick', engine='QUICK', scope='full Fock-build', figure_prefix='gpu', ylabel='Mean Fock-build time (s)'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FormatStrFormatter

    output.mkdir(parents=True, exist_ok=True)
    tables = tables if tables is not None else output.parent / 'tables'
    tables.mkdir(parents=True, exist_ok=True)
    (tables / f'results-{stem}-mean-timings.tex').write_text(timing_table(rows, backends=backends, systems=systems, engine=engine, scope=scope, figure_prefix=figure_prefix))
    by_key = {(r['system'], r['basis'], r['backend']): r for r in rows}
    with (tables / f'results-{stem}-mean-timings.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plt.rcParams.update({'font.size': 11, 'pdf.fonttype': 42})
    for system, (slug, name, copies) in systems.items():
        fig, ax = plt.subplots(figsize=(5.4, 4.1))
        width = 0.155
        for j, (backend, label, color) in enumerate(backends):
            values = [by_key[system, basis, backend] for basis in BASES]
            ax.bar([i + (j - 2) * width for i in range(3)],
                   [r['mean_seconds'] for r in values], width, label=label, color=color,
                   yerr=[r['sd_seconds'] for r in values], capsize=2,
                   error_kw={'elinewidth': 0.8, 'capthick': 0.8})
        ax.set(xticks=range(3), xticklabels=BASES, ylabel=ylabel,
               xlabel='Basis set', title=f'{name}: {copies} dimer' + ('s' if copies != 1 else ''), ylim=(0, None))
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        ax.set_axisbelow(True)
        ax.grid(axis='y', alpha=0.2)
        handles, labels = ax.get_legend_handles_labels()
        # Matplotlib fills columns; arrange entries in bar order when read by row.
        order = [0, 2, 4, 1, 3]
        fig.legend([handles[i] for i in order], [labels[i] for i in order],
                   loc='upper center', ncol=2, fontsize=9, frameon=False)
        fig.tight_layout(rect=(0, 0, 1, 0.82))
        fig.savefig(output / f'results-{stem}-{slug}.pdf')
        plt.close(fig)


def generate(root, output, tables=None):
    identity, rows = load_records(root)
    tables = tables if tables is not None else output.parent / 'tables'
    render(rows, output, tables=tables)
    metadata = dict(identity=identity, summary_sha256=digest(root / 'summary.json'),
                    generator_sha256=digest(Path(__file__)), statistic='arithmetic mean',
                    error_bars='sample standard deviation (ddof=1)',
                    scope='synchronized scf_operator(.false.)', units='seconds',
                    observations=300, means=60)
    (tables / 'results-quick-provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tables', type=Path, help='Table/data directory (default: tables beside the figure directory)')
    args = parser.parse_args()
    generate(args.records, args.output, args.tables)

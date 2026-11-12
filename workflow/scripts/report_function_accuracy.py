"""Regenerate manuscript figures/data from completed scans; no new evaluation."""
import argparse
import hashlib
import json
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from pathlib import Path

from workflow.library_accuracy.core import csv_write, storage, identity


def verify_provenance(folder, complete):
    downloads = json.loads((folder / 'download-manifest.json').read_text())
    names = {'run.json', 'execution.json', 'built.json', 'scan.build.json'}
    if set(downloads['files']) != names:
        raise ValueError('Incomplete accuracy provenance manifest')
    for name, checksum in downloads['files'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f'Accuracy provenance checksum mismatch: {name}')
    run = json.loads((folder / 'run.json').read_text())
    execution = json.loads((folder / 'execution.json').read_text())
    built = json.loads((folder / 'built.json').read_text())
    scanner = json.loads((folder / 'scan.build.json').read_text())
    recipe = run['recipe']
    if identity(recipe) != run['identity'] or run['identity'] != complete['identity'] or identity(execution) != complete['execution']:
        raise ValueError('Accuracy provenance identity mismatch')
    build_hashes = [v for k, v in recipe['resources'].items() if Path(k).name == 'built.json']
    if build_hashes != [downloads['files']['built.json']] or built['adapters'] != recipe['adapters'] or scanner['sha256'] != recipe['scanner_sha256']:
        raise ValueError('Accuracy build provenance mismatch')
    if (recipe['total'], recipe['denominator']) != (complete['inputs'], complete['denominator']):
        raise ValueError('Accuracy provenance grid mismatch')


def load_records(root):
    rows = []
    for platform in ('cpu', 'cuda'):
        folder = root / platform
        manifest = json.loads((folder / 'complete.json').read_text())
        verify_provenance(folder, manifest)
        data = (folder / 'accuracy.json').read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest['files']['accuracy.json']:
            raise ValueError('Accuracy summary checksum mismatch')
        if (manifest['inputs'], manifest['denominator']) != (1000000001, 1000000):
            raise ValueError('Not the complete [0,1000] dense scan')
        records = json.loads(data)
        backends = {'fabo', 'libintx', 'vsr', 'simint', 'laikov', 'fabo_software'} if platform == 'cpu' else {'fabo', 'libintx', 'vsr', 'quick', 'gansu'}
        expected = {(b, m, n, k, metric) for b in backends for m in ('strict', 'fast')
                    for n in range(13) for k in [*range(n + 1), 'all']
                    for metric in ('absolute', 'relative', 'ulp')}
        keys = {(r['backend'], r['mode'], r['N'], r['n'], r['metric']) for r in records}
        if keys != expected or len(records) != len(expected):
            raise ValueError('Incomplete or duplicated scan results')
        if any(r['platform'] != platform or r['invalid'] or r['status'] != 'complete' for r in records):
            raise ValueError('Invalid scan result')
        rows.extend(records)
    return rows


def aggregate_ranges(rows):
    """Pool existing sums/counts across requests, without recounting per-order rows."""
    groups = {}
    seen = set()
    for row in rows:
        if row['n'] != 'all':
            continue
        key = row['platform'], row['mode'], row['backend'], row['metric']
        if (*key, row['N']) in seen:
            raise ValueError('Duplicate pooled request')
        seen.add((*key, row['N']))
        groups.setdefault(key, []).append(row)
    result = []
    for (platform, mode, backend, metric), values in sorted(groups.items()):
        count = sum(r['count'] for r in values)
        if count <= 0 or any(r['invalid'] or r['status'] != 'complete' for r in values):
            raise ValueError('Invalid pooled accuracy result')
        record = dict(platform=platform, mode=mode, backend=backend, metric=metric, count=count)
        with localcontext() as ctx:
            ctx.prec = 80
            for side, rounding in (('lo', ROUND_FLOOR), ('hi', ROUND_CEILING)):
                ctx.rounding = rounding
                total = sum((Decimal(r['sum_' + side]) for r in values), Decimal(0))
                record['sum_' + side] = str(total)
                record['mean_' + side] = str(total / count)
                record['max_' + side] = str(max(Decimal(r['max_' + side]) for r in values))
        result.append(record)
    return result


def accuracy_table(rows):
    labels = {'quick': 'QUICK original', 'simint': 'Simint original', 'libintx': 'LibintX',
              'vsr': 'VSR', 'gansu': 'GANSU', 'laikov': 'Laikov',
              'fabo': 'FABO'}
    indexed = {(r['platform'], r['mode'], r['backend'], r['metric']): r for r in rows}
    def number(value):
        mantissa, exponent = f'{Decimal(value):.2e}'.split('e')
        return rf'${mantissa}\times10^{{{int(exponent)}}}$'
    lines = [r'\begin{table*}[tbp]',
             r'\caption{Maximum and mean errors pooled over all requested ranges $[0,N]$, $N=0,\ldots,12$, on the $10^{-6}$ grid over $[0,1000]$. Each mean is the sum of errors divided by the total number of returned values, $91\times1\,000\,000\,001$, not an unweighted average of the 13 range means. Thus, an output computed by different requested-range implementations is counted once for each request. Errors are measured against unrounded references; maxima and means summarize the upper reference-enclosure bounds, displayed to three significant figures. Strict and fast-math builds remain separate. CPU FABO uses native gather.}',
             r'\label{tab:function-accuracy}', r'\begingroup', r'\setlength{\tabcolsep}{3pt}',
             r'\begin{ruledtabular}', r'\begin{tabular}{llrrrrrr}',
             r'Platform / mode & Boys backend & \multicolumn{2}{c}{Absolute error} & \multicolumn{2}{c}{Relative error} & \multicolumn{2}{c}{ULP error} \\',
             r' & & Max & Mean & Max & Mean & Max & Mean \\', r'\hline']
    for i, (platform, mode) in enumerate((('cuda', 'strict'), ('cuda', 'fast'), ('cpu', 'strict'), ('cpu', 'fast'))):
        if i:
            lines.append(r'\hline')
        backends = ('quick', 'libintx', 'vsr', 'gansu', 'fabo') if platform == 'cuda' else ('simint', 'libintx', 'vsr', 'laikov', 'fabo')
        platform_label = 'GPU' if platform == 'cuda' else 'CPU'
        mode_label = 'strict' if mode == 'strict' else 'fast math'
        for j, backend in enumerate(backends):
            group = rf'\multirow{{{len(backends)}}}{{*}}{{{platform_label} / {mode_label}}}' if j == 0 else ''
            cells = [group, labels[backend]]
            for metric in ('absolute', 'relative', 'ulp'):
                record = indexed[platform, mode, backend, metric]
                cells.extend(number(record[s + '_hi']) for s in ('max', 'mean'))
            lines.append(' & '.join(cells) + r' \\')
    return '\n'.join(lines + [r'\end{tabular}', r'\end{ruledtabular}', r'\endgroup', r'\end{table*}']) + '\n'


def reference_storage(summary, include):
    """Attach each selected model's maximum per-output Taylor degree."""
    sizes = storage(summary, include)
    winners = json.loads(Path(summary).read_text())['winners']
    for row in sizes:
        degrees = winners[f"0-{row['N']}"]['degrees']
        if len(degrees) != row['N'] + 1 or any(type(p) is not int or p < 0 for p in degrees):
            raise ValueError('Invalid per-output Taylor degrees')
        row['max_taylor_degree'] = max(degrees)
    return sizes


def generate(records, figures, tables, summary, include):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    rows = load_records(records)
    sizes = reference_storage(summary, include)
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    csv_write(tables / 'results-function-accuracy.csv', rows)
    csv_write(tables / 'results-reference-storage.csv', sizes)
    (tables / 'results-function-accuracy.json').write_text(json.dumps(rows, indent=2) + '\n')
    (tables / 'results-reference-storage.json').write_text(json.dumps(sizes, indent=2) + '\n')
    pooled = aggregate_ranges(rows)
    csv_write(tables / 'results-function-accuracy-summary.csv', pooled)
    (tables / 'results-function-accuracy-summary.json').write_text(json.dumps(pooled, indent=2) + '\n')
    (tables / 'results-function-accuracy-summary.tex').write_text(accuracy_table(pooled))
    styles = {'fabo': ('FABO', '#0072B2', 'x'), 'libintx': ('LibintX', '#E69F00', 'o'),
              'vsr': ('VSR', '#009E73', 's'), 'quick': ('QUICK original', '#999999', '^'),
              'simint': ('Simint original', '#999999', '^'),
              'laikov': ('Laikov', '#CC79A7', 'D'), 'gansu': ('GANSU', '#CC79A7', 'D')}
    for mode in ('strict', 'fast'):
        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        fig.subplots_adjust(left=.1, right=.98, bottom=.13, top=.9, hspace=.95, wspace=.3)
        for i, platform in enumerate(('cuda', 'cpu')):
            backends = ('quick', 'libintx', 'vsr', 'gansu', 'fabo') if platform == 'cuda' else ('simint', 'libintx', 'vsr', 'laikov', 'fabo')
            for backend in backends:
                points = sorted((r for r in rows if (r['platform'], r['mode'], r['backend'], r['metric'], r['n']) == (platform, mode, backend, 'ulp', 'all')), key=lambda r: r['N'])
                label, color, marker = styles[backend]
                for ax, stat in zip(axes[i], ('max', 'mean')):
                    ax.plot([r['N'] for r in points], [float(r[stat + '_hi']) for r in points],
                            marker=marker, color=color, label=label, linewidth=1, markersize=4)
                    ax.set(xlabel='Requested maximum order N', ylabel=stat.capitalize() + ' ULP error', yscale='log')
                    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                    ax.grid(alpha=.2)
            axes[i, 0].axhline(1, color='#bbbbbb', linestyle='--', linewidth=.8, zorder=0)
            handles, labels = axes[i, 0].get_legend_handles_labels()
            fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.54, .505 if i == 0 else .005), ncol=5, frameon=False)
        fig.text(.54, .97, 'GPU', ha='center', fontsize=13)
        fig.text(.54, .47, 'CPU', ha='center', fontsize=13)
        fig.savefig(figures / f'results-function-accuracy-{mode}.pdf', bbox_inches='tight')
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.5, 3.7))
    n = [r['N'] for r in sizes]
    ax.stackplot(n, [r['main_bytes']/1024 for r in sizes], [r['tail_bytes']/1024 for r in sizes],
                 labels=['Main table', 'Tail table'], colors=['#0072B2', '#E69F00'], alpha=.85)
    ax.axhline(1024, color='gray', linestyle='--', label='1 MiB budget')
    ax.set(xlabel='Requested maximum order N', ylabel='Reference storage (KiB)', xlim=(0, 24), ylim=(0, 1280))
    degree_ax = ax.twinx()
    degrees = [r['max_taylor_degree'] for r in sizes]
    degree_ax.plot(n, degrees, color='#222222', marker='o', markersize=3.5,
                   markerfacecolor='white', linewidth=1.2, label='Max. Taylor degree')
    degree_ax.set(ylabel='Maximum Taylor degree', ylim=(min(degrees)-.5, max(degrees)+.5))
    degree_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    handles, labels = ax.get_legend_handles_labels()
    degree_handles, degree_labels = degree_ax.get_legend_handles_labels()
    fig.legend(handles+degree_handles, labels+degree_labels, ncol=2,
               loc='upper center', frameon=False)
    fig.tight_layout(rect=(0, 0, 1, .86))
    fig.savefig(figures / 'results-reference-storage.pdf')
    plt.close(fig)
    sources = [summary, Path(__file__)] + [records / p / f for p in ('cpu', 'cuda') for f in ('accuracy.json', 'complete.json', 'download-manifest.json', 'run.json', 'execution.json', 'built.json', 'scan.build.json')]
    (tables / 'results-function-provenance.json').write_text(json.dumps(
        dict(sources={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
             plotted='Pooled per-request strict/fast ULP error upper bounds; native CPU gather',
             summary='Maximum and sum/count mean across all requests; each returned value has equal weight',
             storage='Packed main+tail arrays, including corrections and row padding; right axis is max(degrees) for each selected [0,N] model'), indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=Path('data/benchmarks/function-accuracy-20261107'))
    parser.add_argument('--figures', type=Path, default=Path('overleaf-paper2/figure'))
    parser.add_argument('--tables', type=Path, default=Path('overleaf-paper2/tables'))
    parser.add_argument('--summary', type=Path, default=Path('data/numerical/paired-1ulp/summary.json'))
    parser.add_argument('--include', type=Path, default=Path('include'))
    a = parser.parse_args()
    generate(a.records, a.figures, a.tables, a.summary, a.include)

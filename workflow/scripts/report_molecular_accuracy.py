"""Export molecular differences from completed GPU mean and CPU reference records."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

if __package__:
    from .record_manifest import verify_manifest
else:
    from record_manifest import verify_manifest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(gpu, cpu):
    verify_manifest(gpu / 'molecular-means.json')
    verify_manifest(cpu / 'matrix-absolute.json')
    gpu_completion = json.loads((gpu / 'complete.json').read_text())
    means = json.loads((gpu / 'molecular-means.json').read_text())
    if means.get('schema') != 2 or means['identity'] != gpu_completion['identity'] or means['summary_sha256'] != gpu_completion['summary_sha256'] or means['rounds'] != 5:
        raise ValueError('GPU mean reduction is not from the selected run')
    cpu_completion = json.loads((cpu / 'complete.json').read_text())
    if sha(cpu / 'reference-summary.json') != cpu_completion['reference_summary_sha256']:
        raise ValueError('CPU reference checksum mismatch')
    cpu_report = json.loads((cpu / 'matrix-absolute.json').read_text())
    if cpu_report.get('schema') != 2 or cpu_report['reference_summary_sha256'] != cpu_completion['reference_summary_sha256']:
        raise ValueError('CPU matrix reduction is not from the selected reference report')
    rows = []
    for case in means['cases']:
        for backend, metrics in case['backends'].items():
            if any(metrics[m + '_elements'] != case['dimensions'] ** 2 for m in ('fock', 'density')):
                raise ValueError('GPU mean does not cover the complete matrix')
            rows.append(dict(platform='GPU', case=case['case']['id'], backend=backend,
                             energy=metrics['energy_abs_difference'], fock=metrics['fock_max_absolute'],
                             density=metrics['density_max_absolute'],
                             fock_mean_absolute=metrics['fock_mean_absolute'],
                             density_mean_absolute=metrics['density_mean_absolute']))
    for row in cpu_report['results']:
        if not row['bitwise_reproducible']:
            raise ValueError('CPU repeatability check failed')
        if row['backend'] == 'reference':
            continue
        rows.append(dict(platform='CPU', case=row['case']['id'], backend=row['backend'],
                         energy=abs(row['energy_difference']), fock=row['fock']['max_absolute'],
                         density=row['density']['max_absolute'],
                         fock_mean_absolute=row['fock']['mean_absolute'],
                         density_mean_absolute=row['density']['mean_absolute']))
    expected = {'GPU': {'official', 'libintx_gpu', 'vsr', 'gansu', 'fabo_additive'},
                'CPU': {'original', 'libintx', 'vsr', 'laikov', 'fabo'}}
    for platform, backends in expected.items():
        subset = [r for r in rows if r['platform'] == platform]
        cases = {r['case'] for r in subset}
        keys = {(r['case'], r['backend']) for r in subset}
        if len(subset) != 60 or len(cases) != 12 or keys != {(c, b) for c in cases for b in backends}:
            raise ValueError('Incomplete or duplicate accuracy coverage')
    if not all(math.isfinite(r[k]) and r[k] >= 0 for r in rows for k in ('energy', 'fock', 'density', 'fock_mean_absolute', 'density_mean_absolute')):
        raise ValueError('Invalid molecular difference')
    if any(r[m + '_mean_absolute'] > r[m] * (1 + 1e-14) for r in rows for m in ('fock', 'density')):
        raise ValueError('Mean absolute difference exceeds maximum')
    return rows, means


def scientific(value):
    if value == 0:
        return '$0$'
    mantissa, exponent = f'{value:.2e}'.split('e')
    return rf'${mantissa}\times10^{{{int(exponent)}}}$'


def molecular_figure(maxima, groups):
    """Plot the same unrounded casewise maxima used by the summary table."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, NullLocator

    colors = ('#999999', '#E69F00', '#009E73', '#CC79A7', '#0072B2')
    panels = (
        ('Energy', ('energy',), (r'$\max|\Delta E|$',), 'Absolute difference (hartree)'),
        ('Fock matrix', ('fock', 'fock_mean_absolute'),
         (r'$\max|\Delta F|$', r'$\mathrm{mean}|\Delta F|$'), 'Absolute difference (hartree)'),
        ('Density matrix', ('density', 'density_mean_absolute'),
         (r'$\max|\Delta P|$', r'$\mathrm{mean}|\Delta P|$'), 'Absolute difference (dimensionless)'),
    )
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 6.8))
    fig.subplots_adjust(left=.08, right=.985, top=.89, bottom=.13, wspace=.42, hspace=1.05)
    indexed = {(r['platform'], r['backend']): r for r in maxima}
    for row, (platform, backends) in enumerate(groups):
        for ax, (title, metrics, labels, units) in zip(axes[row], panels):
            values = [indexed[platform, backend][m] for backend, _ in backends for m in metrics]
            if not all(math.isfinite(v) and v > 0 for v in values):
                raise ValueError('Logarithmic molecular chart requires positive finite differences')
            for j, ((backend, label), color) in enumerate(zip(backends, colors)):
                positions = [i + (j - 2) * .15 for i in range(len(metrics))]
                ax.bar(positions, [indexed[platform, backend][m] for m in metrics],
                       width=.14, color=color, label=label, zorder=3)
            ax.set_yscale('log')
            ax.set_ylim(10 ** (math.floor(math.log10(min(values))) - 1),
                        10 ** math.ceil(math.log10(max(values))))
            ax.yaxis.set_major_locator(LogLocator(base=10, numticks=5))
            ax.yaxis.set_minor_locator(NullLocator())
            ax.set_xticks(range(len(metrics)), labels)
            ax.set_title(title, fontsize=11)
            ax.set_ylabel(units, fontsize=9)
            ax.tick_params(labelsize=9)
            ax.grid(axis='y', alpha=.25, zorder=0)
            ax.spines[['top', 'right']].set_visible(False)
        handles, labels = axes[row, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.53, .505 if row == 0 else .01),
                   ncol=5, frameon=False, fontsize=10)
    fig.text(.53, .97, 'QUICK (GPU)', ha='center', fontsize=13)
    fig.text(.53, .47, 'NWChem–Simint (CPU)', ha='center', fontsize=13)
    return fig


def generate(gpu, cpu, output, figures=None):
    rows, means = load(gpu, cpu)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'results-molecular-differences.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    groups = [('GPU', [('official', 'QUICK original'), ('libintx_gpu', 'LibintX'), ('vsr', 'VSR'),
                       ('gansu', 'GANSU'), ('fabo_additive', 'FABO')]),
              ('CPU', [('original', 'Simint original'), ('libintx', 'LibintX'), ('vsr', 'VSR'),
                       ('laikov', 'Laikov'), ('fabo', 'FABO')])]
    lines = [r'\begin{table*}[tbp]',
             r'\caption{Absolute differences from the correctly rounded Boys backend. Each column reports the largest casewise value across the 12 molecule--basis cases in the application. GPU differences compare five-run mean energies and elementwise mean matrices; CPU outputs were bitwise reproducible across repetitions. Here $\Delta F$ and $\Delta P$ denote elementwise differences in the Fock and updated density matrices; maxima and means are taken over matrix entries. The matrix mean includes all entries, including zeros and both symmetric halves. Energy and Fock-matrix differences are in hartree; density-matrix coefficients are dimensionless. The maximizing case may differ between columns; these are not averages pooled across cases. CPU and GPU use different stack sizes and integral engines, so the two groups are not a cross-platform accuracy ranking.}',
             r'\label{tab:molecular-differences}', r'\begin{ruledtabular}',
             r'\begin{tabular}{llrrrrr}',
             r'Application & Boys backend & $\max|\Delta E|$ & $\max|\Delta F|$ & $\operatorname{mean}|\Delta F|$ & $\max|\Delta P|$ & $\operatorname{mean}|\Delta P|$ \\', r'\hline']
    maxima = []
    for i, (platform, backends) in enumerate(groups):
        if i:
            lines.append(r'\hline')
        application = 'QUICK (GPU)' if platform == 'GPU' else 'NWChem--Simint (CPU)'
        for j, (backend, label) in enumerate(backends):
            subset = [r for r in rows if (r['platform'], r['backend']) == (platform, backend)]
            maximum = dict(platform=platform, backend=backend)
            for metric in ('energy', 'fock', 'density', 'fock_mean_absolute', 'density_mean_absolute'):
                witness = max(subset, key=lambda r: r[metric])
                maximum[metric] = witness[metric]
                maximum[metric + '_case'] = witness['case']
            maxima.append(maximum)
            application_cell = rf'\multirow{{{len(backends)}}}{{*}}{{{application}}}' if j == 0 else ''
            lines.append(' & '.join([application_cell, label, *(scientific(maximum[m]) for m in ('energy', 'fock', 'fock_mean_absolute', 'density', 'density_mean_absolute'))]) + r' \\')
    lines += [r'\end{tabular}', r'\end{ruledtabular}', r'\end{table*}']
    (output / 'results-molecular-differences.tex').write_text('\n'.join(lines) + '\n')
    metadata = dict(gpu_identity=means['identity'], gpu_mean_report_sha256=sha(gpu / 'molecular-means.json'),
                    cpu_reference_report_sha256=sha(cpu / 'reference-summary.json'),
                    cpu_matrix_report_sha256=sha(cpu / 'matrix-absolute.json'),
                    gpu_reduction_manifest_sha256=sha(gpu / 'molecular-means.manifest.json'),
                    cpu_reduction_manifest_sha256=sha(cpu / 'matrix-absolute.manifest.json'),
                    manifest_helper_sha256=sha(Path(__file__).with_name('record_manifest.py')),
                    generator_sha256=sha(Path(__file__)), maxima=maxima,
                    gpu_reference_variability={metric: max(c['reference_matrix_sd_max'][metric] for c in means['cases']) for metric in ('fock', 'density')})
    (output / 'results-molecular-provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    if figures is not None:
        figures.mkdir(parents=True, exist_ok=True)
        fig = molecular_figure(maxima, groups)
        import matplotlib.pyplot as plt
        fig.savefig(figures / 'results-molecular-differences.pdf', bbox_inches='tight')
        plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu', type=Path, required=True)
    parser.add_argument('--cpu', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, help='Also generate the molecular-difference bar chart')
    args = parser.parse_args()
    generate(args.gpu, args.cpu, args.output, args.figures)

import numpy as np
import pytest
import json
import shutil
from pathlib import Path

from workflow.scripts.quick_molecular_means import BACKENDS, mean_difference, reduce_case, sha
from workflow.scripts.report_molecular_accuracy import generate, load, scientific, molecular_figure
from workflow.scripts.molecular_metrics import MatrixMetrics
from workflow.scripts.record_manifest import write_manifest, verify_manifest


def test_reduction_manifest_roundtrip_and_corruption(tmp_path):
    report = tmp_path / 'result.json'
    report.write_text('{"energy": 0.0}\n')
    write_manifest(report)
    verify_manifest(report)
    report.write_text('{"energy": 1.0}\n')
    with pytest.raises(ValueError, match='checksum'):
        verify_manifest(report)


@pytest.mark.parametrize('platform', ['cpu', 'gpu'])
@pytest.mark.parametrize('change', ['value', 'missing_manifest', 'missing_checksum'])
def test_molecular_export_rejects_changed_reduction(tmp_path, platform, change):
    root = Path(__file__).resolve().parents[2] / 'data/benchmarks'
    gpu, cpu = root / 'quick-fixed-density-20261106', root / 'nwchem-fixed-density-20261106'
    source = gpu if platform == 'gpu' else cpu
    folder = tmp_path / platform
    shutil.copytree(source, folder)
    name = 'molecular-means.json' if platform == 'gpu' else 'matrix-absolute.json'
    report = folder / name
    if change == 'value':
        data = json.loads(report.read_text())
        if platform == 'gpu':
            data['cases'][0]['backends']['official']['energy_abs_difference'] = 1.0
        else:
            data['results'][0]['energy_difference'] = 1.0
        report.write_text(json.dumps(data))
    elif change == 'missing_manifest':
        report.with_suffix('.manifest.json').unlink()
    else:
        report.with_suffix('.manifest.json').write_text('{"schema": 1, "files": {}}')
    with pytest.raises((ValueError, FileNotFoundError)):
        load(folder if platform == 'gpu' else gpu, folder if platform == 'cpu' else cpu)


def test_difference_of_means_not_maximum_repetition_difference():
    hi = np.array([1., 2.])
    lo = np.zeros(2)
    values = [hi + np.array([d, -d]) for d in (-0.5, 0.5, -0.25, 0.25, 0.)]
    np.testing.assert_array_equal(mean_difference(values, hi, lo), np.zeros(2))


def test_centered_mean_preserves_sub_ulp_reference_offset():
    hi = np.array([1.])
    lo = np.array([2. ** -55])
    values = [hi.copy() for _ in range(5)]
    np.testing.assert_array_equal(mean_difference(values, hi, lo), -lo)


def test_nonfinite_output_rejected():
    with pytest.raises(ValueError):
        mean_difference([np.array([np.nan])], np.array([1.]), np.array([0.]))


def test_matrix_absolute_mean_includes_zero_entries():
    metrics = MatrixMetrics()
    metrics.add(np.array([0., -2.]))
    metrics.add(np.array([0., 6.]))
    assert metrics.finish() == dict(max_absolute=6., mean_absolute=2., elements=4)


def test_zero_matrix_has_zero_absolute_statistics():
    metrics = MatrixMetrics()
    metrics.add(np.zeros(7))
    assert metrics.finish() == dict(max_absolute=0., mean_absolute=0., elements=7)


def test_empty_matrix_reduction_rejected():
    with pytest.raises(ValueError, match='Empty matrix'):
        MatrixMetrics().finish()


def test_scientific_table_format():
    assert scientific(1e-9) == r'$1.00\times10^{-9}$'
    assert scientific(0) == '$0$'


def test_archived_mean_metrics_and_complete_coverage():
    root = Path(__file__).resolve().parents[2] / 'data/benchmarks'
    gpu, cpu = root / 'quick-fixed-density-20261106', root / 'nwchem-fixed-density-20261106'
    rows, _ = load(gpu, cpu)
    assert len(rows) == 120
    old = {c['case']['id']: c for c in json.loads((gpu / 'summary.json').read_text())['cases']}
    for row in rows:
        if row['platform'] != 'GPU':
            continue
        for metric in ('fock', 'density'):
            bound = old[row['case']]['variants'][row['backend']]['max_matrix_difference_from_reference_mean'][metric]
            assert row[metric] <= bound * (1 + 1e-12) + 1e-30


def test_merged_table_contains_all_five_statistics(tmp_path):
    root = Path(__file__).resolve().parents[2] / 'data/benchmarks'
    generate(root / 'quick-fixed-density-20261106', root / 'nwchem-fixed-density-20261106', tmp_path)
    table = (tmp_path / 'results-molecular-differences.tex').read_text()
    assert r'$\max|\Delta E|$' in table
    for matrix in ('F', 'P'):
        assert rf'$\max|\Delta {matrix}|$' in table
        assert rf'$\operatorname{{mean}}|\Delta {matrix}|$' in table
    assert r'\multirow{5}{*}{QUICK (GPU)}' in table
    assert r'\multirow{5}{*}{NWChem--Simint (CPU)}' in table
    assert table.count(r'\times10') == 50
    assert not (tmp_path / 'results-molecular-mean-differences.tex').exists()


def test_chart_preserves_all_table_values(tmp_path):
    root = Path(__file__).resolve().parents[2] / 'data/benchmarks'
    generate(root / 'quick-fixed-density-20261106', root / 'nwchem-fixed-density-20261106', tmp_path)
    maxima = json.loads((tmp_path / 'results-molecular-provenance.json').read_text())['maxima']
    groups = [(platform, [(r['backend'], r['backend']) for r in maxima if r['platform'] == platform])
              for platform in ('GPU', 'CPU')]
    fig = molecular_figure(maxima, groups)
    import matplotlib.pyplot as plt
    try:
        metrics = [('energy',), ('fock', 'fock_mean_absolute'), ('density', 'density_mean_absolute')]
        for row, (platform, _) in enumerate(groups):
            records = [r for r in maxima if r['platform'] == platform]
            for col, fields in enumerate(metrics):
                ax = fig.axes[row * 3 + col]
                assert ax.get_yscale() == 'log'
                assert [p.get_height() for p in ax.patches] == [r[m] for r in records for m in fields]
        assert sum(len(ax.patches) for ax in fig.axes) == 50
    finally:
        plt.close(fig)


def test_complete_matrix_reduction_and_checksums(tmp_path):
    cid, identity, n = 'synthetic', 'test-identity', 2
    hi = np.array([1.] * 4 + [2.] * 4, dtype='<f8')
    lo = np.full(8, 2. ** -55, dtype='<f8')
    ref = tmp_path / 'reports' / cid / 'reference-mean'
    ref.mkdir(parents=True)
    for name, value in (('hi', hi), ('lo', lo)):
        (ref / f'{name}.bin').write_bytes(value.tobytes())
    (ref / 'layout.json').write_text(json.dumps(dict(dimensions=[2, n, n],
        files={name + '.bin': sha(ref / (name + '.bin')) for name in ('hi', 'lo')})))
    for backend in BACKENDS:
        for r in range(5):
            folder = tmp_path / 'samples' / cid / f'{r:02d}' / backend
            folder.mkdir(parents=True)
            (folder / 'outputs.bin').write_bytes((hi + (r - 2) * 0.125).tobytes())
            (folder / 'result.json').write_text(json.dumps(dict(variant=backend, round=r,
                case=cid, fixture_sha256='same-input', energy_hartree=1.0)))
            (folder / 'complete.json').write_text(json.dumps(dict(identity=identity,
                files={name: sha(folder / name) for name in ('outputs.bin', 'result.json')})))
    variants = {b: dict(energy_mean=1.0, energy_mean_difference=0.0) for b in BACKENDS}
    variants['reference'] = dict(energy_sd=0.0)
    case = dict(case=dict(id=cid), dimensions=[n, n, 2], identity=identity, rounds=5,
                variants=variants, reference_matrix_sd_max=dict(fock=0., density=0.))
    result = reduce_case(tmp_path, case, identity)
    # Compare to the same centered calculation: here large synthetic differences
    # can round away part of lo, unlike the small real differences.
    expected = float(np.max(np.abs(mean_difference([hi + (r - 2) * .125 for r in range(5)], hi, lo))))
    for metrics in result['backends'].values():
        assert metrics['fock_max_absolute'] == expected
        assert metrics['density_max_absolute'] == expected
        assert metrics['fock_mean_absolute'] == expected
        assert metrics['density_mean_absolute'] == expected
        assert metrics['fock_elements'] == metrics['density_elements'] == 4
    path = tmp_path / 'samples' / cid / '00' / BACKENDS[0] / 'outputs.bin'
    path.write_bytes(hi.tobytes())
    with pytest.raises(ValueError, match='checksum'):
        reduce_case(tmp_path, case, identity)

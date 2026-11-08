import json
import shutil
import pytest
from pathlib import Path
from decimal import Decimal, localcontext

from workflow.scripts.report_function_accuracy import load_records, aggregate_ranges, accuracy_table, verify_provenance
from workflow.library_accuracy.core import storage


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('platform', ['cpu', 'cuda'])
@pytest.mark.parametrize('name', ['run.json', 'execution.json', 'built.json', 'scan.build.json'])
def test_accuracy_provenance_rejects_changed_metadata(tmp_path, platform, name):
    source = ROOT / 'data/benchmarks/function-accuracy-20261107' / platform
    shutil.copytree(source, tmp_path / platform)
    folder = tmp_path / platform
    complete = json.loads((folder / 'complete.json').read_text())
    verify_provenance(folder, complete)
    (folder / name).write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        verify_provenance(folder, complete)


def test_accuracy_provenance_rejects_mismatched_run_identity():
    folder = ROOT / 'data/benchmarks/function-accuracy-20261107/cpu'
    complete = json.loads((folder / 'complete.json').read_text())
    complete['identity'] = 'other-run'
    with pytest.raises(ValueError, match='identity'):
        verify_provenance(folder, complete)


def test_range_pooling_weights_returned_values_and_ignores_duplicate_detail():
    rows = [dict(platform='cpu', mode='strict', backend='fabo', metric='ulp', n='all',
                 N=n, count=count, invalid=0, status='complete', sum_lo=str(total), sum_hi=str(total),
                 max_lo=str(maximum), max_hi=str(maximum))
            for n, count, total, maximum in [(0, 2, 2, 1), (1, 4, 12, 4)]]
    result = aggregate_ranges(rows + [dict(rows[0], n=0)])[0]
    assert result['count'] == 6
    with localcontext() as ctx:
        ctx.prec = 100
        assert Decimal(result['mean_lo']) * 6 <= 14 <= Decimal(result['mean_hi']) * 6
    assert float(result['mean_hi']) != 2  # Unweighted average of range means.
    assert result['max_hi'] == '4'


def test_summary_table_omits_duplicate_loading_policy_but_preserves_records():
    rows = aggregate_ranges(load_records(ROOT / 'data/benchmarks/function-accuracy-20261107'))
    assert len(rows) == 22 * 3
    assert {r['count'] for r in rows} == {91 * 1000000001}
    table = accuracy_table(rows)
    assert table.count(r'\times10') == 20 * 6
    assert 'software' not in table
    assert table.count(r'\multirow{5}') == 4
    assert sum(r['backend'] == 'fabo_software' for r in rows) == 6
    for r in rows:
        assert Decimal(r['mean_lo']) <= Decimal(r['mean_hi']) <= Decimal(r['max_hi'])


def test_manuscript_function_accuracy_numbers():
    rows = load_records(ROOT / 'data/benchmarks/function-accuracy-20261107')
    for platform, backend in [('cpu', 'fabo'), ('cpu', 'fabo_software'), ('cuda', 'fabo')]:
        for mode in ('strict', 'fast'):
            values = [r for r in rows if (r['platform'], r['backend'], r['mode'], r['n']) == (platform, backend, mode, 'all')]
            ulp = [r for r in values if r['metric'] == 'ulp']
            worst = max(ulp, key=lambda r: Decimal(r['max_hi']))
            assert (worst['N'], worst['witness_n'], worst['witness_x']) == (3, 3, 45.382793)
            assert f"{float(worst['max_hi']):.6f}" == '1.066925'
            assert f"{min(float(r['mean_hi']) for r in ulp):.6f}" == '0.250027'
            assert f"{max(float(r['mean_hi']) for r in ulp):.6f}" == '0.250167'
            for metric, expected in [('absolute', '7.67486e-17'), ('relative', '1.86698e-16')]:
                assert f"{max(float(r['max_hi']) for r in values if r['metric'] == metric):.5e}" == expected


def test_manuscript_storage_matches_generated_models():
    rows = storage(ROOT / 'data/numerical/paired-1ulp/summary.json', ROOT / 'include')
    expected = {0: '249.422', 4: '941.703', 8: '771.500', 12: '1023.258', 24: '946.688'}
    for row in rows:
        assert row['total_bytes'] <= 1048576
        assert row['total_bytes'] == sum(row[k] for k in ('coefficient_bytes', 'correction_bytes', 'padding_bytes'))
        if row['N'] in expected:
            assert f"{row['total_bytes']/1024:.3f}" == expected[row['N']]

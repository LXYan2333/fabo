import json
from pathlib import Path
import statistics

from workflow.scripts.plot_nwchem_performance import BACKENDS, SYSTEMS, load_records
from workflow.scripts.plot_quick_performance import timing_table


RECORDS = Path(__file__).resolve().parents[2] / 'data/benchmarks/nwchem-fixed-density-20261106'


def test_means_use_jk_observations_not_full_fock_or_medians():
    rows = load_records(RECORDS)
    raw = json.loads((RECORDS / 'results.json').read_text())
    assert len(rows) == 60
    for row in rows:
        samples = [r for r in raw if (r['case'], r['backend']) == (row['case'], row['backend'])]
        times = [float(r['jk_seconds']) for r in samples]
        assert row['mean_seconds'] == statistics.mean(times)
        assert row['sd_seconds'] == statistics.stdev(times)
        assert row['mean_seconds'] != statistics.mean(float(r['fock_seconds']) for r in samples)


def test_cpu_table_full_coverage_and_trailing_zeros():
    rows = [dict(r, mean_seconds=2.0) for r in load_records(RECORDS)]
    table = timing_table(rows, backends=BACKENDS, systems=SYSTEMS, engine='NWChem--Simint',
                         scope='two-electron Fock-build', figure_prefix='cpu')
    assert table.count('2.000') == 60
    assert 'Laikov' in table and 'GANSU' not in table
    assert 'tab:cpu-fock-times' in table
    assert r'$8\times$ water dimer' in table and r'$1\times$ pentane dimer' in table

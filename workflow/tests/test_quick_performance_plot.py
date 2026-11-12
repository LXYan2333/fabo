import json
from pathlib import Path
import shutil
import statistics

import pytest

from workflow.scripts.plot_quick_performance import digest, load_records, timing_table


RECORDS = Path(__file__).resolve().parents[2] / 'data/benchmarks/quick-fixed-density-20261106'


def test_means_use_all_original_samples():
    identity, rows = load_records(RECORDS)
    raw = json.loads((RECORDS / 'summary.json').read_text())
    assert identity == raw['identity']
    assert len(rows) == 60
    source = {c['case']['id']: c for c in raw['cases']}
    for row in rows:
        samples = source[row['case']]['variants'][row['backend']]['timing']['fock_seconds']['samples']
        assert row['mean_seconds'] == statistics.mean(samples)
        assert row['sd_seconds'] == statistics.stdev(samples)
        assert row['repetitions'] == 5


def test_table_preserves_three_decimal_places():
    _, rows = load_records(RECORDS)
    rows = [dict(row, mean_seconds=1.0) for row in rows]
    table = timing_table(rows)
    assert table.count('1.000') == 60
    assert table.count(' & ') == 13 * 6  # header plus twelve complete rows
    assert r'$128\times$ water dimer' in table
    assert 'Molecule & Basis' in table
    assert 'Dimer stack' not in table and 'parentheses' not in table


@pytest.mark.parametrize('repair_checksum', [False, True])
def test_changed_or_incomplete_data_rejected(tmp_path, repair_checksum):
    for name in ('summary.json', 'complete.json', 'reuse.json', 'execution-repair.json'):
        shutil.copyfile(RECORDS / name, tmp_path / name)
    raw = json.loads((tmp_path / 'summary.json').read_text())
    raw['cases'][0]['variants']['official']['timing']['fock_seconds']['samples'].pop()
    (tmp_path / 'summary.json').write_text(json.dumps(raw))
    if repair_checksum:
        complete = json.loads((tmp_path / 'complete.json').read_text())
        complete['summary_sha256'] = digest(tmp_path / 'summary.json')
        (tmp_path / 'complete.json').write_text(json.dumps(complete))
    with pytest.raises(ValueError, match='Invalid timing samples' if repair_checksum else 'Checksum mismatch'):
        load_records(tmp_path)

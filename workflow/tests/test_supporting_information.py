from pathlib import Path
import csv
import hashlib
import json
import os

import pytest


@pytest.fixture
def si_root():
    """The SI is a separate, locally ignored checkout, not a test dependency."""
    configured = os.environ.get('FABO_SI_ROOT')
    root = Path(configured) if configured else Path(__file__).resolve().parents[2] / 'overleaf-si'
    if not (root / 'data-manifest.json').is_file() or not (root / 'data').is_dir():
        if configured:
            pytest.fail(f'FABO_SI_ROOT is not an unpacked SI package: {root}')
        pytest.skip('Optional SI archive unavailable; unpack data.zip and set FABO_SI_ROOT')
    return root


def test_export_integrity(si_root):
    root=si_root
    manifest=json.loads((root/'data-manifest.json').read_text())
    assert manifest
    for name,digest in manifest.items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name


def test_coverage_and_budget(si_root):
    root=si_root/'data'
    def rows(name):
        with (root/name).open() as stream:
            return list(csv.DictReader(stream))
    models=rows('models.csv')
    assert {int(r['N']) for r in models}==set(range(25))
    table=(si_root/'tables/models.tex').read_text()
    for r in models:
        assert f"{r['N']} & {r['highest_order']} & {r['main_bits']} & {r['tail_bits']} & {r['main_rows']}" in table
    for r in models:
        assert int(r['main_bytes'])+int(r['tail_bytes'])==int(r['total_bytes'])<=1048576
        assert len(r['degrees'].split(';'))==int(r['N'])+1
    timings=rows('timing-observations.csv')
    assert len(timings)==600
    assert len({(r['platform'],r['case'],r['backend'],r['repetition']) for r in timings})==600
    assert len(rows('timing-summary.csv'))==120
    import statistics
    for r in rows('timing-summary.csv'):
        values=[float(v['seconds']) for v in timings if all(v[k]==r[k] for k in ('platform','case','backend'))]
        assert len(values)==5
        assert statistics.mean(values)==float(r['mean_seconds'])
        assert statistics.stdev(values)==float(r['sd_seconds'])
    assert len(rows('molecular-differences.csv'))==120
    ratios=rows('geometric-speedups.csv')
    assert len(ratios)==8
    assert round(min(float(r['speedup_percent']) for r in ratios),2)==1.22
    assert round(max(float(r['speedup_percent']) for r in ratios),2)==10.67


def test_retrieved_input_hashes(si_root):
    root=si_root/'data/application-inputs'
    quick=list((root/'quick/samples').glob('*/00/official/input.in'))
    cpu=list((root/'nwchem/measurements').glob('*/0-original/input.nw'))
    assert len(quick)==len(cpu)==12
    for p in quick+cpu:
        manifest=json.loads(p.with_name('complete.json').read_text())
        entries=manifest.get('files',manifest)
        assert hashlib.sha256(p.read_bytes()).hexdigest()==entries[p.name]


def test_reference_recipe_and_workload_map(si_root):
    import struct
    root=si_root/'data'
    header=json.loads((root/'application-inputs/accuracy-reference-header.json').read_text())
    assert struct.unpack('<QIIIQdd',bytes.fromhex(header['header_hex']))==(1,12,24,256,4000,0.25,1000.0)
    for platform in ('cpu','cuda'):
        recipe=json.loads((root/f'records/benchmarks/function-accuracy-20261107/{platform}/run.json').read_text())['recipe']
        assert recipe['reference_sha256']==header['table_sha256_from_completed_cpu_and_cuda_recipes']
        for path,digest in recipe['sources'].items():
            copied=root/'methods/function-accuracy'/path
            assert hashlib.sha256(copied.read_bytes()).hexdigest()==digest
    rows=list(csv.DictReader((root/'workloads.csv').open()))
    assert len(rows)==24
    for row in rows:
        assert row['dimension']==row['rank']
        assert int(row['electrons'])%2==0
        for key in ('input','geometry','basis_file'):
            assert (root.parent/row[key]).is_file(),row[key]


def test_backend_names():
    from workflow.scripts.export_supporting_information import backend_name
    assert backend_name('official')=='QUICK'
    assert backend_name('original')=='Simint'
    assert backend_name('fabo_additive')=='FABO'


def test_readable_generated_tables(si_root):
    for name in ('timings-CPU','timings-GPU','molecular-CPU','molecular-GPU'):
        text=(si_root/f'tables/{name}.tex').read_text()
        assert r'\newpage' not in text
        assert r'fabo\_additive' not in text
        assert r'libintx\_gpu' not in text


def test_table_generation(tmp_path):
    from workflow.scripts.export_supporting_information import table
    path = tmp_path/'table.tex'
    table(path, 'Caption', ['Case', 'Backend'], [('case_1', 'A&B')])
    text = path.read_text()
    assert r'\Needspace{8\baselineskip}' in text
    assert text.count(r'\label{tab:table}') == 1
    assert r'case\_1 & A\&B' in text
    assert r'\endfirsthead' in text and r'\endhead' in text
    table(path, 'Caption', ['Case', 'Backend'],
          [(f'case_{case}', str(backend)) for case in range(12) for backend in range(5)])
    text = path.read_text()
    assert text.count(r'\\*') == 48
    assert text.count(r'\label{tab:table}') == 1
    assert r'\newpage' not in text and r'\Needspace' not in text
    table(path, 'Caption', ['Molecule', 'Basis', 'Backend'],
          [(f'molecule_{case//3}', f'basis_{case%3}', str(backend))
           for case in range(12) for backend in range(5)], group_columns=2)
    assert path.read_text().count(r'\\*') == 48

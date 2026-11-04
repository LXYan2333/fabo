from pathlib import Path

from workflow.quick.branch_probe import archived_command, config_header, patch, settings


def test_archived_imports_ignore_cached_current_packages(tmp_path):
    import subprocess
    import workflow.quick.calibrate as current
    package=tmp_path/'bundle/workflow/quick'
    package.mkdir(parents=True)
    for path in (package.parent/'__init__.py',package/'__init__.py'):
        path.write_text('')
    (package/'calibrate.py').write_text('SOURCE="archived"\n')
    script=tmp_path/'check.py'
    script.write_text('from workflow.quick import calibrate\nprint(calibrate.SOURCE)\n')
    result=subprocess.run(archived_command(tmp_path,script,[]),capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='archived'
    assert not hasattr(current,'SOURCE')


def test_threshold_grid():
    data = settings()
    assert data['thresholds'] == sorted(set(data['thresholds']))
    assert {0., 117., 1000., 1e7, 1e10} <= set(data['thresholds'])
    assert data['histogram_edges'][0] == 1.
    assert '#define FABO_FAMILY_DOMAIN_END 0x1.312d000000000p+23' in config_header(data)


def test_diagnostic_patch_preserves_evaluator_and_scopes_fock(tmp_path):
    gpu = tmp_path/'src/gpu'; gpu.mkdir(parents=True)
    (gpu/'additive_binding.cuh').write_text('#include "additive_boys.cuh"\n  using Model = typename FaboQuickFamily<FamilyMax>::Model;\n  original_evaluate();\n')
    (gpu/'probe_runtime.h').write_text('#include <time.h>\n')
    module = tmp_path/'src/modules/quick_scf_module.f90'
    module.parent.mkdir()
    module.write_text('setup\n      call scf_operator(.false.)\n      call fabo_probe_sync()\ndiagonalize\n')
    root = Path(__file__).resolve().parents[3]
    patch(tmp_path, root/'benchmark/quick/family_probe.h', settings())
    text = (gpu/'additive_binding.cuh').read_text()
    assert text.index('FaboObserveFamily') < text.index('original_evaluate')
    assert 'original_evaluate();' in text
    assert module.read_text() == 'setup\n      call fabo_warp_begin()\n      call scf_operator(.false.)\n      call fabo_probe_sync()\n      call fabo_warp_end()\ndiagonalize\n'

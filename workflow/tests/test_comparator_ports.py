import hashlib
import json
from pathlib import Path
import shutil

import pytest

from workflow.comparator_ports import CPU_PORTS, PORT_REVISION, copy_cpu_ports


def test_retained_snapshot_and_plain_directory_copy(tmp_path):
    # A source distribution without .git must be sufficient.
    source = tmp_path / 'source'
    shutil.copytree(CPU_PORTS, source)
    manifest = json.loads((source / 'manifest.json').read_text())
    assert manifest['origin_revision'] == PORT_REVISION
    assert len(manifest['files']) == 23
    for name in ('laikov_global_approximation/boys.h',
                 'vikhamar_sandberg_repisky_minimax/source/boys.h',
                 'vikhamar_sandberg_repisky_minimax/source/coefficients.h'):
        assert name in manifest['files']
    (source / 'unrelated.txt').write_text('not a source input')
    destination = copy_cpu_ports(tmp_path / 'copy', source=source, revision='728ec72')
    assert not (destination / 'unrelated.txt').exists()
    assert {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()} == set(manifest['files']) | {'manifest.json'}
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('revision', ['', '728', 'different', 123])
def test_reject_different_revision(tmp_path, revision):
    with pytest.raises(ValueError, match='revision'):
        copy_cpu_ports(tmp_path / 'copy', revision=revision)
    assert not (tmp_path / 'copy').exists()


@pytest.mark.parametrize('damage', ['change', 'missing', 'symlink'])
def test_reject_damaged_snapshot_before_copy(tmp_path, damage):
    source = tmp_path / 'source'
    shutil.copytree(CPU_PORTS, source)
    path = source / 'laikov_global_approximation/boys.h'
    if damage == 'change':
        path.write_text('changed')
    else:
        path.unlink()
        if damage == 'symlink':
            path.symlink_to(CPU_PORTS / 'laikov_global_approximation/boys.h')
    with pytest.raises(ValueError, match='CPU port source'):
        copy_cpu_ports(tmp_path / 'copy', source=source)
    assert not (tmp_path / 'copy').exists()


def test_runtime_driver_contains_snapshot_helper():
    from workflow.nwchem_compare import workflow_files
    assert Path(__file__).resolve().parents[1] / 'comparator_ports.py' in workflow_files()

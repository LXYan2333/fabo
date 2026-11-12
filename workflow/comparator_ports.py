"""Copy the retained CPU comparator sources without requiring legacy Git history."""

import hashlib
import json
from pathlib import Path
import shutil

CPU_PORTS = Path(__file__).resolve().parents[1] / 'benchmark/ports/cpu'
PORT_REVISION = '728ec72e9dae8b3897265500860e9340139c70b1'


def copy_cpu_ports(destination, *, source=CPU_PORTS, revision=None):
    """Verify the frozen snapshot, then copy only its manifest-listed files.

    destination is the include root containing the two comparator directories.
    revision accepts historical short IDs, but never selects a different model.
    """
    source, destination = Path(source), Path(destination)
    manifest_path = source / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['origin_revision'] != PORT_REVISION:
        raise ValueError('unexpected CPU port snapshot revision')
    if revision is not None and (not isinstance(revision, str) or
                                 len(revision) < 7 or not PORT_REVISION.startswith(revision)):
        raise ValueError('requested CPU port revision does not match bundled snapshot')
    for name, digest in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('invalid CPU port snapshot path: ' + name)
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing or symlinked CPU port source: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('changed CPU port source: ' + name)
    for name in manifest['files']:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    shutil.copy2(manifest_path, destination / 'manifest.json')
    return destination

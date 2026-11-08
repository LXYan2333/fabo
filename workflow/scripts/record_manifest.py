"""Companion checksums for compact, reproducible report inputs."""

import hashlib
import json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(path):
    """Publish after the reduction is complete; retain with the measurement file."""
    manifest = dict(schema=1, files={path.name: digest(path)})
    path.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def verify_manifest(path):
    manifest = json.loads(path.with_suffix('.manifest.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('files') != {path.name: digest(path)}:
        raise ValueError(f'Reduction checksum mismatch: {path.name}')

"""Format public headers, excluding data.h, and refresh SIMD source hashes."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STYLE = ROOT / '.clang-format'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formatter_identity(executable):
    return dict(executable=executable,
                version=subprocess.check_output([executable, '--version'], text=True).strip(),
                style_sha256=digest(STYLE))


def format_source(text, executable):
    """Apply the same style to regenerated source for exact-text checks."""
    return subprocess.check_output(
        [executable, '-style=file:' + str(STYLE), '--assume-filename=header.h'],
        input=text, text=True)


def format_headers(include, executable='clang-format-22'):
    include = Path(include)
    identity = formatter_identity(executable)
    # Explicit filtering protects payloads even without ignore-file support,
    # and when formatting an independently reconstructed include directory.
    paths = sorted(p for p in (include / 'fast_boys').rglob('*')
                   if p.is_file() and p.suffix in ('.h', '.cuh') and p.name != 'data.h')
    for path in paths:
        if path.is_symlink():
            raise ValueError('refusing to format a symlink: ' + str(path))
    for start in range(0, len(paths), 100):
        subprocess.run([executable, '-i', '-style=file:' + str(STYLE),
                        *map(str, paths[start:start + 100])], check=True)
    manifest_path = include / 'simd-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        manifest['files'] = {name: digest(include / name) for name in manifest['files']}
        manifest['sources'] = {name: digest(ROOT / name) for name in manifest['sources']}
        manifest['sources']['workflow/scripts/format_public_headers.py'] = digest(Path(__file__).resolve())
        manifest['sources']['.clang-format'] = digest(STYLE)
        manifest['formatting'] = identity
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include', type=Path, default=Path('include'))
    parser.add_argument('--clang-format', default='clang-format-22')
    args = parser.parse_args()
    print(f'Formatted {len(format_headers(args.include, args.clang_format))} headers; data.h excluded.')

"""S66x8 inventory rules retained from fresh-start c3c5788."""
import hashlib
import math
from pathlib import Path
import re

SEPARATIONS = ('0.90', '0.95', '1.00', '1.05', '1.10', '1.25', '1.50', '2.00')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(directory):
    """Validate all 528 original dimers; no geometries are synthesized."""
    root = Path(directory)/'dimers'
    rows = []
    seen = set()
    names = {}
    compositions = {}
    for path in sorted(root.glob('*.xyz')):
        match = re.fullmatch(r'(\d{2})_(.+)_([0-9]+\.[0-9]{2})\.xyz', path.name)
        if not match:
            raise ValueError('unrecognized dimer filename: '+path.name)
        n, name, separation = match.groups()
        system = int(n)
        key = (system, separation)
        if key in seen or not 1 <= system <= 66 or separation not in SEPARATIONS:
            raise ValueError('duplicate/invalid S66 geometry: '+path.name)
        seen.add(key)
        lines = path.read_text().splitlines()
        atoms = int(lines[0])
        if atoms < 1 or len(lines) != atoms+2:
            raise ValueError('invalid XYZ length: '+path.name)
        symbols = []
        for line in lines[2:]:
            parts = line.split()
            if len(parts) != 4 or parts[0] not in ('H', 'C', 'N', 'O') or not all(math.isfinite(float(v)) for v in parts[1:]):
                raise ValueError('invalid S66 atom: '+line)
            symbols.append(parts[0])
        if names.setdefault(system, name) != name or compositions.setdefault(system, symbols) != symbols:
            raise ValueError('system identity/composition changes with separation')
        rows.append({'system': system, 'name': name, 'separation': separation,
                     'atoms': atoms, 'geometry': 'workloads/s66x8/'+path.name,
                     'sha256': sha(path), 'source': str(path.resolve())})
    if seen != {(n,s) for n in range(1,67) for s in SEPARATIONS}:
        raise ValueError('S66x8 requires exactly 66 systems at all eight separations')
    return rows


def cases(manifest, bases, labels):
    result = []
    for row in manifest:
        if row['separation'] not in labels:
            continue
        for basis in bases:
            slug = basis.lower().replace('*','star')
            result.append({k:v for k,v in row.items() if k != 'source'} |
                          {'id': f's66-{row["system"]:02d}-{row["separation"]}--{slug}', 'basis': basis})
    expected = 66*len(bases)*len(labels)
    if len(result) != expected or len({r['id'] for r in result}) != expected:
        raise ValueError('incomplete S66 workload coverage')
    return result

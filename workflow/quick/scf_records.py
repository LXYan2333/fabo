"""SCF result and basis checks retained from fresh-start c3c5788."""
import csv
import math
from pathlib import Path
import re
from .s66 import sha


def verify_basis_output(directory, build, basis):
    """Check QUICK's actual selection, not merely the requested input label."""
    basis_dir=(build/'basis').resolve()
    link=basis_dir/'basis_link'
    filenames=[]
    for line in link.read_text().splitlines():
        fields=line.split('|')
        if len(fields)>=4 and fields[1].strip().upper()=='#'+basis.upper():
            filenames.append(fields[2].strip().upper())
    if len(filenames)!=1 or not filenames[0] or Path(filenames[0]).name!=filenames[0]:
        raise ValueError('missing/ambiguous QUICK basis mapping: '+basis)
    expected=(basis_dir/filenames[0]).resolve(strict=True)
    if not expected.is_relative_to(basis_dir):
        raise ValueError('basis file escapes archived basis directory')
    log=(directory/'input.out').read_text()
    names=re.findall(r'^\s*BASIS SET =\s*([^,\n]*),',log,re.MULTILINE)
    files=re.findall(r'^\s*\|\s*BASIS FILE =\s*(.+)$',log,re.MULTILINE)
    if {name.strip().upper() for name in names}!={basis.upper()}:
        raise ValueError('QUICK reported a missing/different basis name: '+basis)
    actual={(directory/Path(name.strip())).resolve() for name in files}
    if actual!={expected}:
        raise ValueError('QUICK loaded a missing/different basis file: '+basis)
    return {'name':basis.upper(),'file':filenames[0],
            'sha256':sha(expected),'basis_link_sha256':sha(link)}


def read_result(directory, fixed, steps, wall):
    lines = (directory/'scf-summary.txt').read_text().splitlines()
    count, converged, fixed_flag = map(int, lines[0].split())
    loop = float(lines[1])
    dimensions = list(map(int, lines[2].split()))
    with (directory/'scf-iterations.csv').open() as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=['iteration','fock_seconds','iteration_seconds','energy_hartree','prms','pchange']:
            raise ValueError('invalid SCF sample columns')
        rows = [{k:float(v) for k,v in r.items()} for r in reader]
    if len(dimensions)!=3 or not 0<dimensions[1]<=dimensions[0] or dimensions[2]<=0 or dimensions[2]%2:
        raise ValueError('invalid restricted SCF dimensions')
    if (fixed_flag != int(fixed) or converged not in (0,1) or len(rows)!=count or count<1 or
            (fixed and count!=steps) or [r['iteration'] for r in rows]!=list(range(1,count+1))):
        raise ValueError('SCF termination/count mismatch')
    if (not math.isfinite(loop) or not math.isfinite(wall) or not 0<loop<=wall or
            any(not all(math.isfinite(v) for v in r.values()) or
                not 0<r['fock_seconds']<=r['iteration_seconds'] for r in rows)):
        raise ValueError('invalid SCF timings or nonfinite diagnostics')
    fock = sum(r['fock_seconds'] for r in rows)
    if fock > loop:
        raise ValueError('nested Fock time exceeds SCF loop')
    return {'iterations':count, 'converged':bool(converged), 'fixed':fixed,
            'fock_seconds':fock, 'scf_seconds':loop, 'process_seconds':wall,
            'setup_and_teardown_seconds':wall-loop, 'dimensions':dimensions,
            'final_energy_hartree':rows[-1]['energy_hartree']}

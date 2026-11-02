"""Import checked official calibration, never historical timing as new samples."""
import json
from pathlib import Path
import shutil

from benchmark.quick.patch_quick import ROOT, PIN
from .calibrate import CASE_FILES, input_text, write_json
from .s66 import sha


class Archive:
    def __init__(self, root, digest):
        self.root = Path(root).resolve()
        marker = self.root/'complete-scf-calibrate.json'
        if sha(marker) != digest:
            raise ValueError('calibration completion hash mismatch')
        self.marker = json.loads(marker.read_text())
        self.files = self.marker.get('artifacts', self.marker.get('files', {}))

    def file(self, name):
        path = (self.root/name).resolve()
        if not path.is_relative_to(self.root) or name not in self.files or sha(path) != self.files[name]:
            raise ValueError('unrecorded/changed calibration artifact: '+name)
        return path

    def read(self, name):
        return json.loads(self.file(name).read_text())


def import_calibration(root, saved):
    """Validate protocol, every selected case, and bytes; copy only reusable inputs."""
    recipe = saved['recipe']; config = recipe['config']; spec = recipe['comparison']
    archive = Archive(spec['calibration_root'], spec['calibration_sha256'])
    if 'scf-protocol.json' in archive.files:
        protocol = archive.read('scf-protocol.json')
        expected = dict(schema=2, quick_commit=PIN, enable_f=config['enable_f'],
                        max_scf_iterations=config['max_scf_iterations'], density_rms=config['density_rms'])
        if any(protocol.get(k) != v for k,v in expected.items()):
            raise ValueError('incompatible historical calibration protocol')
        # These two exact sources define the state layout and fixed-loop behavior.
        for name in ('scf_training.f90', 'patch_scf_training.py'):
            if protocol['sources'].get('benchmark/quick/'+name) != sha(ROOT/'benchmark/quick'/name):
                raise ValueError('calibration SCF hooks changed: '+name)
    else:
        old = archive.read('run.json')['recipe']
        if old['quick_revision'] != PIN or any(old['config'][k] != config[k] for k in
                ('enable_f','max_scf_iterations','density_rms')):
            raise ValueError('incompatible calibration configuration')
        for name in ('scf_training.f90','patch_scf_training.py'):
            key='bundle/benchmark/quick/'+name
            if old['input_hashes'].get(key) != sha(ROOT/'benchmark/quick'/name):
                raise ValueError('calibration SCF hooks changed: '+name)
        # Modern completion markers refer to per-case manifests transitively.
        for case in recipe['cases']:
            base='calibration/'+case['id']+'/'
            record=archive.read(base+'complete.json')
            if record['identity'] != archive.marker['identity']:
                raise ValueError('calibration case identity mismatch')
            for name,digest in record['files'].items(): archive.files[base+name]=digest
    rows = archive.read('calibration.json')
    if len({r['case'] for r in rows}) != len(rows):
        raise ValueError('duplicate calibration cases')
    by_id = {r['case']:r for r in rows}
    imported=[]
    for case in recipe['cases']:
        base='calibration/'+case['id']+'/'
        if archive.read(base+'case.json') != case:
            raise ValueError('calibration geometry/basis identity mismatch: '+case['id'])
        row=archive.read(base+'result.json')
        if row != by_id.get(case['id']) or not row['converged'] or row['fixed'] or row['variant']!='official':
            raise ValueError('missing/nonconverged official calibration: '+case['id'])
        if type(row['iterations']) is not int or not 1 <= row['iterations'] <= config['max_scf_iterations']:
            raise ValueError('invalid official iteration count')
        # Require the corrected explicit BASIS= input, not the old implicit STO-3G runs.
        if archive.file(base+'input.in').read_text() != input_text(root,config,case):
            raise ValueError('calibration input differs: '+case['id'])
        basis=row['basis']; source=root/'variants/official/source/basis'
        if (Path(basis['file']).name != basis['file'] or basis['name'] != case['basis'].upper() or
                sha(source/basis['file']) != basis['sha256'] or sha(source/'basis_link') != basis['basis_link_sha256']):
            raise ValueError('calibration basis bytes differ')
        state=archive.file(base+'initial.bin')
        if sha(state) != row['fixture_sha256']:
            raise ValueError('calibration initial-state hash mismatch')
        destination=root/'calibration'/case['id']; destination.mkdir(parents=True,exist_ok=True)
        for name in CASE_FILES:
            src=archive.file(base+name); dst=destination/name
            if dst.exists() and sha(dst)!=sha(src):
                raise ValueError('changed imported calibration: '+str(dst))
            if not dst.exists(): shutil.copyfile(src,dst)
        imported.append(row)
    names=[str(p.relative_to(root)) for p in (root/'calibration').rglob('*') if p.is_file()]
    record={'identity':saved['identity'], 'origin_identity':archive.marker['identity'],
            'origin_completion_sha256':spec['calibration_sha256'], 'rows':imported,
            'files':{name:sha(root/name) for name in names}}
    write_json(root/'imported-calibration.json',record)
    return record


def checked_import(root, saved):
    path=root/'imported-calibration.json'
    if not path.exists(): return import_calibration(root,saved)
    record=json.loads(path.read_text())
    if (record['identity']!=saved['identity'] or
            record['origin_completion_sha256']!=saved['recipe']['comparison']['calibration_sha256']):
        raise ValueError('import belongs to another comparison')
    expected={'calibration/'+case['id']+'/'+name for case in saved['recipe']['cases'] for name in CASE_FILES}
    if set(record['files'])!=expected:
        raise ValueError('incomplete imported calibration manifest')
    for name,digest in record['files'].items():
        if sha(root/name)!=digest: raise ValueError('changed imported calibration: '+name)
    rows=[json.loads((root/'calibration'/case['id']/'result.json').read_text()) for case in saved['recipe']['cases']]
    if record['rows']!=rows:
        raise ValueError('changed imported calibration metadata')
    return record

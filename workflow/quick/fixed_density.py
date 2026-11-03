"""Single SAD-density GPU update, five timed backends and an untimed reference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import struct
import subprocess
import tempfile

from benchmark.quick.patch_quick import ROOT, PIN, VARIANTS
from . import calibrate as c
from .compare import bundle_sources, schedule, statistics_for
from .comparators import prepare_tables, conformance
from .prepare import prepare as prepare_quick
from .scf_records import verify_basis_output
from .s66 import inventory, sha


def prepare(root, dataset, raw):
    config = c.settings(raw['config'])
    options = raw['experiment']
    if set(options) != {'copies', 'spacing_angstrom', 'minimum_fock_seconds', 'rounds', 'build_workers', 'cuda_arch', 'reference_python', 'reference_timeout_seconds', 'max_reference_attempts'}:
        raise ValueError('invalid experiment options')
    copies = options['copies']
    if not copies or any(type(v) is not int or v < 1 for v in copies) or copies != sorted(set(copies)):
        raise ValueError('copies must be increasing positive integers')
    for key in ('rounds', 'build_workers', 'reference_timeout_seconds', 'max_reference_attempts'):
        if type(options[key]) is not int or options[key] < 1:
            raise ValueError('invalid '+key)
    if options['rounds'] < 3 or options['build_workers'] > config['slurm']['cpus']:
        raise ValueError('invalid repetitions/build concurrency')
    for key in ('spacing_angstrom', 'minimum_fock_seconds'):
        if not math.isfinite(options[key]) or options[key] <= 0:
            raise ValueError('invalid '+key)
    if config['bases'] != ['def2-SVP'] or config['enable_f']:
        raise ValueError('this stacked-uracil experiment uses def2-SVP without ENABLEF')
    root.mkdir(parents=True, exist_ok=False)
    for variant in (*VARIANTS, 'reference'):
        prepare_quick(root/'variants'/variant/'source', variant, probe=True)
    bundle_sources(root, Path('/usr/include/eigen3'))
    for name in ('workflow/additive/reference.py', 'workflow/scripts/quick_reference_data.py'):
        destination = root/'bundle'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    source = next(r for r in inventory(dataset) if r['system'] == 17 and r['separation'] == '1.00')
    atoms = [line.split() for line in Path(source['source']).read_text().splitlines()[2:]]
    cases = []
    for count in copies:
        path = root/'workloads'/f'uracil-{count}.xyz'
        path.parent.mkdir(exist_ok=True)
        lines = [str(len(atoms)*count), f'{count} translated S66-17 dimers; Angstrom']
        for i in range(count):
            for atom,x,y,z in atoms:
                lines.append(f'{atom} {float(x):.12f} {float(y):.12f} {float(z)+options["spacing_angstrom"]*i:.12f}')
        path.write_text('\n'.join(lines)+'\n')
        cases.append(dict(id=f'uracil-{count}--def2-svp', basis='def2-SVP', copies=count,
                          atoms=len(atoms)*count, geometry=str(path.relative_to(root)), sha256=sha(path)))
    script = c.slurm_script(config).replace('fabo-s66-calibrate', 'fabo-fixed-density').replace('workflow.quick.calibrate execute', 'workflow.quick.fixed_density execute')
    (root/'run.sbatch').write_text(script)
    recipe = dict(schema=1, quick_revision=PIN, config=config, experiment=options, cases=cases,
                  source_geometry=source, initial_guess='official QUICK default SAD',
                  comparison=dict(variants=list(VARIANTS), cuda_arch=options['cuda_arch']),
                  input_hashes={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})
    saved = dict(identity=c.identity(recipe), recipe=recipe)
    c.write_json(root/'run.json', saved)
    for variant in (*VARIANTS, 'reference'):
        child = dict(parent=saved['identity'], variant=variant, config=config|{'build_jobs':1})
        c.write_json(root/'variants'/variant/'run.json', dict(identity=c.identity(child), recipe=child))


def verify(root):
    saved = c.verify_inputs(root)
    for variant in (*VARIANTS, 'reference'):
        expected = dict(parent=saved['identity'], variant=variant, config=saved['recipe']['config']|{'build_jobs':1})
        if json.loads((root/'variants'/variant/'run.json').read_text()) != dict(identity=c.identity(expected), recipe=expected):
            raise ValueError('changed child build identity')
    return saved


def complete(folder, identity):
    c.write_json(folder/'complete.json', dict(identity=identity, files={p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.name!='complete.json'}))


def check_complete(folder, identity, expected_files=None):
    record = json.loads((folder/'complete.json').read_text())
    if record['identity'] != identity:
        raise ValueError('completion identity mismatch')
    if expected_files is not None and set(record['files']) != set(expected_files):
        raise ValueError('completion file set mismatch')
    for name,digest in record['files'].items():
        if sha(folder/name) != digest:
            raise ValueError('changed completed file: '+str(folder/name))


def selected_case(root, saved):
    selection=json.loads((root/'selected-case.json').read_text())
    case=selection['case']
    if case not in saved['recipe']['cases']:
        raise ValueError('selected case is outside the frozen recipe')
    folder=root/'fixtures'/case['id']
    check_complete(folder,saved['identity'],
                   ('fixture.bin','fixture-info.txt','fixture.json','input.in','input.out','process.log'))
    if (selection!=json.loads((folder/'fixture.json').read_text()) or
            sha(folder/'fixture.bin')!=selection['fixture_sha256'] or
            list(fixture_dimensions(folder/'fixture.bin'))!=selection['dimensions']):
        raise ValueError('selected fixture identity mismatch')
    return selection


def sample_files(variant):
    common={'input.in','input.out','process.log','outputs.bin','result.json'}
    return common | ({'check-energy.txt','overrides.bin'} if variant=='reference' else {'timings.csv'})


def checked_sample(folder,saved,selection,variant,round_):
    check_complete(folder,saved['identity'],sample_files(variant))
    row=json.loads((folder/'result.json').read_text())
    if (row['variant']!=variant or type(row['round']) is not int or row['round']!=round_ or
            row['timed'] is not (variant!='reference') or row['basis']!=selection['basis'] or
            row['fixture_sha256']!=selection['fixture_sha256'] or
            row['replay_sha256']!=selection['fixture_sha256'] or
            row['overrides_sha256']!=(sha(folder/'overrides.bin') if variant=='reference' else None)):
        raise ValueError('cached sample semantic identity mismatch')
    raw=read_sample(folder,selection['dimensions'][0],variant=='reference')
    if any(row[k]!=v for k,v in raw.items()):
        raise ValueError('cached sample differs from raw observations')
    return row


def resolve_pending(root,saved,destination):
    """Finish an interrupted MPFR transaction before rerunning the update."""
    overrides=destination/'overrides.bin'
    for folder in sorted((destination/'attempts').glob('*')):
        record=folder/'attempt.json'
        if not record.exists() or (folder/'resolved.json').exists():
            continue
        if json.loads(record.read_text())['exit_code']!=86:
            continue
        requests=folder/'reference-unresolved.bin'
        keys=set(struct.iter_unpack('<QQ',requests.read_bytes()))
        if not keys:
            raise ValueError('empty unresolved reference request list')
        current={(x,n) for x,n,_ in struct.iter_unpack('<QQQ',overrides.read_bytes())}
        if not keys <= current:
            candidate=destination/'overrides.next.bin'
            shutil.copyfile(overrides,candidate)
            c.command([saved['recipe']['experiment']['reference_python'],'-m',
                       'workflow.scripts.quick_reference_data','resolve',candidate,
                       '--requests',requests],folder/'resolve.log',cwd=root/'bundle',timeout=3600)
            candidate.replace(overrides)
        # If interrupted after replace, the key check above avoids a spurious
        # "no progress" resolver error without redoing an expensive Fock build.
        c.write_json(folder/'resolved.json',dict(overrides_sha256=sha(overrides),requests_sha256=sha(requests)))


def fixture_dimensions(path):
    with path.open('rb') as f:
        n, reduced, electrons = struct.unpack('<iii', f.read(12))
    if not 0 < reduced <= n or electrons <= 0 or electrons % 2 or path.stat().st_size != 12+8*(3*n*n+n*reduced):
        raise ValueError('invalid fixture dimensions/size')
    return n, reduced, electrons


def read_outputs(path, n):
    import numpy as np
    if path.stat().st_size != 16*n*n:
        raise ValueError('invalid Fock/density output size')
    values = np.fromfile(path, dtype='<f8').reshape(2,n*n)
    if not np.all(np.isfinite(values)):
        raise ValueError('nonfinite molecular output')
    return values


def read_sample(local, n, untimed):
    read_outputs(local/'outputs.bin', n)
    if untimed:
        if (local/'timings.csv').exists():
            raise ValueError('reference unexpectedly produced timings')
        energy = float((local/'check-energy.txt').read_text())
        result = dict(energy_hartree=energy, timed=False)
    else:
        with (local/'timings.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        if len(rows)!=1 or float(rows[0]['iteration'])!=1:
            raise ValueError('expected exactly one measured update')
        row = {k:float(v) for k,v in rows[0].items()}
        if not 0 < row['fock_seconds'] <= row['iteration_seconds']:
            raise ValueError('invalid nested timings')
        result = dict(energy_hartree=row['energy_diagnostic'], timed=True,
                      fock_seconds=row['fock_seconds'], iteration_seconds=row['iteration_seconds'])
    if any(not math.isfinite(v) for v in result.values()):
        raise ValueError('nonfinite diagnostic')
    return result


def archive(local, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('input.in','input.out','process.log','timings.csv','check-energy.txt','outputs.bin','reference-unresolved.bin','fixture-info.txt'):
        if (local/name).exists():
            shutil.copyfile(local/name, destination/name)


def invoke(root, saved, case, variant, mode, fixture, build, local, overrides=None):
    config = saved['recipe']['config']
    options = saved['recipe']['experiment']
    local.mkdir()
    (local/'input.in').write_text(c.input_text(root,config,case))
    binary, env = build
    runtime = env | dict(QUICK_BASIS=str(root/'variants'/variant/'install/basis'),
                         FABO_QUICK_MODE=mode, FABO_FIXTURE=str(fixture), FABO_WARMUP='0', FABO_INITIAL_GUESS='sad')
    if variant in ('libintx_gpu','gansu'):
        runtime['FABO_COMPARATOR_TABLE'] = str(root/'tables'/(variant+'.bin'))
    if variant=='reference':
        runtime.update(FABO_REFERENCE_TABLE=str(root/'reference-data/table.bin'), FABO_REFERENCE_OVERRIDES=str(overrides))
    timeout = options['reference_timeout_seconds'] if variant=='reference' else config['calculation_timeout_seconds']
    c.command([binary,'input.in'],local/'process.log',cwd=local,env=runtime,timeout=timeout)
    return verify_basis_output(local,root/'variants'/variant/'install',case['basis'])


def reference_data(root, saved, scratch):
    """Check the retained reference evaluator and host fail-closed bridge."""
    config=saved['recipe']['config']; options=saved['recipe']['experiment']
    folder=root/'reference-data'
    if (folder/'complete.json').exists():
        check_complete(folder,saved['identity']); return
    folder.mkdir(exist_ok=True)
    for action,name in (('generate','table.bin'),('fixtures','fixtures.bin')):
        c.command([options['reference_python'],'-m','workflow.scripts.quick_reference_data',action,folder/name],folder/(action+'.log'),cwd=root/'bundle',timeout=3600)
    (scratch/'empty.bin').write_bytes(b'')
    src=root/'bundle/benchmark/quick'
    include=root/'variants/reference/source/src/gpu'
    for mode,flags in (('strict',['--fmad=false']),('fast',['--use_fast_math'])):
        exe=scratch/('reference-'+mode)
        c.command([config['cuda']+'/bin/nvcc','-ccbin',config['cxx'],'-std=c++17','-O3',
                   '-arch='+options['cuda_arch'],*flags,'-I'+str(src),src/'reference_conformance.cu','-o',exe],folder/(mode+'-build.log'))
        c.command([exe,folder/'table.bin',folder/'fixtures.bin'],folder/(mode+'.log'),timeout=600)
    exe=scratch/'reference-runtime'
    c.command([config['cuda']+'/bin/nvcc','-ccbin',config['cxx'],'-std=c++17','-O3','--use_fast_math',
               '-arch='+options['cuda_arch'],'-I'+str(include),src/'reference_runtime_conformance.cu','-o',exe],folder/'runtime-build.log')
    for mode,expected in ((0,0),(1,86),(2,2),(3,2)):
        with (folder/f'runtime-{mode}.log').open('w') as log:
            result=subprocess.run([exe,folder/'table.bin',scratch/'empty.bin',str(mode)],cwd=scratch,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        if result.returncode!=expected:
            raise ValueError('reference runtime check failed')
    complete(folder,saved['identity'])


def run_sample(root,saved,case,reference,variant,round_,build,scratch):
    destination=root/'samples'/f'{round_:02d}'/variant
    if (destination/'complete.json').exists():
        return checked_sample(destination,saved,reference,variant,round_)
    destination.mkdir(parents=True,exist_ok=True)
    fixture=root/'fixtures'/case['id']/'fixture.bin'
    n=fixture_dimensions(fixture)[0]
    overrides=destination/'overrides.bin'
    if variant=='reference' and not overrides.exists():
        overrides.write_bytes(b'')
    if variant=='reference':
        resolve_pending(root,saved,destination)
    options=saved['recipe']['experiment']
    limit=options['max_reference_attempts'] if variant=='reference' else 1
    existing=[int(p.name) for p in (destination/'attempts').glob('*') if p.is_dir() and p.name.isdigit()]
    first_attempt=max(existing,default=-1)+1
    for attempt in range(first_attempt,first_attempt+limit):
        with tempfile.TemporaryDirectory(prefix='update-',dir=scratch) as temp:
            local=Path(temp)/'run'
            override_hash=sha(overrides) if variant=='reference' else None
            attempt_dir=destination/'attempts'/f'{attempt:02d}'
            try:
                basis=invoke(root,saved,case,variant,'check' if variant=='reference' else 'run',fixture,build,local,overrides)
                if basis!=reference['basis'] or sha(local/'replayed-fixture.bin')!=reference['fixture_sha256']:
                    raise ValueError('basis or initial density replay differs')
                result=read_sample(local,n,variant=='reference')
                result.update(variant=variant,round=round_,basis=basis,fixture_sha256=reference['fixture_sha256'],
                              replay_sha256=sha(local/'replayed-fixture.bin'),overrides_sha256=override_hash)
            except subprocess.CalledProcessError as error:
                archive(local,attempt_dir)
                c.write_json(attempt_dir/'attempt.json',dict(exit_code=error.returncode,overrides_sha256=override_hash))
                if variant!='reference' or error.returncode!=86:
                    raise
                resolve_pending(root,saved,destination)
                continue
            except BaseException:
                archive(local,attempt_dir)
                raise
            archive(local,destination)
            c.write_json(destination/'result.json',result)
            complete(destination,saved['identity'])
            return checked_sample(destination,saved,reference,variant,round_)
    raise RuntimeError('reference replay budget exhausted')


def report(root, saved, with_reference):
    import numpy as np
    rounds=saved['recipe']['experiment']['rounds']
    variants=(*VARIANTS,'reference') if with_reference else VARIANTS
    selection=selected_case(root,saved)
    rows={}
    for v in variants:
        rows[v]=[]
        for r in range(rounds):
            folder=root/'samples'/f'{r:02d}'/v
            rows[v].append(checked_sample(folder,saved,selection,v,r))
    summary=dict(identity=saved['identity'],rounds=rounds,initial_guess='official SAD',
                 reference_status='complete' if with_reference else 'pending', variants={})
    for v in variants:
        energies=[r['energy_hartree'] for r in rows[v]]
        summary['variants'][v]=dict(energy_mean=math.fsum(energies)/rounds,energy_sd=statistics.stdev(energies),energy_range=max(energies)-min(energies))
        if v!='reference':
            summary['variants'][v]['timing']={k:statistics_for([r[k] for r in rows[v]]) for k in ('fock_seconds','iteration_seconds')}
    if with_reference:
        n=selection['dimensions'][0]
        arrays=[read_outputs(root/'samples'/f'{r:02d}'/'reference/outputs.bin',n) for r in range(rounds)]
        anchor=arrays[0]
        # Center before averaging, preserving sub-ulp mean displacements. Store
        # two binary64 parts so small backend differences are not rounded away.
        offset=np.sum([a-anchor for a in arrays],axis=0)/rounds
        hi=anchor+offset; lo=(anchor-hi)+offset
        sd=np.sqrt(np.sum([((a-anchor)-offset)**2 for a in arrays],axis=0)/(rounds-1))
        folder=root/'reference-mean';folder.mkdir(exist_ok=True)
        for name,a in (('hi',hi),('lo',lo),('sd',sd)):
            a.astype('<f8').tofile(folder/(name+'.bin'))
        c.write_json(folder/'layout.json',dict(dimensions=[2,n,n],order='Fock then updated density, each column-major',
                     mean='hi+lo, centered binary64 averaging',files={p.name:sha(p) for p in folder.glob('*.bin')}))
        energy_anchor=rows['reference'][0]['energy_hartree']
        energy_offset=math.fsum(r['energy_hartree']-energy_anchor for r in rows['reference'])/rounds
        for v in variants:
            for r,row in enumerate(rows[v]):
                values=read_outputs(root/'samples'/f'{r:02d}'/v/'outputs.bin',n)
                delta=(values-hi)-lo
                row['energy_difference_from_reference_mean']=(row['energy_hartree']-energy_anchor)-energy_offset
                row['matrix_difference_from_reference_mean']={name:dict(max_absolute=float(np.max(np.abs(d))),frobenius=float(np.linalg.norm(d))) for name,d in zip(('fock','density'),delta)}
            summary['variants'][v]['max_abs_energy_difference_from_reference_mean']=max(abs(r['energy_difference_from_reference_mean']) for r in rows[v])
            summary['variants'][v]['energy_mean_difference']=math.fsum(r['energy_hartree']-energy_anchor for r in rows[v])/rounds-energy_offset
            summary['variants'][v]['max_matrix_difference_from_reference_mean']={name:max(r['matrix_difference_from_reference_mean'][name]['max_absolute'] for r in rows[v]) for name in ('fock','density')}
        summary['reference_note']='Mean of correctly-rounded-Boys updates; remaining integral, accumulation and eigensolver rounding is not removed. Not an exact molecular solution.'
        summary['reference_matrix_sd_max']={name:float(np.max(s)) for name,s in zip(('fock','density'),sd)}
    c.write_json(root/('summary.json' if with_reference else 'timing-summary.json'),summary)
    c.write_json(root/('samples.json' if with_reference else 'timing-samples.json'),rows)


def execute(root):
    saved=verify(root); config=saved['recipe']['config']; options=saved['recipe']['experiment']
    lock=(root/'execute.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    environment=dict(host=subprocess.check_output(['hostname'],text=True),gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,uuid,driver_version','--format=csv,noheader'],text=True),
                     nvcc=subprocess.check_output([config['cuda']+'/bin/nvcc','--version'],text=True))
    envfile=root/'environment.json'
    if envfile.exists() and json.loads(envfile.read_text())!=environment:
        raise ValueError('execution environment changed')
    c.write_json(envfile,environment)
    with tempfile.TemporaryDirectory(prefix='fabo-fixed-',dir=os.environ.get('SLURM_TMPDIR','/tmp')) as temp:
        scratch=Path(temp)
        def build(v):
            local=scratch/v;local.mkdir()
            return c.build(root/'variants'/v,json.loads((root/'variants'/v/'run.json').read_text()),local)
        # No compilation overlaps measurements. Each variant builds serially.
        with ThreadPoolExecutor(max_workers=options['build_workers']) as pool:
            builds=dict(zip((*VARIANTS,'reference'),pool.map(build,(*VARIANTS,'reference'))))
        prepare_tables(root,config,scratch)
        conformance(root,saved,scratch)
        reference_data(root,saved,scratch)
        selected=root/'selected-case.json'
        if selected.exists():
            selection=selected_case(root,saved);case=selection['case']
        else:
            for case in saved['recipe']['cases']:
                folder=root/'fixtures'/case['id'];folder.mkdir(parents=True,exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='sizing-',dir=scratch) as tmp:
                    local=Path(tmp)
                    basis=invoke(root,saved,case,'official','prepare',local/'fixture.bin',builds['official'],local/'prepare')
                    dimensions=fixture_dimensions(local/'fixture.bin')
                    shutil.copyfile(local/'fixture.bin',folder/'fixture.bin')
                    archive(local/'prepare',folder)
                    invoke(root,saved,case,'official','run',folder/'fixture.bin',builds['official'],local/'size')
                    sizing=read_sample(local/'size',dimensions[0],False)
                    if sha(local/'size/replayed-fixture.bin')!=sha(folder/'fixture.bin'):
                        raise ValueError('sizing replay differs')
                    archive(local/'size',folder/'sizing')
                    selection=dict(case=case,basis=basis,dimensions=dimensions,fixture_sha256=sha(folder/'fixture.bin'),
                                   sizing=sizing,target_met=sizing['fock_seconds']>=options['minimum_fock_seconds'])
                    c.write_json(folder/'fixture.json',selection);complete(folder,saved['identity'])
                print('sizing',case['id'],sizing['fock_seconds'],flush=True)
                if selection['target_met']:break
            c.write_json(selected,selection)
        for r,_,v in schedule([case],list(VARIANTS),options['rounds']):
            row=run_sample(root,saved,case,selection,v,r,builds[v],scratch)
            print('timing',r,v,row['fock_seconds'],flush=True)
        report(root,saved,False)
        for r in range(options['rounds']):
            run_sample(root,saved,case,selection,'reference',r,builds['reference'],scratch)
            print('untimed reference',r,'accepted',flush=True)
        report(root,saved,True)
        c.write_json(root/'complete.json',dict(identity=saved['identity'],summary_sha256=sha(root/'summary.json')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','execute','report'))
    parser.add_argument('--run',required=True,type=Path)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--dataset',type=Path)
    args=parser.parse_args();root=args.run.resolve()
    if args.stage=='prepare':prepare(root,args.dataset,json.loads(args.config.read_text()))
    elif args.stage=='execute':execute(root)
    else:report(root,verify(root),True)


if __name__=='__main__':main()

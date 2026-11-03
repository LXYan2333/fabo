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
    if set(options) != {'systems', 'copies', 'spacing_angstrom', 'minimum_fock_seconds', 'rounds', 'build_workers', 'cuda_arch', 'reference_python', 'reference_timeout_seconds', 'max_reference_attempts'}:
        raise ValueError('invalid experiment options')
    copies = options['copies']
    if not copies or any(type(v) is not int or v < 1 for v in copies) or copies != sorted(set(copies)):
        raise ValueError('copies must be increasing positive integers')
    systems=options['systems']
    if not systems or len(set(systems))!=len(systems) or any(type(v) is not int or not 1<=v<=66 for v in systems):
        raise ValueError('systems must be unique S66 integer IDs')
    for key in ('rounds', 'build_workers', 'reference_timeout_seconds', 'max_reference_attempts'):
        if type(options[key]) is not int or options[key] < 1:
            raise ValueError('invalid '+key)
    if options['rounds'] < 3 or options['build_workers'] > config['slurm']['cpus']:
        raise ValueError('invalid repetitions/build concurrency')
    for key in ('spacing_angstrom', 'minimum_fock_seconds'):
        if not math.isfinite(options[key]) or options[key] <= 0:
            raise ValueError('invalid '+key)
    if 'def2-SVP' not in config['bases'] or config['enable_f']:
        raise ValueError('size using def2-SVP; this profile supports s/p/d bases without ENABLEF')
    basis_coverage=basis_shells(ROOT/'third_party/quick/basis',config['bases'])
    root.mkdir(parents=True, exist_ok=False)
    for variant in (*VARIANTS, 'reference'):
        prepare_quick(root/'variants'/variant/'source', variant, probe=True)
    bundle_sources(root, Path('/usr/include/eigen3'))
    for name in ('workflow/additive/reference.py', 'workflow/scripts/quick_reference_data.py'):
        destination = root/'bundle'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    sources=[r for r in inventory(dataset) if r['system'] in systems and r['separation']=='1.00']
    cases = []
    for source in sources:
        original=root/'original-geometries'/Path(source['source']).name
        original.parent.mkdir(exist_ok=True);shutil.copyfile(source['source'],original)
        atoms = [line.split() for line in original.read_text().splitlines()[2:]]
        for count in copies:
            path = root/'workloads'/f's66-{source["system"]:02d}-stack-{count}.xyz'
            path.parent.mkdir(exist_ok=True)
            text,translation=stack_geometry(atoms,count,options['spacing_angstrom'])
            path.write_text(text)
            for basis in config['bases']:
                cases.append(dict(id=f's66-{source["system"]:02d}-stack-{count}--{basis.lower().replace("*","star")}',
                                  system=source['system'],name=source['name'],basis=basis,copies=count,
                                  atoms=len(atoms)*count,geometry=str(path.relative_to(root)),sha256=sha(path),
                                  original_geometry=str(original.relative_to(root)),original_sha256=sha(original),
                                  translation_angstrom=translation))
    script = c.slurm_script(config).replace('fabo-s66-calibrate', 'fabo-fixed-density').replace('workflow.quick.calibrate execute', 'workflow.quick.fixed_density execute')
    (root/'run.sbatch').write_text(script)
    recipe = dict(schema=2, quick_revision=PIN, config=config, experiment=options, cases=cases,
                  source_geometries=sources, basis_coverage=basis_coverage, initial_guess='official QUICK default SAD',
                  comparison=dict(variants=list(VARIANTS), cuda_arch=options['cuda_arch']),
                  input_hashes={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})
    saved = dict(identity=c.identity(recipe), recipe=recipe)
    c.write_json(root/'run.json', saved)
    for variant in (*VARIANTS, 'reference'):
        child = dict(parent=saved['identity'], variant=variant, config=config|{'build_jobs':1})
        c.write_json(root/'variants'/variant/'run.json', dict(identity=c.identity(child), recipe=child))


def basis_shells(directory,bases):
    """Check the actual bundled H/C/N/O basis blocks, not their names alone."""
    import re
    result={}
    for basis in bases:
        matches=[line.split('|')[2].strip().upper() for line in (directory/'basis_link').read_text().splitlines()
                 if len(line.split('|'))>=4 and line.split('|')[1].strip().lower()=='#'+basis.lower()]
        if len(matches)!=1:raise ValueError('ambiguous/missing basis mapping')
        path=directory/matches[0];element=None;shells={e:set() for e in ('H','C','N','O')}
        for line in path.read_text().splitlines():
            fields=line.split()
            if len(fields)==2 and fields[1]=='0' and fields[0].isalpha():
                element=fields[0]
            elif line.strip()=='****':element=None
            elif element in shells and len(fields)>=3 and re.fullmatch('[SPDFGHI]+',fields[0]):
                shells[element].update(fields[0])
        if any(not s or s-set('SPD') for s in shells.values()):
            raise ValueError('basis requires unsupported angular momentum or missing H/C/N/O block')
        result[basis]=dict(file=path.name,sha256=sha(path),elements={e:sorted(s,key='SPDFGHI'.index) for e,s in shells.items()})
    return result


def stack_geometry(atoms,count,gap):
    """Translate along the thinnest bounding-box axis; keep copies separated."""
    coordinates=[[float(v) for v in atom[1:]] for atom in atoms]
    spans=[max(r[i] for r in coordinates)-min(r[i] for r in coordinates) for i in range(3)]
    axis=min(range(3),key=lambda i:(spans[i],i))
    translation=[0.,0.,0.];translation[axis]=spans[axis]+gap
    lines=[str(len(atoms)*count),f'{count} translated dimers; Angstrom; translation={translation}']
    for copy in range(count):
        for atom,xyz in zip(atoms,coordinates):
            lines.append(atom[0]+' '+ ' '.join(f'{v+copy*t:.12f}' for v,t in zip(xyz,translation)))
    return '\n'.join(lines)+'\n',translation


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


def selected_case(root, saved, case_id=None):
    path=root/'selections'/(case_id+'.json') if case_id is not None else root/'selected-case.json'
    selection=json.loads(path.read_text())
    case=selection['case']
    if case not in saved['recipe']['cases'] or (case_id is not None and case['id']!=case_id):
        raise ValueError('selected case is outside the frozen recipe')
    folder=root/'fixtures'/case['id']
    check_complete(folder,saved['identity'],
                   ('fixture.bin','fixture-info.txt','fixture.json','input.in','input.out','process.log'))
    if (selection!=json.loads((folder/'fixture.json').read_text()) or
            sha(folder/'fixture.bin')!=selection['fixture_sha256'] or
            list(fixture_dimensions(folder/'fixture.bin'))!=selection['dimensions']):
        raise ValueError('selected fixture identity mismatch')
    return selection


def sample_directory(root,saved,case_id,round_,variant):
    parent=root/'samples'
    if saved['recipe'].get('schema',1)>=2:parent=parent/case_id
    return parent/f'{round_:02d}'/variant


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
    if saved['recipe'].get('schema',1)>=2 and row.get('case')!=selection['case']['id']:
        raise ValueError('cached sample belongs to a different molecule/basis')
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
    destination=sample_directory(root,saved,case['id'],round_,variant)
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
                result.update(variant=variant,round=round_,case=case['id'],basis=basis,fixture_sha256=reference['fixture_sha256'],
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


def report(root, saved, with_reference, case_id=None):
    import numpy as np
    rounds=saved['recipe']['experiment']['rounds']
    variants=(*VARIANTS,'reference') if with_reference else VARIANTS
    selection=selected_case(root,saved,case_id)
    result_root=root/'reports'/case_id if case_id is not None else root
    result_root.mkdir(parents=True,exist_ok=True)
    rows={}
    for v in variants:
        rows[v]=[]
        for r in range(rounds):
            folder=sample_directory(root,saved,selection['case']['id'],r,v)
            rows[v].append(checked_sample(folder,saved,selection,v,r))
    summary=dict(identity=saved['identity'],rounds=rounds,initial_guess='official SAD',case=selection['case'],dimensions=selection['dimensions'],basis=selection['basis'],
                 reference_status='complete' if with_reference else 'pending', variants={})
    for v in variants:
        energies=[r['energy_hartree'] for r in rows[v]]
        summary['variants'][v]=dict(energy_mean=math.fsum(energies)/rounds,energy_sd=statistics.stdev(energies),energy_range=max(energies)-min(energies))
        if v!='reference':
            summary['variants'][v]['timing']={k:statistics_for([r[k] for r in rows[v]]) for k in ('fock_seconds','iteration_seconds')}
    if with_reference:
        n=selection['dimensions'][0]
        arrays=[read_outputs(sample_directory(root,saved,selection['case']['id'],r,'reference')/'outputs.bin',n) for r in range(rounds)]
        anchor=arrays[0]
        # Center before averaging, preserving sub-ulp mean displacements. Store
        # two binary64 parts so small backend differences are not rounded away.
        offset=np.sum([a-anchor for a in arrays],axis=0)/rounds
        hi=anchor+offset; lo=(anchor-hi)+offset
        sd=np.sqrt(np.sum([((a-anchor)-offset)**2 for a in arrays],axis=0)/(rounds-1))
        folder=result_root/'reference-mean';folder.mkdir(exist_ok=True)
        for name,a in (('hi',hi),('lo',lo),('sd',sd)):
            a.astype('<f8').tofile(folder/(name+'.bin'))
        c.write_json(folder/'layout.json',dict(dimensions=[2,n,n],order='Fock then updated density, each column-major',
                     mean='hi+lo, centered binary64 averaging',files={p.name:sha(p) for p in folder.glob('*.bin')}))
        energy_anchor=rows['reference'][0]['energy_hartree']
        energy_offset=math.fsum(r['energy_hartree']-energy_anchor for r in rows['reference'])/rounds
        for v in variants:
            for r,row in enumerate(rows[v]):
                values=read_outputs(sample_directory(root,saved,selection['case']['id'],r,v)/'outputs.bin',n)
                delta=(values-hi)-lo
                row['energy_difference_from_reference_mean']=(row['energy_hartree']-energy_anchor)-energy_offset
                row['matrix_difference_from_reference_mean']={name:dict(max_absolute=float(np.max(np.abs(d))),frobenius=float(np.linalg.norm(d))) for name,d in zip(('fock','density'),delta)}
            summary['variants'][v]['max_abs_energy_difference_from_reference_mean']=max(abs(r['energy_difference_from_reference_mean']) for r in rows[v])
            summary['variants'][v]['energy_mean_difference']=math.fsum(r['energy_hartree']-energy_anchor for r in rows[v])/rounds-energy_offset
            summary['variants'][v]['max_matrix_difference_from_reference_mean']={name:max(r['matrix_difference_from_reference_mean'][name]['max_absolute'] for r in rows[v]) for name in ('fock','density')}
        summary['reference_note']='Mean of correctly-rounded-Boys updates; remaining integral, accumulation and eigensolver rounding is not removed. Not an exact molecular solution.'
        summary['reference_matrix_sd_max']={name:float(np.max(s)) for name,s in zip(('fock','density'),sd)}
    c.write_json(result_root/('summary.json' if with_reference else 'timing-summary.json'),summary)
    c.write_json(result_root/('samples.json' if with_reference else 'timing-samples.json'),rows)
    return summary


def prepare_fixture(root,saved,case,build,scratch,size):
    folder=root/'fixtures'/case['id']
    selection_file=root/'selections'/(case['id']+'.json')
    if selection_file.exists():
        selection=selected_case(root,saved,case['id'])
        if ('sizing' in selection)!=size:raise ValueError('changed fixture sizing role')
        return selection
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fixture-',dir=scratch) as tmp:
        local=Path(tmp)
        basis=invoke(root,saved,case,'official','prepare',local/'fixture.bin',build,local/'prepare')
        dimensions=fixture_dimensions(local/'fixture.bin')
        shutil.copyfile(local/'fixture.bin',folder/'fixture.bin')
        archive(local/'prepare',folder)
        selection=dict(case=case,basis=basis,dimensions=dimensions,fixture_sha256=sha(folder/'fixture.bin'))
        if size:
            invoke(root,saved,case,'official','run',folder/'fixture.bin',build,local/'size')
            sizing=read_sample(local/'size',dimensions[0],False)
            if sha(local/'size/replayed-fixture.bin')!=selection['fixture_sha256']:
                raise ValueError('sizing replay differs')
            archive(local/'size',folder/'sizing')
            selection.update(sizing=sizing,target_met=sizing['fock_seconds']>=saved['recipe']['experiment']['minimum_fock_seconds'])
        c.write_json(folder/'fixture.json',selection);complete(folder,saved['identity'])
    c.write_json(selection_file,selection)
    return selected_case(root,saved,case['id'])


def validate_selections(root,saved):
    records=json.loads((root/'selected-stacks.json').read_text())
    if set(records)!=set(map(str,saved['recipe']['experiment']['systems'])):
        raise ValueError('selected molecule coverage mismatch')
    selected=[]
    for system in saved['recipe']['experiment']['systems']:
        sizing=records[str(system)]
        actual=selected_case(root,saved,sizing['case']['id'])
        if actual!=sizing or sizing['case']['basis']!='def2-SVP' or sizing['case']['system']!=system:
            raise ValueError('invalid def2-SVP sizing selection')
        for basis in saved['recipe']['config']['bases']:
            matches=[case for case in saved['recipe']['cases'] if case['system']==system and case['basis']==basis and case['copies']==sizing['case']['copies']]
            if len(matches)!=1:raise ValueError('missing selected molecule/basis')
            case=matches[0]
            if any(case[key]!=sizing['case'][key] for key in ('geometry','sha256','translation_angstrom','atoms')):
                raise ValueError('basis-specific geometry differs from sizing geometry')
            selection=selected_case(root,saved,case['id'])
            selected.append(selection)
    return selected


def report_suite(root,saved,with_reference):
    selections=validate_selections(root,saved)
    summaries=[report(root,saved,with_reference,s['case']['id']) for s in selections]
    c.write_json(root/('summary.json' if with_reference else 'timing-summary.json'),
                 dict(identity=saved['identity'],reference_status='complete' if with_reference else 'pending',cases=summaries))
    rows=[]
    for summary in summaries:
        baseline=summary['variants']['official']['timing']['fock_seconds']['median']
        for variant,record in summary['variants'].items():
            row=dict(case=summary['case']['id'],system=summary['case']['system'],name=summary['case']['name'],
                     basis=summary['case']['basis'],copies=summary['case']['copies'],atoms=summary['case']['atoms'],
                     basis_functions=summary['dimensions'][0],backend=variant,
                     fock_seconds=None,iteration_seconds=None,cv=None,speedup=None,
                     energy_mean_difference=record.get('energy_mean_difference'))
            if variant!='reference':
                row.update(fock_seconds=record['timing']['fock_seconds']['median'],iteration_seconds=record['timing']['iteration_seconds']['median'],
                           cv=record['timing']['fock_seconds']['cv'],speedup=baseline/record['timing']['fock_seconds']['median'])
            rows.append(row)
    with (root/('summary.csv' if with_reference else 'timing-summary.csv')).open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def select_workloads(root,saved,build,scratch):
    options=saved['recipe']['experiment'];stacks={}
    for system in options['systems']:
        candidates=sorted((case for case in saved['recipe']['cases'] if case['system']==system and case['basis']=='def2-SVP'),key=lambda case:case['copies'])
        if not candidates:raise ValueError('missing def2-SVP sizing candidates')
        for case in candidates:
            selection=prepare_fixture(root,saved,case,build,scratch,True)
            print('sizing',case['id'],selection['sizing']['fock_seconds'],flush=True)
            if selection['target_met']:break
        stacks[str(system)]=selection
    stack_file=root/'selected-stacks.json'
    if stack_file.exists() and json.loads(stack_file.read_text())!=stacks:
        raise ValueError('selected stack counts changed on resume')
    c.write_json(stack_file,stacks)
    for case in saved['recipe']['cases']:
        if case['copies']==stacks[str(case['system'])]['case']['copies']:
            prepare_fixture(root,saved,case,build,scratch,case['basis']=='def2-SVP')
    return validate_selections(root,saved)


def execute(root):
    saved=verify(root); config=saved['recipe']['config']; options=saved['recipe']['experiment']
    if saved['recipe'].get('schema')!=2:raise ValueError('execute with the workflow bundled in the original run')
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
        selections=select_workloads(root,saved,builds['official'],scratch)
        by_id={s['case']['id']:s for s in selections}
        for r,case,v in schedule([s['case'] for s in selections],list(VARIANTS),options['rounds']):
            row=run_sample(root,saved,case,by_id[case['id']],v,r,builds[v],scratch)
            print('timing',case['id'],r,v,row['fock_seconds'],flush=True)
        report_suite(root,saved,False)
        for selection in selections:
            case=selection['case']
            for r in range(options['rounds']):
                run_sample(root,saved,case,selection,'reference',r,builds['reference'],scratch)
                print('untimed reference',case['id'],r,'accepted',flush=True)
            report(root,saved,True,case['id'])
        report_suite(root,saved,True)
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
    else:
        saved=verify(root)
        if saved['recipe'].get('schema',1)>=2:report_suite(root,saved,True)
        else:report(root,saved,True)


if __name__=='__main__':main()

"""Prepare/resume official QUICK S66 SCF iteration calibration; never tune Boys."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time

from benchmark.quick.patch_quick import ROOT, PIN
from .prepare import prepare as prepare_quick
from .s66 import SEPARATIONS, inventory, cases, sha
from .scf_records import read_result, verify_basis_output

DEFAULTS = dict(enable_f=False, bases=['6-31G*', 'def2-SVP'], separations=['1.00'],
                max_scf_iterations=200, density_rms=1e-6,
                calculation_timeout_seconds=3600, post_build_wait_seconds=10,
                build_jobs=16, cmake='/usr/bin/cmake', cc='/usr/bin/gcc',
                cxx='/usr/bin/g++', fc='/usr/bin/gfortran', cuda='/usr/local/cuda',
                quick_arch='blackwell2', build_type='Release', python='/usr/bin/python3',
                slurm=dict(partition='pc', node='pc008', cpus=16, memory='96G', minutes=480))
BUNDLE_FILES = ('benchmark/quick/patch_quick.py', 'benchmark/quick/patch_scf_training.py',
                'benchmark/quick/scf_training.f90', 'benchmark/quick/probe_runtime.h',
                'workflow/quick/__init__.py', 'workflow/quick/prepare.py',
                'workflow/quick/calibrate.py', 'workflow/quick/s66.py',
                'workflow/quick/scf_records.py')
CASE_FILES = ('input.in', 'input.out', 'process.log', 'initial.bin',
              'scf-summary.txt', 'scf-iterations.csv', 'case.json', 'result.json')


def settings(raw):
    if set(raw)-set(DEFAULTS):
        raise ValueError('unknown calibration configuration keys')
    c = DEFAULTS | raw
    if type(c['enable_f']) is not bool:
        raise ValueError('enable_f must be Boolean')
    for key, allowed in (('bases', ('6-31G*', 'def2-SVP', 'def2-TZVP')),
                         ('separations', SEPARATIONS)):
        values = c[key]
        if not isinstance(values,list) or not values or any(not isinstance(v,str) for v in values) or len(set(values))!=len(values) or any(v not in allowed for v in values):
            raise ValueError('invalid '+key)
    if 'def2-TZVP' in c['bases'] and not c['enable_f']:
        raise ValueError('def2-TZVP requires ENABLEF')
    for key in ('max_scf_iterations', 'build_jobs', 'calculation_timeout_seconds'):
        if type(c[key]) is not int or c[key]<1:
            raise ValueError('invalid '+key)
    for key in ('density_rms', 'post_build_wait_seconds'):
        if type(c[key]) not in (float,int) or not math.isfinite(c[key]) or c[key]<=0:
            raise ValueError('invalid '+key)
    if c['build_type'] not in ('Release', 'RelWithDebInfo'):
        raise ValueError('invalid build_type')
    for key in ('cmake','cc','cxx','fc','cuda','python','quick_arch'):
        if not isinstance(c[key],str) or not c[key] or '\n' in c[key]:
            raise ValueError('invalid '+key)
    s = c['slurm']
    if set(s)!=set(DEFAULTS['slurm']):
        raise ValueError('invalid Slurm fields')
    for key in ('partition','node','memory'):
        if not isinstance(s[key],str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',s[key]):
            raise ValueError('invalid Slurm '+key)
    if any(type(s[k]) is not int or s[k]<1 for k in ('cpus','minutes')) or c['build_jobs']>s['cpus']:
        raise ValueError('build jobs must fit the positive Slurm CPU allocation')
    return c


def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def slurm_script(config):
    s=config['slurm']
    return f'''#!/bin/bash
#SBATCH --job-name=fabo-s66-calibrate
#SBATCH --partition={s['partition']}
#SBATCH --nodelist={s['node']}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={s['cpus']}
#SBATCH --gpus=1
#SBATCH --exclusive
#SBATCH --mem={s['memory']}
#SBATCH --time={s['minutes']}
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${{SLURM_SUBMIT_DIR:?Submit from the prepared run directory}}"
run_root="$PWD"
cd "$run_root/bundle"
exec {shlex.quote(config['python'])} -m workflow.quick.calibrate execute --run "$run_root"
'''


def prepare_run(output, dataset, raw):
    config=settings(raw)
    original=inventory(dataset)  # Require the complete original 66 x 8 dataset.
    selected=cases(original,config['bases'],config['separations'])
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    prepare_quick(output/'source','official',training=True)
    for relative in BUNDLE_FILES:
        path=output/'bundle'/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,path)
    for item in original:
        if item['separation'] in config['separations']:
            path=output/item['geometry']; path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(item['source'],path)
            if sha(path)!=item['sha256']:
                raise ValueError('geometry changed during preparation')
    (output/'run.sbatch').write_text(slurm_script(config))
    inputs={str(p.relative_to(output)):sha(p) for dirname in ('bundle','source','workloads')
            for p in sorted((output/dirname).rglob('*')) if p.is_file()}
    inputs['run.sbatch']=sha(output/'run.sbatch')
    recipe={'schema':1, 'quick_revision':PIN, 'config':config, 'cases':selected,
            'initial_guess':'official SAD', 'warmup_iterations':0,
            'protocol_origin':'fresh-start c3c578806a02dc7e00cf076a0be83a3ba25aa6d4',
            'input_hashes':inputs}
    write_json(output/'run.json', {'identity':identity(recipe),'recipe':recipe})
    return output/'run.json'


def verify_inputs(root):
    saved=json.loads((root/'run.json').read_text())
    recipe=saved['recipe']
    if identity(recipe)!=saved['identity']:
        raise ValueError('run identity mismatch')
    settings(recipe['config'])
    for name,digest in recipe['input_hashes'].items():
        if sha(root/name)!=digest:
            raise ValueError('changed prepared input: '+name)
    return saved


def command(args, log, *, cwd=None, env=None, timeout=None):
    start=time.monotonic()
    with Path(log).open('a') as stream:
        stream.write('$ '+shlex.join(map(str,args))+'\n'); stream.flush()
        subprocess.run(list(map(str,args)),stdout=stream,stderr=subprocess.STDOUT,
                       check=True,cwd=cwd,env=env,timeout=timeout)
    return time.monotonic()-start


def clean_environment():
    env={k:v for k,v in os.environ.items() if not k.startswith('FABO_')}
    env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    return env


def dependencies(binary, env):
    text=subprocess.check_output(['ldd',str(binary)],env=env,text=True)
    if 'not found' in text:
        raise ValueError('unresolved QUICK runtime dependency')
    paths=re.findall(r'(?:=>\s+|^\s*)(/\S+)',text,re.MULTILINE)
    return {str(Path(p).resolve()):sha(p) for p in paths}


def export_build(tree, source, prefix):
    """Archive only the GPU target and its libraries, not CPU-only targets."""
    executables=[p for p in tree.rglob('quick.cuda') if p.is_file()]
    if len(executables)!=1:
        raise ValueError('expected one built quick.cuda executable')
    libraries={}
    for path in tree.rglob('*.so*'):
        if path.is_file():
            if path.name in libraries and sha(libraries[path.name])!=sha(path):
                raise ValueError('conflicting built library: '+path.name)
            libraries[path.name]=path
    if 'libquick_cuda.so' not in libraries:
        raise ValueError('missing CUDA shared library')
    # A prior interrupted export is recoverable, never reused as a valid build.
    if prefix.exists():
        prefix.rename(prefix.with_name(prefix.name+'-incomplete-'+str(time.time_ns())))
    (prefix/'bin').mkdir(parents=True); (prefix/'lib').mkdir()
    shutil.copy2(executables[0],prefix/'bin/quick.cuda')
    for name,path in libraries.items(): shutil.copy2(path,prefix/'lib'/name)
    shutil.copytree(source/'basis',prefix/'basis')


def build(root, saved, scratch):
    config=saved['recipe']['config']; prefix=root/'install'
    binary=prefix/'bin/quick.cuda'
    env=clean_environment()
    env['LD_LIBRARY_PATH']=str(prefix/'lib')+':'+env.get('LD_LIBRARY_PATH','')
    marker=root/'build.json'
    if marker.exists():
        record=json.loads(marker.read_text())
        if record['identity']!=saved['identity']:
            raise ValueError('build belongs to a different run')
        for name,digest in record['files'].items():
            if sha(root/name)!=digest:
                raise ValueError('changed installed build: '+name)
        if dependencies(binary,env)!=record['dependencies']:
            raise ValueError('changed QUICK runtime dependencies')
        return binary,env
    source=scratch/'source'; tree=scratch/'build'
    shutil.copytree(root/'source',source)
    args=[config['cmake'],'-S',source,'-B',tree,'-DCOMPILER=GNU','-DCUDA=TRUE',
          '-DMPI=FALSE',f'-DENABLEF={"TRUE" if config["enable_f"] else "FALSE"}',
          '-DQUICK_USER_ARCH='+config['quick_arch'],'-DQUICK_PROFILE=FALSE',
          '-DCMAKE_BUILD_TYPE='+config['build_type'],'-DFORCE_INTERNAL_LIBS=blas;lapack',
          '-DFORCE_DISABLE_LIBS=mkl','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
          '-DCMAKE_INSTALL_PREFIX='+str(prefix),'-DCMAKE_BUILD_RPATH=$ORIGIN/../lib',
          '-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON',
          '-DCUDA_TOOLKIT_ROOT_DIR='+config['cuda'],'-DCMAKE_C_COMPILER='+config['cc'],
          '-DCMAKE_CXX_COMPILER='+config['cxx'],'-DCMAKE_Fortran_COMPILER='+config['fc']]
    env['TMPDIR']=str(scratch)
    command(args,root/'build.log',env=env)
    command([config['cmake'],'--build',tree,'--target','quick.cuda','--parallel',config['build_jobs']],root/'build.log',env=env)
    export_build(tree,source,prefix)
    if not binary.is_file():
        raise ValueError('QUICK install lacks bin/quick.cuda')
    for name in ('CMakeCache.txt','compile_commands.json'):
        if (tree/name).exists(): shutil.copyfile(tree/name,root/name)
    record={'identity':saved['identity'],'configure_command':list(map(str,args)),
            'dependencies':dependencies(binary,env),
            'files':{str(p.relative_to(root)):sha(p) for p in prefix.rglob('*') if p.is_file()}}
    write_json(marker,record)
    time.sleep(config['post_build_wait_seconds'])
    return binary,env


def input_text(root, config, case):
    lines=(root/case['geometry']).read_text().splitlines()
    return (f'HF BASIS={case["basis"]} CHARGE=0 ENERGY SCF={config["max_scf_iterations"]} '
            f'DENSERMS={config["density_rms"]:.17g}\n\n'+'\n'.join(lines[2:])+'\n\n')


def calibration_case(root,saved,case,binary,env,scratch):
    directory=root/'calibration'/case['id']; marker=directory/'complete.json'
    if marker.exists():
        record=json.loads(marker.read_text())
        if record['identity']!=saved['identity']:
            raise ValueError('case belongs to a different run')
        if set(record['files'])!=set(CASE_FILES):
            raise ValueError('incomplete case manifest')
        for name,digest in record['files'].items():
            if sha(directory/name)!=digest:
                raise ValueError('changed completed case: '+case['id']+'/'+name)
        result=json.loads((directory/'result.json').read_text())
        if json.loads((directory/'case.json').read_text())!=case:
            raise ValueError('resumed case differs from workload')
        return result
    config=saved['recipe']['config']
    with tempfile.TemporaryDirectory(prefix=case['id']+'-',dir=scratch) as temporary:
        local=Path(temporary); (local/'input.in').write_text(input_text(root,config,case))
        runtime=env | {'QUICK_BASIS':str(root/'install/basis'),'FABO_SCF_TRAINING':'calibrate',
                       'FABO_SCF_STATE':str(local/'initial.bin'),'FABO_SCF_STEPS':'0'}
        directory.mkdir(parents=True,exist_ok=True)
        try:
            wall=command([binary,'input.in'],local/'process.log',cwd=local,env=runtime,
                         timeout=config['calculation_timeout_seconds'])
            result=read_result(local,False,None,wall)
            if result['iterations']>config['max_scf_iterations']:
                raise ValueError('SCF count exceeds configured limit')
            result['basis']=verify_basis_output(local,root/'install',case['basis'])
            result.update(case=case['id'],variant='official',fixture_sha256=sha(local/'initial.bin'))
            write_json(local/'case.json',case); write_json(local/'result.json',result)
            for name in CASE_FILES:
                shutil.copyfile(local/name,directory/name)
        except Exception:
            for name in ('process.log','input.in','input.out','scf-summary.txt','scf-iterations.csv'):
                if (local/name).exists(): shutil.copyfile(local/name,directory/('failed-'+name))
            raise
    write_json(marker,{'identity':saved['identity'],'files':{name:sha(directory/name) for name in CASE_FILES}})
    return result


def report(root,saved,rows):
    ready=len(rows)==len(saved['recipe']['cases']) and all(r['converged'] for r in rows)
    write_json(root/'calibration.json',rows)
    write_json(root/'iteration-plan.json',{'identity':saved['identity'],'ready':ready,
               'iterations':{r['case']:r['iterations'] for r in rows if r['converged']},
               'nonconverged':[r['case'] for r in rows if not r['converged']],
               'policy':'Replay each archived initial SAD state for exactly its converged official iteration count; no molecular warmup.'})
    lines=['# Official QUICK S66 iteration calibration','',
           f'Completed cases: {len(rows)}/{len(saved["recipe"]["cases"])}; converged: {sum(r["converged"] for r in rows)}. Benchmark-ready: {ready}.','',
           'Iteration counts follow the unchanged official density-convergence and screening rules. Fock time is summed over all iterations; SCF-loop time excludes setup/SAD; process time includes them. No alternate Boys backend, tuning, or repeated timing is run. Nonconverged cases must not be silently dropped.','',
           '| Case | Iterations | Converged | Sum Fock (s) | SCF loop (s) | Process (s) |',
           '|---|---:|---|---:|---:|---:|']
    lines += [f'| {r["case"]} | {r["iterations"]} | {r["converged"]} | {r["fock_seconds"]:.6f} | {r["scf_seconds"]:.6f} | {r["process_seconds"]:.6f} |' for r in rows]
    (root/'CALIBRATION.md').write_text('\n'.join(lines)+'\n')
    return ready


def execute(root):
    root=Path(root).resolve()
    with (root/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        saved=verify_inputs(root)
        config=saved['recipe']['config']
        complete=root/'complete-scf-calibrate.json'
        was_complete=complete.exists()
        if was_complete:
            marker=json.loads(complete.read_text())
            if marker['identity']!=saved['identity']:
                raise ValueError('completion belongs to a different run')
            for name,digest in marker['files'].items():
                if sha(root/name)!=digest:
                    raise ValueError('changed calibration artifact: '+name)
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,uuid,driver_version','--format=csv,noheader'],text=True).strip()
        environment={'gpu':gpu,'node':os.uname().nodename}
        path=root/'environment.json'
        if path.exists() and json.loads(path.read_text())!=environment:
            raise ValueError('calibration GPU/node environment changed; start a new run')
        if not path.exists():
            write_json(path,environment)
        temp_root=os.environ.get('SLURM_TMPDIR',os.environ.get('TMPDIR','/tmp'))
        with tempfile.TemporaryDirectory(prefix='fabo-s66-',dir=temp_root) as temp:
            scratch=Path(temp)
            binary,env=build(root,saved,scratch)
            rows=[]
            for case in saved['recipe']['cases']:
                rows.append(calibration_case(root,saved,case,binary,env,scratch))
                if not was_complete:
                    report(root,saved,rows)
                print(f'{case["id"]}: {rows[-1]["iterations"]} iterations, converged={rows[-1]["converged"]}',flush=True)
            if was_complete:
                # Verifying an archive must not replace its complete summaries
                # with partial prefixes if verification is interrupted.
                if not all(r['converged'] for r in rows):
                    raise ValueError('completed calibration contains nonconverged cases')
                return
            ready=report(root,saved,rows)
        if not ready:
            raise RuntimeError('nonconverged official cases; benchmark plan is not ready')
        names=['run.json','build.json','environment.json','calibration.json','iteration-plan.json','CALIBRATION.md']
        names += [str(p.relative_to(root)) for p in sorted((root/'calibration').glob('*/complete.json'))]
        write_json(root/'complete-scf-calibrate.json',{'identity':saved['identity'],
                   'files':{name:sha(root/name) for name in names}})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare'); p.add_argument('--config',type=Path,required=True)
    p.add_argument('--dataset',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('execute'); p.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='prepare':
        print(prepare_run(args.output,args.dataset,json.loads(args.config.read_text())))
    else:
        execute(args.run)


if __name__=='__main__':
    main()

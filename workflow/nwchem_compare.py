"""Fixed-state NWChem comparison. No search or convergence calibration."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tarfile
import tempfile
import math

from benchmark.nwchem.bindings import BACKENDS, SHARED_TAIL, header
from benchmark.nwchem.simint_binding import patch as patch_simint
from benchmark.nwchem.patch_nwchem import patch_single_update

ROOT=Path(__file__).resolve().parents[1]
NWCHEM='e2869a2c81445f2edfd25bbae652d099fabb9a92'
SIMINT='38b24bb040c647e4acc0e040457180b574089c58'
BASES={'6-31G*':'6-31gs','def2-SVP':'def2-svp','cc-pVDZ':'cc-pvdz'}

def workflow_files():
    return [Path(__file__).resolve(), *sorted((ROOT/'benchmark/nwchem').glob('*.py')),
            *sorted((ROOT/'benchmark/nwchem').glob('*.F')), ROOT/'benchmark/nwchem/mkl_dispatch.c',
            ROOT/'benchmark/nwchem/highway_gather.patch']

def patch_highway(root):
    """PR #3519, from the author's local Highway commits; fail on drift."""
    patch=ROOT/'benchmark/nwchem/highway_gather.patch'
    # Apply to the disposable export even when it sits under another worktree.
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env['GIT_CEILING_DIRECTORIES']=str(Path(root).resolve())
    subprocess.run(['git','apply','--check',str(patch)],cwd=root,env=env,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=root,env=env,check=True)

def verify_manifest(folder, manifest):
    for name,digest in manifest.items():
        if sha(folder/name)!=digest:raise ValueError('changed artifact: '+str(folder/name))

def verify_inputs(out):
    verify_manifest(out,json.loads((out/'inputs.json').read_text()))
    # Reproduction uses the same driver and patches that prepared the run.
    verify_manifest(ROOT,json.loads((out/'workflow.json').read_text()))

def verify_sample(folder):
    verify_manifest(folder,json.loads((folder/'complete.json').read_text()))

def syntax_preflight(c,env,work,log):
    """Fail before expensive builds on an incompatible experimental SIMD."""
    source=work/'simd-check.cc'
    source.write_text('#include <experimental/simd>\n'
        'auto f(std::experimental::native_simd<double> x) { return x >= 1; }\n')
    run([c['cxx'],'-std=c++20','-march='+c['architecture'],'-fsyntax-only',source],work,env,log)

def sample_record(folder):
    """Validate the one-update contract before marking a sample complete."""
    import numpy as np
    with (folder/'scf-iterations.csv').open() as f:rows=list(csv.DictReader(f))
    if len(rows)!=1 or int(rows[0]['iteration'])!=1 or int(rows[0]['energy_gradient_evaluations'])!=1:
        raise ValueError('not one evaluation/update')
    if not all(math.isfinite(float(v)) for v in rows[0].values()):raise ValueError('nonfinite result')
    if any(float(rows[0][k])<=0 for k in ('jk_seconds','fock_seconds','scf_seconds')):
        raise ValueError('invalid timer')
    protocol=list(map(int,(folder/'scf-protocol.txt').read_text().split()))
    if len(protocol)!=4 or protocol[0]!=1 or protocol[1]!=protocol[2] or protocol[1]<1 or protocol[3]!=1:
        raise ValueError('invalid solver/dimensions')
    for matrix in ('density-in','density-out','fock'):
        values=np.fromfile(folder/(matrix+'.bin'),dtype='<f8')
        if (folder/(matrix+'.bin')).stat().st_size!=8*protocol[1]**2 or not np.all(np.isfinite(values)):
            raise ValueError('invalid matrix '+matrix)
    evidence=(folder/'mkl-runtime.txt').read_text()
    if 'THREADS 1\n' not in evidence or 'MAP ' not in evidence:
        raise ValueError('missing MKL runtime evidence')
    return rows[0]

def mapped_libraries(evidence):
    libraries={}
    for line in evidence.splitlines():
        if line.startswith('MAP ') and '/' in line:
            path=Path('/'+line.split('/',1)[1])
            if path.is_file():libraries[str(path)]=sha(path)
    return libraries

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def save(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n'); tmp.replace(path)

def run(args,cwd,env,log):
    with Path(log).open('a') as f:
        f.write(repr(list(map(str,args)))+'\n');f.flush()
        subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=14400)

def export(source,commit,out,paths=()):
    out.mkdir(parents=True,exist_ok=False)
    with subprocess.Popen(['git','-C',str(source),'archive',commit,*paths],stdout=subprocess.PIPE) as p:
        with tarfile.open(fileobj=p.stdout,mode='r|') as t:t.extractall(out,filter='data')
        if p.wait():raise RuntimeError('source export failed')

def environment(config):
    env={k:v for k,v in os.environ.items() if not k.startswith(('FABO_','MKL_','OMP_','NWCHEM_'))
         and k not in ('LD_PRELOAD','LD_AUDIT','MAKEFLAGS','CFLAGS','CXXFLAGS','FFLAGS','CPATH','NWCHEM_BASIS_LIBRARY')}
    env.update(config.get('environment',{}))
    env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MKL_DYNAMIC='FALSE',MKL_VERBOSE='0')
    # Explicitly unset instruction/CNR restrictions: automatic dispatch.
    env.pop('MKL_CBWR',None);env.pop('MKL_ENABLE_INSTRUCTIONS',None)
    return env

def prepare(out,config):
    out.mkdir(parents=True,exist_ok=False)
    save(out/'config.json',config)
    export(config['nwchem_source'],NWCHEM,out/'nwchem')
    patch_single_update(out/'nwchem')
    export(config['simint_source'],SIMINT,out/'generator')
    export(ROOT,config['legacy_revision'],out/'legacy',[
        'benchmark/third_party_boys_impl/laikov_global_approximation',
        'benchmark/third_party_boys_impl/vikhamar_sandberg_repisky_minimax'])
    export(config['libintx_source'],config['libintx_revision'],out/'libintx',
           ['src/libintx','include/eigen3'])
    export(config['highway_source'],config['highway_revision'],out/'highway',['hwy'])
    patch_highway(out/'highway')
    save(out/'highway-patch.json',dict(upstream='https://github.com/google/highway/pull/3519',
        commits=['278be1b6','1d3324fbd8ba209ad5643242de15ced6320a8cc6'],
        base_revision=config['highway_revision'],sha256=sha(ROOT/'benchmark/nwchem/highway_gather.patch')))
    shutil.copyfile(config['ga_archive'],out/'ga-5.9.2.tar.gz')
    save(out/'workflow.json',{str(p.relative_to(ROOT)):sha(p) for p in workflow_files()})
    shutil.copytree(ROOT/'include',out/'include')
    cases=[]
    for system in (1,17,24,34):
        matches=list(Path(config['s66x8']).rglob(f'{system:02d}_*_1.00.xyz'))
        if len(matches)!=1:raise ValueError(f'expected one equilibrium geometry for {system}')
        path=out/'geometries'/matches[0].name;path.parent.mkdir(exist_ok=True);shutil.copyfile(matches[0],path)
        for basis in BASES:
            cases.append(dict(id=f'{system:02d}-{basis.lower().replace("*","s")}',basis=basis,geometry=str(path.relative_to(out))))
    save(out/'cases.json',cases)
    # Copy the exact source code too; hashes alone are not a reproduction archive.
    for p in workflow_files():
        target=out/'driver'/p.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    save(out/'inputs.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})

def build(out):
    c=json.loads((out/'config.json').read_text());env=environment(c)
    if os.uname().nodename.split('.')[0] != c['build_node']:raise RuntimeError('wrong build node')
    verify_inputs(out)
    if (out/'built.json').exists():raise ValueError('already built; use a new run to rebuild')
    with tempfile.TemporaryDirectory(prefix='fabo-nw-',dir=c.get('scratch','/tmp')) as temp:
        work=Path(temp);gen=work/'generator';shutil.copytree(out/'generator',gen)
        log=out/'build.log'
        syntax_preflight(c,env,work,log)
        tools={name:subprocess.check_output([c[name],'--version'],env=env,text=True) for name in ('cc','cxx','fc','mpicc','mpifort')}
        run(['cmake','-S',gen,'-B',gen/'build','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+c['cxx']],work,env,log)
        run(['cmake','--build',gen/'build','-j',str(c['build_workers'])],work,env,log)
        generated=work/'generated'
        run([c['python'],gen/'create.py','-g',gen/'build/generator/ostei','-l','2','-p','2','-d','0','-ve','4','-he','4','-vg','5','-hg','5','-n','1',generated],work,env,log)
        installs={}
        ports=out/'legacy/benchmark/third_party_boys_impl'
        libintx=out/'libintx'
        mkl=Path(c['mkl_root'])
        generated_include=work/'compat/libintx';generated_include.mkdir(parents=True)
        (generated_include/'config.h').write_text('#pragma once\n#define LIBINTX_SIMD 1\n#define LIBINTX_MAX_L 3\n#define LIBINTX_MAX_X 4\n#define LIBINTX_MAX_K 10\nnamespace libintx { constexpr int LMAX=3,XMAX=4,KMAX=10; }\n')
        for backend in BACKENDS:
            tree=work/backend;shutil.copytree(generated,tree)
            bindings=tree/'bindings';bindings.mkdir()
            (bindings/'shared_tail.h').write_text(SHARED_TAIL)
            for n in range(9):
                folder=bindings/f'order-{n}';folder.mkdir()
                if backend!='original':
                    (folder/'binding.h').write_text(header(n,backend))
                    save(folder/'binding.json',{'namespace':f'fabo_nw_{backend}_{n}'})
            patch_simint(tree,backend,8,bindings)
            cm=tree/'simint/CMakeLists.txt'
            with cm.open('a') as f:
                f.write('\ntarget_compile_features(simint PRIVATE cxx_std_20)\n')
                f.write(f'target_sources(simint PRIVATE "{ROOT}/benchmark/nwchem/mkl_dispatch.c")\n')
                f.write(f'target_include_directories(simint PRIVATE "{mkl}/include")\n')
                f.write('target_compile_definitions(simint PRIVATE MKL_ILP64 FABO_NWCHEM_MKL_HOOK)\n')
                if backend=='laikov':
                    f.write('target_sources(simint PRIVATE '+ ' '.join('"'+str(ports/'laikov_global_approximation'/p)+'"' for p in ('adapter.c','source/c0n4.c','source/z1nm4.c'))+')\n')
            flags='-O3 -ffast-math -fopenmp-simd -DNDEBUG -march='+c['architecture']
            includes=[out/'include',out/'highway',ports,generated_include.parent,libintx/'src',libintx/'include/eigen3']
            cxxflags=flags+' -DHWY_COMPILE_ONLY_STATIC '+ ' '.join('-I'+str(p) for p in includes)
            install=work/(backend+'-install');installs[backend]=install
            run(['cmake','-S',tree,'-B',tree/'build','-DSIMINT_VECTOR=commonavx512','-DSIMINT_MAXAM=2','-DSIMINT_MAXDER=0',
                 '-DENABLE_FORTRAN=ON','-DENABLE_TESTS=OFF','-DSIMINT_STANDALONE=OFF','-DBUILD_SHARED_LIBS=OFF',
                 '-DCMAKE_C_COMPILER='+c['cc'],'-DCMAKE_CXX_COMPILER='+c['cxx'],'-DCMAKE_Fortran_COMPILER='+c['fc'],
                 '-DCMAKE_C_FLAGS='+flags,'-DCMAKE_CXX_FLAGS='+cxxflags,'-DCMAKE_Fortran_FLAGS=-fdefault-integer-8 -cpp -std=legacy',
                 '-DCMAKE_INSTALL_LIBDIR=lib','-DCMAKE_INSTALL_PREFIX='+str(install)],work,env,log)
            run(['cmake','--build',tree/'build','-j',str(c['build_workers'])],work,env,log)
            run(['cmake','--install',tree/'build'],work,env,log)
            shutil.copyfile(install/'lib/libsimint.a',install/'lib/libnwc_simint.a')
        core=work/'nwchem';shutil.copytree(out/'nwchem',core)
        shutil.copyfile(out/'ga-5.9.2.tar.gz',core/'src/tools/ga-5.9.2.tar.gz')
        libs=f'-L{mkl}/lib -lmkl_gf_ilp64 -lmkl_sequential -lmkl_core -lpthread -lm -ldl'
        env.update(NWCHEM_TOP=str(core),NWCHEM_TARGET='LINUX64',NWCHEM_MODULES='ddscf hessian',USE_MPI='y',USE_SIMINT='y',
                   SIMINT_SKIPBLD='y',SIMINT_HOME=str(installs['original']),ARMCI_NETWORK='MPI-TS',USE_SERIALEIGENSOLVERS='y',
                   BLAS_SIZE='8',BLASOPT=libs,LAPACK_LIB=libs,CC=c['cc'],CXX=c['cxx'],FC=c['fc'],MPICC=c['mpicc'],MPIF90=c['mpifort'])
        with (core/'src/config/makefile.h').open('a') as f:f.write('\nEXTRA_LIBS += -lstdc++ -lmvec -lquadmath\n')
        run(['make','nwchem_config'],core/'src',env,log)
        run(['make','-j'+str(c['build_workers'])],core/'src',env,log)
        binaries=out/'binaries';binaries.mkdir(exist_ok=True)
        for backend,install in installs.items():
            env['SIMINT_HOME']=str(install)
            run(['make','-j1','link'],core/'src',env,log)
            shutil.copy2(core/'bin/LINUX64/nwchem',binaries/backend)
        basis=out/'basis';basis.mkdir(exist_ok=True)
        for name in BASES.values():shutil.copyfile(core/'src/basis/libraries'/name,basis/name)
        run([c['cc'],'-DMKL_ILP64','-I'+str(mkl/'include'),ROOT/'benchmark/nwchem/mkl_dispatch.c',
             '-L'+str(mkl/'lib'),'-Wl,-rpath,'+str(mkl/'lib'),'-lmkl_gf_ilp64','-lmkl_sequential','-lmkl_core',
             '-lpthread','-lm','-ldl','-o',binaries/'mkl-dispatch'],work,env,log)
        save(out/'built.json',{'binaries':{b:sha(binaries/b) for b in (*BACKENDS,'mkl-dispatch')},'basis':{b:sha(basis/b) for b in BASES.values()},
            'architecture':c['architecture'],'flags':flags,'tool_versions':tools,
            'linkage':{b:subprocess.check_output(['ldd',str(binaries/b)],env=env,text=True) for b in BACKENDS}})

def input_text(case,geometry):
    return '\n'.join(['start fabo','scratch_dir .','permanent_dir .','memory total 8192 mb','charge 0','geometry units angstrom noautosym noautoz','symmetry c1',
        *geometry.read_text().splitlines()[2:],'end','basis spherical segment',f' * library "{case["basis"]}"','end',
        'set int:cando_txs f','set int:cando_nw f','set fock:replicated t','scf',' rhf',' direct',' diis',' maxiter 2',
        ' vectors input atomic output final.movecs','end','task scf energy',''])

def measure(out, smoke=False):
    import fcntl
    lock=(out/'measurement.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    c=json.loads((out/'config.json').read_text());env=environment(c)
    verify_inputs(out)
    if os.uname().nodename.split('.')[0]!=c['timing_node']:raise RuntimeError('wrong timing node')
    built=json.loads((out/'built.json').read_text())
    for b in BASES.values():
        if sha(out/'basis'/b)!=built['basis'][b]:raise ValueError('basis changed')
    for b in (*BACKENDS,'mkl-dispatch'):
        if sha(out/'binaries'/b)!=built['binaries'][b]:raise ValueError('binary changed')
    env['NWCHEM_BASIS_LIBRARY']=str(out/'basis')+'/'
    cases=json.loads((out/'cases.json').read_text())
    if not smoke:
        for b in BACKENDS:verify_sample(out/'smoke'/cases[0]['id']/f'0-{b}')
    if smoke:cases=cases[:1]
    target=out/('smoke' if smoke else 'measurements')
    target.mkdir(exist_ok=True)
    evidence=subprocess.check_output([str(out/'binaries/mkl-dispatch')],env=env,text=True)
    (target/'mkl-dispatch.txt').write_text(evidence)
    libraries=mapped_libraries(evidence)
    linkage={b:subprocess.check_output(['ldd',str(out/'binaries'/b)],env=env,text=True) for b in BACKENDS}
    for listing in linkage.values():
        for line in listing.splitlines():
            fields=line.split()
            for field in fields:
                if field.startswith('/') and Path(field).is_file():libraries[field]=sha(field)
    rc_files=[Path.home()/'.nwchemrc',Path('/etc/nwchemrc')]
    recorded_environment=dict(cpu=Path('/proc/cpuinfo').read_text(),libraries=libraries,
        nwchemrc={str(p):sha(p) if p.exists() else None for p in rc_files},linkage=linkage,
        affinity=sorted(os.sched_getaffinity(0)),
        environment={key:env.get(key) for key in ('MKL_ENABLE_INSTRUCTIONS','MKL_CBWR','MKL_NUM_THREADS',
        'MKL_DOMAIN_NUM_THREADS','MKL_DYNAMIC','MKL_VERBOSE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')},built=built)
    previous=target/'environment.json'
    if previous.exists():
        old=json.loads(previous.read_text())
        if any(old[k]!=recorded_environment[k] for k in ('libraries','environment','built','nwchemrc')):
            raise ValueError('runtime environment changed; use a fresh run')
    else:save(previous,recorded_environment)
    for case in cases:
        fixture=target/case['id']/'fixture';fixture.mkdir(parents=True,exist_ok=True)
        for round_,backend in [(-1,'original')]+[(r,BACKENDS[(j+r)%5]) for r in range(1 if smoke else 5) for j in range(5)]:
            dest=fixture if round_<0 else target/case['id']/f'{round_}-{backend}'
            if (dest/'complete.json').exists():
                verify_sample(dest)
                continue
            with tempfile.TemporaryDirectory(prefix='fabo-nw-sample-',dir=c.get('scratch','/tmp')) as temp:
                local=Path(temp)
                (local/'input.nw').write_text(input_text(case,out/case['geometry']))
                child=env|{'FABO_NWCHEM_MODE':'calibrate' if round_<0 else 'replay','FABO_NWCHEM_STEPS':'1'}
                if round_>=0:shutil.copyfile(fixture/'initial.bin',local/'initial.bin')
                try:
                    run(['taskset','-c',str(c['core']),out/'binaries'/backend,'input.nw'],local,child,local/'nwchem.log')
                    row=sample_record(local)
                    if round_>=0:
                        if sha(local/'initial.bin')!=sha(local/'replayed.bin'):raise ValueError('state replay differs')
                        if sha(local/'density-in.bin')!=sha(fixture/'density-in.bin'):raise ValueError('density differs')
                    save(local/'result.json',dict(backend=backend,round=round_,**row))
                    save(local/'runtime-libraries.json',mapped_libraries((local/'mkl-runtime.txt').read_text()))
                finally:
                    dest.mkdir(parents=True,exist_ok=True)
                    for p in local.iterdir():
                        if p.name in ('nwchem.log','input.nw','initial.bin','replayed.bin','scf-protocol.txt','scf-iterations.csv','scf-summary.txt','result.json','density-in.bin','density-out.bin','fock.bin','mkl-runtime.txt','runtime-libraries.json'):shutil.copyfile(p,dest/p.name)
            save(dest/'complete.json',{p.name:sha(p) for p in dest.iterdir() if p.is_file() and p.name!='complete.json'})

def report(out):
    import numpy as np
    result=[]
    for case in json.loads((out/'cases.json').read_text()):
        base=out/'measurements'/case['id']
        for r in range(5):
            verify_sample(base/f'{r}-original')
            ref=json.loads((base/f'{r}-original/result.json').read_text())
            for backend in BACKENDS:
                folder=base/f'{r}-{backend}';verify_sample(folder)
                row=json.loads((folder/'result.json').read_text())
                sample_record(folder)
                row['case']=case['id']
                delta=float(row['energy_hartree'])-float(ref['energy_hartree'])
                row.update(energy_difference=delta,absolute_energy_difference=abs(delta))
                for matrix in ('fock','density-out'):
                    a=np.fromfile(folder/(matrix+'.bin'),dtype='<f8')
                    b=np.fromfile(base/f'{r}-original'/(matrix+'.bin'),dtype='<f8')
                    if a.shape!=b.shape or not a.size:raise ValueError('matrix shape mismatch')
                    diff=a-b
                    row[matrix+'_max_difference']=float(np.max(np.abs(diff)))
                    row[matrix+'_frobenius_difference']=float(np.linalg.norm(diff))
                result.append(row)
    save(out/'results.json',result)
    summary=[]
    for case in json.loads((out/'cases.json').read_text()):
        reference=statistics.median(float(r['jk_seconds']) for r in result if r['case']==case['id'] and r['backend']=='original')
        for backend in BACKENDS:
            rows=[r for r in result if r['case']==case['id'] and r['backend']==backend]
            times=[float(r['jk_seconds']) for r in rows];median=statistics.median(times)
            summary.append(dict(case=case['id'],backend=backend,jk_seconds=median,speedup=reference/median,
                cv=statistics.stdev(times)/statistics.mean(times),mad_over_median=statistics.median(abs(v-median) for v in times)/median,
                fock_seconds=statistics.median(float(r['fock_seconds']) for r in rows),
                update_seconds=statistics.median(float(r['scf_seconds']) for r in rows),
                energy_repeat_range=max(float(r['energy_hartree']) for r in rows)-min(float(r['energy_hartree']) for r in rows),
                max_energy_difference=max(r['absolute_energy_difference'] for r in rows),
                max_fock_difference=max(r['fock_max_difference'] for r in rows),
                max_density_difference=max(r['density-out_max_difference'] for r in rows)))
    save(out/'summary.json',summary)
    with (out/'summary.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cases=json.loads((out/'cases.json').read_text())
    fig,axes=plt.subplots(4,3,figsize=(15,13))
    for ax,case in zip(axes.flat,cases):
        rows=[r for r in summary if r['case']==case['id']]
        ax.bar([r['backend'] for r in rows],[r['jk_seconds'] for r in rows])
        ax.set_title(case['id']);ax.set_ylabel('JK build / s');ax.tick_params(axis='x',rotation=30)
    fig.tight_layout();fig.savefig(out/'jk-times.pdf');plt.close(fig)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','build','smoke','benchmark','report'));p.add_argument('--run',type=Path,required=True);p.add_argument('--config',type=Path)
    a=p.parse_args();out=a.run.resolve()
    if a.stage=='prepare':prepare(out,json.loads(a.config.read_text()))
    elif a.stage=='build':build(out)
    elif a.stage=='report':report(out)
    else:measure(out,smoke=a.stage=='smoke')

if __name__=='__main__':main()

"""Fixed-state NWChem comparison with independent def2-SVP stack sizing."""
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
import struct

from benchmark.nwchem.bindings import BACKENDS, SHARED_TAIL, header
from benchmark.nwchem.simint_binding import patch as patch_simint
from benchmark.nwchem.patch_nwchem import patch_single_update

ROOT=Path(__file__).resolve().parents[1]
NWCHEM='e2869a2c81445f2edfd25bbae652d099fabb9a92'
SIMINT='38b24bb040c647e4acc0e040457180b574089c58'
BASES={'6-31G*':'6-31gs','def2-SVP':'def2-svp','cc-pVDZ':'cc-pvdz'}
ALL_BACKENDS=(*BACKENDS,'reference')

def reference_cmake(source, prefix):
    """Static Simint consumers (including its examples) need the oracle libs."""
    return (f'\ntarget_sources(simint PRIVATE "{source}")\n'
            f'set_source_files_properties("{source}" PROPERTIES COMPILE_OPTIONS "-fno-fast-math;-ffp-contract=off;-fno-lto")\n'
            f'target_link_libraries(simint PUBLIC "{prefix}/lib/libmpfr.so" "{prefix}/lib/libgmp.so")\n')

def workflow_files():
    return [Path(__file__).resolve(), *sorted((ROOT/'benchmark/nwchem').glob('*.py')),
            *sorted((ROOT/'benchmark/nwchem').glob('*.F')), ROOT/'benchmark/nwchem/mkl_dispatch.c',
            ROOT/'benchmark/nwchem/highway_gather.patch',ROOT/'benchmark/nwchem/reference.cc',
            ROOT/'benchmark/nwchem/reference_check.cc',
            ROOT/'workflow/quick/geometry.py',ROOT/'workflow/nwchem_cluster.py',ROOT/'workflow/scripts/quick_reference_data.py',
            ROOT/'workflow/additive/reference.py']

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
    verify_input_modes(out)
    # Reproduction uses the same driver and patches that prepared the run.
    verify_manifest(ROOT,json.loads((out/'workflow.json').read_text()))

def verify_input_modes(out):
    # Older archives lack the mode manifest; still reject the known failure
    # before spending minutes building unrelated Simint variants.
    for name in ('src/config/strip_compiler.sh','src/config/check_env.sh',
                 'src/util/util_nwchem_version.bash','src/tools/get-tools-github'):
        path=out/'nwchem'/name
        if not path.is_file() or not path.stat().st_mode & 0o111:
            raise ValueError('missing executable NWChem script: '+str(path))
    modes=out/'input-modes.json'
    if modes.exists():
        for name,expected in json.loads(modes.read_text()).items():
            if (out/name).stat().st_mode & 0o111 != expected:
                raise ValueError('changed executable mode: '+name)

def restart_prepared(source,out):
    """Clone only verified prepared inputs, preserving permissions, not results."""
    source=source.resolve();out=out.resolve()
    manifest=json.loads((source/'inputs.json').read_text())
    verify_manifest(source,manifest);verify_input_modes(source)
    out.mkdir(parents=True,exist_ok=False)
    for name in manifest:
        if name.startswith('driver/') or name in ('workflow.json','input-modes.json','restart.json'):continue
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('invalid snapshot path')
        destination=out/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source/relative,destination)
    save(out/'restart.json',dict(source_run=str(source),source_manifest_sha256=sha(source/'inputs.json'),
                               reuse='Verified prepared inputs only; copy2 preserves executable permissions'))
    freeze_workflow(out);verify_inputs(out)

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
    for matrix in ('density-in','density-out','fock','hcore'):
        values=np.fromfile(folder/(matrix+'.bin'),dtype='<f8')
        if (folder/(matrix+'.bin')).stat().st_size!=8*protocol[1]**2 or not np.all(np.isfinite(values)):
            raise ValueError('invalid matrix '+matrix)
    energy=(folder/'energy.bin').read_bytes()
    if len(energy)!=8 or struct.unpack('<d',energy)[0]!=float(rows[0]['energy_hartree']):raise ValueError('energy bits disagree with diagnostic')
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
    if not config['copies'] or config['copies']!=sorted(set(config['copies'])) or any(type(v)!=int or v<1 for v in config['copies']):raise ValueError('invalid copy counts')
    if config['rounds']<2 or config['reference_rounds']!=2 or config['minimum_fock_seconds']<=0:raise ValueError('invalid protocol')
    if not config['systems'] or len(set(config['systems']))!=len(config['systems']) or set(config['bases'])!=set(BASES):raise ValueError('invalid workload selection')
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
    shutil.copytree(ROOT/'include',out/'include')
    cases=[]
    from workflow.quick.geometry import stack_geometry
    for system in config['systems']:
        matches=list(Path(config['s66x8']).rglob(f'{system:02d}_*_1.00.xyz'))
        if len(matches)!=1:raise ValueError(f'expected one equilibrium geometry for {system}')
        path=out/'geometries'/matches[0].name;path.parent.mkdir(exist_ok=True);shutil.copyfile(matches[0],path)
        atoms=[line.split() for line in path.read_text().splitlines()[2:]]
        for copies in config['copies']:
            text,translation=stack_geometry(atoms,copies,config['spacing_angstrom'])
            stacked=out/'geometries'/f'{system:02d}-stack-{copies}.xyz';stacked.write_text(text)
            for basis in config['bases']:
                cases.append(dict(id=f'{system:02d}-stack-{copies}-{basis.lower().replace("*","s")}',system=system,
                    copies=copies,atoms=len(atoms)*copies,translation=translation,original_sha256=sha(path),
                    basis=basis,geometry=str(stacked.relative_to(out)),geometry_sha256=sha(stacked)))
    save(out/'cases.json',cases)
    reference=out/'reference';reference.mkdir()
    from workflow.scripts.quick_reference_data import generate,fixtures
    generate(reference/'table.bin');fixtures(reference/'fixtures.bin')
    freeze_workflow(out)

def freeze_workflow(out):
    """Publish the source identity last, before any build/measurement starts."""
    if (out/'built.json').exists():raise ValueError('cannot refreeze a built run')
    verify_input_modes(out)
    save(out/'workflow.json',{str(p.relative_to(ROOT)):sha(p) for p in workflow_files()})
    # Copy the exact source code too; hashes alone are not a reproduction archive.
    for p in workflow_files():
        target=out/'driver'/p.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    save(out/'input-modes.json',{str(p.relative_to(out)):p.stat().st_mode & 0o111 for p in out.rglob('*')
                                if p.is_file() and p.name not in ('inputs.json','input-modes.json')})
    save(out/'inputs.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'inputs.json'})

def build(out):
    c=json.loads((out/'config.json').read_text());env=environment(c)
    if os.uname().nodename.split('.')[0] != c['build_node']:raise RuntimeError('wrong build node')
    verify_inputs(out)
    if (out/'built.json').exists():raise ValueError('already built; use a new run to rebuild')
    with tempfile.TemporaryDirectory(prefix='fabo-nw-',dir=c.get('scratch','/tmp')) as temp:
        work=Path(temp);gen=work/'generator';shutil.copytree(out/'generator',gen)
        log=out/'build.log'
        syntax_preflight(c,env,work,log)
        mkl=Path(c['mkl_root'])
        oracle=work/'reference-check'
        run([c['cxx'],'-O2','-std=c++17','-fno-fast-math','-ffp-contract=off',
             '-I'+str(mkl/'include'),ROOT/'benchmark/nwchem/reference.cc',ROOT/'benchmark/nwchem/reference_check.cc',
             '-L'+str(mkl/'lib'),'-lmpfr','-lgmp','-o',oracle],work,env,log)
        run([oracle,out/'reference/fixtures.bin'],work,env|{'FABO_REFERENCE_TABLE':str(out/'reference/table.bin')},out/'reference-check.log')
        run([oracle,out/'reference/fixtures.bin'],work,env|{'FABO_REFERENCE_TABLE':str(out/'reference/table.bin'),'FABO_REFERENCE_FORCE_FALLBACK':'1'},out/'reference-fallback-check.log')
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
        for backend in ALL_BACKENDS:
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
                if backend=='reference':
                    f.write(reference_cmake(ROOT/'benchmark/nwchem/reference.cc',mkl))
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
        libs=f'-L{mkl}/lib -lmkl_gf_ilp64 -lmkl_sequential -lmkl_core -lmpfr -lgmp -lpthread -lm -ldl'
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
        save(out/'built.json',{'binaries':{b:sha(binaries/b) for b in (*ALL_BACKENDS,'mkl-dispatch')},'basis':{b:sha(basis/b) for b in BASES.values()},
            'architecture':c['architecture'],'flags':flags,'tool_versions':tools,
            'linkage':{b:subprocess.check_output(['ldd',str(binaries/b)],env=env,text=True) for b in ALL_BACKENDS}})

def input_text(case,geometry):
    return '\n'.join(['start fabo','scratch_dir .','permanent_dir .','memory total 8192 mb','charge 0','geometry units angstrom noautosym noautoz','symmetry c1',
        *geometry.read_text().splitlines()[2:],'end','basis spherical segment',f' * library "{case["basis"]}"','end',
        'set int:cando_txs f','set int:cando_nw f','set fock:replicated t','scf',' rhf',' direct',' diis',' maxiter 2',
        ' vectors input atomic output final.movecs','end','task scf energy',''])

def selected_cases(out):
    config=json.loads((out/'config.json').read_text())
    cases=json.loads((out/'cases.json').read_text());chosen={}
    for system in config['systems']:
        for case in (r for r in cases if r['system']==system and r['basis']=='def2-SVP'):
            fixture=out/'sizing'/case['id']/'fixture'
            verify_sample(fixture)
            if float(sample_record(fixture)['fock_seconds'])>=config['minimum_fock_seconds']:
                chosen[str(system)]=case;break
        else:raise ValueError('no qualifying stack count')
    selected=[r for r in cases if r['copies']==chosen[str(r['system'])]['copies']]
    if json.loads((out/'selected-stacks.json').read_text())!=chosen or json.loads((out/'selected-cases.json').read_text())!=selected:
        raise ValueError('selected workload differs from sizing evidence')
    return selected

def measure(out, smoke=False, sizing=False, reference=False):
    import fcntl
    lock=(out/'measurement.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    c=json.loads((out/'config.json').read_text());env=environment(c)
    verify_inputs(out)
    if os.uname().nodename.split('.')[0]!=c['timing_node']:raise RuntimeError('wrong timing node')
    built=json.loads((out/'built.json').read_text())
    for b in BASES.values():
        if sha(out/'basis'/b)!=built['basis'][b]:raise ValueError('basis changed')
    for b in (*ALL_BACKENDS,'mkl-dispatch'):
        if sha(out/'binaries'/b)!=built['binaries'][b]:raise ValueError('binary changed')
    env['NWCHEM_BASIS_LIBRARY']=str(out/'basis')+'/'
    env['FABO_REFERENCE_TABLE']=str(out/'reference/table.bin')
    cases=json.loads((out/'cases.json').read_text())
    if not smoke and not sizing:
        cases=selected_cases(out)
    if sizing:cases=[r for r in cases if r['basis']=='def2-SVP']
    if not smoke:
        smoke_case=json.loads((out/'cases.json').read_text())[0]
        for b in ALL_BACKENDS:verify_sample(out/'smoke'/smoke_case['id']/f'0-{b}')
    if smoke:cases=cases[:1]
    target=out/('smoke' if smoke else 'sizing' if sizing else 'measurements')
    target.mkdir(exist_ok=True)
    evidence=subprocess.check_output([str(out/'binaries/mkl-dispatch')],env=env,text=True)
    (target/'mkl-dispatch.txt').write_text(evidence)
    libraries=mapped_libraries(evidence)
    linkage={b:subprocess.check_output(['ldd',str(out/'binaries'/b)],env=env,text=True) for b in ALL_BACKENDS}
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
    chosen={}
    for case in cases:
        if sizing and case['system'] in chosen:continue
        fixture=target/case['id']/'fixture';fixture.mkdir(parents=True,exist_ok=True)
        sequence=[(-1,'original')]
        if not sizing:
            backends=ALL_BACKENDS if smoke else ('reference',) if reference else BACKENDS
            sequence += [(r,backends[(j+r)%len(backends)]) for r in range(2 if smoke else c['reference_rounds'] if reference else c['rounds']) for j in range(len(backends))]
        for round_,backend in sequence:
            dest=fixture if round_<0 else target/case['id']/f'{round_}-{backend}'
            if (dest/'complete.json').exists():
                verify_sample(dest)
                sample_record(dest)
                record=json.loads((dest/'result.json').read_text())
                if record['case']!=case['id'] or record['backend']!=backend or record['round']!=round_:raise ValueError('cached sample identity changed')
                if record['fixture_sha256']!=sha(dest/'initial.bin'):raise ValueError('cached fixture changed')
                if round_>=0 and any(sha(dest/name)!=sha(fixture/name) for name in ('initial.bin','density-in.bin','hcore.bin')):raise ValueError('cached initial state differs')
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
                        if sha(local/'hcore.bin')!=sha(fixture/'hcore.bin'):raise ValueError('core Hamiltonian differs')
                    save(local/'result.json',dict(backend=backend,round=round_,case=case['id'],fixture_sha256=sha(local/'initial.bin'),**row))
                    save(local/'runtime-libraries.json',mapped_libraries((local/'mkl-runtime.txt').read_text()))
                finally:
                    dest.mkdir(parents=True,exist_ok=True)
                    for p in local.iterdir():
                        if p.name in ('nwchem.log','input.nw','initial.bin','replayed.bin','scf-protocol.txt','scf-iterations.csv','scf-summary.txt','result.json','density-in.bin','density-out.bin','fock.bin','hcore.bin','energy.bin','mkl-runtime.txt','runtime-libraries.json'):shutil.copyfile(p,dest/p.name)
            save(dest/'complete.json',{p.name:sha(p) for p in dest.iterdir() if p.is_file() and p.name!='complete.json'})
        if sizing:
            row=sample_record(fixture)
            print('sizing',case['id'],row['fock_seconds'],flush=True)
            if float(row['fock_seconds'])>=c['minimum_fock_seconds']:chosen[case['system']]=case
    if sizing:
        if set(chosen)!=set(c['systems']):raise RuntimeError('stack candidates exhausted before timing target; extend copies in a new run')
        all_cases=json.loads((out/'cases.json').read_text())
        selected=[r for r in all_cases if r['copies']==chosen[r['system']]['copies']]
        for case in selected:
            if case['geometry_sha256']!=chosen[case['system']]['geometry_sha256']:raise ValueError('geometry changed across bases')
        save(out/'selected-stacks.json',chosen);save(out/'selected-cases.json',selected)
    if smoke or reference:
        for case in cases:
            for backend in (ALL_BACKENDS if smoke else ALL_BACKENDS):
                count=2 if smoke or backend=='reference' else c['rounds']
                folders=[target/case['id']/f'{r}-{backend}' for r in range(count)]
                check_repeatability(folders)

def check_repeatability(folders):
    for folder in folders:verify_sample(folder);sample_record(folder)
    for name in ('density-in.bin','density-out.bin','fock.bin','hcore.bin','energy.bin'):
        if len({sha(p/name) for p in folders})!=1:raise ValueError('nonreproducible '+name)

def report(out):
    import numpy as np
    result=[]
    cases=selected_cases(out)
    config=json.loads((out/'config.json').read_text())
    for case in cases:
        base=out/'measurements'/case['id']
        for backend in BACKENDS:
            check_repeatability([base/f'{r}-{backend}' for r in range(config['rounds'])])
        for r in range(config['rounds']):
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
    for case in cases:
        reference=statistics.median(float(r['jk_seconds']) for r in result if r['case']==case['id'] and r['backend']=='original')
        for backend in BACKENDS:
            rows=[r for r in result if r['case']==case['id'] and r['backend']==backend]
            times=[float(r['jk_seconds']) for r in rows];median=statistics.median(times)
            summary.append(dict(case=case['id'],system=case['system'],copies=case['copies'],atoms=case['atoms'],basis=case['basis'],geometry_sha256=case['geometry_sha256'],backend=backend,jk_seconds=median,speedup=reference/median,
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
    fig,axes=plt.subplots(len(config['systems']),3,figsize=(15,3.25*len(config['systems'])),squeeze=False)
    for ax,case in zip(axes.flat,cases):
        rows=[r for r in summary if r['case']==case['id']]
        ax.bar([r['backend'] for r in rows],[r['jk_seconds'] for r in rows])
        ax.set_title(case['id']);ax.set_ylabel('JK build / s');ax.tick_params(axis='x',rotation=30)
    fig.tight_layout();fig.savefig(out/'jk-times.pdf');plt.close(fig)

def reference_report(out):
    import numpy as np
    config=json.loads((out/'config.json').read_text());results=[]
    for case in selected_cases(out):
        base=out/'measurements'/case['id'];ref=base/'0-reference'
        for backend in ALL_BACKENDS:
            folders=[base/f'{r}-{backend}' for r in range(config['reference_rounds'] if backend=='reference' else config['rounds'])]
            check_repeatability(folders)
            p=folders[0];energy=struct.unpack('<d',(p/'energy.bin').read_bytes())[0];re=struct.unpack('<d',(ref/'energy.bin').read_bytes())[0]
            row=dict(case=case,backend=backend,energy_hartree=energy,energy_difference=energy-re,bitwise_reproducible=True)
            for name in ('fock','density-out'):
                delta=np.fromfile(p/(name+'.bin'),dtype='<f8')-np.fromfile(ref/(name+'.bin'),dtype='<f8')
                row[name]=dict(max_absolute=float(np.max(np.abs(delta))),frobenius=float(np.linalg.norm(delta)))
            results.append(row)
    save(out/'reference-summary.json',dict(reference='Correctly-rounded Boys substitution, not exact molecular observables',results=results))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','restart','build','smoke','size','benchmark','reference','report'));p.add_argument('--run',type=Path,required=True);p.add_argument('--config',type=Path);p.add_argument('--source-run',type=Path)
    a=p.parse_args();out=a.run.resolve()
    if a.stage=='prepare':prepare(out,json.loads(a.config.read_text()))
    elif a.stage=='restart':
        if a.source_run is None:p.error('restart requires --source-run')
        restart_prepared(a.source_run,out)
    elif a.stage=='build':build(out)
    elif a.stage=='report':report(out)
    else:
        measure(out,smoke=a.stage=='smoke',sizing=a.stage=='size',reference=a.stage=='reference')
        if a.stage=='reference':reference_report(out)

if __name__=='__main__':main()

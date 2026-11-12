import json
from pathlib import Path
import shutil
import subprocess

import pytest
from benchmark.nwchem.bindings import BACKENDS, header, SHARED_TAIL
from benchmark.nwchem.patch_nwchem import patch_single_update
from benchmark.nwchem.simint_binding import patch
from workflow.nwchem_compare import environment,input_text,sample_record,save,sha,verify_sample,syntax_preflight

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('backend',BACKENDS[1:])
@pytest.mark.parametrize('n',range(9))
def test_bindings(n,backend):
    text=header(n,backend)
    assert f'namespace fabo_nw_{backend}_{n}' in text
    assert f'out[{n}]' in text or f'out+{n}' in text
    assert 'copy_from' not in text and 'Store(' not in text
    if backend=='fabo':
        assert f'evaluate<0,{n}>' in text
        assert 'make_evaluator(table.view()' in text

def test_patch_real_source(tmp_path):
    source=ROOT/'.work/nwchem-setup/dependencies/nwchem'
    if not source.exists():pytest.skip('pinned NWChem source unavailable')
    for p in ('src/ddscf','src/NWints/simint/source'):shutil.copytree(source/p,tmp_path/p)
    patch_single_update(tmp_path)
    text=(tmp_path/'src/ddscf/rohf_diis.F').read_text()
    start=text.index('      do iter=1,maxiter')
    end=text.index('      enddo',start)
    loop=text[start:end]
    assert loop.count('rohf_energy(')==1
    assert loop.index('ga_copy(g_tmp, g_movecs)') < loop.index('fabo_nw_record') < loop.index('goto 333')
    assert 'fabo_nw_stop' not in loop
    with pytest.raises(ValueError):patch_single_update(tmp_path)

def test_environment(monkeypatch):
    monkeypatch.setenv('MKL_CBWR','SSE2');monkeypatch.setenv('MKL_ENABLE_INSTRUCTIONS','AVX2')
    e=environment({})
    assert 'MKL_CBWR' not in e and 'MKL_ENABLE_INSTRUCTIONS' not in e
    assert e['MKL_NUM_THREADS']==e['OMP_NUM_THREADS']=='1'

def test_input(tmp_path):
    xyz=tmp_path/'water.xyz';xyz.write_text('1\ntest\nHe 0 0 0\n')
    text=input_text({'basis':'cc-pVDZ'},xyz)
    assert ' rhf\n direct' in text and 'cc-pVDZ' in text
    assert 'set int:cando_nw f' in text and 'basis spherical segment' in text

def test_reference_binding_has_explicit_valid_lanes():
    text=header(8,'reference')
    assert 'int lanes' in text and 'fabo_reference_boys(8,lanes,input,values)' in text
    assert 'reference' not in BACKENDS

def test_reference_libraries_propagate_to_static_consumers():
    from workflow.nwchem_compare import reference_cmake
    text=reference_cmake('/source/reference.cc','/environment')
    assert 'target_link_libraries(simint PUBLIC "/environment/lib/libmpfr.so" "/environment/lib/libgmp.so")' in text
    assert '-fno-fast-math;-ffp-contract=off;-fno-lto' in text

def test_restart_preserves_and_checks_executable_modes(tmp_path,monkeypatch):
    import workflow.nwchem_compare as module
    repo=tmp_path/'repo';repo.mkdir();driver=repo/'driver.py';driver.write_text('# driver\n')
    monkeypatch.setattr(module,'ROOT',repo)
    monkeypatch.setattr(module,'workflow_files',lambda:[driver])
    source=tmp_path/'original';source.mkdir()
    for name in ('src/config/strip_compiler.sh','src/config/check_env.sh',
                 'src/util/util_nwchem_version.bash','src/tools/get-tools-github'):
        p=source/'nwchem'/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
    module.freeze_workflow(source)
    (source/'build.log').write_text('failed build')
    dest=tmp_path/'restart';module.restart_prepared(source,dest)
    assert not (dest/'build.log').exists()
    module.verify_inputs(dest)
    script=dest/'nwchem/src/config/strip_compiler.sh'
    assert script.stat().st_mode & 0o111 == 0o111
    script.chmod(0o644)
    with pytest.raises(ValueError,match='executable'):module.verify_inputs(dest)
    with pytest.raises(ValueError,match='executable'):module.restart_prepared(dest,tmp_path/'bad')

def test_bundled_driver_has_standalone_geometry_and_scheduler(tmp_path):
    from workflow.nwchem_compare import workflow_files
    for path in workflow_files():
        dest=tmp_path/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
    import sys
    subprocess.run([sys.executable,'-c',
        'from workflow.quick.geometry import stack_geometry; '
        'from workflow.nwchem_cluster import write_scripts; '
        'from workflow.nwchem_compare import prepare; '
        'assert stack_geometry([["H","0","0","0"]],2,3.4)[1]==[3.4,0.,0.]'],cwd=tmp_path,check=True)

def test_exact_repeatability(tmp_path):
    from workflow.nwchem_compare import check_repeatability
    folders=[tmp_path/str(i) for i in range(2)]
    for p in folders:
        write_sample(p)
        save(p/'complete.json',{f.name:sha(f) for f in p.iterdir()})
    check_repeatability(folders)
    p=folders[1]
    import numpy as np
    np.array([1,0,0,np.nextafter(1.,2.)],dtype='<f8').tofile(p/'fock.bin')
    save(p/'complete.json',{f.name:sha(f) for f in p.iterdir() if f.name!='complete.json'})
    with pytest.raises(ValueError,match='nonreproducible fock'):check_repeatability(folders)

def test_frozen_selection_is_bound_to_sizing_records(tmp_path):
    from workflow.nwchem_compare import selected_cases
    cases=[dict(id=f'{n}-{basis}',system=1,copies=n,basis=basis,geometry_sha256=f'geometry-{n}') for n in (1,2) for basis in ('def2-SVP','cc-pVDZ')]
    save(tmp_path/'config.json',dict(systems=[1],minimum_fock_seconds=2))
    save(tmp_path/'cases.json',cases)
    for case in cases:
        if case['basis']!='def2-SVP':continue
        p=tmp_path/'sizing'/case['id']/'fixture';write_sample(p)
        if case['copies']==1:
            csv=p/'scf-iterations.csv';csv.write_text(csv.read_text().replace('1,2,1,3,','1,1.5,1,3,'))
        save(p/'complete.json',{f.name:sha(f) for f in p.iterdir()})
    save(tmp_path/'selected-stacks.json',{'1':cases[2]})
    save(tmp_path/'selected-cases.json',cases[2:])
    assert selected_cases(tmp_path)==cases[2:]
    save(tmp_path/'selected-cases.json',cases[:2])
    with pytest.raises(ValueError,match='sizing evidence'):selected_cases(tmp_path)

@pytest.mark.parametrize('compiler',['g++','clang++'])
def test_compile_fabo_binding(tmp_path,compiler):
    hwy=ROOT/'third_party/workflow/highway'
    if not shutil.which(compiler) or not hwy.exists():pytest.skip('compiler/Highway required')
    simint=tmp_path/'simint/vectorization';simint.mkdir(parents=True)
    (simint/'vectorization.h').write_text('#include <immintrin.h>\n#define SIMINT_SIMD_LEN 8\n#define SIMINT_DBLTYPE __m512d\n')
    (tmp_path/'shared_tail.h').write_text(SHARED_TAIL)
    (tmp_path/'binding.h').write_text(header(4,'fabo'))
    (tmp_path/'test.cc').write_text('#include "binding.h"\nstatic_assert(!fast_boys::simd::HWY_NAMESPACE::kDefaultUseSoftwareGather);\nvoid f(__m512d x,__m512d* out){fabo_nw_fabo_4::evaluate(x,out);}\n')
    subprocess.run([compiler,'-std=c++20','-march=sapphirerapids','-DHWY_COMPILE_ONLY_STATIC',
        '-I'+str(tmp_path),'-I'+str(ROOT/'include'),'-I'+str(hwy),'-fsyntax-only',str(tmp_path/'test.cc')],check=True)

@pytest.mark.parametrize('backend',['vsr','laikov','libintx'])
def test_compile_comparator(tmp_path,backend):
    hwy=ROOT/'third_party/workflow/highway'
    # All five production variants use GCC; do not mix integral compilers.
    compiler='g++'
    if not shutil.which(compiler) or not hwy.exists():pytest.skip('compiler/Highway required')
    from workflow.comparator_ports import copy_cpu_ports
    copy_cpu_ports(tmp_path/'legacy/benchmark/third_party_boys_impl')
    simint=tmp_path/'simint/vectorization';simint.mkdir(parents=True)
    (simint/'vectorization.h').write_text('#include <immintrin.h>\n#define SIMINT_SIMD_LEN 8\n#define SIMINT_DBLTYPE __m512d\n')
    config=tmp_path/'libintx';config.mkdir()
    (config/'config.h').write_text('#pragma once\n#define LIBINTX_SIMD 1\nnamespace libintx { constexpr int LMAX=3,XMAX=4,KMAX=10; }\n')
    (tmp_path/'binding.h').write_text(header(4,backend))
    (tmp_path/'test.cc').write_text(f'#include "binding.h"\nvoid f(__m512d x,__m512d* out){{fabo_nw_{backend}_4::evaluate(x,out);}}\n')
    subprocess.run([compiler,'-std=c++20','-march=sapphirerapids','-DHWY_COMPILE_ONLY_STATIC',
        '-I'+str(tmp_path),'-I'+str(ROOT/'include'),'-I'+str(hwy),
        '-I'+str(tmp_path/'legacy/benchmark/third_party_boys_impl'),
        '-I'+str(ROOT/'third_party/libintx/src'),'-I'+str(ROOT/'third_party/libintx/include/eigen3'),
        '-fsyntax-only',str(tmp_path/'test.cc')],check=True)


def test_gcc_experimental_simd(tmp_path):
    if not shutil.which('g++'):pytest.skip('GCC unavailable')
    log=tmp_path/'compile.log'
    syntax_preflight({'cxx':'g++','architecture':'sapphirerapids'},environment({}),tmp_path,log)


def test_simint_patch(tmp_path):
    folder=tmp_path/'simint/ostei';folder.mkdir(parents=True)
    (tmp_path/'simint/CMakeLists.txt').write_text('add_library(simint kernels.c)\n')
    for n in range(3):
        (folder/f'kernel{n}.c').write_text(f'boys_F_split(result, F_x, {n});\n')
        b=tmp_path/f'bindings/order-{n}';b.mkdir(parents=True)
        save(b/'binding.json',{'namespace':f'fabo_nw_fabo_{n}'})
    result=patch(tmp_path,'fabo',2,tmp_path/'bindings')
    assert result['orders']==[0,1,2]
    for n in range(3):
        assert f'::fabo_nw_fabo_{n}::evaluate(F_x,result)' in (folder/f'kernel{n}.c').read_text()
    assert 'LANGUAGE CXX' in (tmp_path/'simint/CMakeLists.txt').read_text()
    with pytest.raises(ValueError):patch(tmp_path,'fabo',2,tmp_path/'bindings')


def write_sample(folder):
    import numpy as np
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'scf-iterations.csv').write_text('iteration,fock_seconds,jk_seconds,scf_seconds,energy_hartree,gradient_norm,energy_gradient_evaluations\n1,2,1,3,-4,0.1,1\n')
    (folder/'scf-protocol.txt').write_text('1 2 2 1\n')
    (folder/'mkl-runtime.txt').write_text('THREADS 1\nMAP fake\n')
    import struct
    (folder/'energy.bin').write_bytes(struct.pack('<d',-4))
    for name in ('density-in','density-out','fock','hcore'):
        np.array([1,0,0,1],dtype='<f8').tofile(folder/(name+'.bin'))


def test_sample_validation(tmp_path):
    write_sample(tmp_path)
    assert sample_record(tmp_path)['iteration']=='1'
    (tmp_path/'fock.bin').write_bytes(b'')
    with pytest.raises(ValueError,match='invalid matrix'):sample_record(tmp_path)


def test_sample_hashes(tmp_path):
    (tmp_path/'result.json').write_text('{}')
    save(tmp_path/'complete.json',{'result.json':sha(tmp_path/'result.json')})
    verify_sample(tmp_path)
    (tmp_path/'result.json').write_text('{"changed":true}')
    with pytest.raises(ValueError,match='changed artifact'):verify_sample(tmp_path)


def test_fortran_hooks_syntax(tmp_path):
    if not shutil.which('gfortran'):pytest.skip('gfortran unavailable')
    (tmp_path/'global.fh').write_text('      integer ga_nnodes\n      logical ga_duplicate,ga_destroy\n')
    (tmp_path/'cscf.fh').write_text('      integer nmo,nbf,nclosed,nopen,maxiter,g_movecs(2)\n      integer k_occ,k_eval\n')
    (tmp_path/'mafdecls.fh').write_text('      double precision dbl_mb(100)\n')
    (tmp_path/'util.fh').write_text('      double precision util_wallsec\n')
    for file in ('training_hooks.F','matrices.F'):
        subprocess.run(['gfortran','-fsyntax-only','-cpp','-fdefault-integer-8','-std=legacy',
            '-I'+str(tmp_path),str(ROOT/'benchmark/nwchem'/file)],check=True)


def test_highway_patch(tmp_path):
    from workflow.nwchem_compare import patch_highway
    hwy=ROOT/'third_party/workflow/highway/hwy/ops'
    if not hwy.exists():pytest.skip('pinned Highway unavailable')
    dest=tmp_path/'hwy/ops';dest.mkdir(parents=True)
    for width in (128,256,512):
        shutil.copyfile(hwy/f'x86_{width}-inl.h',dest/f'x86_{width}-inl.h')
    patch_highway(tmp_path)
    for width in (128,256,512):
        assert 'HWY_DISABLE_GCC_GATHER_WORKAROUND' in (dest/f'x86_{width}-inl.h').read_text()
    with pytest.raises(subprocess.CalledProcessError):patch_highway(tmp_path)


@pytest.mark.parametrize('arch',['haswell','icelake-server'])
def test_patched_highway_gathers(tmp_path,arch):
    from workflow.nwchem_compare import patch_highway
    from workflow.additive.tests.simd_support import require_host_isa
    flags=['-march='+arch,'-maes']
    require_host_isa(flags,execute=True)
    source=ROOT/'third_party/workflow/highway/hwy'
    if not shutil.which('g++') or not source.exists():pytest.skip('GCC/Highway unavailable')
    shutil.copytree(source,tmp_path/'hwy')
    patch_highway(tmp_path)
    code=tmp_path/'gathers.cc'
    code.write_text(r'''
#include "hwy/highway.h"
#include <cstdint>
namespace hn=hwy::HWY_NAMESPACE;
template<class D> int check(D d) {
  using T=hn::TFromD<D>;
  const hn::RebindToSigned<D> di;
  using I=hn::TFromD<decltype(di)>;
  HWY_ALIGN_MAX T table[17],out[hn::MaxLanes(d)];
  HWY_ALIGN_MAX I indices[hn::MaxLanes(di)];
  for(int i=0;i<17;++i)table[i]=T(i*13+7);
  for(int repeat=0;repeat<20;++repeat) {
    for(unsigned l=0;l<hn::Lanes(di);++l)indices[l]=repeat<17?repeat:(l*7+repeat)%17;
    auto ix=hn::Load(di,indices);
    hn::Store(hn::GatherIndex(d,table,ix),d,out);
    for(unsigned l=0;l<hn::Lanes(d);++l)if(out[l]!=table[indices[l]])return 1;
    hn::Store(hn::GatherOffset(d,table,hn::Mul(ix,hn::Set(di,sizeof(T)))),d,out);
    for(unsigned l=0;l<hn::Lanes(d);++l)if(out[l]!=table[indices[l]])return 2;
  }
  return 0;
}
template<class T> int types() { return check(hn::ScalableTag<T>()) || check(hn::CappedTag<T,2>()); }
int main(){return types<std::uint32_t>() || types<std::uint64_t>() || types<float>() || types<double>();}
''')
    exe=tmp_path/'gathers'
    subprocess.run(['g++','-std=c++20','-O3','-DHWY_COMPILE_ONLY_STATIC',*flags,'-I'+str(tmp_path),
        str(code),str(tmp_path/'hwy/abort.cc'),'-o',str(exe)],check=True)
    subprocess.run([exe],check=True)

from pathlib import Path
import hashlib
import json
import shutil
import subprocess

import pytest
from benchmark.quick.patch_quick import ROOT, patch


def source_tree(tmp_path):
    for name in ('src/gpu/gpu_get2e_subs.h','src/gpu/cuda/gpu_get2e.cu',
                 'src/gpu/cuda/gpu.cu','src/gpu/cuda/CMakeLists.txt',
                 'src/main.f90','src/modules/quick_scf_module.f90'):
        dst=tmp_path/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'third_party/quick'/name,dst)
    return tmp_path


@pytest.mark.parametrize('variant',['official','fabo_additive'])
def test_patch_and_manifest(tmp_path,variant):
    root=source_tree(tmp_path)
    manifest=patch(root,variant,probe=True)
    cmake=(root/'src/gpu/cuda/CMakeLists.txt').read_text()
    assert 'set(CMAKE_CXX_STANDARD 17)' in cmake
    assert '-std=c++17' in cmake
    calls=(root/'src/gpu/gpu_get2e_subs.h').read_text()
    if variant=='fabo_additive':
        assert calls.count('FaboQuickFmT<FABO_QUICK_FAMILY_MAX>(I + J + K + L,')==2
        assert 'FmT(I + J + K + L,' not in calls
        assert set(manifest['models'])=={'0-4','0-8','0-12'}
        assert 'list(APPEND QUICK_CUDA_SOURCE ../additive_host.cc)' in cmake
        assert 'fabo_quick_boys_init_();\n    PRINTDEBUG' in (root/'src/gpu/cuda/gpu.cu').read_text()
    else:
        assert calls==(ROOT/'third_party/quick/src/gpu/gpu_get2e_subs.h').read_text()
    for name,digest in manifest['copied_sources'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    with pytest.raises(ValueError,match='already patched'):
        patch(root,variant)


def test_context_failure_does_not_modify_source(tmp_path):
    root=source_tree(tmp_path)
    path=root/'src/gpu/cuda/gpu.cu'
    path.write_text(path.read_text().replace('PRINTDEBUG("FINISH GPU INIT")','different_marker'))
    before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='context changed'):
        patch(root,'fabo_additive')
    assert before=={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('enable_f',[False,True])
def test_host_binding_layout(tmp_path,enable_f):
    compiler=shutil.which('clang++')
    if not compiler: pytest.skip('Clang unavailable')
    source=r'''
#include <cstdint>
#include <cstddef>
#define __device__
#define __constant__
#define __forceinline__ inline
struct Dimensions { unsigned x; } gridDim{1},blockDim{17};
#define min(a,b) fake_min(a,b)
#define max(a,b) fake_max(a,b)
#include "additive_binding.cuh"
#ifndef min
#error min macro was not restored
#endif
#undef min
#undef max
extern "C" const std::uint64_t* fabo_quick_host_table(int,std::size_t*);
template<int Family> int check() {
  using M=typename FaboQuickFamily<Family>::Model;
  using T=fast_boys::selected::Tail;
  using O=fast_boys::detail::Binary64;
  std::size_t bytes;
  fabo_quick_main[Family/4-1]=fabo_quick_host_table(M::last,&bytes);
  if(bytes!=M::table_bytes) return 1;
  fabo_quick_tail=fabo_quick_host_table(-1,&bytes);
  auto e=fast_boys::cuda::make_evaluator(
    fast_boys::TableView<M>::from_pointer(fabo_quick_main[Family/4-1]),
    fast_boys::TableView<T>::from_pointer(fabo_quick_tail));
  const double points[]={0.,0.01,1.,100.,1e7,1e8};
  for(int last=0;last<=M::last;++last) for(double x:points) {
    double out[13*17],expected[13];
    for(auto& v:out) v=-1;
    FaboQuickFmT<Family>(last,x,out+5);
    e.template evaluate<0>(x,last,expected);
    for(int i=0;i<13*17;++i) {
      const double value=(i%17==5 && i/17<=last)?expected[i/17]:-1.;
      if(O::bits(out[i])!=O::bits(value)) return 2;
    }
  }
  return 0;
}
int main(){
  static_assert(FaboQuickFamily<4>::last==4);
#ifdef ENABLEF
  static_assert(FaboQuickFamily<8>::last==12);
  return check<4>() || check<8>() || check<12>();
#else
  static_assert(FaboQuickFamily<8>::last==8);
  return check<4>() || check<8>();
#endif
}
'''
    path=tmp_path/'binding.cc'; path.write_text(source)
    command=[compiler,'-std=c++17','-O2','-fno-fast-math','-ffp-contract=off',
             '-I'+str(ROOT/'include'),'-I'+str(ROOT/'benchmark/quick')]
    if enable_f: command+=['-DENABLEF']
    subprocess.run(command+[str(path),str(ROOT/'benchmark/quick/additive_host.cc'),
                            '-o',str(tmp_path/'binding')],check=True,capture_output=True)
    subprocess.run([str(tmp_path/'binding')],check=True)

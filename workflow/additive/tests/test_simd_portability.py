"""Small compile/ABI probes, independent of large constexpr payloads."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from workflow.additive.tests.simd_support import require_host_isa

ROOT = Path(__file__).resolve().parents[3]
HWY = Path(os.environ.get('FABO_HIGHWAY_ROOT', ROOT / 'third_party/workflow/highway'))


def compile_source(tmp_path, source, compiler='clang++', flags=(), link=False):
    require_host_isa(flags,execute=link)
    if not shutil.which(compiler) or not (HWY / 'hwy/highway.h').exists():
        pytest.skip('compiler or Highway unavailable')
    src = tmp_path / 'probe.cc'
    src.write_text(source)
    exe = tmp_path / 'probe'
    cmd = [compiler, '-std=c++17', '-O2', '-ffp-contract=off',
           '-I'+str(ROOT/'include'), '-I'+str(HWY), '-I'+str(tmp_path),
           *flags, str(src)]
    cmd += [str(HWY/'hwy/abort.cc'), '-o', str(exe)] if link else ['-c','-o',str(tmp_path/'probe.o')]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return exe


PROBE = '''
#include "fast_boys/simd_config.h"
#include "fast_boys/selected_simd.h"
namespace fb=fast_boys::simd::HWY_NAMESPACE;
using M=fast_boys::selected::Model<4>;
using T=fast_boys::selected::Tail;
void probe(const std::uint64_t* main,const std::uint64_t* tail,
           fb::V x,fb::V& a,fb::V& b) {
 auto e=fb::make_evaluator(fast_boys::TableView<M>::from_pointer(main),
                          fast_boys::TableView<T>::from_pointer(tail));
 e.evaluate<1,2>(x,a,b);
}
'''


@pytest.mark.parametrize('compiler,flags', [
    ('clang++', ['-DHWY_COMPILE_ONLY_SCALAR']),
    ('g++', ['-DHWY_COMPILE_ONLY_STATIC','-DHWY_DISABLED_TARGETS=0','-march=westmere','-maes']),
    ('aarch64-linux-gnu-g++', ['-DHWY_COMPILE_ONLY_STATIC','-march=armv8-a']),
    ('aarch64-linux-gnu-g++', ['-DHWY_COMPILE_ONLY_STATIC','-march=armv8-a+sve']),
    ('riscv64-linux-gnu-g++', ['-DHWY_COMPILE_ONLY_STATIC','-march=rv64gcv']),
])
def test_compile_portability(tmp_path, compiler, flags):
    if 'riscv' in compiler:
        condition='HWY_TARGET == HWY_RVV'
    elif '-march=armv8-a+sve' in flags:
        condition='(HWY_TARGET & HWY_ALL_SVE) != 0'
    elif 'aarch64' in compiler:
        condition='(HWY_TARGET & HWY_ALL_NEON) != 0'
    elif '-DHWY_COMPILE_ONLY_SCALAR' in flags:
        condition='HWY_TARGET == HWY_SCALAR'
    else:
        condition='HWY_TARGET == HWY_SSE4'
    compile_source(tmp_path, PROBE+f'\nstatic_assert({condition},"test target mismatch");\n', compiler, flags)


def test_foreach_target(tmp_path):
    source = '''
#include "fast_boys/simd_config.h"
#undef HWY_TARGET_INCLUDE
#define HWY_TARGET_INCLUDE "probe.cc"
#include "hwy/foreach_target.h"
#include "fast_boys/selected_simd.h"
HWY_BEFORE_NAMESPACE();
namespace app { namespace HWY_NAMESPACE {
namespace fb=fast_boys::simd::HWY_NAMESPACE;
using M=fast_boys::selected::Model<0>;
using T=fast_boys::selected::Tail;
void Probe(const std::uint64_t* main,const std::uint64_t* tail,double* out) {
 auto e=fb::make_evaluator(fast_boys::TableView<M>::from_pointer(main),
                          fast_boys::TableView<T>::from_pointer(tail));
 fb::V f;
 e.evaluate<0,0>(hwy::HWY_NAMESPACE::Zero(fb::D()),f);
 hwy::HWY_NAMESPACE::StoreU(f,fb::D(),out);
}
} }
HWY_AFTER_NAMESPACE();
'''
    compile_source(tmp_path, source)


@pytest.mark.parametrize('isa', ['avx2','avx512'])
def test_gather_guard_page(tmp_path, isa):
    source = '''
#include "fast_boys/simd.h"
#include <sys/mman.h>
#include <unistd.h>
#include <cstring>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
template<std::uint64_t Max,unsigned Last=Max> bool check(std::uint64_t* table) {
 HWY_ALIGN_MAX std::uint64_t indices[hn::MaxLanes(fb::DU())],a[hn::MaxLanes(fb::DU())],b[hn::MaxLanes(fb::DU())];
 for(unsigned i=0;i<hn::Lanes(fb::DU());++i) indices[i]=i%3 ? 0 : Last;
 auto ix=hn::Load(fb::DU(),indices);
 hn::Store(fb::detail::Gather<true,Max>(table,ix),fb::DU(),a);
 hn::Store(fb::detail::Gather<false,Max>(table,ix),fb::DU(),b);
 for(unsigned i=0;i<hn::Lanes(fb::DU());++i)
  if(a[i]!=table[indices[i]] || a[i]!=b[i]) return false;
 return true;
}
int main() {
 const auto page=sysconf(_SC_PAGESIZE);
 auto* mem=static_cast<unsigned char*>(mmap(nullptr,4*page,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0));
 if(mem==MAP_FAILED || mprotect(mem+page,2*page,PROT_READ|PROT_WRITE)) return 2;
 auto* table=reinterpret_cast<std::uint64_t*>(mem+page);
 for(unsigned i=0;i<2*page/8;++i) table[i]=0x3ff0000000000000ULL+i;
 bool ok=check<255>(table) && check<1023>(table) && check<255>(table+2*page/8-256)
         && check<UINT32_MAX,1023>(table) && check<(1ULL<<32),1023>(table);
 munmap(mem,4*page);
 return !ok;
}
'''
    expected='HWY_AVX3_DL' if isa=='avx512' else 'HWY_AVX2'
    source+=f'\nstatic_assert(HWY_TARGET=={expected},"test must exercise the named ISA");\n'
    flags=['-DHWY_COMPILE_ONLY_STATIC', '-march=icelake-server' if isa=='avx512' else '-march=haswell', '-maes']
    exe=compile_source(tmp_path,source,flags=flags,link=True)
    subprocess.run([exe],check=True)


def test_simd_manifest():
    manifest=json.loads((ROOT/'include/simd-manifest.json').read_text())
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((ROOT/'include'/name).read_bytes()).hexdigest()==digest
    for name,digest in manifest['sources'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((ROOT/'include/manifest.json').read_bytes()).hexdigest()==manifest['numerical_manifest_sha256']


def test_regeneration(tmp_path):
    from workflow.additive.simd_headers import generate
    shutil.copyfile(ROOT/'include/manifest.json',tmp_path/'manifest.json')
    generate(tmp_path)
    manifest=json.loads((tmp_path/'simd-manifest.json').read_text())
    for name in manifest['files']:
        assert (tmp_path/name).read_bytes()==(ROOT/'include'/name).read_bytes()
    assert (tmp_path/'simd-manifest.json').read_bytes()==(ROOT/'include/simd-manifest.json').read_bytes()


@pytest.mark.parametrize('target,flags', [
    ('HWY_AVX2',['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes']),
    ('HWY_AVX3_DL',['-DHWY_COMPILE_ONLY_STATIC','-march=icelake-server']),
    ('HWY_SSE4',['-DHWY_COMPILE_ONLY_STATIC','-DHWY_DISABLED_TARGETS=0','-march=westmere','-maes']),
    ('HWY_SCALAR',['-DHWY_COMPILE_ONLY_SCALAR']),
])
def test_each_correction_byte(tmp_path,target,flags):
    source='''
#include "fast_boys/simd.h"
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
template<int Byte> bool check(fb::U words,const std::uint64_t* inputs) {
 HWY_ALIGN_MAX std::uint64_t out[hn::MaxLanes(fb::DU())];
 hn::Store(fb::detail::ByteAt<Byte>(words),fb::DU(),out);
 for(unsigned i=0;i<hn::Lanes(fb::DU());++i)
  if(out[i]!=((inputs[i]>>(8*Byte))&255)) return false;
 if constexpr(Byte<7) return check<Byte+1>(words,inputs);
 return true;
}
int main() {
 HWY_ALIGN_MAX std::uint64_t inputs[hn::MaxLanes(fb::DU())];
 for(unsigned trial=0;trial<256;++trial) {
  for(unsigned i=0;i<hn::Lanes(fb::DU());++i) {
   inputs[i]=0;
   for(unsigned j=0;j<8;++j)
    inputs[i]|=std::uint64_t((trial+37*i+19*j)&255)<<(8*j);
  }
  if(!check<0>(hn::Load(fb::DU(),inputs),inputs)) return 1;
 }
}
'''+f'\nstatic_assert(HWY_TARGET=={target},"test target mismatch");\n'
    exe=compile_source(tmp_path,source,flags=flags,link=True)
    subprocess.run([exe],check=True)


@pytest.mark.parametrize('compiler',['clang++','g++'])
@pytest.mark.parametrize('flags',[
    ['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes'],
    ['-DHWY_COMPILE_ONLY_STATIC','-march=icelake-server'],
])
def test_x86_byte_shift_instruction(tmp_path,compiler,flags):
    if not shutil.which('objdump'):
        pytest.skip('objdump unavailable')
    source='''
#include "fast_boys/simd.h"
namespace fb=fast_boys::simd::HWY_NAMESPACE;
extern "C" fb::U extract_byte1(fb::U words) {
 return fb::detail::ByteAt<1>(words);
}
'''
    compile_source(tmp_path,source,compiler,flags)
    asm=subprocess.check_output(['objdump','-d',str(tmp_path/'probe.o')],text=True)
    assert 'vpsrldq' in asm, asm


@pytest.mark.parametrize('compiler',['clang++','g++'])
@pytest.mark.parametrize('flags',[
    ['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes'],
    ['-DHWY_COMPILE_ONLY_STATIC','-march=icelake-server'],
])
def test_software_gather_has_no_calls(tmp_path,compiler,flags):
    if not shutil.which('objdump'):
        pytest.skip('objdump unavailable')
    source='''
#include "fast_boys/simd.h"
namespace fb=fast_boys::simd::HWY_NAMESPACE;
extern "C" fb::U gather_words(const std::uint64_t* table,fb::U index) {
 return fb::detail::Gather<true,66371>(table,index);
}
'''
    compile_source(tmp_path,source,compiler,flags)
    asm=subprocess.check_output(['objdump','-dr',str(tmp_path/'probe.o')],text=True)
    assert 'memcpy' not in asm and '\tcall' not in asm, asm


def test_runtime_isa_gating(monkeypatch):
    from workflow.additive.tests import simd_support as support
    monkeypatch.setattr(support.platform,'machine',lambda:'aarch64')
    with pytest.raises(pytest.skip.Exception,match='x86 host'):
        support.require_host_isa(['-march=haswell'],execute=True)
    monkeypatch.setattr(support.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(support.Path,'exists',lambda self:True)
    monkeypatch.setattr(support.Path,'read_text',lambda self:'flags : sse2 ssse3 sse4_1 sse4_2 popcnt aes pclmulqdq\n')
    support.require_host_isa(['-march=westmere'],execute=True)
    with pytest.raises(pytest.skip.Exception,match='unsupported runtime ISA'):
        support.require_host_isa(['-march=haswell'],execute=True)
    support.require_host_isa(['-march=haswell'],execute=False)

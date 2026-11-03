"""Correctness and code-generation probes for the GCC false-dependency fix."""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from workflow.additive.tests.simd_support import require_host_isa

ROOT=Path(__file__).resolve().parents[3]
HWY=Path(os.environ.get('FABO_HIGHWAY_ROOT',ROOT/'third_party/workflow/highway'))
SOURCE=r'''
#include "fast_boys/simd_config.h"
#include "fast_boys/simd.h"
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
extern "C" HWY_NOINLINE fb::U native_words(const std::uint64_t* table,fb::U indices) {
  return fb::detail::Gather<false,16>(table,indices);
}
extern "C" HWY_NOINLINE fb::U software_words(const std::uint64_t* table,fb::U indices) {
  return fb::detail::Gather<true,16>(table,indices);
}
int main() {
  // Arbitrary bit patterns, including NaNs as doubles: gather is bitwise.
  HWY_ALIGN_MAX std::uint64_t table[17],idx[hn::MaxLanes(fb::DU())],out[hn::MaxLanes(fb::DU())];
  for(unsigned i=0;i<17;++i) table[i]=0xfff0000000000000ULL+(i*0x20000001000001ULL);
  for(unsigned batch=0;batch<40;++batch) {
    for(unsigned lane=0;lane<hn::Lanes(fb::DU());++lane)
      idx[lane]=batch<17?batch:(batch+lane*7)%17;
    const auto index=hn::Load(fb::DU(),idx);
    for(auto value:{native_words(table,index),software_words(table,index)}) {
      hn::Store(value,fb::DU(),out);
      for(unsigned lane=0;lane<hn::Lanes(fb::DU());++lane)
        if(out[lane]!=table[idx[lane]]) return 1;
    }
  }
}
'''


@pytest.mark.parametrize('compiler',['g++','clang++'])
@pytest.mark.parametrize('arch',['haswell','icelake-server'])
def test_native_gather(tmp_path,compiler,arch):
    if not shutil.which(compiler) or not (HWY/'hwy/highway.h').exists():pytest.skip('compiler/Highway unavailable')
    flags=['-march='+arch,'-maes']
    require_host_isa(flags,execute=True)
    src=tmp_path/'gather.cc';src.write_text(SOURCE)
    exe=tmp_path/'gather'
    subprocess.run([compiler,'-std=c++17','-O3','-ffast-math','-DHWY_COMPILE_ONLY_STATIC',*flags,
        '-I'+str(ROOT/'include'),'-I'+str(HWY),str(src),str(HWY/'hwy/abort.cc'),'-o',str(exe)],check=True)
    subprocess.run([exe],check=True)


@pytest.mark.parametrize('arch',['haswell','icelake-server','sapphirerapids'])
def test_gcc_zero_merge_assembly(tmp_path,arch):
    if not shutil.which('g++') or not (HWY/'hwy/highway.h').exists():pytest.skip('GCC/Highway unavailable')
    src=tmp_path/'gather.cc';src.write_text(SOURCE.split('int main()')[0])
    asm=tmp_path/'gather.s'
    subprocess.run(['g++','-std=c++17','-O3','-ffast-math','-DHWY_COMPILE_ONLY_STATIC',
        '-march='+arch,'-maes','-I'+str(ROOT/'include'),'-I'+str(HWY),str(src),'-S','-o',str(asm)],check=True)
    body=asm.read_text().split('native_words:',1)[1].split('.size',1)[0]
    gather=re.search(r'v(?:p)?gather\w+[^\n]*',body)
    assert gather,body
    # A value-producing zero idiom must survive before the masked gather.
    before=body[:gather.start()]
    destination=re.search(r',\s*%[xyz]mm(\d+)(?:\{|$)',gather.group()).group(1)
    assert re.search(r'v(?:p?xor\w*)\s+%[xyz]mm'+destination+
        r',\s*%[xyz]mm'+destination+r',\s*%[xyz]mm'+destination+r'\b',before),body
    assert not re.search(r'\bcall\b',body),body

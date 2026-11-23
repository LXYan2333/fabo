"""Both sides of the all-normal branch, with an independent integer oracle."""
import subprocess
import pytest
from workflow.additive.tests.test_simd_portability import compile_source


@pytest.mark.parametrize('flags',[
    ['-DHWY_COMPILE_ONLY_SCALAR'],
    ['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes'],
    ['-DHWY_COMPILE_ONLY_STATIC','-march=icelake-server'],
])
def test_scaling_underflow(tmp_path,flags):
    source=r'''
#include "fast_boys/simd.h"
#include "fast_boys/detail/cuda/arithmetic.cuh"
#include <xmmintrin.h>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
using O=fast_boys::detail::Binary64;
std::uint64_t oracle(std::uint64_t bits,unsigned power) {
  const unsigned e=unsigned(bits>>52);
  if(power<e) return bits-(std::uint64_t(power)<<52);
  const unsigned shift=power-e+1;
  if(shift>53) return 0;
  const auto sig=(bits&0xfffffffffffffULL)|(1ULL<<52);
  const auto q=sig>>shift,r=sig&((1ULL<<shift)-1),half=1ULL<<(shift-1);
  return q+(r>half || (r==half && (q&1)));
}
int main() {
  _mm_setcsr(_mm_getcsr()&~0x8040U);
  constexpr auto cap=hn::MaxLanes(fb::DU());
  HWY_ALIGN_MAX std::uint64_t words[cap],powers[cap],out[cap];
  for(unsigned e:{1U,2U,990U,1023U,1055U,2046U})
  for(std::uint64_t mantissa:{0ULL,1ULL,2ULL,3ULL,0x7ffffffffffffULL,0xffffffffffffeULL,0xfffffffffffffULL})
  for(unsigned p=0;p<=e+55;++p) {
    for(unsigned lane=0;lane<hn::Lanes(fb::DU());++lane) {
      words[lane]=(std::uint64_t(e)<<52)|mantissa;
      powers[lane]=lane%2?0:p; // Mixed normal and underflow lanes.
    }
    const auto value=fb::detail::Ops<fb::D>::Scale(hn::Load(fb::DU(),words),hn::Load(fb::DU(),powers));
    hn::Store(fb::detail::Ops<fb::D>::Bits(value),fb::DU(),out);
    for(unsigned lane=0;lane<hn::Lanes(fb::DU());++lane) {
      const auto expected=oracle(words[lane],unsigned(powers[lane]));
      if(out[lane]!=expected) return 1;
      if(O::bits(O::scale(O::value(words[lane]),unsigned(powers[lane])))!=expected) return 2;
    }
  }
}
'''
    exe=compile_source(tmp_path,source,flags=[*flags,'-fno-fast-math'],link=True)
    subprocess.run([exe],check=True)

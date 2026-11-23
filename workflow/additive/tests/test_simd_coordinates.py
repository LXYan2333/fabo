"""Shared-coordinate SIMD preparation matches scalar bits in mixed vectors."""
import subprocess

import pytest

from workflow.additive.tests.test_simd_portability import compile_source


@pytest.mark.parametrize('flags', [
    ['-DHWY_COMPILE_ONLY_SCALAR'],
    ['-DHWY_COMPILE_ONLY_STATIC', '-march=haswell', '-maes'],
    ['-DHWY_COMPILE_ONLY_STATIC', '-march=icelake-server'],
])
@pytest.mark.parametrize('tail_bits', [9, 11, 13])
@pytest.mark.parametrize('fast', [False, True])
def test_shared_coordinates(tmp_path, flags, tail_bits, fast):
    source = r'''
#include "fast_boys/simd.h"
#include "fast_boys/detail/cuda/evaluator.cuh"
#include <cmath>
#include <limits>
#include <vector>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
using O=fast_boys::detail::Binary64;
struct M {
  static constexpr double domain_end=0x1.8122d2dea3c0cp+5,offset=0x1.51e0000000000p+2;
  static constexpr unsigned discarded_bits=41,tail_retained_bits=TAIL_BITS,tail_discarded_bits=52-tail_retained_bits;
  static constexpr std::uint64_t key_min=2099855,tail_row_offset=6861,row_count=6861;
  static constexpr std::size_t row_words=11,tail_row_count=(2ULL<<tail_retained_bits)+1;
};
int main() {
  std::vector<double> xs={-0.,0.,M::domain_end,std::nextafter(M::domain_end,0.),
      std::nextafter(M::domain_end,INFINITY),std::numeric_limits<double>::max()};
  for(unsigned e=0;e<2047;++e)
    for(std::uint64_t m:{0ULL,1ULL,0x7ffffffffffffULL,0xfffffffffffffULL})
      xs.push_back(O::value((std::uint64_t(e)<<52)|m));
  for(std::uint64_t key=M::key_min;key<M::key_min+M::row_count;++key) {
    const double x=O::sub(O::value((key<<41)+(1ULL<<40)),M::offset);
    if(x>=0 && x<=M::domain_end)
      for(double v:{std::nextafter(x,0.),x,std::nextafter(x,INFINITY)}) xs.push_back(v);
  }
  for(std::uint64_t m=0;m<(1ULL<<52);m+=1ULL<<M::tail_discarded_bits) {
    const auto tie=(1030ULL<<52)|m|(1ULL<<(M::tail_discarded_bits-1));
    for(auto bits:{tie-1,tie,tie+1}) xs.push_back(O::value(bits));
  }
  constexpr auto capacity=hn::MaxLanes(fb::D());
  HWY_ALIGN_MAX double input[capacity],hs[capacity];
  HWY_ALIGN_MAX std::uint64_t rows[capacity],ks[capacity];
  const auto lanes=hn::Lanes(fb::D());
  for(std::size_t i=0;i<xs.size();i+=lanes) {
    for(std::size_t j=0;j<lanes;++j) input[j]=xs[(i+j)%xs.size()];
    fb::U row,k; fb::V h;
    fb::detail::Ops<fb::D>::PrepareCombinedCoordinates<M>(hn::Load(fb::D(),input),row,h,k);
    hn::Store(row,fb::DU(),rows); hn::Store(k,fb::DU(),ks); hn::Store(h,fb::D(),hs);
    for(std::size_t j=0;j<lanes;++j) {
      std::size_t r; unsigned exponent; double delta;
      fast_boys::cuda::detail::PrepareCoordinates<M>(input[j],r,delta,exponent);
      if(rows[j]!=r*M::row_words || ks[j]!=exponent || O::bits(hs[j])!=O::bits(delta)) return 1;
    }
  }
}
'''
    exe = compile_source(tmp_path, source.replace('TAIL_BITS', str(tail_bits)),
                         flags=[*flags, *(['-ffast-math'] if fast else [])], link=True)
    subprocess.run([str(exe)], check=True)

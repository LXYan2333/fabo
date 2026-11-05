"""Main-key union extraction and unchanged tail-coordinate arithmetic."""
from workflow.additive.tests.test_headers import compile_run


def test_grid_key_and_coordinates(tmp_path):
    source=r'''
#include "fast_boys/detail/cuda/evaluator.cuh"
#include <cstdint>
#include <initializer_list>
#include <cmath>
using O=fast_boys::detail::Binary64;
using fast_boys::cuda::detail::RoundedMainGridKey;
template<unsigned S> bool check(std::uint64_t bits) {
  const unsigned __int128 wide=static_cast<unsigned __int128>(bits)+(std::uint64_t(1)<<(S-1));
  return RoundedMainGridKey<S>(O::value(bits))==(std::uint64_t(wide)>>S);
}
template<unsigned S> bool keys() {
  const auto half=std::uint64_t(1)<<(S-1);
  for(std::uint64_t u:{0ULL,1ULL,0xffffffffULL,0x100000000ULL,
      0x7fefffffffffffffULL,0x8000000000000000ULL,~0ULL})
    if(!check<S>(u)) return false;
  for(std::uint64_t key:{0ULL,1ULL,1023ULL,2099855ULL,2106715ULL,~0ULL>>S}) {
    const std::uint64_t tie=(key<<S)+half;
    for(std::uint64_t u:{tie-1,tie,tie+1}) if(!check<S>(u)) return false;
  }
  std::uint64_t u=0x981ac12b89034123ULL;
  for(int i=0;i<10000;++i) {
    u^=u<<13; u^=u>>7; u^=u<<17;
    if(!check<S>(u)) return false;
  }
  if constexpr(S<63) return keys<S+1>();
  return true;
}
struct Model {
  static constexpr double domain_end=0x1.8122d2dea3c0cp+5,offset=0x1.51e0000000000p+2;
  static constexpr unsigned discarded_bits=41,tail_discarded_bits=41,tail_retained_bits=11;
  static constexpr std::uint64_t key_min=2099855,tail_row_offset=6861;
};
bool coordinate(double x) {
  std::size_t row; double h; unsigned k;
  fast_boys::cuda::detail::PrepareCoordinates<Model>(x,row,h,k);
  std::uint64_t expected_row; double expected_h; unsigned expected_k=0;
  if(x<=Model::domain_end) {
    const auto y=O::add(x,Model::offset);
    const auto key=(O::bits(y)+(1ULL<<40))>>41;
    expected_row=key-Model::key_min;
    expected_h=O::sub(O::sub(O::value(key<<41),Model::offset),x);
  } else {
    const auto bits=O::bits(x);
    const auto exponent=unsigned(bits>>52)-1023;
    expected_k=exponent>>1;
    const auto u=O::value((bits&0xfffffffffffffULL)|(std::uint64_t(1023+(exponent&1))<<52));
    const auto key=(O::bits(u)+(1ULL<<40))>>41;
    expected_row=6861+key-(1023ULL<<11);
    expected_h=O::sub(O::value(key<<41),u);
  }
  return row==expected_row && O::bits(h)==O::bits(expected_h) && k==expected_k;
}
int main() {
  if(!keys<1>()) return 1;
  for(double x:{-0.0,0.0,Model::domain_end,
      std::nextafter(Model::domain_end,0.0),std::nextafter(Model::domain_end,INFINITY)})
    if(!coordinate(x)) return 2;
  for(unsigned e=0;e<2047;++e)
    for(std::uint64_t m:{0ULL,1ULL,0x7ffffffffffffULL,0xfffffffffffffULL})
      if(!coordinate(O::value((std::uint64_t(e)<<52)|m))) return 3;
  // Reference-grid key ties and their neighboring binary64 inputs.
  for(std::uint64_t key=Model::key_min;key<Model::key_min+6861;++key) {
    const auto x=O::sub(O::value((key<<41)+(1ULL<<40)),Model::offset);
    if(x>=0) for(double v:{std::nextafter(x,0.0),x,std::nextafter(x,INFINITY)})
      if(!coordinate(v)) return 4;
  }
}
'''
    compile_run(tmp_path,source,[])

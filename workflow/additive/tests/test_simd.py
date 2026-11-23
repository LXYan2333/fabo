import os
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from workflow.additive.tests.simd_support import require_host_isa

ROOT=Path(__file__).resolve().parents[3]
HWY=Path(os.environ.get('FABO_HIGHWAY_ROOT',ROOT/'third_party/workflow/highway'))
CXX=os.environ.get('FABO_SIMD_CXX','clang++')
INCLUDE=Path(os.environ.get('FABO_TEST_INCLUDE',ROOT/'include'))


@pytest.mark.parametrize('isa,flags',[('avx2',['-march=haswell','-maes']),('avx512',['-march=icelake-server'])])
@pytest.mark.parametrize('n,first',[(0,0),(4,0),(24,0),(24,7)])
def test_simd(tmp_path,isa,flags,n,first,fast=False):
    if not (HWY/'hwy/highway.h').exists(): pytest.skip('set FABO_HIGHWAY_ROOT to Highway 1.4')
    if not shutil.which(CXX): pytest.skip('Clang required')
    require_host_isa(flags,execute=True)
    variables=','.join(f'f{i}' for i in range(first,n+1))
    source=f"""
#include "fast_boys/simd_config.h"
#include "fast_boys/selected_simd.h"
#include "fast_boys/cuda.cuh"
#include "fast_boys/models/data_0_{n}.h"
#include <cstdio>
#include <limits>
#include <vector>
#include <xmmintrin.h>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
static_assert(HWY_TARGET=={'HWY_AVX2' if isa=='avx2' else 'HWY_AVX3_DL'},"test must exercise the named ISA");
using M=fast_boys::selected::Model<{n}>;
static constexpr fast_boys::BoysTable<M> main_table{{}};
__attribute__((noinline)) void reference(double x,double* ref) {{
 auto scalar=fast_boys::cuda::make_evaluator(main_table.view());
 scalar.template evaluate<0,{n}>(x,ref);
}}
template<bool Software> __attribute__((noinline)) void evaluate(fb::V x,{','.join(f'fb::V& f{i}' for i in range(first,n+1))}) {{
 auto e=fb::make_evaluator<Software>(main_table.view());
 e.template evaluate<{first},{n}>(fb::D(), x,{variables});
}}
template<bool Software> int check() {{
 using O=fast_boys::detail::Binary64;
 constexpr auto cap=hn::MaxLanes(fb::D());
 HWY_ALIGN_MAX double xs[cap],out[{n+1}][cap];
 const double special[]={{0.,-0.,M::domain_end,std::nextafter(M::domain_end,0.),std::nextafter(M::domain_end,INFINITY),1e8,1e100,1e300,
   std::numeric_limits<double>::max()}};
 std::vector<double> samples(std::begin(special),std::end(special));
 for(unsigned i=0;i<1200;++i) samples.push_back(std::exp(i*0.013));
 // Exercise every paired-tail reference cell across normal/subnormal scales.
 constexpr auto tail_rows=M::tail_row_count;
 constexpr auto tail_bits=M::tail_retained_bits,tail_shift=M::tail_discarded_bits;
 for(int exponent:{{6,24,50,100,300,600,1000,1022}})
  for(unsigned j=0;j<tail_rows;++j) {{
   const double u=O::value(((std::uint64_t(1023)<<tail_bits)+j)<<tail_shift);
   const double v=std::ldexp(u,exponent);
   if(std::isfinite(v)) {{
    samples.push_back(std::nextafter(v,0.));
    samples.push_back(v);
    const double right=std::nextafter(v,INFINITY);
    if(std::isfinite(right)) samples.push_back(right);
   }}
  }}
 for(std::uint64_t key=M::key_min;key<=M::key_max;++key) {{
  // Center and quantizer tie neighborhood, including unequal seam cells.
  const double y=O::value(key<<M::discarded_bits);
  const double tie=O::value((key<<M::discarded_bits)-(1ULL<<(M::discarded_bits-1)));
  for(double scaled:{{y,tie}}) {{
   const double v=scaled-M::offset;
   for(double test:{{std::nextafter(v,-INFINITY),v,std::nextafter(v,INFINITY)}})
    if(test>=0 && test<=M::domain_end) samples.push_back(test);
  }}
 }}
 for(std::size_t batch=0;batch<samples.size();batch+=hn::Lanes(fb::D())) {{
  for(unsigned lane=0;lane<hn::Lanes(fb::D());++lane)
   xs[lane]=samples[(batch+lane)%samples.size()];
  const auto x=hn::Load(fb::D(),xs);
  fb::V {variables};
  evaluate<Software>(x,{variables});
  double ref[{n+1}];
  {''.join(f'hn::Store(f{i},fb::D(),out[{i}]);' for i in range(first,n+1))}
  for(unsigned lane=0;lane<hn::Lanes(fb::D());++lane) {{
   reference(xs[lane],ref);
   for(int i={first};i<={n};++i) if(O::bits(out[i][lane])!=O::bits(ref[i])) {{
    std::fprintf(stderr,"order %d x=%a got=%a expected=%a\\n",i,xs[lane],out[i][lane],ref[i]); return 1;
   }}
  }}
 }}
 return 0;
}}
int main(){{_mm_setcsr(_mm_getcsr() & ~0x8040U); return check<false>() || check<true>();}}
"""
    src=tmp_path/'check.cc'; exe=tmp_path/'check'
    common=[CXX,'-std=c++17','-O2','-ffp-contract=off','-DHWY_COMPILE_ONLY_STATIC',
            *flags,'-I'+str(INCLUDE),'-I'+str(ROOT/'include'),'-I'+str(HWY)]
    extra=[]
    if fast:
        # Freeze the strict oracle in a separate object; do not recompile it
        # with the diagnostic evaluator's fast-math options.
        ref=tmp_path/'reference.cc'; ref.write_text(source.split('template<bool Software>')[0])
        obj=tmp_path/'reference.o'
        result=subprocess.run([*common,'-fno-fast-math','-c',str(ref),'-o',str(obj)],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        begin=source.index('__attribute__((noinline)) void reference')
        end=source.index('template<bool Software>')
        source=source[:begin]+'void reference(double x,double* ref);\n'+source[end:]
        extra=[str(obj)]
    src.write_text(source)
    command=[*common,'-ffast-math' if fast else '-fno-fast-math',str(src),*extra,str(HWY/'hwy/abort.cc'),'-o',str(exe)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    result=subprocess.run([exe],capture_output=True,text=True)
    if fast:
        (tmp_path/'fast-math.json').write_text(json.dumps(dict(
            isa=isa,compiler=CXX,flags=command,strict_oracle='reference.o',
            exit_status=result.returncode,first_mismatch=result.stderr),indent=2))
        assert result.returncode in (0,1), result.stderr
    else:
        assert result.returncode==0,result.stderr


@pytest.mark.parametrize('isa,flags',[('avx2',['-march=haswell','-maes']),('avx512',['-march=icelake-server'])])
def test_fast_math_diagnostic(tmp_path,isa,flags):
    test_simd(tmp_path,isa,flags,4,0,fast=True)

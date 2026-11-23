"""Small, independently evaluated nonmonotonic-degree SIMD fixture."""
import hashlib
import math
import subprocess

import pytest

from workflow.additive.headers import generate
from workflow.additive.model import Grid, storage, evaluate_order
from workflow.additive.reference import bits64
from workflow.additive.search import payload_rows
from workflow.additive import tail
from workflow.additive.simd_headers import generate as generate_simd
from workflow.additive.tests.test_simd_portability import compile_source


@pytest.mark.parametrize('compiler,flags,target', [
    ('clang++',['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes'],'HWY_AVX2'),
    ('g++',['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes'],'HWY_AVX2'),
    ('clang++',['-DHWY_COMPILE_ONLY_SCALAR'],'HWY_SCALAR'),
    ('clang++',['-DHWY_COMPILE_ONLY_EMU128'],'HWY_EMU128'),
    ('g++',['-DHWY_COMPILE_ONLY_STATIC','-march=x86-64'],'HWY_SSE2'),
    ('g++',['-DHWY_COMPILE_ONLY_STATIC','-march=westmere','-maes'],'HWY_SSE4'),
])
def test_nonmonotonic_nonzero_start(tmp_path, compiler,flags,target):
    grid=Grid(3,-3,4,1.)
    record=dict(first=2,last=5,degrees=[5,2,1,3],grid=grid.metadata(),
                minimum_order_prebiased=True,status='qualified',
                qualification=[{'status':'qualified','scope':'fixture only'}]*4)
    record['storage']=storage(grid,2,record['degrees'])
    record['payload_sha256']=hashlib.sha256(b''.join(payload_rows(record))).hexdigest()
    record['tail']=tail.construct(2,5,record['degrees'],3,1.)
    summary=dict(complete=True,identity='simd-fixture-not-production',
                 config={'error':{'metric':'ulp','limit':1},'budget_bytes':1048576},winners={'2-5':record})
    manifest=generate(summary,tmp_path)
    generate_simd(tmp_path)
    entry=manifest['models']['2-5']
    inputs=[0.,-0.,0.03,2.,math.nextafter(1.,0.),math.nextafter(1.,2.),
            1.,0.8,2.0**408,2.0**1023,0.07,0.79]
    expected=[bits64(evaluate_order(grid,x,n,record['degrees'][n-2]) if x<=1.
                     else tail.evaluate(record['tail'],x)[n])
              for x in inputs for n in range(2,6)]
    source=f'''
#include "fast_boys/models/{entry['id']}/simd-inl.h"
#include "fast_boys/models/{entry['id']}/data.h"
#include <cstdio>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
static_assert(HWY_TARGET=={target},"test target mismatch");
using M={entry['cpp_model']};
static constexpr fast_boys::BoysTable<M> table{{}};
int main() {{
const double inputs[]={{{','.join(x.hex() for x in inputs)}}};
const auto lanes=hn::Lanes(fb::D());
for(size_t batch=0; batch<sizeof(inputs)/sizeof(double); batch+=lanes) {{
 auto x=hn::LoadU(fb::D(),inputs+batch);
 fb::V a,b,c,d;
 fb::make_evaluator<false>(table.view()).evaluate<2,5>(fb::D(), x,a,b,c,d);
 for(size_t lane=0;lane<lanes;++lane) {{
  for(auto bits:{{hn::ExtractLane(fb::detail::Ops<fb::D>::Bits(a),lane),hn::ExtractLane(fb::detail::Ops<fb::D>::Bits(b),lane),
                  hn::ExtractLane(fb::detail::Ops<fb::D>::Bits(c),lane),hn::ExtractLane(fb::detail::Ops<fb::D>::Bits(d),lane)}})
    std::printf("%llu\\n",(unsigned long long)bits);
 }}
 // Nonzero subsets restart coefficient/factor reuse independently.
 fb::V e,f;
 fb::make_evaluator<true>(table.view()).evaluate<3,4>(fb::D(), x,e,f);
 if(!hn::AllTrue(fb::D(),hn::Eq(e,b)) || !hn::AllTrue(fb::D(),hn::Eq(f,c))) return 1;
}}
}}
'''
    exe=compile_source(tmp_path,source,compiler,
                       [*flags,'-I'+str(tmp_path)],link=True)
    actual=list(map(int,subprocess.check_output([exe],text=True).split()))
    assert actual==expected

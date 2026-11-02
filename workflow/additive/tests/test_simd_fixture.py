"""Small, independently evaluated nonmonotonic-degree SIMD fixture."""
import hashlib
import subprocess

import pytest

from workflow.additive.headers import generate
from workflow.additive.model import Grid, storage, evaluate_order
from workflow.additive.reference import bits64
from workflow.additive.search import payload_rows
from workflow.additive.simd_headers import generate as generate_simd
from workflow.additive.tests.test_simd_portability import compile_source


@pytest.mark.parametrize('compiler,flags', [
    ('clang++',['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes']),
    ('g++',['-DHWY_COMPILE_ONLY_STATIC','-march=haswell','-maes']),
    ('clang++',['-DHWY_COMPILE_ONLY_SCALAR']),
    ('g++',['-DHWY_COMPILE_ONLY_STATIC','-DHWY_DISABLED_TARGETS=0','-march=westmere','-maes']),
])
def test_nonmonotonic_nonzero_start(tmp_path, compiler,flags):
    grid=Grid(3,-3,4,0.8)
    record=dict(first=2,last=5,degrees=[5,2,1,3],grid=grid.metadata(),
                minimum_order_prebiased=True,status='qualified',
                qualification=[{'status':'qualified','scope':'fixture only'}]*4)
    record['storage']=storage(grid,2,record['degrees'])
    record['payload_sha256']=hashlib.sha256(b''.join(payload_rows(record))).hexdigest()
    summary=dict(complete=True,identity='simd-fixture-not-production',
                 config={'error':{'metric':'ulp','limit':1}},winners={'2-5':record})
    manifest=generate(summary,tmp_path)
    generate_simd(tmp_path)
    entry=manifest['models']['2-5']
    inputs=[0.,-0.,0.03,0.07,0.2,0.4,0.79,0.8]
    expected=[bits64(evaluate_order(grid,x,n,record['degrees'][n-2]))
              for x in inputs for n in range(2,6)]
    source=f'''
#include "fast_boys/models/{entry['id']}/simd-inl.h"
#include "fast_boys/models/{entry['id']}/data.h"
#include <cstdio>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
static_assert(HWY_TARGET=={'HWY_SCALAR' if '-DHWY_COMPILE_ONLY_SCALAR' in flags else 'HWY_SSE4' if '-march=westmere' in flags else 'HWY_AVX2'},"test target mismatch");
using M={entry['cpp_model']};
static constexpr fast_boys::BoysTable<M> table{{}};
int main() {{
const double inputs[]={{{','.join(x.hex() for x in inputs)}}};
for(double x:inputs) {{
 fb::V a,b,c,d;
 fb::Kernel<M>::run<2,5,false>(table.data(),hn::Set(fb::D(),x),a,b,c,d);
 for(auto bits:{{hn::GetLane(fb::detail::Bits(a)),hn::GetLane(fb::detail::Bits(b)),hn::GetLane(fb::detail::Bits(c)),hn::GetLane(fb::detail::Bits(d))}})
  std::printf("%llu\\n",(unsigned long long)bits);
 // Nonzero subsets restart coefficient/factor reuse independently.
 fb::V e,f;
 fb::Kernel<M>::run<3,4,true>(table.data(),hn::Set(fb::D(),x),e,f);
 if(hn::GetLane(fb::detail::Bits(e))!=hn::GetLane(fb::detail::Bits(b)) ||
    hn::GetLane(fb::detail::Bits(f))!=hn::GetLane(fb::detail::Bits(c))) return 1;
}}
}}
'''
    exe=compile_source(tmp_path,source,compiler,
                       [*flags,'-I'+str(tmp_path)],link=True)
    actual=list(map(int,subprocess.check_output([exe],text=True).split()))
    assert actual==expected

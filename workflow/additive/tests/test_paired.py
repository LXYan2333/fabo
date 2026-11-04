import hashlib
import json
import math
import struct
import pytest
from workflow.additive import tail
from workflow.additive.model import Grid,storage,evaluate_order
from workflow.additive.reference import bits64
from workflow.additive.search import payload_rows
from workflow.additive.headers import generate
from workflow.additive.simd_headers import generate as simd_generate
from workflow.additive.tests.test_headers import compile_run


def test_tail_storage_and_payload():
    m=tail.construct(3,5,[5,3,2],4)
    rows=list(tail.payload_rows(m))
    assert len(rows)==33
    assert sum(map(len,rows))==m['storage']['table_bytes']
    for i,row in enumerate(rows):
        hi,low=tail.coefficients(tail.node(i,4),8,3,5)
        words=struct.unpack('<'+'Q'*(len(row)//8),row)
        assert words[0]==bits64(hi[3])+1
        assert list(row[6*8:6*8+3])==low[3:6]
    assert tail.row_index(math.nextafter(4.,0.),4)==32


def test_tail_rounding_and_scaling():
    m=tail.construct(0,3,[7]*4,7)
    for x in (1e8,1e100,float.fromhex('0x1.fffffffffffffp1023')):
        values=tail.evaluate(m,x)
        u,k=tail.normalize(x)
        for n,v in values.items():
            lo,hi=tail.true_interval(tail.reference(u,3,512)[n],n,k,512)
            assert tail.measured_error(v,lo,hi,'ulp')<=1


def test_far_qualification_rejects_lower_anchor():
    with pytest.raises(ValueError,match='1e7 anchor'):
        tail.qualify(tail.construct(0,0,5,4,40.),dict(metric='ulp',limit=1))


def paired_fixture(tmp_path):
    grid=Grid(3,domain_end=40.,offset_code=0)
    degrees=[5,2,1,3]
    r=dict(first=0,last=3,degrees=degrees,grid=grid.metadata(),status='qualified',minimum_order_prebiased=True,
           qualification=[dict(status='qualified',scope='fixture only')]*4)
    r['storage']=storage(grid,0,degrees)
    r['tail']=tail.construct(0,3,degrees,3,40.)
    r['tail_qualification']=[dict(status='qualified',scope='fixture only')]*4
    r['payload_sha256']=hashlib.sha256(b''.join(payload_rows(r))).hexdigest()
    summary=dict(complete=True,unresolved=0,identity='fixture-not-production',config=dict(error=dict(metric='ulp',limit=1),budget_bytes=1048576),winners={'0-3':r})
    manifest=generate(summary,tmp_path/'include')
    simd_generate(tmp_path/'include')
    return grid,degrees,r,manifest


@pytest.mark.parametrize('cuda',[False,True])
def test_paired_header_conformance(tmp_path,cuda):
    grid,degrees,r,manifest=paired_fixture(tmp_path)
    main=manifest['models']['0-3']; tt=manifest['tails']['0-3']
    source=f'''#include "fast_boys/cuda.cuh"
#include "fast_boys/models/{main['id']}/data.h"
#include "fast_boys/models/{tt['id']}/data.h"
#include <cstdio>
using M={main['cpp_model']}; using T={tt['cpp_model']};
static constexpr fast_boys::BoysTable<M> m;
static constexpr fast_boys::BoysTable<T> t;
#if defined(__CUDACC__)
__global__ void instantiate(const std::uint64_t* a,const std::uint64_t* b,const double* x,double* out) {{
 auto e=fast_boys::cuda::make_evaluator(fast_boys::TableView<M>::from_pointer(a),fast_boys::TableView<T>::from_pointer(b));
 e.evaluate<0>(x[threadIdx.x],int(threadIdx.x%4),out+threadIdx.x,blockDim.x);
}}
#endif
int main() {{ auto e=fast_boys::cuda::make_evaluator(m.view(),t.view());
'''
    inputs=[-0.,0.1,40.,math.nextafter(40.,math.inf),1e8,1e100,float.fromhex('0x1.fffffffffffffp1023')]
    expected=[]
    for x in inputs:
        source+=f'{{ double out[4]; e.evaluate<0,3>({x.hex()},out); for(double v:out) std::printf("%a\\n",v); }}\n'
        expected.extend([evaluate_order(grid,x,n,p) for n,p in enumerate(degrees)] if x<=40 else tail.evaluate(r['tail'],x).values())
    source+='}'
    output=compile_run(tmp_path,source,[tmp_path/'include'],cuda=cuda)
    assert list(map(float.fromhex,output.split()))==expected
    src=(tmp_path/'include/fast_boys/models'/main['id']/'model.h').read_text()
    assert 'scale_k ? O::scale' in src
    assert manifest['tails']['0-3']['record']['degrees']==degrees


@pytest.mark.parametrize('isa,flags',[('avx2',['-march=haswell','-maes']),('avx512',['-march=icelake-server'])])
def test_paired_simd_conformance(tmp_path,isa,flags):
    import shutil
    import subprocess
    from workflow.additive.tests.test_simd import HWY,CXX,ROOT
    from workflow.additive.tests.simd_support import require_host_isa
    if not (HWY/'hwy/highway.h').exists() or not shutil.which(CXX):
        pytest.skip('Highway or compiler unavailable')
    require_host_isa(flags,execute=True)
    _,_,_,manifest=paired_fixture(tmp_path)
    main=manifest['models']['0-3']; tt=manifest['tails']['0-3']
    source=f'''#include "fast_boys/selected_simd.h"
#include "fast_boys/cuda.cuh"
#include "fast_boys/models/{main['id']}/data.h"
#include "fast_boys/models/{tt['id']}/data.h"
#include <limits>
#include <xmmintrin.h>
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
using M={main['cpp_model']}; using T={tt['cpp_model']};
static constexpr fast_boys::BoysTable<M> m;
static constexpr fast_boys::BoysTable<T> t;
template<bool Software> int check() {{
 auto simd=fb::make_evaluator<Software>(m.view(),t.view());
 auto scalar=fast_boys::cuda::make_evaluator(m.view(),t.view());
 constexpr auto cap=hn::MaxLanes(fb::D());
 HWY_ALIGN_MAX double x[cap],out[4][cap];
 const double points[]={{-0.,0.1,40.,std::nextafter(40.,INFINITY),1e8,1e100,std::numeric_limits<double>::max()}};
 for(unsigned start=0;start<7;++start) {{
  for(unsigned j=0;j<hn::Lanes(fb::D());++j) x[j]=points[(start+j)%7];
  fb::V a,b,c,d;
  simd.template evaluate<0,3>(hn::Load(fb::D(),x),a,b,c,d);
  hn::Store(a,fb::D(),out[0]); hn::Store(b,fb::D(),out[1]);
  hn::Store(c,fb::D(),out[2]); hn::Store(d,fb::D(),out[3]);
  for(unsigned j=0;j<hn::Lanes(fb::D());++j) {{
   double ref[4]; scalar.template evaluate<0,3>(x[j],ref);
   for(unsigned n=0;n<4;++n)
    if(fast_boys::detail::Binary64::bits(ref[n])!=fast_boys::detail::Binary64::bits(out[n][j])) return 1;
  }}
 }}
 return 0;
}}
int main() {{ _mm_setcsr(_mm_getcsr() & ~0x8040U); return check<false>() || check<true>(); }}
'''
    src=tmp_path/'simd.cc'; src.write_text(source)
    exe=tmp_path/'simd'
    command=[CXX,'-std=c++17','-O2','-fno-fast-math','-ffp-contract=off','-DHWY_COMPILE_ONLY_STATIC',
             *flags,'-I'+str(tmp_path/'include'),'-I'+str(ROOT/'include'),'-I'+str(HWY),
             str(src),str(HWY/'hwy/abort.cc'),'-o',str(exe)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    subprocess.run([str(exe)],check=True)


def test_paired_task_budget():
    from workflow.additive.paired import tasks
    config=dict(requested_ranges=[[0,0],[4,8]],minimum_degree=1,budget_bytes=4096)
    for first,last,b in tasks(config):
        s=tail.storage(first,[1]*(last-first+1),b)
        assert s['table_bytes']+s['row_bytes']<=4096


def test_paired_screen_and_frozen_seam(monkeypatch):
    from workflow.additive import paired
    c=dict(error=dict(metric='ulp',limit=1),minimum_degree=1,maximum_degree=3,
           retained_bits=[2],budget_bytes=1048576,screen_subdivisions=4,
           final_subdivisions=16,refinement_rounds=4)
    monkeypatch.setattr(paired,'geometry',lambda *a:True)
    monkeypatch.setattr(paired,'first_fit',lambda *a:1000)
    monkeypatch.setattr(paired,'shrink',lambda start,*a:start)
    def tq(m,*a):
        n=m['first']; p=m['degrees'][0]
        return dict(status='qualified' if p>=n+2 else 'failed',boundary=float(32+n).hex())
    monkeypatch.setattr(paired.tail,'boundary',tq)
    monkeypatch.setattr(paired.tail,'check_point',tq)
    monkeypatch.setattr(paired,'qualify',lambda grid,n,p,**kw:dict(status='qualified' if p>=n+2 else 'failed',max_error_upper=0.5))
    a=paired.selection(0,1,2,c,{},lambda:None)
    b=paired.selection(0,1,2,dict(c,cheap_screen=False),{},lambda:None)
    assert a==b
    assert a['degrees']==[2,3]
    assert a['tail']['degrees']==a['degrees']
    assert a['tail']['minimum_x']==33.
    assert a['combined_table_bytes']<=c['budget_bytes']

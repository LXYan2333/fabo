"""Generated scalar-index stages, exact payloads, and optional CUDA execution."""
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess

import pytest
from workflow.additive.headers import (generate, ROOT,
                                       coefficient_word, correction_word, interleaved_rows)
from workflow.additive.model import Grid, storage, evaluate_order
from workflow.additive.reference import bits64
from workflow.additive.search import payload_rows
from workflow.additive import tail


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    directory=tmp_path_factory.mktemp('generated')
    grid=Grid(3,-3,4,1.)
    # Deliberately nonmonotonic n+p[n]; covers nonzero subset starts.
    record=dict(first=0,last=3,degrees=[5,2,1,3],grid=grid.metadata(),
                status='qualified',minimum_order_prebiased=True,
                qualification=[{'status':'qualified','scope':'test fixture only'}]*4)
    record['storage']=storage(grid,0,record['degrees'])
    record['payload_sha256']=hashlib.sha256(b''.join(payload_rows(record))).hexdigest()
    record['tail']=tail.construct(record['first'],record['last'],record['degrees'],3,grid.domain_end)
    summary=dict(complete=True,unresolved=0,identity='test-fixture-not-production',
                 config={'budget_bytes':1048576,'error':{'metric':'ulp','limit':1}},winners={'0-3':record})
    manifest=generate(summary,directory)
    return directory,grid,record,summary,manifest


def compile_run(tmp_path,source,includes,flags=(),cuda=False):
    compiler=os.environ.get('FABO_NVCC',shutil.which('nvcc')) if cuda else shutil.which('clang++')
    if not compiler:
        pytest.skip('NVCC unavailable' if cuda else 'Clang unavailable')
    path=tmp_path/('check.cu' if cuda else 'check.cc'); path.write_text(source)
    exe=tmp_path/'check'
    command=[compiler,'-std=c++17','-O2']
    if not cuda:
        command+=['-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror=uninitialized']
    command+=list(flags)+['-I'+str(ROOT/'include')]+['-I'+str(p) for p in includes]+[str(path),'-o',str(exe)]
    subprocess.run(command,check=True,capture_output=True,text=True)
    if cuda and os.environ.get('FABO_CUDA_COMPILE_ONLY')=='1':
        pytest.skip('NVCC compilation passed; GPU execution explicitly disabled')
    return subprocess.check_output([str(exe)],text=True)


def preamble(manifest):
    main=manifest['models']['0-3']
    return f'''#include "fast_boys/cuda.cuh"
#include "fast_boys/models/{main['id']}/data.h"
#include <cstdio>
using M={main['cpp_model']};
using O=fast_boys::detail::Binary64;
inline constexpr fast_boys::BoysTable<M> table{{}};
'''


def test_reject_split_catalog_before_emission(fixture,tmp_path):
    import copy
    from workflow.additive.simd_headers import generate as generate_simd
    _,_,_,summary,manifest=fixture
    mixed=copy.deepcopy(summary)
    legacy=mixed['winners']['0-4']=dict(mixed['winners']['0-3'])
    del legacy['tail']
    output=tmp_path/'generated'
    with pytest.raises(ValueError,match='combined-table'):
        generate(mixed,output)
    assert not output.exists()
    old=dict(manifest,combined_table=False)
    (tmp_path/'manifest.json').write_text(json.dumps(old))
    with pytest.raises(ValueError,match='combined-table'):
        generate_simd(tmp_path)
    assert not (tmp_path/'fast_boys').exists()


def test_payload_and_generated_structure(fixture,tmp_path):
    directory,grid,record,summary,manifest=fixture
    regenerated=generate(summary,tmp_path)
    assert regenerated==manifest
    source=(directory/'fast_boys/models'/manifest['models']['0-3']['id']/'model.h').read_text()
    assert 'double c1 FAST_BOYS_INDETERMINATE;' in source
    assert 'double c1=' not in source and 'memcpy' not in source
    assert 'high_before(First,2)' in source
    assert 'if(last_output==0) return;' in source
    assert manifest['models']['0-3']['table_bytes']==record['storage']['table_bytes']+record['tail']['storage']['table_bytes']
    broken=json.loads(json.dumps(summary)); broken['winners']['0-3']['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='SHA-256'):
        generate(broken,tmp_path/'broken')
    assert not list((tmp_path/'broken').rglob('*.tmp'))


@pytest.mark.parametrize('first,count',[(0,1),(2,7),(0,8),(3,9),(0,16),(4,17),(0,25)])
def test_interleaved_word_mapping(first,count):
    grid=Grid(3,-3,4,1.)
    record=dict(first=first,last=first+count-1,degrees=[6]*count,grid=grid.metadata())
    record['storage']=storage(grid,first,record['degrees'])
    high=record['storage']['highest_reference_order']
    coefficient_count=high-first+1
    # Distinct synthetic words also verify preservation of unused padding bits.
    words=list(range(record['storage']['row_bytes']//8))
    raw=struct.pack('<'+'Q'*len(words),*words)
    rows=[raw]*len(grid.keys)
    record['payload_sha256']=hashlib.sha256(b''.join(rows)).hexdigest()
    for packed in interleaved_rows(record,rows):
        actual=struct.unpack('<'+'Q'*len(words),packed)
        assert sorted(actual)==words
        for n in range(first,high+1):
            assert actual[coefficient_word(record,n)]==n-first
        for n in range(first,first+count):
            assert actual[correction_word(record,n)]==coefficient_count+(n-first)//8


def test_low_order_sector_locality():
    # Selected SP layout: F0 degree 5, highest reference order 10, 96-byte rows.
    # With a sector-aligned table base each row also starts on a 32-byte sector.
    record={'first':0,'last':4}
    old_words=[*range(6),11]
    new_words=[coefficient_word(record,n) for n in range(6)]+[correction_word(record,0)]
    assert len({8*w//32 for w in old_words})==3
    assert len({8*w//32 for w in new_words})==2


def test_interleaved_multi_block_evaluation(tmp_path):
    grid=Grid(3,-3,4,1.)
    first,last=2,18
    degrees=[1+(n%6) for n in range(first,last+1)]
    record=dict(first=first,last=last,degrees=degrees,grid=grid.metadata(),
                status='qualified',minimum_order_prebiased=True,
                qualification=[{'status':'qualified','scope':'fixture only'}]*len(degrees))
    record['storage']=storage(grid,first,degrees)
    record['payload_sha256']=hashlib.sha256(b''.join(payload_rows(record))).hexdigest()
    record['tail']=tail.construct(record['first'],record['last'],record['degrees'],3,grid.domain_end)
    summary=dict(complete=True,identity='fixture',config={'budget_bytes':1048576,'error':{'metric':'ulp','limit':1}},winners={'2-18':record})
    manifest=generate(summary,tmp_path/'generated')
    model=manifest['models']['2-18']
    source=f'''#include "fast_boys/cuda.cuh"
#include "fast_boys/models/{model['id']}/data.h"
#include <cstdio>
#include <cstdlib>
using M={model['cpp_model']}; using O=fast_boys::detail::Binary64;
static constexpr fast_boys::BoysTable<M> table{{}};
int main(){{auto e=fast_boys::cuda::make_evaluator(table.view());
'''
    expected=[]
    for begin in (2,9,10,17,18):
        for end in range(begin,last+1):
            for x in (0.,0.125,grid.domain_end):
                source+=f'''{{double a[40],b[40]; for(int i=0;i<40;++i) a[i]=b[i]=-1;
e.evaluate<{begin},{end}>({x.hex()},a,2); e.evaluate<{begin},18>({x.hex()},{end},b,2);
for(int i=0;i<40;++i) {{if(O::bits(a[i])!=O::bits(b[i])) return 1; printf("%llu\\n",(unsigned long long)O::bits(a[i]));}}}}
'''
                values=[-1.]*40
                for n in range(begin,end+1):
                    values[2*(n-begin)]=evaluate_order(grid,x,n,degrees[n-first])
                expected.extend(map(bits64,values))
    source+='}\n'
    actual=compile_run(tmp_path,source,[tmp_path/'generated'])
    assert list(map(int,actual.split()))==expected


def test_host_subsets_and_index_boundaries(fixture,tmp_path):
    directory,grid,record,_,manifest=fixture
    points={0.,-0.,grid.domain_end}
    for key in grid.keys:
        a,b=grid.cell(key)
        points.update((a,b,(a+b)/2))
        for x in (a,b):
            points.update(y for y in (math.nextafter(x,0.),math.nextafter(x,math.inf)) if 0<=y<=grid.domain_end)
    statements=[]; expected=[]
    for first in range(4):
        for last in range(first,4):
            for x in sorted(points):
                statements.append(f'''{{double a[12],b[12]; for(int i=0;i<12;++i) a[i]=b[i]=-1;
e.evaluate<{first},{last}>({x.hex()},a,2); e.evaluate<{first},3>({x.hex()},{last},b,2);
for(int i=0;i<12;++i) {{if(O::bits(a[i])!=O::bits(b[i])) return 2; printf("%llu\\n",(unsigned long long)O::bits(a[i]));}}}}''')
                values=[-1.]*12
                for n in range(first,last+1): values[2*(n-first)]=evaluate_order(grid,x,n,record['degrees'][n])
                expected.extend(map(bits64,values))
    source=preamble(manifest)+'int main(){ auto e=fast_boys::cuda::make_evaluator(table.view());\n'+'\n'.join(statements)+'}\n'
    assert list(map(int,compile_run(tmp_path,source,[directory]).split()))==expected
    fast=list(map(int,compile_run(tmp_path,source,[directory],['-ffast-math']).split()))
    (tmp_path/'fast-math.json').write_text(json.dumps({'cases':len(expected),'different_bits':sum(a!=b for a,b in zip(expected,fast))}))


def test_two_translation_units(fixture,tmp_path):
    directory,_,_,_,manifest=fixture
    model=manifest['models']['0-3']
    header=f'#include "fast_boys/models/{model["id"]}/data.h"\ninline constexpr fast_boys::BoysTable<{model["cpp_model"]}> shared_table{{}};\n'
    (tmp_path/'shared.h').write_text(header)
    (tmp_path/'a.cc').write_text('#include "shared.h"\nconst void* other(){return shared_table.data();}\n')
    compiler=shutil.which('clang++')
    if not compiler: pytest.skip('Clang unavailable')
    compile_run(tmp_path,'#include "shared.h"\nconst void* other(); int main(){return other()!=shared_table.data();}',[directory,tmp_path],[str(tmp_path/'a.cc')])


def test_positioned_correction_decoder(tmp_path):
    source='''
#include "fast_boys/detail/cuda/arithmetic.cuh"
#include <initializer_list>
using O=fast_boys::detail::Binary64;
template<int Byte> bool check() {
 for(auto hi : {0x3ff0000000000000ULL,0x3fefffffffffffffULL,
                0x200abcdef0123456ULL,0x7fefffffffffffffULL})
  for(unsigned code=0;code<256;++code)
   for(auto noise : {0ULL,~0ULL,0x0123456789abcdefULL,0xfedcba9876543210ULL}) {
    auto word=(noise & ~(255ULL<<(8*Byte))) | (std::uint64_t(code)<<(8*Byte));
    if(O::bits(O::correction(hi,code)) !=
       O::bits(O::correction_from_word<Byte>(hi,word))) return false;
   }
 if constexpr(Byte<7) return check<Byte+1>();
 return true;
}
int main(){return !check<0>();}
'''
    compile_run(tmp_path,source,[ROOT/'include'])


@pytest.mark.parametrize('ndebug',[False,True])
def test_opt_in_assertions(fixture,tmp_path,ndebug):
    directory,_,_,_,manifest=fixture
    compiler=shutil.which('clang++')
    if not compiler: pytest.skip('Clang unavailable')
    source=preamble(manifest)+r'''
#include <csignal>
#include <cstdlib>
void caught_abort(int) { std::_Exit(86); }
int main(int argc,char** argv) {
  std::signal(SIGABRT,caught_abort);
  int evaluated=0;
  FAST_BOYS_ASSERT(++evaluated==1);
  if(evaluated!=FAST_BOYS_ENABLE_ASSERTS) return 1;
  if(argc==1) return 0;
  const int mode=std::atoi(argv[1]);
  double out[4];
  auto e=fast_boys::cuda::make_evaluator(table.view());
  if(mode==1) e.evaluate<0>(0.,-1,out);
  if(mode==2) e.evaluate<0>(0.,4,out);
  if(mode==3) e.evaluate<0>(0.,3,out,0);
  if(mode==4) e.evaluate<0>(1e8,4,out);
}
'''
    path=tmp_path/'assertions.cc'; path.write_text(source)
    for enabled in (False,True):
        exe=tmp_path/f'assertions-{enabled}'
        flags=['-DNDEBUG'] if ndebug else []
        if enabled: flags+=['-DFAST_BOYS_ENABLE_ASSERTS=1']
        subprocess.run([compiler,'-std=c++17','-O2',*flags,'-I'+str(ROOT/'include'),
                        '-I'+str(directory),str(path),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True)
        if enabled:
            for mode in range(1,5):
                result=subprocess.run([str(exe),str(mode)],capture_output=True,text=True)
                assert result.returncode==86
                assert 'fast_boys assertion failed' in result.stderr


def test_catalog_and_opt_in_payload(fixture,tmp_path):
    directory,_,_,summary,manifest=fixture
    source='''#include "fast_boys/selected.h"
#include "fast_boys/models/data_0_3.h"
#include <type_traits>
using M=fast_boys::selected::Model<3>;
static_assert(M::first==0 && M::last==3);
static_assert(M::combined_table);
static constexpr fast_boys::BoysTable<M> table{};
int main(){return table.data()==nullptr;}
'''
    # Generated root first: it may override the bundled production catalog.
    compiler=shutil.which('clang++')
    if not compiler: pytest.skip('Clang unavailable')
    src=tmp_path/'catalog.cc'; src.write_text(source)
    subprocess.run([compiler,'-std=c++17','-I'+str(directory),'-I'+str(ROOT/'include'),
                    str(src),'-o',str(tmp_path/'catalog')],check=True,capture_output=True)
    subprocess.run([str(tmp_path/'catalog')],check=True)
    assert generate(summary,directory)==manifest
    assert generate(summary,tmp_path/'parallel',workers=2)==manifest


def test_bundled_combined_sources_match_generator():
    """Do not ship an older evaluation graph under the current catalog."""
    from workflow.additive._frozen_v3.paired_headers import combined_source, LAYOUT
    from workflow.additive._frozen_v3.headers import digest
    path=ROOT/'include/manifest.json'
    if not path.exists(): pytest.skip('bundled production catalog not generated')
    manifest=json.loads(path.read_text())
    assert manifest['combined_table'] is True
    summary=json.loads((ROOT/'data/numerical/paired-1ulp/summary.json').read_text())
    from workflow.additive._frozen_v3 import headers, paired_headers
    emitter=hashlib.sha256(Path(paired_headers.__file__).read_bytes()+
                          Path(headers.__file__).read_bytes()).hexdigest()
    assert manifest['generator_sha256']==emitter
    recorded=json.loads((ROOT/'include/simd-manifest.json').read_text()).get('formatting')
    if recorded:
        from workflow.scripts.format_public_headers import format_source, formatter_identity
        if not shutil.which(recorded['executable']):
            pytest.skip('recorded clang-format required for exact formatted regeneration')
        assert formatter_identity(recorded['executable'])==recorded
    for entry in manifest['models'].values():
        record=entry['record']; error=summary['config']['error']
        assert entry['id']==digest(dict(recipe=record,error=error,layout=LAYOUT,emitter=emitter))
        expected=combined_source(record,entry['id'],error,entry['payload_sha256'])
        if recorded:
            expected=format_source(expected,recorded['executable'])
        assert (ROOT/'include/fast_boys/models'/entry['id']/'model.h').read_text()==expected


def test_bundled_catalog_coverage():
    path=ROOT/'include/manifest.json'
    if not path.exists(): pytest.skip('bundled production catalog not generated')
    manifest=json.loads(path.read_text())
    summary=json.loads((ROOT/'data/numerical/paired-1ulp/summary.json').read_text())
    assert manifest['numerical_identity']==summary['identity']
    assert set(manifest['models'])=={f'0-{n}' for n in range(25)}
    for key,model in manifest['models'].items():
        assert model['record']==summary['winners'][key]
        assert (ROOT/'include/fast_boys/models'/model['id']/'data.h').is_file()
        assert manifest['combined_table'] is True
        assert model['payload_layout']=='materialized-nextup-main-tail-v3'
        text=(ROOT/'include/fast_boys/models'/model['id']/'data.h').read_text()
        words=[int(word,16) for word in re.findall(r'0x([0-9a-f]{16})ULL',text)]
        raw=struct.pack('<'+'Q'*len(words),*words)
        assert hashlib.sha256(raw).hexdigest()==model['payload_sha256']
        record=model['record']; row_words=record['storage']['row_bytes']//8
        boundary=record['storage']['table_bytes']
        assert model['tail_row_offset']==record['grid']['row_count']
        assert model['table_bytes']==boundary+record['tail']['storage']['table_bytes']
        assert model['table_bytes']<=summary['config']['budget_bytes']
        assert hashlib.sha256(raw[:boundary]).hexdigest()==model['section_sha256']['main']
        assert hashlib.sha256(raw[boundary:]).hexdigest()==model['section_sha256']['tail']
        canonical_tail=hashlib.sha256()
        tm=record['tail']; tail_words=words[boundary//8:]
        for start in range(0,len(tail_words),row_words):
            row=tail_words[start:start+row_words]
            restored=[row[coefficient_word(tm,n)] for n in range(tm['first'],tm['storage']['highest_reference_order']+1)]
            restored += [row[correction_word(tm,n)] for n in range(tm['first'],tm['last']+1,8)]
            canonical_tail.update(struct.pack('<'+'Q'*len(restored),*restored))
        assert canonical_tail.hexdigest()==tm['payload_sha256']
        words=words[:boundary//8]
        high=record['storage']['highest_reference_order']
        canonical=hashlib.sha256()
        for start in range(0,len(words),row_words):
            row=words[start:start+row_words]
            restored=[row[coefficient_word(record,n)] for n in range(record['first'],high+1)]
            restored += [row[correction_word(record,n)] for n in range(record['first'],record['last']+1,8)]
            canonical.update(struct.pack('<'+'Q'*len(restored),*restored))
        assert canonical.hexdigest()==record['payload_sha256']
    expected_dirs={e['id'] for e in manifest['models'].values()}
    assert {p.name for p in (ROOT/'include/fast_boys/models').iterdir() if p.is_dir()}==expected_dirs
    assert not list((ROOT/'include/fast_boys/models').glob('tail_data*'))


def test_selected_production_witnesses(tmp_path):
    path=os.environ.get('FABO_GENERATED_MANIFEST')
    if not path:
        pytest.skip('set FABO_GENERATED_MANIFEST to check regenerated production selections')
    path=Path(path).resolve(); manifest=json.loads(path.read_text())
    for name,model in manifest['models'].items():
        record=model['record']; from workflow.additive.model import from_metadata
        grid=from_metadata(record['grid']); first,last=record['first'],record['last']
        source=f'''#include "fast_boys/cuda.cuh"
#include "fast_boys/models/{model['id']}/data.h"
#include <cstdio>
#include <cstdlib>
using M={model['cpp_model']}; using O=fast_boys::detail::Binary64;
static constexpr fast_boys::BoysTable<M> table{{}};
int main(){{auto e=fast_boys::cuda::make_evaluator(table.view()); double out[{last-first+1}];
'''
        expected=[]
        for n,q in zip(range(first,last+1),record['qualification']):
            for x in (0.,grid.domain_end,float.fromhex(q['witness'])):
                source+=f'e.evaluate<{n},{n}>({x.hex()},out); printf("%llu\\n",(unsigned long long)O::bits(out[0]));\n'
                expected.append(bits64(evaluate_order(grid,x,n,record['degrees'][n-first])))
        source+='}\n'
        assert list(map(int,compile_run(tmp_path,source,[path.parent]).split()))==expected,name


def test_cuda_mixed_requests(fixture,tmp_path):
    if os.environ.get('FABO_RUN_CUDA')!='1':
        pytest.skip('set FABO_RUN_CUDA=1 on an allocated GPU to run device conformance')
    directory,grid,record,_,manifest=fixture
    # 47 lanes: partial final warp; divergence at entry and varying endpoints.
    source='#include <cuda_runtime.h>\n#include "fast_boys/cuda/upload.cuh"\n'+preamble(manifest)+'''
__global__ void run(fast_boys::TableView<M> view, unsigned long long* result) {
 int i=blockIdx.x*blockDim.x+threadIdx.x; if(i>=47) return;
 double out[4]={-1,-1,-1,-1}; const int last=i%4;
 fast_boys::cuda::make_evaluator(view).evaluate<0>(i%3==0?1e100:0.125,last,out);
 for(int n=0;n<4;++n) result[i*4+n]=O::bits(out[n]);
}
int main(){
 fast_boys::cuda::DeviceTable<M> d(table);
 unsigned long long *p,host[47*4]; if(cudaMalloc(&p,sizeof(host))!=cudaSuccess) return 2;
 run<<<1,64>>>(d.view(),p);
 if(cudaGetLastError()!=cudaSuccess || cudaMemcpy(host,p,sizeof(host),cudaMemcpyDeviceToHost)!=cudaSuccess) return 3;
 cudaFree(p); for(auto v:host) printf("%llu\\n",v);
}
'''
    expected=[]; tail_values=tail.evaluate(record['tail'],1e100)
    for i in range(47):
        for n in range(4): expected.append(bits64(-1. if n>i%4 else tail_values[n] if i%3==0 else evaluate_order(grid,0.125,n,record['degrees'][n])))
    actual=list(map(int,compile_run(tmp_path,source,[directory],['--fmad=false','--diag-error=20013'],cuda=True).split()))
    assert actual==expected
    fast=list(map(int,compile_run(tmp_path,source,[directory],['--use_fast_math'],cuda=True).split()))
    (tmp_path/'cuda-fast-math.json').write_text(json.dumps({'cases':len(expected),'different_bits':sum(a!=b for a,b in zip(expected,fast))}))

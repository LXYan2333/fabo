"""Build standalone CPU/CUDA library adapters; never build integral engines."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from .adapters import source as fabo_source
from .core import ROOT, save, sha
from workflow.comparator_ports import copy_cpu_ports

SIMINT_REVISION='38b24bb040c647e4acc0e040457180b574089c58'
BACKENDS={'cpu':['simint','fabo','libintx','vsr','laikov'], 'cuda':['quick','fabo','libintx','vsr','gansu']}

def export(repo,revision,dest,paths):
    dest.mkdir(parents=True,exist_ok=True)
    with subprocess.Popen(['git','-C',str(repo),'archive',revision,*paths],stdout=subprocess.PIPE) as process:
        with tarfile.open(fileobj=process.stdout,mode='r|') as archive:archive.extractall(dest,filter='data')
        if process.wait():raise RuntimeError('source snapshot failed')

def cpu_source(n,backend):
    if backend in ('fabo','fabo_software'):return fabo_source(n,software=backend=='fabo_software')
    headers={'simint':'"simint/boys/boys.h"','libintx':'<libintx/boys/chebyshev.h>',
             'vsr':'"vikhamar_sandberg_repisky_minimax/source/boys.h"','laikov':'"laikov_global_approximation/boys.h"'}
    head='#include <cstddef>\n#include <algorithm>\n#include <immintrin.h>\n#include "hwy/highway.h"\n'
    if backend=='libintx':head+='#include <libintx/simd.h>\n'
    head+='#include '+headers[backend]+'\nnamespace hn=hwy::HWY_NAMESPACE;\n'
    if backend=='simint':compute=f'__m512d values[{n+1}];boys_F_split(values,_mm512_load_pd(buf),{n});'
    elif backend=='libintx':compute=f'using V=libintx::simd_t<double>;V values[{n+1}]{{}};static const auto& e=libintx::boys::chebyshev<{n}>();e.template compute<{n}>(V(_mm512_load_pd(buf)),values);'
    else:
        ns='vikhamar_sandberg_repisky' if backend=='vsr' else 'laikov'
        compute=f'auto values=fast_boys::benchmark::{ns}::boys<{n}>(d,hn::Load(d,buf));'
    store={'simint':'_mm512_store_pd(buf,values[j]);','libintx':'values[j].copy_to(buf,std::experimental::vector_aligned);','vsr':'hn::Store(values[j],d,buf);','laikov':'hn::Store(values[j],d,buf);'}[backend]
    return head+f'''extern "C" void boys_accuracy(size_t count,const double* x,double* out) {{
 hn::ScalableTag<double> d;static_assert(hn::MaxLanes(decltype(d)())==8);
 alignas(64) double buf[8];
 for(size_t i=0;i<count;i+=8) {{size_t active=std::min(size_t(8),count-i);
 for(size_t j=0;j<8;++j)buf[j]=j<active?x[i+j]:0.;
 {compute}
 for(int j=0;j<={n};++j){{{store}for(size_t k=0;k<active;++k)out[j*count+i+k]=buf[k];}}
 }}
}}
'''

def cuda_source(n,backend,table_path=None):
    if backend=='fabo':return fabo_source(n,True)
    head='#include <cuda_runtime.h>\n#include <stdexcept>\n#include <cstdio>\n#include <vector>\n#include <filesystem>\n#include <dlfcn.h>\n'
    if backend=='quick':
        head+='using QUICKDouble=double;\n#define PIE4 (0.78539816339744827900)\n#define FMT_NAME StandaloneQuick\n#define VY(a,b,n) YVerticalTemp[(n)*size_t(gridDim.x)*blockDim.x]\n#include "gpu_fmt.h"\n'
        call=f'StandaloneQuick({n},x[i],out+i);'
    else:
        head+='#include "'+{'libintx':'libintx_boys.h','vsr':'vsr_boys.h','gansu':'gansu_boys.h'}[backend]+'"\n'
        call={'libintx':f'FaboLibintxBoys({n},x[i],out+i,stride,table);','vsr':f'FaboVsrBoys({n},x[i],out+i,stride);','gansu':f'fabo_gansu::getIncrementalBoys({n},x[i],table,out+i,stride);'}[backend]
    init=''
    if table_path:
        count=8*13*819 if backend=='libintx' else 30720
        head+='static std::string table_file(const char* name){Dl_info info{};if(!dladdr((void*)&table_file,&info))throw std::runtime_error("cannot locate adapter");return (std::filesystem::path(info.dli_fname).parent_path().parent_path()/name).string();}\n'
        init=f'''if(!table){{std::vector<double> host({count});FILE* f=std::fopen(table_file({json.dumps(table_path.name)}).c_str(),"rb");
 if(!f)throw std::runtime_error("missing coefficient table");bool ok=std::fread(host.data(),8,{count},f)=={count}&&std::fgetc(f)==EOF;std::fclose(f);
 if(!ok)throw std::runtime_error("invalid coefficient table");check(cudaMalloc(&table,{count}*8));check(cudaMemcpy(table,host.data(),{count}*8,cudaMemcpyHostToDevice));}}'''
    return head+f'''
static void check(cudaError_t e){{if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}}
__global__ void evaluate(size_t count,const double* x,double* out,const double* table){{
 size_t i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
 size_t stride=size_t(gridDim.x)*blockDim.x;{call}
}}
extern "C" void boys_accuracy(size_t count,const double* x,double* out){{
 static double *table=nullptr,*dx=nullptr,*dy=nullptr;static size_t capacity=0;
 {init}
 size_t stride=(count+127)/128*128;
 if(stride>capacity){{if(dx)check(cudaFree(dx));if(dy)check(cudaFree(dy));check(cudaMalloc(&dx,stride*8));check(cudaMalloc(&dy,stride*8*{n+1}));capacity=stride;}}
 check(cudaMemcpy(dx,x,count*8,cudaMemcpyHostToDevice));evaluate<<<stride/128,128>>>(count,dx,dy,table);check(cudaGetLastError());
 check(cudaMemcpy2D(out,count*8,dy,stride*8,count*8,{n+1},cudaMemcpyDeviceToHost));
}}
'''

def build(config,out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'built.json').exists():raise ValueError('already built; use a new output directory')
    platform=config['platform'];backends=list(config.get('backends',BACKENDS[platform]));orders=config.get('orders',list(range(13)))
    if platform=='cpu' and config.get('software_gather',False):backends.append('fabo_software')
    allowed=set(BACKENDS[platform])|({'fabo_software'} if platform=='cpu' else set())
    if not backends or not orders or set(backends)-allowed or any(type(n)!=int or not 0<=n<=12 for n in orders):raise ValueError('invalid coverage')
    if len(set(backends))!=len(backends) or len(set(orders))!=len(orders):raise ValueError('duplicate coverage')
    cxx=config['cxx'];cc=config.get('cc','gcc');sources=out/'sources';sources.mkdir(exist_ok=True)
    if platform=='cpu':
        if config.get('ports_snapshot'):
            shutil.copytree(config['ports_snapshot'],sources/'ports',dirs_exist_ok=True)
        else:
            copy_cpu_ports(sources/'ports/benchmark/third_party_boys_impl')
        ports=sources/'ports/benchmark/third_party_boys_impl'
        if 'simint' in backends:
            if config.get('simint_snapshot'):
                shutil.copytree(Path(config['simint_snapshot'])/'skel',sources/'simint',dirs_exist_ok=True)
                license=Path(config['simint_snapshot'])/'LICENSE'
                if license.exists():shutil.copyfile(license,sources/'simint/LICENSE')
            else:
                export(config['simint'],SIMINT_REVISION,sources/'simint-export',['skel','LICENSE'])
                shutil.copytree(sources/'simint-export/skel',sources/'simint',dirs_exist_ok=True)
                shutil.copyfile(sources/'simint-export/LICENSE',sources/'simint/LICENSE')
            (sources/'simint/simint/vectorization/vector_config.h').write_text('#pragma once\n#define SIMINT_COMMONAVX512 1\n')
        export(config['highway'],'9ca61efcab7f54c244cc211e573324e6a29ffa17',sources/'highway',['hwy','LICENSE'])
        from workflow.nwchem_compare import patch_highway
        patch_highway(sources/'highway')
    compat=sources/'compat/libintx';compat.mkdir(parents=True,exist_ok=True)
    (compat/'config.h').write_text('#pragma once\n#define LIBINTX_SIMD 1\n#define LIBINTX_MAX_L 3\n#define LIBINTX_MAX_X 4\n#define LIBINTX_MAX_K 10\nnamespace libintx {constexpr int LMAX=3,XMAX=4,KMAX=10;}\n')
    libintx=Path(config.get('libintx',ROOT/'third_party/libintx')).resolve()
    includes=[ROOT/'include',compat.parent,libintx/'src',libintx/'include/eigen3']
    if platform=='cpu':includes += [sources/'highway',ports,sources/'simint']
    else:includes += [ROOT/'benchmark/quick',ROOT/'third_party/quick/src/gpu']
    if platform=='cuda':
        for b in ('libintx','gansu'):
            if b not in backends:continue
            exe=out/(b+'-table');src=ROOT/'benchmark/quick'/('libintx_table.cc' if b=='libintx' else 'gansu_table.cc')
            cmd=[cxx,'-std=c++20','-O2',str(src),*[f'-I{x}' for x in includes],'-I'+str(ROOT/'third_party/gansu/upstream'),'-o',str(exe)]
            subprocess.run(cmd,check=True);subprocess.run([str(exe),str(out/(b+'.bin'))],check=True)
    def one(job):
        b,mode,n=job;id_=f'{platform}-{mode}-{b}-{n}';folder=out/id_;folder.mkdir(exist_ok=True)
        src=folder/('adapter.cu' if platform=='cuda' else 'adapter.cc')
        src.write_text(cpu_source(n,b) if platform=='cpu' else cuda_source(n,b,out/(b+'.bin') if b in ('libintx','gansu') else None))
        flags=['-O3' if platform=='cpu' else '-O2','-DNDEBUG','-std=c++20',*[f'-I{x}' for x in includes]]
        objects=[];commands=[]
        if platform=='cpu':
            flags += ['-fPIC','-fvisibility=hidden','-fno-lto','-DHWY_COMPILE_ONLY_STATIC','-march='+config.get('architecture','sapphirerapids')]
            # Explicit public ABI despite hidden comparator internals.
            src.write_text(src.read_text().replace('extern "C" void boys_accuracy','extern "C" __attribute__((visibility("default"))) void boys_accuracy'))
            flags += ['-ffast-math','-ffp-contract=fast'] if mode=='fast' else ['-fno-fast-math','-ffp-contract=off']
            extra=[]
            if b=='simint':extra=[sources/'simint/simint/boys/boys_shortgrid.c']
            if b=='laikov':extra=[ports/'laikov_global_approximation'/p for p in ('adapter.c','source/c0n4.c','source/z1nm4.c')]
            for i,file in enumerate([src,*extra]):
                obj=folder/f'{i}.o';objects.append(obj)
                cmd=([cxx,*flags] if i==0 else [cc,'-O3','-fPIC','-fvisibility=hidden','-ffast-math' if mode=='fast' else '-fno-fast-math',*[f'-I{x}' for x in includes]])+['-c',str(file),'-o',str(obj)]
                commands.append(list(map(str,cmd)))
            commands.append([cxx,'-shared','-fno-fast-math','-Wl,-Bsymbolic',*map(str,objects),*config.get('link_flags',[]),config.get('libmvec','-lmvec'),'-lm','-lquadmath','-o',str(folder/'adapter.so')])
        else:
            commands.append([config['nvcc'],'-ccbin',cxx,*flags,'-arch='+config.get('cuda_arch','sm_120'),*(['--use_fast_math'] if mode=='fast' else ['--fmad=false']),'-Xcompiler=-fPIC,-fvisibility=hidden', '-shared',str(src),'-o',str(folder/'adapter.so')])
            src.write_text(src.read_text().replace('extern "C" void boys_accuracy','extern "C" __attribute__((visibility("default"))) void boys_accuracy'))
        with (folder/'build.log').open('w') as log:
            for cmd in commands:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        return dict(id=id_,N=n,platform=platform,backend=b,mode=mode,path=str(folder/'adapter.so'),commands=commands,sha256=sha(folder/'adapter.so'))
    jobs=[(b,m,n) for b in backends for m in ('strict','fast') for n in orders]
    with ThreadPoolExecutor(max_workers=config.get('workers',2)) as pool:adapters=list(pool.map(one,jobs))
    save(out/'built.json',dict(config=config,adapters=adapters,compiler=subprocess.check_output([cxx,'--version'],text=True),
        nvcc=subprocess.check_output([config['nvcc'],'--version'],text=True) if platform=='cuda' else None,
        source_hashes={str(p):sha(p) for base in [sources,ROOT/'include',ROOT/'benchmark/quick',libintx/'src',libintx/'include/eigen3',ROOT/'third_party/quick/src/gpu',ROOT/'third_party/gansu/upstream'] for p in base.rglob('*') if p.is_file()}))
    resources=[str(p) for p in out.glob('*.bin')]+[str(out/'built.json')]
    save(out/'scan-config.json',dict(scanner=config['scanner'],reference_table=config['reference_table'],adapters=adapters,resources=resources,batch=config.get('batch',1024),shard_size=config.get('shard_size',1000000),total=config.get('total',1000000001),platform=platform))

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(json.loads(a.config.read_text()),a.output)
if __name__=='__main__':main()

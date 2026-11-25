"""Emit standalone FABO adapters, with dedicated [0,N] allocations."""
import argparse
from pathlib import Path

def source(n, cuda=False, software=False):
    if not 0<=n<=24:raise ValueError('order must be 0..24')
    common=f'''#include <cstddef>
#include "fast_boys/models/data_0_{n}.h"
#include "fast_boys/selected.h"
using M=fast_boys::selected::Model<{n}>;
static constexpr fast_boys::BoysTable<M> table{{}};
'''
    if cuda:
        return '#include "fast_boys/cuda.cuh"\n#include <cuda_runtime.h>\n#include <stdexcept>\n'+common+f'''
static void check(cudaError_t e) {{if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e));}}
__global__ void kernel(size_t count,const double* x,double* out,const std::uint64_t* data) {{
 size_t i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
 auto e=fast_boys::cuda::make_evaluator(fast_boys::TableView<M>::from_pointer(data));
 double values[{n+1}];e.template evaluate<0,{n}>(x[i],values);
 for(int j=0;j<={n};++j)out[j*count+i]=values[j];
}}
extern "C" void boys_accuracy(size_t count,const double* x,double* out) {{
 static std::uint64_t* data=nullptr;
 if(!data){{check(cudaMalloc(&data,M::table_bytes));check(cudaMemcpy(data,table.view().data(),M::table_bytes,cudaMemcpyHostToDevice));}}
 double *dx=nullptr,*dy=nullptr;check(cudaMalloc(&dx,count*8));check(cudaMalloc(&dy,count*8*{n+1}));
 check(cudaMemcpy(dx,x,count*8,cudaMemcpyHostToDevice));kernel<<<(count+127)/128,128>>>(count,dx,dy,data);
 check(cudaGetLastError());check(cudaMemcpy(out,dy,count*8*{n+1},cudaMemcpyDeviceToHost));check(cudaFree(dx));check(cudaFree(dy));
}}
'''
    variables=','.join(f'f{i}' for i in range(n+1))
    stores='\n'.join(f'hn::StoreU(f{i},d,buffer);for(size_t j=0;j<active;++j)out[{i}*count+pos+j]=buffer[j];' for i in range(n+1))
    return '#include "fast_boys/selected_simd.h"\n#include <algorithm>\n'+common+f'''
namespace fb=fast_boys::simd::HWY_NAMESPACE;
namespace hn=hwy::HWY_NAMESPACE;
extern "C" void boys_accuracy(size_t count,const double* x,double* out) {{
 fb::D d;const size_t lanes=hn::Lanes(d);HWY_ALIGN_MAX double buffer[hn::MaxLanes(fb::D())];
 auto e=fb::make_evaluator<{str(software).lower()}>(table.view());
 for(size_t pos=0;pos<count;pos+=lanes) {{
  size_t active=std::min(lanes,count-pos);for(size_t j=0;j<lanes;++j)buffer[j]=j<active?x[pos+j]:0.;
  auto vx=hn::LoadU(d,buffer);fb::V {variables};e.template evaluate<0,{n}>(d, vx,{variables});
  {stores}
 }}
}}
'''

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--order',type=int,required=True);p.add_argument('--cuda',action='store_true');p.add_argument('--software',action='store_true');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.write_text(source(a.order,a.cuda,a.software))
if __name__=='__main__':main()

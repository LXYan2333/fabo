// Bitwise equivalence diagnostic, compilable as ordinary C++ or CUDA.
#include "fast_boys/detail/cuda/arithmetic.cuh"
#include "fast_boys/selected.h"
#include "fast_boys/models/tail_data.h"
#include "fast_boys/models/25bc55ce50b43704e75e98382d315646c856053c2f35dbe6d6c543987425dfbb/data.h"
#include <cstdio>
#ifdef __CUDACC__
#include <cuda_runtime.h>
#endif
using Old=fast_boys::models::m_25bc55ce50b43704e75e98382d315646c856053c2f35dbe6d6c543987425dfbb::Model;
using New=fast_boys::selected::Tail;
using O=fast_boys::detail::Binary64;
static constexpr fast_boys::BoysTable<Old> old_table;
static constexpr fast_boys::BoysTable<New> new_table;
FAST_BOYS_HD bool check(unsigned i,const std::uint64_t* a,const std::uint64_t* b) {
  const int powers[]={11,12,23,100,200,340,511};
  const unsigned sample=i/7;
  double u=1.0+3.0*double(sample)/8192.0;
  if(sample>8192) {
    const unsigned t=sample-8193;
    const std::uint64_t center=(std::uint64_t(65472+t/3)<<46);
    u=O::value(center+(t%3)-1);
    if(u<1.0 || u>4.0) return true;
  }
  double x[25],y[25];
  Old::evaluate<O,0,24>(a,u,powers[i%7],24,x,1);
  New::evaluate<O,0,24>(b,u,powers[i%7],24,y,1);
  for(int n=0;n<=24;++n) if(O::bits(x[n])!=O::bits(y[n])) return false;
  New::evaluate<O,3,8>(b,u,powers[i%7],8,y,1);
  for(int n=3;n<=8;++n) if(O::bits(x[n])!=O::bits(y[n-3])) return false;
  return true;
}
#ifdef __CUDACC__
__global__ void checks(const std::uint64_t* a,const std::uint64_t* b,unsigned* errors,unsigned count) {
  unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count && !check(i,a,b)) atomicAdd(errors,1U);
}
#endif
int main() {
  constexpr unsigned count=(8193+129*3)*7;
  unsigned errors=0;
#ifdef __CUDACC__
  std::uint64_t *a,*b;unsigned* e;
  #define CHECK(call) do {auto s=(call);if(s!=cudaSuccess){std::fprintf(stderr,"%s\n",cudaGetErrorString(s));return 2;}}while(0)
  CHECK(cudaMalloc(&a,Old::table_bytes));CHECK(cudaMalloc(&b,New::table_bytes));CHECK(cudaMalloc(&e,sizeof(unsigned)));
  CHECK(cudaMemcpy(a,old_table.data(),Old::table_bytes,cudaMemcpyHostToDevice));
  CHECK(cudaMemcpy(b,new_table.data(),New::table_bytes,cudaMemcpyHostToDevice));CHECK(cudaMemset(e,0,sizeof(unsigned)));
  checks<<<(count+127)/128,128>>>(a,b,e,count);CHECK(cudaDeviceSynchronize());CHECK(cudaMemcpy(&errors,e,sizeof(unsigned),cudaMemcpyDeviceToHost));
  CHECK(cudaFree(a));CHECK(cudaFree(b));CHECK(cudaFree(e));
#else
  for(unsigned i=0;i<count;++i) errors+=!check(i,old_table.data(),new_table.data());
#endif
  std::printf("%u input/exponent checks, full and subset outputs; %u mismatches\n",count,errors);
  return errors?1:0;
}

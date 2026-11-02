// Untimed CUDA binding check. The generated oracle includes supplied minimax.c
// with only its function name/device annotation changed, not its arithmetic.
#include <cuda_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <algorithm>
#include "vsr_boys.h"
#include "vsr_supplied_device.h"
#undef k

static void check(cudaError_t e) {
    if (e!=cudaSuccess) { std::fprintf(stderr,"%s\n",cudaGetErrorString(e)); std::exit(2); }
}
__global__ void adapted(int maximum, const double* xs, size_t count, double* out) {
    const size_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=count) return;
    FaboVsrBoys(maximum<0 ? i%13 : maximum, xs[i], out+i, count);
}
__global__ void supplied12(const double* xs, size_t count, double* out) {
    const size_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=count) return;
    double input[1]={xs[i]/2}, y[1]={1}, c[13]={}, z[1];
    for(int n=0;n<13;++n) {
        if(n) c[n-1]=0;
        c[n]=1;
        VsrSuppliedDevice(1,input,y,c,z);
        out[n*count+i]=z[0];
    }
}
static uint64_t bits(double x) { uint64_t u; std::memcpy(&u,&x,8); return u; }
int main() {
    const size_t count=2053;  // Includes a partially active final block/warp.
    const double sentinel=-987.0;
    std::vector<double> x(count), init(14*count,sentinel), got(init.size()), mixed(init.size()), oracle(init.size());
    uint64_t state=42;
    for(size_t i=0;i<count;++i) {
        state=state*6364136223846793005ULL+1;
        const double u=double(state>>11)*0x1p-53;
        x[i]=i%2 ? 60*u : std::exp(u*std::log(1e7));
    }
    x[0]=0.; x[1]=-0.;
    size_t pos=2;
    for(double seam : {fabo_vsr_x_0,fabo_vsr_x_1}) {
        x[pos++]=std::nextafter(seam,0.);x[pos++]=seam;x[pos++]=std::nextafter(seam,INFINITY);
    }
    double *dx,*dy;
    check(cudaMalloc(&dx,count*8));check(cudaMalloc(&dy,init.size()*8));
    check(cudaMemcpy(dx,x.data(),count*8,cudaMemcpyHostToDevice));
    check(cudaMemcpy(dy,init.data(),init.size()*8,cudaMemcpyHostToDevice));
    supplied12<<<(count+127)/128,128>>>(dx,count,dy);check(cudaGetLastError());
    check(cudaMemcpy(oracle.data(),dy,init.size()*8,cudaMemcpyDeviceToHost));
    check(cudaMemcpy(dy,init.data(),init.size()*8,cudaMemcpyHostToDevice));
    adapted<<<(count+127)/128,128>>>(-1,dx,count,dy);check(cudaGetLastError());
    check(cudaMemcpy(mixed.data(),dy,init.size()*8,cudaMemcpyDeviceToHost));
    size_t errors=0, oracle_differences=0;
    uint64_t max_ulps=0;
    double max_abs=0.;
    for(int n=0;n<=12;++n) {
        check(cudaMemcpy(dy,init.data(),init.size()*8,cudaMemcpyHostToDevice));
        adapted<<<(count+127)/128,128>>>(n,dx,count,dy);check(cudaGetLastError());
        check(cudaMemcpy(got.data(),dy,init.size()*8,cudaMemcpyDeviceToHost));
        for(size_t i=0;i<count;++i) for(int l=0;l<14;++l) {
            const size_t index=l*count+i;
            if(l>n) errors += got[index]!=sentinel;
            else {
                errors += !std::isfinite(got[index]) || got[index]<0.;
                if(int(i%13)==n) errors += bits(mixed[index])!=bits(got[index]);
                if(n==12) {
                    errors += !std::isfinite(oracle[index]) || oracle[index]<0.;
                    auto a=bits(got[index]),b=bits(oracle[index]);
                    oracle_differences += a!=b;
                    max_ulps=std::max(max_ulps,a>b ? a-b : b-a);
                    max_abs=std::max(max_abs,std::abs(got[index]-oracle[index]));
                }
            }
            if(l>int(i%13)) errors += mixed[index]!=sentinel;
        }
    }
    check(cudaFree(dx));check(cudaFree(dy));
    std::printf("{\"inputs\":%zu,\"orders\":13,\"guard_mixed_finite_errors\":%zu,\"author12_differences\":%zu,\"author12_max_ulp_difference\":%llu,\"author12_max_abs_difference\":%.17g}\n",
                count,errors,oracle_differences,(unsigned long long)max_ulps,max_abs);
#ifdef FABO_VSR_STRICT_CHECK
    errors += oracle_differences;
#endif
    return errors ? 1 : 0;
}

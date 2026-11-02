// Untimed test of the stride adapter against the unmodified release header.
#include <cuda_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <algorithm>
#include <limits>
#include "fabo_probe_runtime.h"
#define VY(a,b,l) YVerticalTemp[(l) * (gridDim.x * blockDim.x)]
#include "fabo_probe_boys.h"
#undef VY
#include "boys.hpp"

static void check(cudaError_t e) {
    if (e != cudaSuccess) { std::fprintf(stderr,"%s\n",cudaGetErrorString(e)); std::exit(2); }
}
__global__ void adapted(int n, const double* xs, size_t count, const double* table, double* out) {
    const size_t i = blockIdx.x*blockDim.x+threadIdx.x;
    if (i >= count) return;
    FaboProbeFmT(n < 0 ? i%13 : n, xs[i], out+i);
}
__global__ void original(int n, const double* xs, size_t count, const double* table, double* out) {
    const size_t i = blockIdx.x*blockDim.x+threadIdx.x;
    if (i >= count) return;
    double values[13];
    gansu::gpu::getIncrementalBoys(n, xs[i], table, values);
    for (int l=0; l<=n; ++l) out[l*(gridDim.x*blockDim.x)+i] = values[l];
}
static uint64_t bits(double x) { uint64_t u; std::memcpy(&u,&x,8); return u; }
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    std::vector<double> table(30720);
    FILE* f = std::fopen(argv[1],"rb");
    if (!f) return 2;
    bool valid = std::fread(table.data(),8,table.size(),f)==table.size() && std::fgetc(f)==EOF;
    if (std::fclose(f)!=0 || !valid) return 2;
    if (setenv("FABO_GANSU_TABLE",argv[1],1)!=0) return 2;
    fabo_probe_init_();
    const size_t count=4099; // Mixed requests, repeated inputs and a partial warp/block.
    const size_t stride=(count+127)/128*128;
    const double sentinel=-987.;
    std::vector<double> xs(count), init(stride*14,sentinel), got(init.size()), oracle(init.size()), mixed(init.size());
    uint64_t state=42;
    for (size_t i=0; i<count; ++i) {
        state = state*6364136223846793005ULL+1;
        double u = double(state>>11)*0x1p-53;
        xs[i] = i%2 ? 60*u : std::exp(u*std::log(1e7));
    }
    xs[0]=0.; xs[1]=-0.; xs[2]=std::numeric_limits<double>::max(); xs[3]=1e100;
    size_t pos=4;
    for (int n=0; n<=12; ++n) for (double b : {A_TR*n+B_TR,A_RS*n+B_RS}) {
        xs[pos++]=std::nextafter(b,0.); xs[pos++]=b; xs[pos++]=std::nextafter(b,INFINITY);
    }
    for (int i=0; i<140; ++i) {
        const double tie=(i+0.5)*LUT_XI_INTERVAL;
        xs[pos++]=std::nextafter(tie,0.); xs[pos++]=tie; xs[pos++]=std::nextafter(tie,INFINITY);
    }
    for (int i=0; i<32; ++i) xs[pos++]=1.;
    double *dx,*dy,*dt;
    check(cudaMalloc(&dx,count*8)); check(cudaMalloc(&dy,init.size()*8)); check(cudaMalloc(&dt,table.size()*8));
    check(cudaMemcpy(dx,xs.data(),count*8,cudaMemcpyHostToDevice));
    check(cudaMemcpy(dt,table.data(),table.size()*8,cudaMemcpyHostToDevice));
    check(cudaMemcpy(dy,init.data(),init.size()*8,cudaMemcpyHostToDevice));
    adapted<<<(count+127)/128,128>>>(-1,dx,count,dt,dy); check(cudaGetLastError());
    check(cudaMemcpy(mixed.data(),dy,init.size()*8,cudaMemcpyDeviceToHost));
    size_t errors=0,differences=0; uint64_t max_ulps=0; double max_abs=0.;
    for (int n=0; n<=12; ++n) {
        check(cudaMemcpy(dy,init.data(),init.size()*8,cudaMemcpyHostToDevice));
        original<<<(count+127)/128,128>>>(n,dx,count,dt,dy); check(cudaGetLastError());
        check(cudaMemcpy(oracle.data(),dy,init.size()*8,cudaMemcpyDeviceToHost));
        check(cudaMemcpy(dy,init.data(),init.size()*8,cudaMemcpyHostToDevice));
        adapted<<<(count+127)/128,128>>>(n,dx,count,dt,dy); check(cudaGetLastError());
        check(cudaMemcpy(got.data(),dy,init.size()*8,cudaMemcpyDeviceToHost));
        for (size_t i=0; i<stride; ++i) for (int l=0; l<14; ++l) {
            const size_t idx=l*stride+i;
            if (i>=count) {
                errors += got[idx]!=sentinel || mixed[idx]!=sentinel || oracle[idx]!=sentinel;
                continue;
            }
            if (l>n) errors += got[idx]!=sentinel;
            else {
                errors += !std::isfinite(got[idx]) || got[idx]<0. || !std::isfinite(oracle[idx]) || oracle[idx]<0.;
                if (int(i%13)==n) errors += bits(mixed[idx])!=bits(got[idx]);
                uint64_t a=bits(got[idx]), b=bits(oracle[idx]);
                differences += a!=b;
                max_ulps=std::max(max_ulps,a>b ? a-b : b-a);
                max_abs=std::max(max_abs,std::abs(got[idx]-oracle[idx]));
            }
            if (l>int(i%13)) errors += mixed[idx]!=sentinel;
        }
    }
    check(cudaFree(dx)); check(cudaFree(dy)); check(cudaFree(dt));
    std::printf("{\"inputs\":%zu,\"orders\":13,\"guard_mixed_finite_errors\":%zu,\"upstream_differences\":%zu,\"upstream_max_ulp_difference\":%llu,\"upstream_max_abs_difference\":%.17g}\n",
                count,errors,differences,(unsigned long long)max_ulps,max_abs);
#ifdef FABO_GANSU_STRICT_CHECK
    errors += differences;
#endif
    return errors ? 1 : 0;
}

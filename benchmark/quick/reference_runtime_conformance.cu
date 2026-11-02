// Compile the real host bridge under QUICK/LibXC's macro environment.
#include <cuda_runtime.h>
#define min(x,y) (((x)<(y)) ? (x) : (y))
#define max(x,y) (((x)<(y)) ? (y) : (x))
#define FABO_PROBE_VARIANT 4
#include "cuda/probe_runtime.h"
#ifndef min
#error QUICK's min macro was not restored
#endif
#ifndef max
#error QUICK's max macro was not restored
#endif
static_assert(min(3,4)==3 && max(3,4)==4,"QUICK macros changed");

__global__ void runtime_test(int mode,double* output) {
    if (mode==1) *output=fabo_reference::resolve(1,0.0,0.0);
    else if (mode==2) {
        fabo_reference::request_count=fabo_reference::Capacity;
        *output=fabo_reference::resolve(1,0.0,0.0);
    } else if (mode==3) *output=fabo_reference::rounded(0,-1.0);
    else *output=fabo_reference::rounded(0,0.0);
}

int main(int argc,char** argv) {
    if (argc!=4) return 3;
    if (setenv("FABO_QUICK_MODE","check",1) ||
        setenv("FABO_REFERENCE_TABLE",argv[1],1) ||
        setenv("FABO_REFERENCE_OVERRIDES",argv[2],1)) return 3;
    fabo_probe_init_();
    double* result;
    fabo_check(cudaMalloc(&result,sizeof(double)));
    runtime_test<<<1,1>>>(std::atoi(argv[3]),result);
    fabo_check(cudaGetLastError());
    fabo_probe_sync_();
    double value;
    fabo_check(cudaMemcpy(&value,result,sizeof(double),cudaMemcpyDeviceToHost));
    if (std::atoi(argv[3]) || value!=1.0) return 4;
    std::puts("{\"runtime_initialization_and_check\":true}");
}

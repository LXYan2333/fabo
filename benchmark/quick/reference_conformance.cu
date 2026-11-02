// Standalone checks of the same evaluator used by the QUICK reference patch.
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "reference_boys.h"

static void check(cudaError_t status) {
    if (status != cudaSuccess) { std::fprintf(stderr,"%s\n",cudaGetErrorString(status)); std::exit(2); }
}
struct Test { double x; unsigned long long order, expected; };
struct Result { unsigned long long lo,hi,value; unsigned invalid; };
__global__ void evaluate(const Test* inputs,Result* outputs,size_t count) {
    const size_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if (i>=count) return;
    fabo_reference::Q value,error;
    const auto input=inputs[i];
    const bool valid=fabo_reference::evaluate(input.order,input.x,&value,&error);
    if (!valid) { outputs[i]={0,0,0,1}; return; }
    const auto lower=fabo_reference::sub(value,error);
    outputs[i]={static_cast<unsigned long long>(__double_as_longlong(static_cast<double>(lower>0?lower:fabo_reference::Q(0)))),
        static_cast<unsigned long long>(__double_as_longlong(static_cast<double>(fabo_reference::add(value,error)))),
        static_cast<unsigned long long>(__double_as_longlong(fabo_reference::rounded(input.order,input.x))),0};
}
__global__ void force_fallback(const Test* inputs,Result* outputs) {
    const unsigned i=threadIdx.x;
    outputs[i].value=__double_as_longlong(fabo_reference::resolve(inputs[i].order,inputs[i].x,-1.0));
}
template<class T> std::vector<T> read(const char* path) {
    FILE* f=std::fopen(path,"rb"); if(!f) std::exit(2);
    std::vector<T> a; T v;
    while(std::fread(&v,sizeof(v),1,f)==1) a.push_back(v);
    if(std::ferror(f)||std::fclose(f)) std::exit(2);
    return a;
}
int main(int argc,char** argv) {
    if(argc!=3) return 2;
    using namespace fabo_reference;
    const auto data=read<Q>(argv[1]);
    if(data.size()!=Rows*Columns+Degree+2) return 2;
    Q* device;
    check(cudaMalloc(&device,Rows*Columns*sizeof(Q)));
    check(cudaMemcpy(device,data.data(),Rows*Columns*sizeof(Q),cudaMemcpyHostToDevice));
    check(cudaMemcpyToSymbol(table,&device,sizeof(device)));
    check(cudaMemcpyToSymbol(inverse,data.data()+Rows*Columns,(Degree+1)*sizeof(Q)));
    check(cudaMemcpyToSymbol(sqrt_pi_over_two,data.data()+Rows*Columns+Degree+1,sizeof(Q)));
    const auto input=read<Test>(argv[2]);
    Test* din; Result* dout;
    check(cudaMalloc(&din,input.size()*sizeof(Test))); check(cudaMalloc(&dout,input.size()*sizeof(Result)));
    check(cudaMemcpy(din,input.data(),input.size()*sizeof(Test),cudaMemcpyHostToDevice));
    evaluate<<<(input.size()+63)/64,64>>>(din,dout,input.size());
    check(cudaGetLastError()); check(cudaDeviceSynchronize());
    std::vector<Result> output(input.size());
    check(cudaMemcpy(output.data(),dout,output.size()*sizeof(Result),cudaMemcpyDeviceToHost));
    size_t certified=0,ambiguous=0;
    std::vector<Override> fixes;
    for(size_t i=0;i<input.size();++i) {
        const auto r=output[i]; const auto t=input[i];
        if(r.invalid||r.lo>t.expected||r.hi<t.expected) {
            std::fprintf(stderr,"enclosure failure n=%llu x=%a [%llx,%llx] expected=%llx\n",t.order,t.x,r.lo,r.hi,t.expected); return 3;
        }
        if(r.lo==r.hi) { if(r.value!=t.expected) return 4; ++certified; }
        else { unsigned long long bits; std::memcpy(&bits,&t.x,8); fixes.push_back({bits,t.order,t.expected}); ++ambiguous; }
    }
    // Fixtures are sorted by nonnegative x then order, as required by lookup.
    if(!fixes.empty()) {
        Override* df; check(cudaMalloc(&df,fixes.size()*sizeof(Override)));
        check(cudaMemcpy(df,fixes.data(),fixes.size()*sizeof(Override),cudaMemcpyHostToDevice));
        check(cudaMemcpyToSymbol(overrides,&df,sizeof(df)));
        unsigned count=fixes.size(),zero=0;
        check(cudaMemcpyToSymbol(override_count,&count,sizeof(count)));
        check(cudaMemcpyToSymbol(request_count,&zero,sizeof(zero)));
        evaluate<<<(input.size()+63)/64,64>>>(din,dout,input.size());
        check(cudaGetLastError()); check(cudaDeviceSynchronize());
        check(cudaMemcpy(output.data(),dout,output.size()*sizeof(Result),cudaMemcpyDeviceToHost));
        check(cudaMemcpyFromSymbol(&count,request_count,sizeof(count)));
        if(count) return 5;
        for(size_t i=0;i<input.size();++i) if(output[i].value!=input[i].expected) return 6;
    }
    // Exercise the queue and exact override lookup even when random samples
    // happen not to contain a hard-to-round value.
    if(input.size()<64) return 7;
    unsigned zero=0,count;
    check(cudaMemcpyToSymbol(override_count,&zero,sizeof(zero)));
    check(cudaMemcpyToSymbol(request_count,&zero,sizeof(zero)));
    force_fallback<<<1,64>>>(din,dout); check(cudaGetLastError()); check(cudaDeviceSynchronize());
    check(cudaMemcpyFromSymbol(&count,request_count,sizeof(count)));
    if(count!=64) return 8;
    std::vector<Override> forced;
    for(unsigned i=0;i<64;++i) { unsigned long long bits; std::memcpy(&bits,&input[i].x,8); forced.push_back({bits,input[i].order,input[i].expected}); }
    Override* df; check(cudaMalloc(&df,forced.size()*sizeof(Override)));
    check(cudaMemcpy(df,forced.data(),forced.size()*sizeof(Override),cudaMemcpyHostToDevice));
    check(cudaMemcpyToSymbol(overrides,&df,sizeof(df)));
    check(cudaMemcpyToSymbol(override_count,&count,sizeof(count)));
    check(cudaMemcpyToSymbol(request_count,&zero,sizeof(zero)));
    force_fallback<<<1,64>>>(din,dout); check(cudaGetLastError()); check(cudaDeviceSynchronize());
    check(cudaMemcpyFromSymbol(&count,request_count,sizeof(count)));
    check(cudaMemcpy(output.data(),dout,64*sizeof(Result),cudaMemcpyDeviceToHost));
    if(count) return 9;
    for(unsigned i=0;i<64;++i) if(output[i].value!=input[i].expected) return 10;
    std::printf("{\"tested\":%zu,\"certified_fp128\":%zu,\"mpfr_fallback\":%zu,\"forced_fallback_tests\":64,\"correctly_rounded\":true}\n",input.size(),certified,ambiguous);
}

// Host setup and fail-closed rounding check for the untimed reference backend.
// QUICK's gpu.h brings in LibXC's function-like min/max macros. Isolate
// standard-library includes without changing those macros in QUICK itself.
#pragma push_macro("min")
#pragma push_macro("max")
#undef min
#undef max
#include "../reference_boys.h"
#include <vector>
#pragma pop_macro("max")
#pragma pop_macro("min")

static void fabo_reference_init() {
    using namespace fabo_reference;
    if (!std::getenv("FABO_QUICK_MODE") || std::strcmp(std::getenv("FABO_QUICK_MODE"),"check")) {
        std::fprintf(stderr,"FP128 reference is restricted to untimed check mode\n"); std::exit(2);
    }
    const char* name = std::getenv("FABO_REFERENCE_TABLE");
    FILE* file = name ? std::fopen(name,"rb") : nullptr;
    if (!file) { std::fprintf(stderr,"FABO_REFERENCE_TABLE is required\n"); std::exit(2); }
    std::vector<Q> host(Rows*Columns+Degree+2);
    bool ok = std::fread(host.data(),sizeof(Q),host.size(),file)==host.size() && std::fgetc(file)==EOF;
    if (std::fclose(file) || !ok) { std::fprintf(stderr,"Invalid reference table\n"); std::exit(2); }
    Q* device;
    fabo_check(cudaMalloc(&device,Rows*Columns*sizeof(Q)));
    fabo_check(cudaMemcpy(device,host.data(),Rows*Columns*sizeof(Q),cudaMemcpyHostToDevice));
    fabo_check(cudaMemcpyToSymbol(table,&device,sizeof(device)));
    fabo_check(cudaMemcpyToSymbol(inverse,host.data()+Rows*Columns,(Degree+1)*sizeof(Q)));
    fabo_check(cudaMemcpyToSymbol(sqrt_pi_over_two,host.data()+Rows*Columns+Degree+1,sizeof(Q)));
    std::vector<Override> corrections;
    name = std::getenv("FABO_REFERENCE_OVERRIDES");
    file = name ? std::fopen(name,"rb") : nullptr;
    if (!file) { std::fprintf(stderr,"FABO_REFERENCE_OVERRIDES is required\n"); std::exit(2); }
    Override item;
    while (true) {
        const auto count = std::fread(&item,1,sizeof(item),file);
        if (!count && std::feof(file)) break;
        if (count != sizeof(item) || item.order > MaxOrder ||
            (!corrections.empty() && (item.x < corrections.back().x ||
             (item.x == corrections.back().x && item.order <= corrections.back().order)))) {
            std::fprintf(stderr,"Invalid reference overrides\n"); std::exit(2);
        }
        corrections.push_back(item);
    }
    if (std::fclose(file) || corrections.size() > Capacity) std::exit(2);
    const unsigned count=corrections.size();
    if (count) {
        Override* data;
        fabo_check(cudaMalloc(&data,count*sizeof(Override)));
        fabo_check(cudaMemcpy(data,corrections.data(),count*sizeof(Override),cudaMemcpyHostToDevice));
        fabo_check(cudaMemcpyToSymbol(overrides,&data,sizeof(data)));
    }
    fabo_check(cudaMemcpyToSymbol(override_count,&count,sizeof(count)));
}

static void fabo_reference_check() {
    using namespace fabo_reference;
    unsigned invalid=0,count=0;
    fabo_check(cudaMemcpyFromSymbol(&invalid,invalid_count,sizeof(invalid)));
    fabo_check(cudaMemcpyFromSymbol(&count,request_count,sizeof(count)));
    if (invalid || count > Capacity) {
        std::fprintf(stderr,"Reference invalid-input/overflow flag=%u, unresolved=%u (capacity %u)\n",invalid,count,Capacity);
        std::exit(2);
    }
    if (!count) return;
    std::vector<Request> host(count);
    fabo_check(cudaMemcpyFromSymbol(host.data(),requests,count*sizeof(Request)));
    FILE* file=std::fopen("reference-unresolved.bin","wb");
    if (!file || std::fwrite(host.data(),sizeof(Request),count,file)!=count || std::fclose(file)) std::exit(2);
    std::fprintf(stderr,"Reference needs MPFR for %u requests; discard this update\n",count);
    std::exit(86);
}

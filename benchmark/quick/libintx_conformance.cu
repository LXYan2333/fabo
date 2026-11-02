// GPU adapter check against the unmodified LibintX sequence evaluator.
#include <cuda_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <vector>
#include "libintx/boys/gpu/chebyshev.h"
#include "libintx_boys.h"

static void check(cudaError_t status) {
    if (status != cudaSuccess) {
        std::fprintf(stderr, "%s\n", cudaGetErrorString(status));
        std::exit(2);
    }
}

static std::vector<double> coefficients;
// Minimal host allocation/I/O definitions used by the original class; its
// device evaluator is included unchanged. Both paths read identical bytes.
namespace libintx::gpu {
void* device_memory_t::allocate(size_t size) { void* p; check(cudaMalloc(&p, size)); return p; }
void device_memory_t::free(void* p) { check(cudaFree(p)); }
void memcpy(void* dst, const void* src, size_t size) { check(cudaMemcpy(dst, src, size, cudaMemcpyDefault)); }
}
namespace libintx::boys {
std::unique_ptr<double[]> chebyshev_interpolation_table(int o, int m, int t, int s) {
    if (o != 7 || m != 13 || t != 117 || s != 819) std::exit(2);
    auto p = std::make_unique<double[]>(coefficients.size());
    std::memcpy(p.get(), coefficients.data(), coefficients.size()*sizeof(double));
    return p;
}
}
using Boys = libintx::boys::gpu::Chebyshev<7,13,117,819>;

template<int N> __global__ void oracle(Boys boys, const double* x, size_t count, double* out, bool mixed) {
    size_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    if (mixed && i % 13 != N) return;
    double values[N+1];
    boys.template compute<N>(x[i], 0, values);
    for (int m = 0; m <= N; ++m) out[i + m*count] = values[m];
}

__global__ void adapted(const double* table, int n, const double* x, size_t count, double* out) {
    size_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    if (n < 0) n = i % 13;
    FaboLibintxBoys(n, x[i], out + i, count, table);
}

template<int N=0> void launch_oracle(int n, Boys& boys, double* x, size_t count, double* out) {
    if (n == N || n < 0) oracle<N><<<(count+255)/256,256>>>(boys, x, count, out, n < 0);
    if constexpr (N < 12) { if (n > N || n < 0) launch_oracle<N+1>(n, boys, x, count, out); }
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    coefficients.resize(8*13*819);
    std::ifstream file(argv[1], std::ios::binary);
    if (!file.read(reinterpret_cast<char*>(coefficients.data()), coefficients.size()*8)) return 2;
    std::vector<double> x = {0, 0x1p-1022, 0.1, 116.99, 117, 128, 700, 1000, 10000, 1e6};
    // All segment centers and boundaries, both neighboring binary64 values.
    for (int k = 0; k <= 819; ++k) {
        for (double v : {k/7.0, (k+0.5)/7.0}) {
            x.push_back(v);
            if (v > 0) x.push_back(std::nextafter(v, 0.0));
            x.push_back(std::nextafter(v, INFINITY));
        }
    }
    // Alternating interpolation/asymptotic lanes with every requested order.
    for (int i = 0; i < 64; ++i) x.push_back(i % 2 ? 128.0 : 0.25);
    const size_t count = x.size(), size = 15*count;
    std::vector<double> sentinel(size, -12345.0), a(size), b(size);
    double *dx, *da, *db, *table;
    check(cudaMalloc(&dx, count*8)); check(cudaMalloc(&da, size*8));
    check(cudaMalloc(&db, size*8)); check(cudaMalloc(&table, coefficients.size()*8));
    check(cudaMemcpy(dx, x.data(), count*8, cudaMemcpyHostToDevice));
    check(cudaMemcpy(table, coefficients.data(), coefficients.size()*8, cudaMemcpyHostToDevice));
    Boys boys;
    size_t tested = 0;
    for (int n = -1; n <= 12; ++n) {
        check(cudaMemcpy(da, sentinel.data(), size*8, cudaMemcpyHostToDevice));
        check(cudaMemcpy(db, sentinel.data(), size*8, cudaMemcpyHostToDevice));
        launch_oracle(n, boys, dx, count, da+count);
        adapted<<<(count+255)/256,256>>>(table, n, dx, count, db+count);
        check(cudaGetLastError()); check(cudaDeviceSynchronize());
        check(cudaMemcpy(a.data(), da, size*8, cudaMemcpyDeviceToHost));
        check(cudaMemcpy(b.data(), db, size*8, cudaMemcpyDeviceToHost));
        for (size_t i = 0; i < size; ++i) {
            const int order = n < 0 ? (i % count) % 13 : n;
            const bool guard = i / count == 0 || i / count >= size_t(order + 2);
            if (std::memcmp(&a[i], &b[i], 8) ||
                (guard && b[i] != sentinel[i])) {
                std::fprintf(stderr, "mismatch mixed=%d order=%d offset=%zu oracle=%a adapted=%a\n", n < 0, order, i, a[i], b[i]);
                return 1;
            }
            if (!guard) ++tested;
        }
    }
    std::printf("{\"bitwise_equal\":true,\"guard_intact\":true,\"runtime_orders\":[0,12],\"mixed_orders\":true,\"mixed_branches\":true,\"inputs\":%zu,\"outputs\":%zu}\n", count, tested);
    check(cudaFree(dx)); check(cudaFree(da)); check(cudaFree(db)); check(cudaFree(table));
}

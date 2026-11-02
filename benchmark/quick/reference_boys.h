// Untimed reference backend (MPL-2.0). See workflow/QUICK_REFERENCE.md.
#ifndef FABO_REFERENCE_BOYS_H
#define FABO_REFERENCE_BOYS_H
#include <crt/device_fp128_functions.h>

namespace fabo_reference {
using Q = __float128;
constexpr int MaxOrder = 12;
constexpr int Degree = 24;
constexpr int Columns = MaxOrder + Degree + 1;
constexpr int Rows = 513; // quarter-spaced nodes on [0,128]
constexpr unsigned Capacity = 65536;
struct Request { unsigned long long x; unsigned long long order; };
struct Override { unsigned long long x, order, value; };
static __constant__ const Q* table;
static __constant__ Q inverse[Degree + 1];
static __constant__ Q sqrt_pi_over_two;
static __constant__ const Override* overrides;
static __constant__ unsigned override_count;
static __device__ Request requests[Capacity];
static __device__ unsigned request_count;
static __device__ unsigned invalid_count;

__device__ __forceinline__ Q add(Q a, Q b) { return __nv_fp128_add(a,b); }
__device__ __forceinline__ Q mul(Q a, Q b) { return __nv_fp128_mul(a,b); }
__device__ __forceinline__ Q sub(Q a, Q b) { return __nv_fp128_sub(a,b); }
__device__ __forceinline__ Q div(Q a, Q b) { return __nv_fp128_div(a,b); }

// A complete interval, not an assertion that binary128 implies correct rounding.
// The deliberately loose relative bound exceeds the Taylor, stored-data and
// arithmetic bounds derived in QUICK_REFERENCE.md. All Q operations are explicit.
__device__ __forceinline__ bool evaluate(int order, double x, Q* center, Q* radius) {
    const auto bits = static_cast<unsigned long long>(__double_as_longlong(x));
    if (order < 0 || order > MaxOrder || ((bits >> 63) && (bits << 1)) ||
        ((bits & 0x7ff0000000000000ULL) == 0x7ff0000000000000ULL && (bits << 12))) return false;
    if (bits == 0x7ff0000000000000ULL) { *center = 0; *radius = 0; return true; }
    const Q slack = __nv_fp128_ldexp(Q(1), -88);
    if (x <= 128.0) {
        const int row = static_cast<int>(__dadd_rn(__dmul_rn(x,4.0),0.5));
        // Do not subtract in double: rounding the index can select row 1 just
        // below x=1/8, where a double subtraction loses a significant low bit.
        const Q d = sub(Q(x),Q(0.25*row));
        const Q* values = table + row*Columns + order;
        Q h = values[Degree];
        for (int k = Degree-1; k >= 0; --k)
            h = __nv_fp128_fma(-mul(d,inverse[k+1]),h,values[k]);
        *center = h;
        *radius = mul(values[0],slack);
    } else {
        const Q xx = Q(x);
        Q a = div(sqrt_pi_over_two,__nv_fp128_sqrt(xx));
        const Q rho = div(Q(0.5),xx);
        for (int l = 1; l <= order; ++l) a = mul(mul(Q(2*l-1),rho),a);
        // Tail <= exp(-x)/(2*(x-max(order-1/2,0))) < exp(-x).
        // 23/16 < log2(e); use a looser constant bound beyond 8192.
        const int exponent = x < 8192.0 ? static_cast<int>(mul(xx,Q(23)/Q(16))) : 8192;
        const Q tail = __nv_fp128_ldexp(Q(1),-exponent);
        *center = a;
        *radius = add(mul(a,slack),tail);
    }
    return true;
}

__device__ __forceinline__ double resolve(int order, double x, double provisional) {
    const auto bits = static_cast<unsigned long long>(__double_as_longlong(x));
    unsigned first=0, last=override_count;
    while (first < last) {
        const unsigned mid = first+(last-first)/2;
        const Override item = overrides[mid];
        if (item.x < bits || (item.x == bits && item.order < static_cast<unsigned>(order))) first=mid+1;
        else last=mid;
    }
    if (first < override_count && overrides[first].x == bits && overrides[first].order == static_cast<unsigned>(order))
        return __longlong_as_double(overrides[first].value);
    const unsigned slot = atomicAdd(&request_count,1U);
    if (slot < Capacity) requests[slot] = {bits,static_cast<unsigned long long>(order)};
    else atomicExch(&invalid_count,1U); // sticky: even counter wrap cannot accept an overflowed update
    // This update is discarded by the host before diagonalization/output.
    return provisional;
}

// Keep quad arithmetic out of QUICK's already large integral kernel body.
__device__ __noinline__ double rounded(int order, double x) {
    Q value, error;
    if (!evaluate(order,x,&value,&error)) {
        atomicExch(&invalid_count,1U);
        return 0.0;
    }
    const Q lower = sub(value,error);
    const double lo = static_cast<double>(lower > 0 ? lower : Q(0));
    const double hi = static_cast<double>(add(value,error));
    if (__double_as_longlong(lo) == __double_as_longlong(hi)) return lo;
    return resolve(order,x,static_cast<double>(value));
}
} // namespace fabo_reference
#endif

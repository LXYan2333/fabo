#ifndef FAST_BOYS_DETAIL_CUDA_ARITHMETIC_CUH_
#define FAST_BOYS_DETAIL_CUDA_ARITHMETIC_CUH_
#include "fast_boys/boys_types.h"
#include <cmath>
#include <cstring>
#include <limits>
namespace fast_boys::detail {
static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559 &&
                  std::numeric_limits<double>::digits == 53,
              "IEEE binary64 required");
struct Binary64 {
  FAST_BOYS_HD static inline std::uint64_t bits(double x) {
#if defined(__CUDA_ARCH__)
    return static_cast<std::uint64_t>(__double_as_longlong(x));
#else
    std::uint64_t r;
    std::memcpy(&r, &x, sizeof(r));
    return r;
#endif
  }
  FAST_BOYS_HD static inline double value(std::uint64_t x) {
#if defined(__CUDA_ARCH__)
    return __longlong_as_double(static_cast<long long>(x));
#else
    double r;
    std::memcpy(&r, &x, sizeof(r));
    return r;
#endif
  }
  FAST_BOYS_HD static inline double add(double a, double b) {
#if defined(__CUDA_ARCH__)
    return __dadd_rn(a, b);
#else
    volatile double r = a + b;
    return r;
#endif
  }
  FAST_BOYS_HD static inline double sub(double a, double b) {
    return add(a, -b);
  }
  FAST_BOYS_HD static inline double mul(double a, double b) {
#if defined(__CUDA_ARCH__)
    return __dmul_rn(a, b);
#else
    volatile double r = a * b;
    return r;
#endif
  }
  FAST_BOYS_HD static inline double fma(double a, double b, double c) {
#if defined(__CUDA_ARCH__)
    return __fma_rn(a, b, c);
#else
    return std::fma(a, b, c);
#endif
  }
  FAST_BOYS_HD static inline double correction(std::uint64_t ordinary_hi,
                                               unsigned code) {
    return value(((ordinary_hi & 0x7ff0000000000000ULL) - (53ULL << 52)) +
                 (std::uint64_t(code) << 45));
  }
  // Exact power-of-two scaling of positive normal values, RN-even on underflow.
  FAST_BOYS_HD static inline double scale(double v, unsigned power) {
    const auto u = bits(v);
    const unsigned exponent = unsigned(u >> 52);
    if (power < exponent)
      return value(u - (std::uint64_t(power) << 52));
    const std::uint64_t sig = (u & 0xfffffffffffffULL) | (1ULL << 52);
    const unsigned shift = power - exponent + 1;
    if (shift > 53)
      return 0.0;
    const auto q = sig >> shift;
    const auto r = sig & ((1ULL << shift) - 1);
    const auto half = 1ULL << (shift - 1);
    return value(q + (r > half || (r == half && (q & 1))));
  }
};
} // namespace fast_boys::detail
#endif

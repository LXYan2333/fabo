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
  FAST_BOYS_HD static FAST_BOYS_INLINE std::uint64_t bits(double x) {
#if defined(__CUDA_ARCH__)
    return static_cast<std::uint64_t>(__double_as_longlong(x));
#else
    std::uint64_t r;
    std::memcpy(&r, &x, sizeof(r));
    return r;
#endif
  }
  FAST_BOYS_HD static FAST_BOYS_INLINE double value(std::uint64_t x) {
#if defined(__CUDA_ARCH__)
    return __longlong_as_double(static_cast<long long>(x));
#else
    double r;
    std::memcpy(&r, &x, sizeof(r));
    return r;
#endif
  }
  FAST_BOYS_HD static FAST_BOYS_INLINE double add(double a, double b) {
#if defined(__CUDA_ARCH__)
    return __dadd_rn(a, b);
#else
    volatile double r = a + b;
    return r;
#endif
  }
  FAST_BOYS_HD static FAST_BOYS_INLINE double sub(double a, double b) {
#if defined(__CUDA_ARCH__)
    return __dsub_rn(a, b);
#else
    return add(a, -b);
#endif
  }
  FAST_BOYS_HD static FAST_BOYS_INLINE double mul(double a, double b) {
#if defined(__CUDA_ARCH__)
    return __dmul_rn(a, b);
#else
    volatile double r = a * b;
    return r;
#endif
  }
  FAST_BOYS_HD static FAST_BOYS_INLINE double fma(double a, double b, double c) {
#if defined(__CUDA_ARCH__)
    return __fma_rn(a, b, c);
#else
    return std::fma(a, b, c);
#endif
  }
  FAST_BOYS_HD static FAST_BOYS_INLINE double correction(std::uint64_t ordinary_hi,
                                               unsigned code) {
    return value(((ordinary_hi & 0x7ff0000000000000ULL) - (53ULL << 52)) +
                 (std::uint64_t(code) << 45));
  }
  template <int Byte>
  FAST_BOYS_HD static FAST_BOYS_INLINE double
  correction_from_word(std::uint64_t ordinary_hi, std::uint64_t word) {
    static_assert(0 <= Byte && Byte < 8,
                  "byte index must be inside a u64 word");
    constexpr int shift = 45 - 8 * Byte;
    std::uint64_t positioned;
    if constexpr (shift >= 0)
      positioned = word << shift;
    else
      positioned = word >> -shift;
    positioned &= std::uint64_t(255) << 45;
    // Bit 52 contributes to the exponent: addition, not bitwise OR.
    return value(((ordinary_hi & 0x7ff0000000000000ULL) - (53ULL << 52)) +
                 positioned);
  }
  // Positive normal input; power <= 25039 for finite x and orders through 24.
  // power=0 takes the normal path and preserves the input bits exactly.
  FAST_BOYS_HD static FAST_BOYS_INLINE double scale(double v, unsigned power) {
    const auto u = bits(v);
    const unsigned result_biased_exponent = unsigned(u >> 52);
    if (FAST_BOYS_LIKELY(power < result_biased_exponent))
      return value(u - (std::uint64_t(power) << 52));
    return ::ldexp(v, -static_cast<int>(power));
  }
};
} // namespace fast_boys::detail
#endif

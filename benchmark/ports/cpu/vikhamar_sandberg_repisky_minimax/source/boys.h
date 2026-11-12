#ifndef FAST_BOYS_BENCHMARK_VIKHAMAR_SANDBERG_REPISKY_BOYS_H_
#define FAST_BOYS_BENCHMARK_VIKHAMAR_SANDBERG_REPISKY_BOYS_H_

#include "coefficients.h"

#include <hwy/highway.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <tuple>

namespace fast_boys::benchmark::vikhamar_sandberg_repisky {

namespace hn = hwy::HWY_NAMESPACE;

namespace detail {

#if HWY_ARCH_X86_64 && (HWY_COMPILER_GCC || HWY_COMPILER_CLANG)
// glibc libmvec's x86-64 vector-function ABI entry points. The paper used its
// compiler/OpenACC math implementation; libmvec is this Highway port's
// independent GCC/x86 choice for providing vector exp without scalarization.
// Only returned values are observed: these benchmark ports do not inspect
// errno/FP status flags or enable floating-point traps.
extern "C" __m128d _ZGVbN2v_exp(__m128d) __attribute__((pure));
extern "C" __m256d _ZGVdN4v_exp(__m256d) __attribute__((pure));
extern "C" __m512d _ZGVeN8v_exp(__m512d) __attribute__((pure));
#else
#error "This benchmark target requires the x86-64 glibc libmvec ABI"
#endif

template <class D>
HWY_INLINE hn::VFromD<D> exp_minus_x(const D d, const hn::VFromD<D> x) {
  using V = hn::VFromD<D>;
  const V negative_x = hn::Neg(x);
  if constexpr (HWY_MAX_LANES_D(D) == 1) {
    return hn::Set(d, std::exp(hn::GetLane(negative_x)));
  } else if constexpr (HWY_MAX_LANES_D(D) == 2) {
    return V{_ZGVbN2v_exp(negative_x.raw)};
  } else if constexpr (HWY_MAX_LANES_D(D) == 4) {
    return V{_ZGVdN4v_exp(negative_x.raw)};
  } else if constexpr (HWY_MAX_LANES_D(D) == 8) {
    return V{_ZGVeN8v_exp(negative_x.raw)};
  } else {
    static_assert(HWY_MAX_LANES_D(D) <= 8,
                  "libmvec has no matching x86-64 vector ABI entry point");
  }
}

// F0 alone uses rational/asymptotic evaluation and has no recurrence.
template <std::size_t MaxOrder, class D>
HWY_INLINE hn::VFromD<D> recurrence_exponential(const D d, const hn::VFromD<D> x) {
  if constexpr (MaxOrder == 0) {
    return hn::Zero(d);
  } else {
    return exp_minus_x(d, x);
  }
}

template <std::size_t Degree, class Coefficients, class D>
HWY_INLINE hn::VFromD<D> horner(const D d, const hn::VFromD<D> x,
                                const Coefficients& coefficients) {
  if constexpr (Degree + 1 == std::tuple_size_v<Coefficients>) {
    return hn::Set(d, coefficients[Degree]);
  } else {
    return hn::MulAdd(horner<Degree + 1>(d, x, coefficients), x,
                      hn::Set(d, coefficients[Degree]));
  }
}

template <class Coefficients, class D>
HWY_INLINE hn::VFromD<D> rational(const D d, const hn::VFromD<D> x) {
  return hn::Div(horner<0>(d, x, Coefficients::numerator),
                 horner<0>(d, x, Coefficients::denominator));
}

template <std::size_t Order, class D, class V, std::size_t Size>
HWY_INLINE void recur_downward(const D d, const V two_x,
                               const V exponential,
                               std::array<V, Size>& values) {
  if constexpr (Order > 0) {
    values[Order - 1] = hn::Div(
        hn::MulAdd(two_x, values[Order], exponential),
        hn::Set(d, static_cast<double>(2 * Order - 1)));
    recur_downward<Order - 1>(d, two_x, exponential, values);
  }
}

template <std::size_t Order, std::size_t MaxOrder, class D, class V,
          std::size_t Size>
HWY_INLINE void recur_upward(const D d, const V two_x, const V exponential,
                             std::array<V, Size>& values) {
  if constexpr (Order < MaxOrder) {
    values[Order + 1] = hn::Div(
        hn::MulSub(hn::Set(d, static_cast<double>(2 * Order + 1)),
                   values[Order], exponential),
        two_x);
    recur_upward<Order + 1, MaxOrder>(d, two_x, exponential, values);
  }
}

template <std::size_t Order, std::size_t MaxOrder, class D, class V,
          std::size_t Size>
HWY_INLINE void recur_asymptotic(const D d, const V inverse_two_x,
                                 std::array<V, Size>& values) {
  if constexpr (Order < MaxOrder) {
    values[Order + 1] = hn::Mul(
        values[Order],
        hn::Mul(hn::Set(d, static_cast<double>(2 * Order + 1)),
                inverse_two_x));
    recur_asymptotic<Order + 1, MaxOrder>(d, inverse_two_x, values);
  }
}

template <std::size_t MaxOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaxOrder + 1> region_a_values(
    const D d, const hn::VFromD<D> x, const hn::VFromD<D> exponential) {
  using V = hn::VFromD<D>;
  std::array<V, MaxOrder + 1> values;
  values[MaxOrder] = rational<coefficients::RegionA<MaxOrder>>(d, x);
  recur_downward<MaxOrder>(d, hn::Add(x, x), exponential, values);
  return values;
}

template <std::size_t MaxOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaxOrder + 1> region_b_values(
    const D d, const hn::VFromD<D> x, const hn::VFromD<D> exponential) {
  using V = hn::VFromD<D>;
  std::array<V, MaxOrder + 1> values;
  values[0] = rational<coefficients::RegionB>(d, x);
  recur_upward<0, MaxOrder>(d, hn::Add(x, x), exponential, values);
  return values;
}

template <std::size_t MaxOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaxOrder + 1> region_c_values(
    const D d, const hn::VFromD<D> x) {
  using V = hn::VFromD<D>;
  std::array<V, MaxOrder + 1> values;
  // Algorithm 1 uses the semi-infinite-interval expression in region C.
  // This decimal is sqrt(pi)/2 rounded to binary64.
  constexpr double kHalfSqrtPi = 0.88622692545275801365;
  values[0] = hn::Div(hn::Set(d, kHalfSqrtPi), hn::Sqrt(x));
  recur_asymptotic<0, MaxOrder>(d, hn::Div(hn::Set(d, 0.5), x), values);
  return values;
}

template <std::size_t Order, std::size_t MaxOrder, class M, class V,
          std::size_t Size>
HWY_INLINE void blend_regions(const M region_a, const M region_b,
                              const std::array<V, Size>& values_a,
                              const std::array<V, Size>& values_b,
                              const std::array<V, Size>& values_c,
                              std::array<V, Size>& values) {
  values[Order] = hn::IfThenElse(
      region_a, values_a[Order],
      hn::IfThenElse(region_b, values_b[Order], values_c[Order]));
  if constexpr (Order < MaxOrder) {
    blend_regions<Order + 1, MaxOrder>(region_a, region_b, values_a,
                                       values_b, values_c, values);
  }
}

}  // namespace detail

// The tag is part of the interface so a benchmark can select a full or capped
// Highway vector without an adapter or a conversion to a project-wide type.
template <std::size_t MaxOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaxOrder + 1> boys(
    const D d, const hn::VFromD<D> x) {
  static_assert(MaxOrder <= 32, "Appendix D supplies coefficients through F_32");

  namespace table = coefficients;
  using V = hn::VFromD<D>;
  const V region_a_end = hn::Set(d, table::kRegionAEnd);
  const V region_b_end = hn::Set(d, table::kRegionBEnd);
  const auto region_a = hn::Lt(x, region_a_end);
  const auto below_region_c = hn::Lt(x, region_b_end);
  const auto region_b = hn::AndNot(region_a, below_region_c);
  const auto region_c = hn::Not(below_region_c);

  // Algorithm 1 selects exactly one region for a scalar x. Preserve that
  // behavior for homogeneous SIMD batches: only the selected approximation
  // and recurrence are executed. Mixed batches use masked-input evaluation of
  // the required region candidates followed by lane-wise blending below.
  if (hn::AllTrue(d, region_a)) {
    return detail::region_a_values<MaxOrder>(
        d, x, detail::recurrence_exponential<MaxOrder>(d, x));
  }
  if (hn::AllTrue(d, region_b)) {
    return detail::region_b_values<MaxOrder>(
        d, x, detail::recurrence_exponential<MaxOrder>(d, x));
  }
  if (hn::AllTrue(d, region_c)) {
    return detail::region_c_values<MaxOrder>(d, x);
  }

  // Substitute an in-domain value on inactive lanes. SIMD arithmetic is
  // lane-wise but unmasked evaluation could otherwise divide by zero or probe
  // a rational approximation outside the interval for which it was fitted.
  const V x_a = hn::IfThenElse(region_a, x, hn::Zero(d));
  const V x_b = hn::IfThenElse(region_b, x, region_a_end);
  const V x_c = hn::IfThenElse(region_c, x, hn::Set(d, 1.0));
  const V exponential = detail::recurrence_exponential<MaxOrder>(d, x);
  const auto values_a =
      detail::region_a_values<MaxOrder>(d, x_a, exponential);
  const auto values_b =
      detail::region_b_values<MaxOrder>(d, x_b, exponential);
  const auto values_c = detail::region_c_values<MaxOrder>(d, x_c);

  std::array<V, MaxOrder + 1> values;
  detail::blend_regions<0, MaxOrder>(region_a, region_b, values_a, values_b,
                                     values_c, values);
  return values;
}

}  // namespace fast_boys::benchmark::vikhamar_sandberg_repisky

#endif  // FAST_BOYS_BENCHMARK_VIKHAMAR_SANDBERG_REPISKY_BOYS_H_

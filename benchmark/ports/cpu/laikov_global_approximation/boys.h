#ifndef FAST_BOYS_BENCHMARK_LAIKOV_GLOBAL_APPROXIMATION_BOYS_H_
#define FAST_BOYS_BENCHMARK_LAIKOV_GLOBAL_APPROXIMATION_BOYS_H_

#include "adapter.h"

#include <hwy/highway.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <utility>

namespace fast_boys::benchmark::laikov {

namespace hn = hwy::HWY_NAMESPACE;

namespace detail {

#if HWY_ARCH_X86_64 && (HWY_COMPILER_GCC || HWY_COMPILER_CLANG)
// The author implementation calls the compiler's exp function. Use the glibc
// vector-function ABI explicitly so vectorization does not depend on GCC's
// loop-vectorizer recognizing the translated Highway kernel.
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

template <std::size_t Remaining, class D>
HWY_INLINE hn::VFromD<D> multiply_binary_power(
    const D d, const hn::VFromD<D> result,
    const hn::VFromD<D> power) {
  hn::VFromD<D> next_result = result;
  if constexpr (Remaining & 1U) {
    next_result = hn::Mul(result, power);
  }
  if constexpr ((Remaining >> 1U) == 0) {
    return next_result;
  } else {
    return multiply_binary_power<(Remaining >> 1U)>(
        d, next_result, hn::Mul(power, power));
  }
}

template <std::size_t Order, class D>
HWY_INLINE hn::VFromD<D> pow_order_plus_half(
    const D d, const hn::VFromD<D> x) {
  if constexpr (Order == 0) {
    return hn::Sqrt(x);
  } else {
    return multiply_binary_power<Order>(d, hn::Sqrt(x), x);
  }
}

template <std::size_t MaximumOrder>
struct ApproximationShape {
  static_assert(MaximumOrder <= 36,
                "the supplied coefficients cover orders through 36");

  // t_fn.c's nc53 table: the root-factor approximation degree selected for
  // each requested maximum order in IEEE binary64 arithmetic.
  static constexpr std::array<int, 37> kDegrees = {
      10, 10, 11, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13,
      13, 13, 13, 13, 13, 14, 14, 14, 14, 14, 14, 14, 14,
      14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14,
  };

  // Entries o00..o36 in the author's z1nm4.c give the number of complex
  // conjugate root pairs in numerator and denominator for the nc53 degree.
  // Encoding them as template constants lets the translated kernel follow
  // the paper's intended fully generated/unrolled evaluation.
  static constexpr std::array<int, 37> kNumeratorPairs = {
      5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6,
      6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7,
      7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
  };
  static constexpr std::array<int, 37> kDenominatorPairs = {
      4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6,
      6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
      6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
  };

  static constexpr int degree = kDegrees[MaximumOrder];
  static constexpr int numerator_pairs = kNumeratorPairs[MaximumOrder];
  static constexpr int denominator_pairs = kDenominatorPairs[MaximumOrder];
};

template <int Pair, int PairCount, int Coefficient, class D>
HWY_INLINE hn::VFromD<D> multiply_root_pairs(
    const D d, const hn::VFromD<D> x,
    const fast_boys_laikov_parameters& parameters,
    const hn::VFromD<D> product) {
  if constexpr (Pair == PairCount) {
    return product;
  } else {
    auto root = hn::Add(x, hn::Set(d, parameters.coefficients[Coefficient]));
    root = hn::MulAdd(
        root, root, hn::Set(d, parameters.coefficients[Coefficient + 1]));
    return multiply_root_pairs<Pair + 1, PairCount, Coefficient + 2>(
        d, x, parameters, hn::Mul(product, root));
  }
}

template <int Factor, int FactorCount, int Coefficient, class D>
HWY_INLINE hn::VFromD<D> multiply_real_roots(
    const D d, const hn::VFromD<D> x,
    const fast_boys_laikov_parameters& parameters,
    const hn::VFromD<D> product) {
  if constexpr (Factor == FactorCount) {
    return product;
  } else {
    return multiply_real_roots<Factor + 1, FactorCount, Coefficient + 1>(
        d, x, parameters,
        hn::Mul(product,
                hn::Add(x, hn::Set(d, parameters.coefficients[Coefficient]))));
  }
}

template <std::size_t MaximumOrder, class D>
HWY_INLINE hn::VFromD<D> root_factor_approximation(
    const D d, const hn::VFromD<D> x,
    const fast_boys_laikov_parameters& parameters) {
  using Shape = ApproximationShape<MaximumOrder>;
  constexpr int degree = Shape::degree;
  constexpr int numerator_pairs = Shape::numerator_pairs;
  constexpr int denominator_pairs = Shape::denominator_pairs;
  constexpr int numerator_real_roots = degree - 2 * numerator_pairs;
  constexpr int denominator_coefficient = 1 + degree;
  constexpr int denominator_real_roots = degree - 1 - 2 * denominator_pairs;
  constexpr int final_coefficient = 2 * degree;

  auto product = multiply_root_pairs<0, numerator_pairs, 1>(
      d, x, parameters, hn::Set(d, parameters.coefficients[0]));
  product = multiply_real_roots<0, numerator_real_roots,
                                1 + 2 * numerator_pairs>(
      d, x, parameters, product);
  product = hn::Div(hn::Set(d, 1.0), product);
  product = multiply_root_pairs<0, denominator_pairs,
                                denominator_coefficient>(
      d, x, parameters, product);
  product = multiply_real_roots<0, denominator_real_roots,
                                denominator_coefficient +
                                    2 * denominator_pairs>(
      d, x, parameters, product);
  product = hn::MulAdd(
      x, product, hn::Set(d, parameters.coefficients[final_coefficient]));
  return hn::MulAdd(
      x, product, hn::Set(d, parameters.coefficients[final_coefficient + 1]));
}

template <std::size_t Order, std::size_t MaximumOrder, class D, class V>
HWY_INLINE void downward_recurrence(
    const D d, const V two_x, const V exponential,
    std::array<V, MaximumOrder + 1>& values) {
  values[Order - 1] = hn::Div(
      hn::MulAdd(two_x, values[Order], exponential),
      hn::Set(d, static_cast<double>(2 * Order - 1)));
  if constexpr (Order > 1) {
    downward_recurrence<Order - 1, MaximumOrder>(d, two_x, exponential,
                                                 values);
  }
}

template <std::size_t Order, std::size_t MaximumOrder, class D, class V>
HWY_INLINE void upward_asymptotic_recurrence(
    const D d, const V inverse_two_x,
    std::array<V, MaximumOrder + 1>& values) {
  values[Order] = hn::Mul(
      values[Order - 1],
      hn::Mul(hn::Set(d, static_cast<double>(2 * Order - 1)), inverse_two_x));
  if constexpr (Order < MaximumOrder) {
    upward_asymptotic_recurrence<Order + 1, MaximumOrder>(
        d, inverse_two_x, values);
  }
}

template <std::size_t MaximumOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaximumOrder + 1> approximation(
    const D d, const hn::VFromD<D> x,
    const fast_boys_laikov_parameters& parameters) {
  using V = hn::VFromD<D>;
  std::array<V, MaximumOrder + 1> values;
  const V exponential = exp_minus_x(d, x);
  const V q = root_factor_approximation<MaximumOrder>(d, x, parameters);
  V power = pow_order_plus_half<MaximumOrder>(d, q);
  constexpr int amplitude_index = 2 + 2 * ApproximationShape<MaximumOrder>::degree;
  const V c = hn::Set(d, parameters.coefficients[amplitude_index]);
  power = hn::Div(c, hn::MulAdd(power, exponential, x));
  values[MaximumOrder] = pow_order_plus_half<MaximumOrder>(d, power);

  const V two_x = hn::Add(x, x);
  if constexpr (MaximumOrder > 0) {
    downward_recurrence<MaximumOrder, MaximumOrder>(
        d, two_x, exponential, values);
  }
  return values;
}

template <std::size_t MaximumOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaximumOrder + 1> asymptotic(
    const D d, const hn::VFromD<D> x) {
  using V = hn::VFromD<D>;
  std::array<V, MaximumOrder + 1> values;
  const V inverse_two_x = hn::Div(hn::Set(d, 0.5), x);
  // t_fpn.c computes sqrt(0.5 * pi * (0.5 / x)).
  values[0] = hn::Sqrt(hn::Mul(hn::Set(d, 0.5 * 3.14159265358979323846),
                               inverse_two_x));
  if constexpr (MaximumOrder > 0) {
    upward_asymptotic_recurrence<1, MaximumOrder>(d, inverse_two_x, values);
  }
  return values;
}

template <class Mask, class V, std::size_t... Orders>
HWY_INLINE std::array<V, sizeof...(Orders)> blend_values(
    const Mask use_approximation,
    const std::array<V, sizeof...(Orders)>& near_values,
    const std::array<V, sizeof...(Orders)>& far_values,
    std::index_sequence<Orders...>) {
  return {hn::IfThenElse(use_approximation, near_values[Orders],
                         far_values[Orders])...};
}

}  // namespace detail

template <std::size_t MaximumOrder>
struct Parameters {
  static_assert(MaximumOrder <= 36,
                "the supplied coefficients cover orders through 36");

  Parameters() {
    if (fast_boys_laikov_initialize(&value, MaximumOrder) <= 0) {
      std::abort();
    }
  }

  fast_boys_laikov_parameters value{};
};

template <std::size_t MaximumOrder>
inline Parameters<MaximumOrder> parameters_for_order;

template <std::size_t MaximumOrder, class D>
HWY_INLINE std::array<hn::VFromD<D>, MaximumOrder + 1> boys(
    const D d, const hn::VFromD<D> x) {
  using V = hn::VFromD<D>;
  const auto& parameters = parameters_for_order<MaximumOrder>.value;
  constexpr int cutoff_index = 3 + 2 * detail::ApproximationShape<MaximumOrder>::degree;
  const V cutoff = hn::Set(d, parameters.coefficients[cutoff_index]);
  const auto use_approximation = hn::Lt(x, cutoff);

  // Match the author's branch whenever all SIMD lanes select one region.
  // This is common for order-dependent cutoffs and avoids evaluating an
  // entirely unused approximation or asymptotic path.
  if (hn::AllTrue(d, use_approximation)) {
    return detail::approximation<MaximumOrder>(d, x, parameters);
  }
  if (hn::AllFalse(d, use_approximation)) {
    return detail::asymptotic<MaximumOrder>(d, x);
  }

  // Highway has no portable per-lane control flow. For a vector straddling the
  // cutoff, evaluate both formulas with safe arguments and blend per lane.
  // This preserves the author's strict cutoff and the common SIMD API; only
  // genuinely mixed vectors pay for both paths.
  const V approximation_x =
      hn::IfThenElse(use_approximation, x, hn::Zero(d));
  const V asymptotic_x = hn::IfThenElse(use_approximation, cutoff, x);
  const auto near_values = detail::approximation<MaximumOrder>(
      d, approximation_x, parameters);
  const auto far_values = detail::asymptotic<MaximumOrder>(d, asymptotic_x);

  return detail::blend_values(
      use_approximation, near_values, far_values,
      std::make_index_sequence<MaximumOrder + 1>{});
}

}  // namespace fast_boys::benchmark::laikov

#endif  // FAST_BOYS_BENCHMARK_LAIKOV_GLOBAL_APPROXIMATION_BOYS_H_

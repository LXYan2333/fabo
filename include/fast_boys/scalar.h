#ifndef FAST_BOYS_SCALAR_H_
#define FAST_BOYS_SCALAR_H_
#include "fast_boys/detail/scalar_tail.h"
#include <array>
#include <type_traits>
namespace fast_boys::scalar {
namespace detail {
template <unsigned Shift>
FAST_BOYS_HD FAST_BOYS_INLINE std::uint64_t RoundedMainGridKey(double value) {
  static_assert(Shift > 0 && Shift < 64, "invalid quantizer shift");
#if defined(__CUDA_ARCH__)
  if constexpr (Shift > 32) {
    // Intentional compiler-supported union punning. Direct word access lets
    // NVCC keep the rounding add/shift in u32 instead of widening to u64.
    union Representation {
      double value;
      struct {
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
        std::uint32_t high, low;
#else
        std::uint32_t low, high;
#endif
      } words;
    } repr;
    repr.value = value;
    const std::uint32_t high = repr.words.high;
    const std::uint32_t rounded = high + (std::uint32_t(1) << (Shift - 33));
    // Widen only the result: callers reconstruct with shifts larger than 31.
    return rounded >> (Shift - 32);
  } else
#endif
  {
    const auto bits = fast_boys::detail::Binary64::bits(value);
    return (bits + (std::uint64_t(1) << (Shift - 1))) >> Shift;
  }
}
// One coordinate decision and one physical row pointer for both regions.
template <class Model>
FAST_BOYS_HD FAST_BOYS_INLINE void
PrepareCoordinates(double x, std::size_t &logical_row, double &h, unsigned &k) {
  using O = fast_boys::detail::Binary64;
  const bool use_main = x <= Model::domain_end;
  double coordinate;
  if (use_main) {
    coordinate = O::add(x, Model::offset);
    k = 0;
  } else {
    constexpr std::uint64_t exponent_bias = 1023ULL << 52;
    const auto unbiased_bits = O::bits(x) - exponent_bias;
    // Keep mantissa and exponent parity in place; addition restores the
    // normalized exponent, including its carry from 1023 to 1024.
    coordinate = O::value((unbiased_bits & ((1ULL << 53) - 1)) + exponent_bias);
    k = unsigned(unbiased_bits >> 53);
  }
  const double argument = use_main ? x : coordinate;
  const double reference_offset = use_main ? Model::offset : 0.0;
  const std::uint64_t key_origin =
      use_main
          ? Model::key_min
          : (1023ULL << Model::tail_retained_bits) - Model::tail_row_offset;
  std::uint64_t key;
  if constexpr (Model::discarded_bits == Model::tail_discarded_bits) {
    key = RoundedMainGridKey<Model::discarded_bits>(coordinate);
  } else {
    key = use_main ? RoundedMainGridKey<Model::discarded_bits>(coordinate)
                   : RoundedMainGridKey<Model::tail_discarded_bits>(coordinate);
  }
  const unsigned shift =
      use_main ? Model::discarded_bits : Model::tail_discarded_bits;
  const double reference = O::sub(O::value(key << shift), reference_offset);
  h = O::sub(reference, argument);
  logical_row = key - key_origin;
}

template <int First, int Limit, class Model>
FAST_BOYS_HD FAST_BOYS_INLINE void
EvaluateCombined(TableView<Model> table, double x, int last,
                 double *FAST_BOYS_RESTRICT out, std::size_t stride) {
  static_assert(Model::combined_table && Model::domain_end >= 1,
                "combined tail requires C >= 1");
  static_assert(Model::first <= First && First <= Limit && Limit <= Model::last,
                "invalid subset");
  FAST_BOYS_ASSERT(First <= last && last <= Limit && stride > 0);
#if defined(__CUDA_ARCH__)
  // The runtime order obeys the same subset contract even when checks are
  // off.
  __builtin_assume(First <= last && last <= Limit);
#endif
  using O = fast_boys::detail::Binary64;
  FAST_BOYS_ASSERT((x >= 0 && O::bits(x) < 0x7ff0000000000000ULL) ||
                   O::bits(x) == 0x8000000000000000ULL);
  std::size_t row FAST_BOYS_INDETERMINATE;
  double h FAST_BOYS_INDETERMINATE;
  unsigned k FAST_BOYS_INDETERMINATE;
  detail::PrepareCoordinates<Model>(x, row, h, k);
  Model::template evaluate<O, First, Limit>(
      table.data() + row * Model::row_words, h, last, out, stride, k);
}

template <class Tail, class = void>
struct SharesArithmetic : std::false_type {};
template <class Tail>
struct SharesArithmetic<Tail, std::void_t<decltype(Tail::shared_arithmetic)>>
    : std::bool_constant<Tail::shared_arithmetic> {};

template <int First, int Limit, class Model, class Tail>
FAST_BOYS_HD inline void
EvaluatePaired(TableView<Model> main, TableView<Tail> tail, double x, int last,
               double *FAST_BOYS_RESTRICT out, std::size_t stride) {
  static_assert(Model::row_words == Tail::row_words,
                "paired row layout mismatch");
  static_assert(std::is_same<Model, typename Tail::MainModel>::value,
                "tail belongs to a different main model");
  FAST_BOYS_ASSERT(First <= last && last <= Limit && stride > 0);
  using O = fast_boys::detail::Binary64;
  FAST_BOYS_ASSERT((x >= 0 && O::bits(x) < 0x7ff0000000000000ULL) ||
                   O::bits(x) == 0x8000000000000000ULL);
  const std::uint64_t *row;
  double h;
  unsigned k = 0;
  if (x <= Model::domain_end) {
    const double y = O::add(x, Model::offset);
    const auto key = detail::RoundedMainGridKey<Model::discarded_bits>(y);
    h = O::sub(O::sub(O::value(key << Model::discarded_bits), Model::offset),
               x);
    row = main.data() + (key - Model::key_min) * Model::row_words;
  } else {
    const auto bits = O::bits(x);
    const unsigned x_biased_exponent = unsigned(bits >> 52);
    const unsigned x_unbiased_exponent = x_biased_exponent - 1023;
    k = x_unbiased_exponent / 2;
    const auto mantissa_bits = bits & 0xfffffffffffffULL;
    const unsigned u_biased_exponent = 1023 + (x_unbiased_exponent & 1);
    const auto u_bits =
        mantissa_bits | (std::uint64_t(u_biased_exponent) << 52);
    const double u = O::value(u_bits);
    constexpr auto rounding_bit = 1ULL << (Tail::discarded_bits - 1);
    const auto key = (u_bits + rounding_bit) >> Tail::discarded_bits;
    const double u_ref = O::value(key << Tail::discarded_bits);
    h = O::sub(u_ref, u);
    row = tail.data() +
          (key - (1023ULL << Tail::retained_bits)) * Tail::row_words;
  }
  Model::template evaluate<O, First, Limit>(row, h, last, out, stride, k);
}

template <int First, int Limit, class Model, class OutsideDomain>
FAST_BOYS_HD inline void
EvaluateWithFallback(TableView<Model> table, const OutsideDomain &outside,
                     double x, int last, double *FAST_BOYS_RESTRICT out,
                     std::size_t stride) {
  static_assert(Model::first <= First && First <= Limit && Limit <= Model::last,
                "requested range outside model");
  FAST_BOYS_ASSERT(First <= last && last <= Limit && stride > 0);
  using O = fast_boys::detail::Binary64;
  const auto bits = O::bits(x);
  // Bit tests remain meaningful in fast-math builds; -0 is admitted.
  if (FAST_BOYS_UNLIKELY(((bits >> 63) && (bits << 1)) ||
                         (bits & 0x7fffffffffffffffULL) >
                             O::bits(Model::domain_end))) {
    outside.template evaluate<First, Limit>(x, last, out, stride);
    return;
  }
  const double y = O::add(x, Model::offset);
  const auto key = detail::RoundedMainGridKey<Model::discarded_bits>(y);
  const double r =
      O::sub(O::value(key << Model::discarded_bits), Model::offset);
  const double h = O::sub(r, x);
  const auto *row = table.data() + (key - Model::key_min) * Model::row_words;
  Model::template evaluate<O, First, Limit>(row, h, last, out, stride);
}

template <class Model, class Tail> FAST_BOYS_HD constexpr void CheckPair() {
  static_assert(Model::domain_end == Tail::minimum_x,
                "main/tail domain seam mismatch");
  static_assert(Tail::first <= Model::first && Model::last <= Tail::last,
                "tail does not cover this model");
  static_assert(Model::error_metric == Tail::error_metric &&
                    Model::error_limit == Tail::error_limit,
                "tail has a different qualification target; use an explicit "
                "custom handler");
}
template <int First, int Last, class Model, class Tail>
inline void EvaluateTwoTables(TableView<Model> main, TableView<Tail> tail,
                              double x, double *FAST_BOYS_RESTRICT out,
                              std::size_t stride) {
  CheckPair<Model, Tail>();
  if constexpr (SharesArithmetic<Tail>::value)
    EvaluatePaired<First, Last>(main, tail, x, Last, out, stride);
  else
    EvaluateWithFallback<First, Last>(main, LargeArgumentFallback<Tail>(tail),
                                      x, Last, out, stride);
}
} // namespace detail

// Finite, nonnegative x (including -0). Element i is F_{First+i}(x).
template <int First, int Last, class Model>
[[nodiscard]] FAST_BOYS_INLINE auto evaluate(TableView<Model> table, double x) {
  static_assert(First <= Last, "empty output range");
  std::array<double, Last - First + 1> out FAST_BOYS_INDETERMINATE;
  detail::EvaluateCombined<First, Last>(table, x, Last, out.data(), 1);
  return out;
}

template <int First, int Last, class Model, class Tail>
[[nodiscard]] FAST_BOYS_INLINE auto evaluate(TableView<Model> main,
                                             TableView<Tail> tail, double x) {
  static_assert(First <= Last, "empty output range");
  std::array<double, Last - First + 1> out FAST_BOYS_INDETERMINATE;
  detail::EvaluateTwoTables<First, Last>(main, tail, x, out.data(), 1);
  return out;
}
} // namespace fast_boys::scalar
#endif

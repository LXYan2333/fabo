// Include simd_config.h before foreach_target.h to select default targets.
#if defined(FAST_BOYS_SIMD_H_) == defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_H_
#undef FAST_BOYS_SIMD_H_
#else
#define FAST_BOYS_SIMD_H_
#endif
#include "fast_boys/simd_config.h"
#include "fast_boys/scalar.h"

#include "hwy/highway.h"

#include "fast_boys/detail/simd/ops-inl.h"
HWY_BEFORE_NAMESPACE();
namespace fast_boys {
namespace simd {
namespace HWY_NAMESPACE {
#if !HWY_NATIVE_FMA
namespace detail {
// Cross the vector/scalar boundary only at the edges of a complete evaluation.
template <int First, int Last, class Model, class TailView, class... Outputs>
HWY_INLINE void EvaluateLanes(TableView<Model> table, TailView tail, V x,
                              Outputs &...out) {
  constexpr size_t count = Last - First + 1;
  constexpr size_t capacity = hn::MaxLanes(D());
  const size_t lanes = hn::Lanes(D());
  double values[count * capacity];
  double inputs[capacity];
  if constexpr (capacity == 1)
    inputs[0] = hn::GetLane(x);
  else
    hn::StoreU(x, D(), inputs);
  for (size_t lane = 0; lane < lanes; ++lane) {
    if constexpr (!std::is_same_v<TailView, std::nullptr_t>) {
      // Preserve the two-table interface's infinity/invalid-input results.
      const auto bits = fast_boys::detail::Binary64::bits(inputs[lane]);
      if (bits > 0x7ff0000000000000ULL && bits != 0x8000000000000000ULL) {
        for (size_t i = 0; i < count; ++i)
          values[i * lanes + lane] =
              fast_boys::detail::Binary64::value(0x7ff8000000000000ULL);
        continue;
      }
      if (bits == 0x7ff0000000000000ULL) {
        for (size_t i = 0; i < count; ++i)
          values[i * lanes + lane] = 0.0;
        continue;
      }
      scalar::detail::EvaluateTwoTables<First, Last>(table, tail, inputs[lane],
                                                     values + lane, lanes);
    } else {
      scalar::detail::EvaluateCombined<First, Last>(table, inputs[lane], Last,
                                                    values + lane, lanes);
    }
  }
  size_t order = 0;
  if constexpr (capacity == 1)
    ((out = hn::Set(D(), values[order++])), ...);
  else
    ((out = hn::LoadU(D(), values + lanes * order++)), ...);
}
} // namespace detail
#endif
template <class Model, bool Software = kDefaultUseSoftwareGather>
class CombinedEvaluator {
public:
  constexpr explicit CombinedEvaluator(TableView<Model> table)
      : table_(table) {}
  template <int First, int Last, class... Outputs>
  HWY_INLINE void evaluate(const V x, Outputs &HWY_RESTRICT... out) const {
    static_assert(Model::combined_table && Model::domain_end >= 1,
                  "combined tail requires C >= 1");
    static_assert(Model::first <= First && First <= Last && Last <= Model::last,
                  "invalid subset");
    static_assert(sizeof...(Outputs) == Last - First + 1,
                  "one distinct output reference per order required");
    static_assert((std::is_same<V, Outputs>::value && ...),
                  "outputs must be binary64 vectors");
    // Finite x >= -0 is a caller precondition; do not inspect lanes at runtime.
#if HWY_NATIVE_FMA
    Kernel<Model>::template run<First, Last, Software>(table_.data(), x,
                                                       out...);
#else
    detail::EvaluateLanes<First, Last>(table_, nullptr, x, out...);
#endif
  }

private:
  TableView<Model> table_;
};
template <bool Software = kDefaultUseSoftwareGather, class Model>
constexpr auto make_evaluator(TableView<Model> table) {
  return CombinedEvaluator<Model, Software>(table);
}
// No vector-valued members or containers: compatible with sizeless vectors.
// RN-even and gradual underflow required. Users should not enable FP traps.
template <class Model, class Tail, bool Software = kDefaultUseSoftwareGather>
class Evaluator {
  static_assert(Model::domain_end == Tail::minimum_x,
                "main/tail seam mismatch");
  static_assert(Tail::first <= Model::first && Model::last <= Tail::last,
                "tail order coverage");
  static_assert(Model::error_metric == Tail::error_metric &&
                    Model::error_limit == Tail::error_limit,
                "tail accuracy target mismatch");

public:
  constexpr Evaluator(TableView<Model> main, TableView<Tail> tail)
      : main_(main), tail_(tail) {}
  template <int First, int Last, class... Outputs>
  HWY_INLINE void evaluate(const V x, Outputs &HWY_RESTRICT... out) const {
    static_assert(Model::first <= First && First <= Last && Last <= Model::last,
                  "invalid subset");
    static_assert(sizeof...(Outputs) == Last - First + 1,
                  "one distinct output reference per order required");
    static_assert((std::is_same<V, Outputs>::value && ...),
                  "outputs must be binary64 vectors");
#if HWY_NATIVE_FMA
    const auto bits = detail::Bits(x);
    const auto absolute = hn::And(bits, detail::SU(0x7fffffffffffffffULL));
    const auto negative =
        hn::And(hn::Ne(hn::ShiftRight<63>(bits), detail::SU(0)),
                hn::Ne(absolute, detail::SU(0)));
    const auto bounded =
        hn::And(hn::Not(negative),
                hn::Le(absolute, detail::Bits(detail::S(Model::domain_end))));
    Kernel<Model>::template run<First, Last, Software>(
        main_.data(), hn::IfThenElseZero(hn::RebindMask(D(), bounded), x),
        out...);
    if (HWY_UNLIKELY(!hn::AllTrue(DU(), bounded))) {
      const auto finite = hn::Lt(absolute, detail::SU(0x7ff0000000000000ULL));
      const auto tail =
          hn::And(hn::Not(bounded), hn::And(hn::Not(negative), finite));
      const auto mask = hn::RebindMask(D(), tail);
      const auto safe = hn::IfThenElse(mask, x, detail::S(2 * Tail::minimum_x));
      TailKernel<Tail>::template run<First, Last, Software>(tail_.data(), safe,
                                                            mask, out...);
      const auto infinity = hn::Eq(bits, detail::SU(0x7ff0000000000000ULL));
      const auto invalid = hn::Not(hn::Or(bounded, hn::Or(tail, infinity)));
      ((out = hn::IfThenElse(
            hn::RebindMask(D(), invalid),
            detail::Float(detail::SU(0x7ff8000000000000ULL)),
            hn::IfThenZeroElse(hn::RebindMask(D(), infinity), out))),
       ...);
    }
#else
    detail::EvaluateLanes<First, Last>(main_, tail_, x, out...);
#endif
  }

private:
  TableView<Model> main_;
  TableView<Tail> tail_;
};
template <bool Software = kDefaultUseSoftwareGather, class Model, class Tail>
constexpr auto make_evaluator(TableView<Model> main, TableView<Tail> tail) {
  return Evaluator<Model, Tail, Software>(main, tail);
}
} // namespace HWY_NAMESPACE
} // namespace simd
} // namespace fast_boys
HWY_AFTER_NAMESPACE();
#endif

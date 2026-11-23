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
template <int First, int Last, class Model, class D, class... Outputs>
HWY_INLINE void EvaluateLanes(TableView<Model> table, D d, hn::VFromD<D> x,
                              Outputs &...out) {
  constexpr size_t count = Last - First + 1;
  constexpr size_t capacity = hn::MaxLanes(D());
  const size_t lanes = hn::Lanes(d);
  double values[count * capacity];
  double inputs[capacity];
  if constexpr (capacity == 1)
    inputs[0] = hn::GetLane(x);
  else
    hn::StoreU(x, d, inputs);
  for (size_t lane = 0; lane < lanes; ++lane) {
    scalar::detail::EvaluateCombined<First, Last>(table, inputs[lane], Last,
                                                  values + lane, lanes);
  }
  size_t order = 0;
  if constexpr (capacity == 1)
    ((out = hn::Set(d, values[order++])), ...);
  else
    ((out = hn::LoadU(d, values + lanes * order++)), ...);
}
} // namespace detail
#endif
template <class Model, bool Software = kDefaultUseSoftwareGather>
class CombinedEvaluator {
public:
  constexpr explicit CombinedEvaluator(TableView<Model> table)
      : table_(table) {}
  template <int First, int Last, class D, class... Outputs>
  HWY_INLINE void evaluate(D d, const hn::VFromD<D> x,
                           Outputs &HWY_RESTRICT... out) const {
    static_assert(Model::combined_table && Model::domain_end >= 1,
                  "combined tail requires C >= 1");
    static_assert(Model::first <= First && First <= Last && Last <= Model::last,
                  "invalid subset");
    static_assert(std::is_same_v<hn::TFromD<D>, double>,
                  "binary64 tag required");
    static_assert(sizeof...(Outputs) == Last - First + 1,
                  "one distinct output reference per order required");
    static_assert((std::is_same<hn::VFromD<D>, Outputs>::value && ...),
                  "outputs must be binary64 vectors");
    // Finite x >= -0 is a caller precondition; do not inspect lanes at runtime.
#if HWY_NATIVE_FMA
    Kernel<Model>::template run<First, Last, Software>(d, table_.data(), x,
                                                       out...);
#else
    detail::EvaluateLanes<First, Last>(table_, d, x, out...);
#endif
  }

private:
  TableView<Model> table_;
};
template <bool Software = kDefaultUseSoftwareGather, class Model>
constexpr auto make_evaluator(TableView<Model> table) {
  return CombinedEvaluator<Model, Software>(table);
}
} // namespace HWY_NAMESPACE
} // namespace simd
} // namespace fast_boys
HWY_AFTER_NAMESPACE();
#endif

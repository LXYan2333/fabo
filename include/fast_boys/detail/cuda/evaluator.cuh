#pragma once
#include "fast_boys/scalar.h"
namespace fast_boys::cuda {
namespace detail {
using scalar::detail::PrepareCoordinates;
using scalar::detail::RoundedMainGridKey;
} // namespace detail
// Combined immutable table; finite nonnegative x (including -0) required.
template <class Model> class CombinedEvaluator {
public:
  FAST_BOYS_HD constexpr explicit CombinedEvaluator(TableView<Model> table)
      : table_(table) {}
  template <int First, int Last>
  FAST_BOYS_HD FAST_BOYS_INLINE void evaluate(const double x,
                                              double *FAST_BOYS_RESTRICT out,
                                              std::size_t stride = 1) const {
    evaluate<First, Last>(x, Last, out, stride);
  }
  template <int First, int Limit = Model::last>
  FAST_BOYS_HD FAST_BOYS_INLINE void evaluate(const double x, int last,
                                              double *FAST_BOYS_RESTRICT out,
                                              std::size_t stride = 1) const {
    scalar::detail::EvaluateCombined<First, Limit>(table_, x, last, out,
                                                   stride);
  }

private:
  TableView<Model> table_;
};
template <class Model>
FAST_BOYS_HD constexpr auto make_evaluator(TableView<Model> table) {
  return CombinedEvaluator<Model>(table);
}

} // namespace fast_boys::cuda

#pragma once
#include "fast_boys/scalar.h"
namespace fast_boys::cuda {
using scalar::LargeArgumentFallback;
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

using scalar::detail::SharesArithmetic;

// Finite x >= 0 (including -0) is a caller precondition. Coordinate preparation
// diverges, but both tables feed the same loads, correction and Horner graph.
template <class Model, class Tail> class PairedEvaluator {
public:
  FAST_BOYS_HD constexpr PairedEvaluator(TableView<Model> main,
                                         TableView<Tail> tail)
      : main_(main), tail_(tail) {}
  template <int First, int Last>
  FAST_BOYS_HD inline void evaluate(double x, double *FAST_BOYS_RESTRICT out,
                                    std::size_t stride = 1) const {
    evaluate<First, Last>(x, Last, out, stride);
  }
  template <int First, int Limit = Model::last>
  FAST_BOYS_HD inline void evaluate(double x, int last,
                                    double *FAST_BOYS_RESTRICT out,
                                    std::size_t stride = 1) const {
    scalar::detail::EvaluatePaired<First, Limit>(main_, tail_, x, last, out,
                                                 stride);
  }

private:
  TableView<Model> main_;
  TableView<Tail> tail_;
};
// RN-even, gradual underflow, explicit FMA. Users should not enable floating-
// point traps. No allocation, synchronization, or full-warp assumption here.
template <class Model, class OutsideDomain> class Evaluator {
public:
  FAST_BOYS_HD constexpr Evaluator(TableView<Model> table,
                                   OutsideDomain outside)
      : table_(table), outside_(outside) {}
  template <int First, int Last>
  FAST_BOYS_HD inline void evaluate(const double x,
                                    double *FAST_BOYS_RESTRICT out,
                                    std::size_t stride = 1) const {
    evaluate<First, Last>(x, Last, out, stride);
  }
  // Each lane may request a different last. Only [First,last] is written.
  template <int First, int Limit = Model::last>
  FAST_BOYS_HD inline void evaluate(const double x, int last,
                                    double *FAST_BOYS_RESTRICT out,
                                    std::size_t stride = 1) const {
    scalar::detail::EvaluateWithFallback<First, Limit>(table_, outside_, x,
                                                       last, out, stride);
  }

private:
  TableView<Model> table_;
  OutsideDomain outside_;
};
template <class Model, class Tail>
FAST_BOYS_HD constexpr auto make_evaluator(TableView<Model> main,
                                           TableView<Tail> tail) {
  scalar::detail::CheckPair<Model, Tail>();
  if constexpr (SharesArithmetic<Tail>::value)
    return PairedEvaluator<Model, Tail>(main, tail);
  else
    return Evaluator<Model, LargeArgumentFallback<Tail>>(
        main, LargeArgumentFallback<Tail>(tail));
}
} // namespace fast_boys::cuda

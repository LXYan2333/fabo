#ifndef FAST_BOYS_DETAIL_CUDA_EVALUATOR_CUH_
#define FAST_BOYS_DETAIL_CUDA_EVALUATOR_CUH_
#include "fast_boys/detail/cuda/large_argument.cuh"
namespace fast_boys::cuda {
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
    static_assert(Model::first <= First && First <= Limit &&
                      Limit <= Model::last,
                  "requested range outside model");
    FAST_BOYS_ASSERT(First <= last && last <= Limit && stride > 0);
    using O = detail::Binary64;
    const auto bits = O::bits(x);
    // Bit tests remain meaningful in fast-math builds; -0 is admitted.
    if (FAST_BOYS_UNLIKELY(((bits >> 63) && (bits << 1)) ||
                           (bits & 0x7fffffffffffffffULL) >
                               O::bits(Model::domain_end))) {
      outside_.template evaluate<First, Limit>(x, last, out, stride);
      return;
    }
    const double y = O::add(x, Model::offset);
    const auto key = (O::bits(y) + (1ULL << (Model::discarded_bits - 1))) >>
                     Model::discarded_bits;
    const double r =
        O::sub(O::value(key << Model::discarded_bits), Model::offset);
    const double h = O::sub(r, x);
    const auto *row = table_.data() + (key - Model::key_min) * Model::row_words;
    Model::template evaluate<O, First, Limit>(row, h, last, out, stride);
  }

private:
  TableView<Model> table_;
  OutsideDomain outside_;
};
template <class Model, class Tail>
FAST_BOYS_HD constexpr auto make_evaluator(TableView<Model> main,
                                           TableView<Tail> tail) {
  static_assert(Model::domain_end == Tail::minimum_x,
                "main/tail domain seam mismatch");
  static_assert(Tail::first <= Model::first && Model::last <= Tail::last,
                "tail does not cover this model");
  static_assert(Model::error_metric == Tail::error_metric &&
                    Model::error_limit == Tail::error_limit,
                "tail has a different qualification target; use an explicit "
                "custom handler");
  return Evaluator<Model, LargeArgumentFallback<Tail>>(
      main, LargeArgumentFallback<Tail>(tail));
}
} // namespace fast_boys::cuda
#endif

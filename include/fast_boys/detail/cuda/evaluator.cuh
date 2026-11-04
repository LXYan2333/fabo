#ifndef FAST_BOYS_DETAIL_CUDA_EVALUATOR_CUH_
#define FAST_BOYS_DETAIL_CUDA_EVALUATOR_CUH_
#include "fast_boys/detail/cuda/large_argument.cuh"
#include <type_traits>
namespace fast_boys::cuda {
template<class Tail,class=void> struct SharesArithmetic : std::false_type {};
template<class Tail> struct SharesArithmetic<Tail,std::void_t<decltype(Tail::shared_arithmetic)>>
    : std::bool_constant<Tail::shared_arithmetic> {};

// Finite x >= 0 (including -0) is a caller precondition. Coordinate preparation
// diverges, but both tables feed the same loads, correction and Horner graph.
template<class Model,class Tail> class PairedEvaluator {
public:
  FAST_BOYS_HD constexpr PairedEvaluator(TableView<Model> main,TableView<Tail> tail)
      : main_(main),tail_(tail) {}
  template<int First,int Last>
  FAST_BOYS_HD inline void evaluate(double x,double* FAST_BOYS_RESTRICT out,std::size_t stride=1) const {
    evaluate<First,Last>(x,Last,out,stride);
  }
  template<int First,int Limit=Model::last>
  FAST_BOYS_HD inline void evaluate(double x,int last,double* FAST_BOYS_RESTRICT out,std::size_t stride=1) const {
    static_assert(Model::row_words==Tail::row_words,"paired row layout mismatch");
    static_assert(std::is_same<Model,typename Tail::MainModel>::value,"tail belongs to a different main model");
    FAST_BOYS_ASSERT(First<=last && last<=Limit && stride>0);
    using O=detail::Binary64;
    FAST_BOYS_ASSERT((x>=0 && O::bits(x)<0x7ff0000000000000ULL) || O::bits(x)==0x8000000000000000ULL);
    const std::uint64_t* row;
    double h;
    unsigned k=0;
    if(x<=Model::domain_end) {
      const double y=O::add(x,Model::offset);
      const auto key=(O::bits(y)+(1ULL<<(Model::discarded_bits-1)))>>Model::discarded_bits;
      h=O::sub(O::sub(O::value(key<<Model::discarded_bits),Model::offset),x);
      row=main_.data()+(key-Model::key_min)*Model::row_words;
    } else {
      const auto bits=O::bits(x);
      const unsigned exponent=unsigned(bits>>52)-1023;
      k=exponent/2;
      const double u=O::value((bits&0xfffffffffffffULL)|(std::uint64_t(1023+(exponent&1))<<52));
      const auto key=(O::bits(u)+(1ULL<<(Tail::discarded_bits-1)))>>Tail::discarded_bits;
      h=O::sub(O::value(key<<Tail::discarded_bits),u);
      row=tail_.data()+(key-(1023ULL<<Tail::retained_bits))*Tail::row_words;
    }
    Model::template evaluate<O,First,Limit>(row,h,last,out,stride,k);
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
  if constexpr(SharesArithmetic<Tail>::value)
    return PairedEvaluator<Model,Tail>(main,tail);
  else
    return Evaluator<Model, LargeArgumentFallback<Tail>>(main, LargeArgumentFallback<Tail>(tail));
}
} // namespace fast_boys::cuda
#endif

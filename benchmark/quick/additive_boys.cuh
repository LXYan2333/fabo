#ifndef FAST_BOYS_QUICK_ADDITIVE_BOYS_CUH_
#define FAST_BOYS_QUICK_ADDITIVE_BOYS_CUH_
// QUICK/LibXC define function-like min/max macros before including this file.
#pragma push_macro("min")
#pragma push_macro("max")
#undef min
#undef max
#include "fast_boys/cuda.cuh"
#pragma pop_macro("max")
#pragma pop_macro("min")

// Thin source-level binding for QUICK's FmT(MaxM, X, YVerticalTemp).
// Select Model using the actual call-site request ceiling. In particular,
// ENABLEF's SPD-labelled kernel can require F_12, not merely F_8.
// The caller supplies its lane-specific YVerticalTemp pointer and
// order_stride = size_t(gridDim.x) * blockDim.x (QUICK's LOCVY layout).
// Upload each immutable main table once; share one compact tail allocation.
// No scratch output array, warp reduction, or indirect function call is needed.
template <class Model, class Tail>
FAST_BOYS_HD inline void
FaboAdditiveBoys(const int last, const double x,
                 double *FAST_BOYS_RESTRICT output, std::size_t order_stride,
                 fast_boys::TableView<Model> main_table,
                 fast_boys::TableView<Tail> tail_table) {
  static_assert(Model::first == 0,
                "QUICK FmT requires outputs starting at zero");
  const auto boys = fast_boys::cuda::make_evaluator(main_table, tail_table);
  boys.template evaluate<0>(x, last, output, order_stride);
}
#endif

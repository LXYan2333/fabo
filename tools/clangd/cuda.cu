// Editor translation unit: open this for the CUDA evaluator and upload helper.
#include "fast_boys/cuda.cuh"
#include "fast_boys/cuda/upload.cuh"
#include "fast_boys/selected.h"

namespace fabo_editor {
using Model = fast_boys::selected::Model<4>;

__global__ void evaluate_cuda(fast_boys::TableView<Model> table, double x,
                              int last, double *out) {
  const auto evaluator = fast_boys::cuda::make_evaluator(table);
  evaluator.evaluate<0, 4>(x, out);
  evaluator.evaluate<0>(x, last, out);
}
} // namespace fabo_editor

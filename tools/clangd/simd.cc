// Editor translation unit: open this for the Highway CPU evaluator.
#include "fast_boys/simd_config.h"
#include "fast_boys/selected_simd.h"

namespace fabo_editor {
namespace fb = fast_boys::simd::HWY_NAMESPACE;
using Model = fast_boys::selected::Model<4>;

void evaluate_simd(fast_boys::TableView<Model> table, fb::V x, fb::V &f0,
                   fb::V &f1, fb::V &f2, fb::V &f3, fb::V &f4) {
  const auto evaluator = fb::make_evaluator(table);
  evaluator.evaluate<0, 4>(fb::D(), x, f0, f1, f2, f3, f4);
}
} // namespace fabo_editor

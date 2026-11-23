#ifndef FAST_BOYS_QUICK_ADDITIVE_BINDING_CUH_
#define FAST_BOYS_QUICK_ADDITIVE_BINDING_CUH_
#include "additive_boys.cuh"
#include "fast_boys/selected.h"

// Pointers, not payloads, occupy CUDA constant memory. Payloads are immutable
// global allocations, uploaded once on QUICK's selected device during setup.
static __constant__ const std::uint64_t *fabo_quick_main[3];

template <int FamilyMax> struct FaboQuickFamily {
  static_assert(FamilyMax == 4 || FamilyMax == 8 || FamilyMax == 12);
#ifdef ENABLEF
  static constexpr int last = FamilyMax == 4 ? 4 : 12;
#else
  static constexpr int last = FamilyMax;
#endif
  using Model = fast_boys::selected::Model<last>;
};

template <int FamilyMax>
__device__ static __forceinline__ void
FaboQuickFmT(const int last, const double x, double *output) {
  using Model = typename FaboQuickFamily<FamilyMax>::Model;
  FaboAdditiveBoys<Model>(last,x,output,std::size_t(gridDim.x)*blockDim.x,
      fast_boys::TableView<Model>::from_pointer(fabo_quick_main[FamilyMax/4-1]));
}
#endif

#ifndef FABO_QUICK_REFERENCE_BINDING_CUH_
#define FABO_QUICK_REFERENCE_BINDING_CUH_
#pragma push_macro("min")
#pragma push_macro("max")
#undef min
#undef max
#include "reference_boys.h"
// Same strided output ABI as QUICK. Only accepted, uniquely rounded intervals
// reach molecular output; unresolved requests abort and replay from fixed P0.
__device__ static __forceinline__ void
FaboReferenceFmT(int last, double x, double* output) {
  const unsigned long long stride =
      static_cast<unsigned long long>(gridDim.x) * blockDim.x;
  if (last < 0 || last > fabo_reference::MaxOrder) {
    atomicExch(&fabo_reference::invalid_count, 1U);
    return;
  }
  for (int n = 0; n <= last; ++n)
    output[n * stride] = fabo_reference::rounded(n, x);
}
#pragma pop_macro("max")
#pragma pop_macro("min")
#endif

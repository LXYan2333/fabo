#ifndef FABO_QUICK_COMPARATOR_BINDING_CUH_
#define FABO_QUICK_COMPARATOR_BINDING_CUH_
#pragma push_macro("min")
#pragma push_macro("max")
#undef min
#undef max
#include <cstddef>
#if (defined(FABO_COMPARATOR_LIBINTX) + defined(FABO_COMPARATOR_VSR) + defined(FABO_COMPARATOR_GANSU)) != 1
#error Select exactly one QUICK comparator
#endif
#if defined(FABO_COMPARATOR_LIBINTX)
#include "libintx_boys.h"
#elif defined(FABO_COMPARATOR_VSR)
#include "vsr_boys.h"
#else
#include "gansu_boys.h"
#endif
#if !defined(FABO_COMPARATOR_VSR)
static __constant__ const double *fabo_comparator_table;
#endif

// QUICK's two energy-integral call sites pass a lane pointer. Successive Boys
// orders are gridDim.x*blockDim.x doubles apart; the requested order may differ
// between threads. No temporary sequence, collective, or function pointer.
__device__ static __forceinline__ void
FaboComparatorFmT(int last, double x, double *output) {
  const std::size_t stride = std::size_t(gridDim.x) * blockDim.x;
#if defined(FABO_COMPARATOR_LIBINTX)
  FaboLibintxBoys(last, x, output, stride, fabo_comparator_table);
#elif defined(FABO_COMPARATOR_VSR)
  FaboVsrBoys(last, x, output, stride);
#else
  fabo_gansu::getIncrementalBoys(last, x, fabo_comparator_table, output, stride);
#endif
}
#pragma pop_macro("max")
#pragma pop_macro("min")
#endif

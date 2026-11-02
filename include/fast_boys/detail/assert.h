#ifndef FAST_BOYS_DETAIL_ASSERT_H_
#define FAST_BOYS_DETAIL_ASSERT_H_
#include "fast_boys/detail/config.h"
#if FAST_BOYS_ENABLE_ASSERTS
#include <cstdio>
#include <cstdlib>
namespace fast_boys::detail {
FAST_BOYS_HD static inline void assertion_failed(const char *expression,
                                                const char *file, int line) {
#if defined(__CUDA_ARCH__)
  printf("fast_boys assertion failed: %s (%s:%d)\n", expression, file, line);
  __trap();
#else
  std::fprintf(stderr, "fast_boys assertion failed: %s (%s:%d)\n", expression,
               file, line);
  std::abort();
#endif
}
} // namespace fast_boys::detail
#define FAST_BOYS_ASSERT(condition)                                            \
  do {                                                                        \
    if (!(condition))                                                         \
      ::fast_boys::detail::assertion_failed(#condition, __FILE__, __LINE__);     \
  } while (false)
#else
// Do not evaluate the expression, including any side effects.
#define FAST_BOYS_ASSERT(condition) ((void)0)
#endif
#endif

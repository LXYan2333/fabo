#ifndef FAST_BOYS_DETAIL_CONFIG_H_
#define FAST_BOYS_DETAIL_CONFIG_H_
// Runtime precondition checks are opt-in, independently of NDEBUG. Use the
// same setting in every translation unit that instantiates the evaluator.
#ifndef FAST_BOYS_ENABLE_ASSERTS
#define FAST_BOYS_ENABLE_ASSERTS 0
#endif
#if FAST_BOYS_ENABLE_ASSERTS != 0 && FAST_BOYS_ENABLE_ASSERTS != 1
#error "FAST_BOYS_ENABLE_ASSERTS must be 0 or 1"
#endif
#if __cplusplus < 201703L
#error "fast_boys requires C++17 or newer"
#endif
#if defined(__CUDACC__)
#define FAST_BOYS_HD __host__ __device__
#else
#define FAST_BOYS_HD
#endif
#if defined(_MSC_VER)
#define FAST_BOYS_RESTRICT __restrict
#else
#define FAST_BOYS_RESTRICT __restrict__
#endif
// C++26 distinguishes erroneous from indeterminate uninitialized storage.
// This attribute does not initialize the variable or permit reading it before
// assignment. Generated stages always assign every coefficient before use.
#define FAST_BOYS_INDETERMINATE
#if defined(__has_cpp_attribute)
#if __cplusplus > 202302L && __has_cpp_attribute(indeterminate)
#undef FAST_BOYS_INDETERMINATE
#define FAST_BOYS_INDETERMINATE [[indeterminate]]
#endif
#endif
#if defined(__GNUC__) || defined(__clang__)
#define FAST_BOYS_UNLIKELY(x) __builtin_expect(bool(x), false)
#else
#define FAST_BOYS_UNLIKELY(x) (x)
#endif
#endif

#ifndef FAST_BOYS_SIMD_CONFIG_H_
#define FAST_BOYS_SIMD_CONFIG_H_

// Include before any Highway headers, especially hwy/foreach_target.h.
// SSE targets have no native FMA. Keep Highway's scalar/emulated baseline as
// a compatibility path, but omit these SIMD targets by default. An explicit
// HWY_DISABLED_TARGETS (including 0) takes precedence. If Highway has already
// selected targets, leave that translation unit's configuration unchanged.
#if !defined(HIGHWAY_HWY_DETECT_TARGETS_H_) && !defined(HWY_DISABLED_TARGETS)
#define HWY_DISABLED_TARGETS (HWY_SSE2 | HWY_SSSE3 | HWY_SSE4)
#endif

#endif // FAST_BOYS_SIMD_CONFIG_H_

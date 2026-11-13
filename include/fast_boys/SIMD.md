# Highway SIMD API

The CPU backend reuses the CUDA evaluator's exact paired table words, additive grid, order-dependent degrees, next-up corrections, and materialized large-argument model. It does not create another numerical selection or table layout. Use C++17 and Highway 1.4 or newer with binary64 support.

## Compile-time output ranges

```cpp
// Include this before hwy/foreach_target.h when using Highway dispatch.
#include "fast_boys/simd_config.h"
#include "fast_boys/selected_simd.h"
// Include payloads only in the translation unit that owns storage.
#include "fast_boys/models/data_0_4.h"

using Model = fast_boys::selected::Model<4>;
static constexpr fast_boys::BoysTable<Model> table{};

// Inside a HWY_BEFORE_NAMESPACE / HWY_AFTER_NAMESPACE target namespace:
namespace fb = fast_boys::simd::HWY_NAMESPACE;
auto boys = fb::make_evaluator(table.view());
fb::V f1, f2, f3;
boys.evaluate<1, 3>(x, f1, f2, f3);
```

`x` is a full Highway binary64 vector (`VFromD<ScalableTag<double>>`). Each output is a separate `HWY_RESTRICT` vector reference, in increasing order, and must not alias another output or table storage. The input is passed by value. No containers of SIMD vectors are used, allowing sizeless SVE/RVV vector types. Subsets share the original table and omit unrelated main-path coefficients and Horner calculations. There is no runtime-order CPU overload.

`selected_simd.h` is a convenience catalog, not payload storage. A minimal caller can instead include `simd.h` and its combined `models/<id>/simd-inl.h` companion. These are target-toggle headers compatible with `hwy/foreach_target.h`; place application functions in the corresponding target namespace. The owning `BoysTable` belongs outside target namespaces and can be shared across targets or translation units through `TableView`. Keep its lifetime longer than every evaluator. No runtime table initialization is required for constexpr storage. Mixed main/tail vectors select logical row indices before gathering, so each coefficient or correction word requires only one gather from the combined allocation.

## Gather policy

`make_evaluator<true>` selects software gather; `<false>` selects Highway's native/fallback gather. The default is software on AVX2, AVX3, and AVX3_DL, native elsewhere. This is an ISA-based conservative GDS policy, not CPU vulnerability detection. The specialized software loader requires x86-64; on other architectures, including 32-bit x86, the software choice delegates to Highway's gather implementation.

On GCC x86 AVX2/AVX-512 targets, native word gathers use the zero-merge, opaque-all-active-mask workaround from [Highway PR #3519](https://github.com/google/highway/pull/3519), preventing GCC PR #127946's false destination dependency. The empty register-only asm hides the mask, not table values or arithmetic, and has no memory clobber. AVX2 uses the double-mask representation required by Highway's 64-bit masked-gather helper. This also supports Highway releases predating the PR; defining `HWY_DISABLE_GCC_GATHER_WORKAROUND` disables it consistently with the PR. Clang and other targets retain ordinary Highway gathers. No numerical table or loading policy changes are involved.

The x86-64 software path narrows physical word indices only when the maximum index fits, extracts packed indices, and loads exactly eight bytes per lane using `_mm_load_sd` for the low half and `_mm_loadh_pd` for the high half before combining vectors. These direct loads deliberately rely on compiler-intrinsic handling of uint64_t storage through double pointers, rather than a portable C++ aliasing guarantee. The checked Clang/GCC builds emit paired memory loads without stack staging or a separate unpack. It never reads an unused neighboring table entry. Main and correction words are gathered at eight-byte-aligned addresses; no unaligned-gather optimization or extra guard padding is used. Row multiplication uses identity, constant shift, or bounded 32-by-32 multiplication when applicable, otherwise ordinary Highway multiplication.

On native x86 SIMD targets, correction-byte extraction uses `ShiftRightBytes` followed by a per-u64 `And(255)` to favor shuffle resources over lane-shift resources. Although the shift spans each 128-bit block, the retained low byte belongs to the original u64 lane for byte offsets 0–7. Offset zero needs only the mask. GCC/Clang use an empty register operand to preserve the entire shifted vector before masking; otherwise Clang can replace the shuffle with lane shifts. This emits no instruction or memory fence. Other compilers may still rewrite the operation. Other architectures and scalar/emulated targets retain ordinary lane shifts; this policy is not a measured speedup claim for every x86 microarchitecture.

## Numerical contract and portability

Final power-of-two scaling uses an `AllTrue` check on every target to return integer exponent adjustment immediately when every lane's result remains normal. This fast path requires no integer-to-floating conversion or floating-point scaling instruction. Otherwise Highway's `MulByPow2` handles the entire vector, including underflow and zero results. Floating-point scaling follows the execution environment: enabling FTZ can flush subnormal outputs to zero and is outside the strict one-ULP qualification contract. Fast-math builds are diagnostic configurations; compiler flags alone do not establish the runtime FTZ/DAZ state. The evaluator does not change that state.

Use round-to-nearest, ties-to-even and gradual underflow (FTZ/DAZ off). Users should not enable floating-point traps. The evaluator neither changes nor checks those settings. Main and tail gathers use sanitized, valid indices even in mixed vectors. The combined evaluator requires finite nonnegative inputs, including negative zero; infinity, negative arguments and NaNs are outside its contract. Floating-point status flags are not part of the API contract.

Explicit FMA and numerical reassociation fences preserve the existing operation graph. `simd_config.h` disables SSE2/SSSE3/SSE4 by default unless the caller already defines `HWY_DISABLED_TARGETS` or Highway has selected its targets. An override is supported for convenience: targets without native FMA use per-lane `std::fma`, which is not a tuned performance path. Do not interpret a fast-math build as a new numerical certificate. Strict scalar/SIMD bitwise conformance and separate fast-math diagnostics complement the archived sampled one-ULP qualification; they do not prove a continuous-domain error bound.

## Generation and checks

```sh
python -m workflow.additive.simd_headers --include include
python -m workflow.scripts.format_public_headers --include include --clang-format clang-format-22
FABO_HIGHWAY_ROOT=/path/to/highway python -m pytest workflow/additive/tests/test_simd*.py -q
```

The separate generator reads `include/manifest.json`. It writes only SIMD companions, the SIMD catalog, and `simd-manifest.json`, whose hashes associate the implementation with the unchanged numerical manifest. It does not rewrite CUDA headers, payloads, or search results. The combined SIMD evaluator prepares main and tail coordinates and selects between them before shared reference reconstruction, displacement, coefficient gathers, and Horner arithmetic. Equal grid resolutions also share one key calculation; unequal resolutions retain compile-time shifts and select the resulting key and reference bits. Compiler/ISA tests skip unavailable dependencies; cross-compilation alone does not validate runtime behavior on another architecture.

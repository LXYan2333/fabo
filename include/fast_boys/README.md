# Evaluation APIs

The CUDA API is described below. See [SIMD.md](SIMD.md) for the Highway CPU API with compile-time output ranges and native/software gather selection.

The evaluator uses fully materialized reference coefficients on the selected additive grid. It has no main-domain recurrence patches, exponential dictionary, or runtime exponential. Numerical models and exact table words are portable; CUDA operations and allocation helpers are separate.

## Bundled selections

The source tree includes the completed one-ULP selections for every range `[0,N]`, N=0–24. Their frozen search summary is `data/numerical/additive-1ulp-summary.json`; `include/manifest.json` records the exact generated model and payload identities. Regenerate all bundled headers without repeating the search using:

```sh
python -m workflow.additive.headers data/numerical/additive-1ulp-summary.json --output include
```

Include `fast_boys/selected.h` for lightweight model aliases. `fast_boys::selected::Model<24>` selects the `[0,24]` model, and `fast_boys::selected::Tail` selects the shared compact fallback. Include `fast_boys/models/data_0_24.h` and `fast_boys/models/tail_data.h` only in the host initialization translation unit to instantiate their `BoysTable` storage. Substitute another N in the alias and data-header name to use its independently selected grid and degrees. Including the catalog alone does not allocate or embed any table payload; subset evaluation of one model continues to share that model's table.

Generate headers from a completed numerical summary (no parameter search):

```sh
python -m workflow.additive.headers PATH/summary.json \
  --output .work/generated/include --ranges 0-4 0-8 0-12
```

Omit `--ranges` to generate every selected model. Add `include` and the generated include root to the compiler include path. When using an alternative catalog's `selected.h`, put its generated include root first; explicit hash-qualified model headers do not need the convenience alias. `manifest.json` names each hash-qualified C++ model, the original numerical identity, table sizes, and generator/runtime source hashes. Generation checks the frozen canonical payload SHA-256 before publishing reordered data; the emitted payload has a separate SHA-256 and layout identifier. Different generated models can coexist; filenames and namespaces are content/version qualified.

## Ownership and use

Include `fast_boys/models/<id>/model.h` in kernel translation units. Include its separate `data.h` only where host storage is initialized. `fast_boys::BoysTable<Model>` owns immutable words, is constexpr-initializable, and performs no numerical synthesis. Use static storage for large tables. The public `cuda.cuh` header includes neither generated payloads nor allocation machinery.

```cpp
// Initialization translation unit; Model and Tail are aliases from manifest.json.
#include "fast_boys/cuda/upload.cuh"
static constexpr fast_boys::BoysTable<Model> host_main{};
static constexpr fast_boys::BoysTable<Tail> host_tail{};
fast_boys::cuda::DeviceTable<Model> main_device(host_main);
fast_boys::cuda::DeviceTable<Tail> tail_device(host_tail);

// Inside the caller's CUDA kernel, using the uploaded TableView handles:
auto boys = fast_boys::cuda::make_evaluator(main_view, tail_view);
boys.evaluate<0, 4>(x, output, order_stride);
boys.evaluate<2, 4>(x, output, order_stride);
boys.evaluate<0>(x, runtime_last, output, order_stride);
boys.evaluate<2, 4>(x, runtime_last, output, order_stride);
```

`output[(n-First)*order_stride]` receives F_n; all other output locations are untouched. `order_stride` is in doubles, not bytes. The runtime overload requires `First <= runtime_last <= Limit`, with `Limit=Model::last` by default. Static subsets are always compile-time checked. Runtime bounds and a nonzero stride are caller preconditions; checks are disabled by default in every build type. Define `FAST_BOYS_ENABLE_ASSERTS=1` before including any library header (or pass `-DFAST_BOYS_ENABLE_ASSERTS=1`) to enable them for debugging/conformance, independently of `NDEBUG`. Failure prints a diagnostic and aborts on the host or traps on CUDA. Use the same macro setting across translation units. These checks do not change floating-point exception settings. Input/output storage must not alias the read-only table. Every thread may have a different endpoint or argument, even in a partial warp or a divergent calling context; there are no warp collectives.

The generated code declares individual coefficient variables without initialization, assigns each at first use, and returns before loads needed only by later outputs. All coefficient indices and Taylor degrees are compile-time constants. Higher outputs reuse loaded coefficients and Horner factors. The compiler controls physical registers and may spill under pressure; source-level reuse is not a promise of zero machine-code reloads. `[[indeterminate]]` is emitted through a feature- and language-guarded macro in supporting C++26 compilers. It never licenses an uninitialized read and is unnecessary for leaving a C++17 declaration uninitialized.

Each main-table row interleaves one 64-bit correction word before each group of eight corresponding reference coefficients: corrections for outputs 0–7, coefficients 0–7, corrections for outputs 8–15, coefficients 8–15, and so on (indices are relative to the model's first order). Once all output corrections have been placed, remaining Taylor coefficients follow without extra correction slots. The final correction word retains the original zero padding. This brings low-order corrections closer to the coefficients used by short requests without increasing row size or changing numerical values. All generated accesses use constant word offsets. The compact cold-tail layout is unchanged. Reduced memory-sector traffic is layout-dependent, not a measured speedup guarantee.

`DeviceTable` is an optional synchronous host upload helper. It is move-only and must be destroyed on its allocation device after kernels have finished. The core accepts caller-managed allocations through `TableView<Model>::from_pointer`; this is an explicit trust boundary and requires matching bytes, lifetime, address space, and eight-byte alignment. Sharing a tail allocation across evaluators is encouraged. Do not copy an owning table into each GPU thread.

## Numerical and large-argument behavior

Use C++17 or later, binary64 RN-even arithmetic, and gradual underflow. Users should not enable floating-point traps; the library does not inspect or change trap settings. CUDA uses explicit rounded add/multiply and FMA intrinsics to preserve the canonical numerical DAG. The host-parsable implementation is for conformance, not a tuned CPU backend. Strict and fast-math validation are distinct artifacts. The numerical one-ULP target is sampled qualification against directed reference enclosures, not a continuous-domain guarantee.

The default factory pairs the main domain `[0,1e7]` with the archived compact large-argument model on `(1e7,DBL_MAX]`. It checks matching domains, order coverage, and error targets at compile time. Positive infinity returns zero; negative inputs and NaNs return NaNs without table access. Negative zero is accepted. An explicitly supplied `Evaluator<Model,Handler>` can use another outside-domain policy; `Handler::evaluate<First,Limit>(x,last,output,stride)` must implement the required behavior and has independent numerical responsibility.

The cold tail retains 129 rows and 9,288 bytes. It uses exact exponent normalization, a patched reference recurrence for the complete integral A_n(u), degree-12 factorial Horner, unsigned next-up corrections, and RN-even power-of-two scaling into subnormals/zero. It does not store every order or compute exp(-x). Its retained accuracy target is one ULP for orders 0–24; it cannot automatically qualify a different requested error target. Its original data and provenance are in `data/numerical/compact-tail-1ulp.json`; the archived patch words are copied exactly, not regenerated by a new search.

## QUICK integration

QUICK's `VY(0,0,n)` has an order stride of `gridDim.x * blockDim.x` doubles from the lane-specific output pointer. Pass that pointer and stride directly to the runtime overload; no intermediate output array or global function pointer is needed. Select the numerical model from the actual request ceiling, not just the family label: ordinary SP/SPD ceilings are 4/8, while the ENABLEF SPD path can request order 12. A binding must account for gradients or other callers separately rather than assuming these bounds universally.

## Checks

```sh
python -m pytest -q
# On an allocated GPU, with NVCC on PATH (or FABO_NVCC=/path/to/nvcc):
FABO_RUN_CUDA=1 python -m pytest workflow/additive/tests/test_headers.py -q
```

Tests cover exact serialized words, incremental loading with nonmonotonic degrees, every fixture cell boundary, static/runtime subsets, output sentinels, correction decoding, compact-tail scaling and MPFR checks, and multi-translation-unit ownership. CUDA execution tests partial/divergent warps and heterogeneous request endpoints. Fast-math differences are written as diagnostics in pytest's temporary directory. Device tests are explicitly skipped without an allocation; a host pass alone does not qualify device execution.

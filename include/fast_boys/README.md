# Evaluation APIs

Combined catalogs (`FAST_BOYS_COMBINED_TABLE`) select `Model<Last,First>` with one `data_First_Last.h` payload header. One array stores main rows followed by tail rows; `Model::tail_row_offset` is the compile-time row offset, and `table_bytes` includes both regions. CUDA and Highway select coordinates and a logical row, then execute common coefficient loads and Horner arithmetic. Subsets reuse the allocation. Inputs must be finite and nonnegative, including -0.0; infinity and NaN are outside this contract. Users should not enable floating-point traps.

The CUDA API is described below. See [SIMD.md](SIMD.md) for the Highway CPU API with compile-time output ranges and native/software gather selection.

The evaluator uses fully materialized reference coefficients on the selected additive grid. It has no main-domain recurrence patches, exponential dictionary, or runtime exponential. Numerical models and exact table words are portable; CUDA operations and allocation helpers are separate.

## Bundled selections

The source tree includes the completed paired one-ULP selections for every range `[0,N]`, N=0–24. Their frozen search summary is `data/numerical/paired-1ulp/summary.json`; that directory also contains the configuration and exact numerical producer sources. `include/manifest.json` records the generated model and payload identities. Regenerate all bundled headers without repeating the search using:

```sh
python -m workflow.additive.headers data/numerical/paired-1ulp/summary.json --output .work/generated/include
python -m workflow.additive.simd_headers --include .work/generated/include
```

Include `fast_boys/selected.h` for lightweight model aliases. `fast_boys::selected::Model<24>` selects `[0,24]`; include `fast_boys/models/data_0_24.h` only in the host initialization translation unit to instantiate its `BoysTable` storage. Substitute another N in the alias and data-header name to use its independently selected model. Including the catalog alone does not allocate or embed any table payload; subset evaluation continues to share the configured allocation.

Generate headers from a completed numerical summary (no parameter search):

```sh
python -m workflow.additive.headers PATH/summary.json \
  --output .work/generated/include --ranges 0-4 0-8 0-12
```

Omit `--ranges` to generate every selected model. Add `include` and the generated include root to the compiler include path. When using an alternative catalog's `selected.h`, put its generated include root first; explicit hash-qualified model headers do not need the convenience alias. `manifest.json` names each hash-qualified C++ model, the original numerical identity, table sizes, and generator hash. `simd-manifest.json` records SIMD source hashes. Generation checks the frozen canonical payload SHA-256 before publishing reordered data; the emitted payload has a separate SHA-256. Different generated models can coexist; filenames and namespaces are content/version qualified.

## Ownership and use

Include `fast_boys/models/<id>/model.h` in kernel translation units. Include its separate `data.h` only where host storage is initialized. `fast_boys::BoysTable<Model>` owns immutable words, is constexpr-initializable, and performs no numerical synthesis. Use static storage for large tables. The public `cuda.cuh` header includes neither generated payloads nor allocation machinery.

```cpp
// Initialization translation unit; Model is an alias from manifest.json.
#include "fast_boys/cuda/upload.cuh"
static constexpr fast_boys::BoysTable<Model> host_table{};
fast_boys::cuda::DeviceTable<Model> device_table(host_table);

// Inside the caller's CUDA kernel, using the uploaded TableView handles:
auto boys = fast_boys::cuda::make_evaluator(table_view);
boys.evaluate<0, 4>(x, output, order_stride);
boys.evaluate<2, 4>(x, output, order_stride);
boys.evaluate<0>(x, runtime_last, output, order_stride);
boys.evaluate<2, 4>(x, runtime_last, output, order_stride);
```

`output[(n-First)*order_stride]` receives F_n; all other output locations are untouched. `order_stride` is in doubles, not bytes. The runtime overload requires `First <= runtime_last <= Limit`, with `Limit=Model::last` by default. Static subsets are always compile-time checked. Runtime bounds and a nonzero stride are caller preconditions; checks are disabled by default in every build type. Define `FAST_BOYS_ENABLE_ASSERTS=1` before including any library header (or pass `-DFAST_BOYS_ENABLE_ASSERTS=1`) to enable them for debugging/conformance, independently of `NDEBUG`. Failure prints a diagnostic and aborts on the host or traps on CUDA. Use the same macro setting across translation units. These checks do not change floating-point exception settings. Input/output storage must not alias the read-only table. Every thread may have a different endpoint or argument, even in a partial warp or a divergent calling context; there are no warp collectives.

The generated CUDA code declares individual coefficient variables without initialization and loads newly required coefficients inside a runtime output-order loop with generated switch cases. All coefficient offsets and Taylor degrees are compile-time constants. Higher outputs reuse loaded coefficients and Horner factors, and the loop stops at each thread's requested endpoint. Small helpers use `__forceinline__` under CUDA; SIMD helpers use `HWY_INLINE`. The compiler controls physical registers and may spill under pressure; source-level reuse is not a promise of zero machine-code reloads. `[[indeterminate]]` is emitted through a feature- and language-guarded macro in supporting C++26 compilers. It never licenses an uninitialized read and is unnecessary for leaving a C++17 declaration uninitialized.

Each main and tail row interleaves one 64-bit correction word before each group of eight corresponding reference coefficients: corrections for outputs 0–7, coefficients 0–7, corrections for outputs 8–15, coefficients 8–15, and so on (indices are relative to the model's first order). Once all output corrections have been placed, remaining Taylor coefficients follow without extra correction slots. The final correction word retains zero padding. This brings low-order corrections closer to the coefficients used by short requests without increasing row size or changing numerical values. All generated accesses use constant word offsets. Reduced memory-sector traffic is layout-dependent, not a measured speedup guarantee.

`DeviceTable` is an optional synchronous host upload helper. It is move-only and must be destroyed on its allocation device after kernels have finished. The core accepts caller-managed allocations through `TableView<Model>::from_pointer`; this is an explicit trust boundary and requires matching bytes, lifetime, address space, and eight-byte alignment. Evaluators using the same configured pair can share its allocations; different pairs have different tails. Do not copy an owning table into each GPU thread.

## Numerical and large-argument behavior

Use C++17 or later, binary64 RN-even arithmetic, and gradual underflow. Users should not enable floating-point traps; the library does not inspect or change trap settings. CUDA uses explicit rounded add/multiply and FMA intrinsics to preserve the canonical numerical DAG. The host-parsable implementation is for conformance, not a tuned CPU backend. Strict and fast-math validation are distinct artifacts. The numerical one-ULP target is sampled qualification against directed reference enclosures, not a continuous-domain guarantee.

The default factory pairs the main domain `[0,C]` with its normalized materialized tail on `(C,DBL_MAX]`, where C is `Model::domain_end` and varies by configured range. It checks matching domains, order coverage, error targets, and pair identity. Only finite nonnegative arguments are admitted; negative zero is accepted. An explicitly supplied `Evaluator<Model,Handler>` can use another outside-domain policy; `Handler::evaluate<First,Limit>(x,last,output,stride)` must implement the required behavior and has independent numerical responsibility.

The tail normalizes x=u*2^(2k) with 1<=u<4 and tabulates the complete integral A_n(u), not F_n(u). It stores every needed reference coefficient and output correction; no reference recurrence or exponential is evaluated. Both tables feed the same CUDA factorial-Horner graph, followed by RN-even power-of-two scaling for tail outputs, including subnormals and zero. Qualification accounts for the omitted integral near C and checks scaling classes at large x. Each pair fits the combined 1 MiB budget; the selected `[0,4]`, `[0,8]`, and `[0,12]` switches are approximately 48.1420, 58.3906, and 66.6379. The exact constants, degrees, storage and sampled error witnesses are in the frozen summary.

## QUICK integration

QUICK's `VY(0,0,n)` has an order stride of `gridDim.x * blockDim.x` doubles from the lane-specific output pointer. Pass that pointer and stride directly to the runtime overload; no intermediate output array or global function pointer is needed. Select the numerical model from the actual request ceiling, not just the family label: ordinary SP/SPD ceilings are 4/8, while the ENABLEF SPD path can request order 12. A binding must account for gradients or other callers separately rather than assuming these bounds universally.

## Checks

```sh
python -m pytest -q
# On an allocated GPU, with NVCC on PATH (or FABO_NVCC=/path/to/nvcc):
FABO_RUN_CUDA=1 python -m pytest workflow/additive/tests/test_headers.py -q
```

Tests cover exact serialized words, incremental loading with nonmonotonic degrees, every fixture cell boundary, static/runtime subsets, output sentinels, correction decoding, compact-tail scaling and MPFR checks, and multi-translation-unit ownership. CUDA execution tests partial/divergent warps and heterogeneous request endpoints. Fast-math differences are written as diagnostics in pytest's temporary directory. Device tests are explicitly skipped without an allocation; a host pass alone does not qualify device execution.

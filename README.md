<p align="center">
  <img src="assets/fabo-logo.svg" alt="FABO logo" width="200">
</p>

# FABO — Fast and Accurate Boys

FABO is a header-only C++ library for evaluating Boys functions on CUDA GPUs and SIMD CPUs:

$$
F_n(x)=\int_0^1 t^{2n}\exp(-xt^2)\,dt.
$$

It is designed for use inside molecular-integral kernels. Precomputed tables and order-dependent Taylor polynomials provide double-precision outputs, with a normalized large-argument table covering the rest of the finite input range. Evaluation does not require a runtime exponential or error function.

The project name is **Fast and Accurate Boys**; the C++ namespace and include paths remain **`fast_boys`** for historical reason.

## What is included?

- A ready-to-use evaluator for Boys functions through order 24. For requested orders through 12, the largest error observed in the dense scan was about 1.07 ULPs.
- A CUDA evaluator with compile-time ranges or a per-thread runtime final order.
- A [Google Highway](https://github.com/google/highway) CPU evaluator with compile-time ranges and separate vector-reference outputs.
- A plain binary64 CPU evaluator requiring only C++17, also used lane by lane for Highway targets without native SIMD FMA.
- Immutable, constexpr-initializable host tables. Each bundled model's combined main/tail storage is at most 1 MiB.
- Subset evaluation: a `[0,24]` model can supply `[0,3]` or `[4,24]` without allocating another table. A dedicated smaller model may use less storage and different Taylor degrees.

No numerical search, Python environment, MPFR installation, or quantum-chemistry package is needed to use the bundled library.

The CPU and CUDA comparator ports used in the paper, including their coefficient sources and application bindings, are indexed in [benchmark/ports/README.md](benchmark/ports/README.md). They are separate from the library API and have their own upstream dependencies and licensing notices.

## Getting started

Add this repository's `include/` directory to your compiler's include path. Use C++17 or later. The SIMD backend additionally requires Highway 1.4 or newer; the GPU backend requires a CUDA compiler and device with double-precision support. QUICK, LibintX, and other benchmark dependencies are not required for normal library use, so there is no need to initialize their submodules.

Choose a model with `fast_boys::selected::Model<N>` and include its matching `fast_boys/models/data_0_N.h` payload where table storage is instantiated. Use static storage for host tables rather than placing a large table on the stack. Construct/upload a table once and reuse it across evaluations.

### CMake

CMake integration requires CMake 3.23 or newer. `fabo::fabo` provides the common headers and tables. `fabo::simd` also links Highway, while `fabo::cuda` also links the CUDA runtime and requires CUDA C++17.

For a source-tree dependency:

```cmake
# Highway must provide hwy::hwy, either from a parent add_subdirectory()
# or from an installed package discoverable through CMAKE_PREFIX_PATH.
add_subdirectory(path/to/fabo)
target_link_libraries(my_application PRIVATE fabo::simd)
```

`FABO_ENABLE_SIMD` defaults to `ON` and requires Highway **1.4.0 or newer**. CMake accepts an existing `hwy::hwy` target (the parent must ensure that version requirement); otherwise it calls `find_package(hwy 1.4.0 CONFIG REQUIRED)`. There are no automatic downloads. `FABO_ENABLE_CUDA` defaults to `OFF`; enabling it finds `CUDAToolkit`. For CUDA-only use, disable SIMD, enable CUDA, and link `fabo::cuda`. Your application enables the CUDA language and selects its GPU architectures. Core-only use disables both options and links `fabo::fabo`.

Highway 1.4.0's source build exposes the target `hwy`; after adding that source tree, use `add_library(hwy::hwy ALIAS hwy)` if the namespaced target does not already exist. Installed Highway packages already supply `hwy::hwy`.

Installation rules are enabled by default for a standalone build and disabled under `add_subdirectory()`, so vendored dependencies need no export rules. To install FABO from a parent project, set `FABO_ENABLE_INSTALL=ON` and use imported dependency targets or also export the vendored dependencies.

To install the default SIMD-enabled package:

```sh
cmake -S . -B build/cmake -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/path/to/highway/install \
  -DCMAKE_INSTALL_PREFIX=/path/to/fabo/install
cmake --install build/cmake
```

Then consume it with:

```cmake
find_package(fabo CONFIG REQUIRED COMPONENTS simd)
target_link_libraries(my_application PRIVATE fabo::simd)
```

Include the FABO and Highway installation prefixes in `CMAKE_PREFIX_PATH`. Request `COMPONENTS cuda` for a CUDA-enabled installation, or omit components for the dependency-free `fabo::fabo` target. Components are available only if enabled when installing. The package currently has no assigned release version, so use an unversioned `find_package(fabo ...)` call. CMake does not impose optimization, architecture, fast-math, or Highway dispatch flags on consumers. Existing direct-header usage and pytest-based research workflows remain supported; Python is not an installation dependency.

Use `OPTIONAL_COMPONENTS simd` or `OPTIONAL_COMPONENTS cuda` when a missing backend should leave the core usable; check `fabo_simd_FOUND` or `fabo_cuda_FOUND` before linking it.

### CPU scalar

For a plain C++17 scalar caller, include `fast_boys/scalar.h`, the model selection, and the matching data header. No Highway or CUDA is needed:

```cpp
#include "fast_boys/scalar.h"
#include "fast_boys/selected.h"
#include "fast_boys/models/data_0_4.h"

inline constexpr fast_boys::BoysTable<fast_boys::selected::Model<4>> table{};
auto evaluate_one(double x) {
  return fast_boys::scalar::evaluate<1, 3>(table.view(), x);
} // std::array<double, 3> containing F1, F2, F3, in order.
```

In CMake, link `fabo::fabo`; for a scalar-only installation set `FABO_ENABLE_SIMD=OFF`.

### Highway SIMD

This single-target example evaluates one full SIMD vector of arguments, returning orders 0–4 to five arrays. Each input/output array must have room for `hwy::HWY_NAMESPACE::Lanes(fast_boys::simd::HWY_NAMESPACE::D())` doubles; the five output arrays must not overlap each other or the table. Unaligned input/output pointers are supported by the loads and stores shown here.

```cpp
#include "fast_boys/simd_config.h"
#include "fast_boys/selected_simd.h"
#include "fast_boys/models/data_0_4.h"

using Model = fast_boys::selected::Model<4>;
inline constexpr fast_boys::BoysTable<Model> table{};

HWY_BEFORE_NAMESPACE();
namespace example {
namespace HWY_NAMESPACE {
namespace hn = hwy::HWY_NAMESPACE;
namespace fb = fast_boys::simd::HWY_NAMESPACE;

void evaluate_packet(const double* x, double* f0, double* f1,
                     double* f2, double* f3, double* f4) {
  const fb::D d;
  const auto vx = hn::LoadU(d, x);
  auto boys = fb::make_evaluator(table.view());
  fb::V v0, v1, v2, v3, v4;
  boys.evaluate<0, 4>(d, vx, v0, v1, v2, v3, v4);
  hn::StoreU(v0, d, f0);
  hn::StoreU(v1, d, f1);
  hn::StoreU(v2, d, f2);
  hn::StoreU(v3, d, f3);
  hn::StoreU(v4, d, f4);
}
}  // namespace HWY_NAMESPACE
}  // namespace example
HWY_AFTER_NAMESPACE();
```

For example, save this as `example.cc` and compile for the current CPU:

```sh
c++ -std=c++17 -O3 -march=native -DHWY_COMPILE_ONLY_STATIC \
  -I/path/to/fabo/include -I/path/to/highway -c example.cc
```

This produces an object file, not a complete executable. Call `example::HWY_NAMESPACE::evaluate_packet` from your application and handle partial final vectors in your batching code. For portable binaries, use Highway's target dispatch; see the [SIMD API guide](include/fast_boys/SIMD.md).

`fb::make_evaluator<false>(table.view())` selects native gather; `<true>` selects software gather. For most situations, omit the parameter: `fb::make_evaluator(table.view())` uses a suitable default. The default is software gather on Highway's AVX2, AVX3, and AVX3_DL targets and native gather elsewhere. Explicitly set this parameter to `false` only when your CPU is affected by Gather Data Sampling (GDS) and the related mitigation is not enabled. This is a conservative target policy, not runtime CPU vulnerability detection. Both policies use the same numerical model.

On binary64 Highway targets with `HWY_NATIVE_FMA == 0`, the SIMD API is provided for convenience: FABO evaluates the full requested range once per lane with the same scalar arithmetic. In Highway 1.4.0 the complete fallback list is:

| Target family | Highway targets that use scalar FABO |
| --- | --- |
| x86 | `HWY_SSE2`, `HWY_SSSE3`, `HWY_SSE4`; also `HWY_AVX2` **only** when `HWY_DISABLE_BMI2_FMA` is defined |
| WebAssembly | `HWY_WASM`, `HWY_WASM_EMU256` |
| Portable | `HWY_EMU128`, `HWY_SCALAR` |

Ordinary AVX2 builds use vector FMA. AArch64 NEON also uses vector FMA; 32-bit ARM NEON lacks Highway binary64 vector support, so it is not a fallback target. Use the plain scalar API there.

### CUDA

Pass a lightweight table view into your kernel. This example writes `out[n * count + i] = F_n(x[i])` for orders 0–4:

```cpp
#include "fast_boys/cuda.cuh"
#include "fast_boys/cuda/upload.cuh"
#include "fast_boys/selected.h"
#include "fast_boys/models/data_0_4.h"

using Model = fast_boys::selected::Model<4>;
inline constexpr fast_boys::BoysTable<Model> host_table{};

__global__ void evaluate_batch(fast_boys::TableView<Model> table,
                               const double* x, double* out,
                               std::size_t count) {
  const std::size_t i = std::size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i >= count) return;
  auto boys = fast_boys::cuda::make_evaluator(table);
  boys.evaluate<0, 4>(x[i], out + i, count);
}
```

Compile kernel code with your application's CUDA settings, for example:

```sh
nvcc -std=c++17 -O3 -arch=sm_120 -I/path/to/fabo/include -c example.cu
```

Replace `sm_120` with your device's architecture. On the host, after selecting the CUDA device, create `fast_boys::cuda::DeviceTable<Model> device_table(host_table)` and pass `device_table.view()` when launching the kernel. The optional owner uploads synchronously; keep it alive until all consuming kernels finish and destroy it on its allocation device. Input and output buffers must be device-accessible, and this example requires `5 * count` output doubles. Check CUDA launch and completion errors in the calling application.

For heterogeneous per-thread requests, replace the evaluation call with:

```cpp
boys.evaluate<0>(x[i], last_order[i], out + i, count);
```

Each thread may independently request `0 <= last_order[i] <= 4`. Only its requested outputs are written. No full-warp guarantee is needed. The stride is measured in doubles, not bytes; use stride 1 for contiguous per-thread output storage. See the [CUDA and table-ownership guide](include/fast_boys/README.md) for subsets, caller-managed allocations, and debugging assertions.

## Numerical contract

- Inputs must be finite and nonnegative; `-0.0` is accepted. NaNs, infinity, and negative arguments are outside the API contract.
- Use binary64 round-to-nearest, ties-to-even, with gradual underflow. Users should not enable floating-point traps. FABO does not change the floating-point environment.
- Host `double` intermediates must also have binary64 precision. On x86, x87 extended-precision evaluation is not supported. Most users do not need to care about this.
- The bundled models target one-ULP accuracy under sampled construction checks, **not guaranteed correct rounding or a proven one-ULP bound for every input**. Independent scans over `[0,1000]` at spacing `10^-6` for ranges `[0,N]`, `N <= 12`, observed a maximum of approximately **1.067 ULP**.
- Strict and fast-math validation are recorded separately. Fast-math compiler settings do not establish the required rounding/underflow environment or guarantee identical behavior in another application.

The [validation records](data/benchmarks/function-accuracy-20261107/README.md) document the tested builds and reference method. Other architectures and compiler versions should be validated for your application; Highway portability is not evidence that every target has been tested.

## Further information

- [CUDA API, table ownership, and model selection](include/fast_boys/README.md)
- [CPU SIMD API and gather policy](include/fast_boys/SIMD.md)
- [Numerical construction metadata](data/numerical/paired-1ulp/README.md)
- [QUICK integration and benchmarks](workflow/quick/README.md)
- [NWChem–Simint fixed-density benchmarks](workflow/NWCHEM_FIXED_DENSITY.md)

The construction and benchmarking workflows are optional research tools, not installation steps for library users.

## Citation

If you use FABO in your research, please cite the [FABO paper (arXiv:2611.32943)](https://arxiv.org/abs/2611.32943):

```bibtex
@misc{yan2026fastaccurateboysfunction,
  title         = {Fast and Accurate {Boys} Function Evaluation Using Nonuniform Gridded {Taylor} Expansions},
  author        = {Longxiang Yan and Wei Wu and Peifeng Su},
  year          = {2026},
  eprint        = {2611.32943},
  archivePrefix = {arXiv},
  primaryClass  = {physics.chem-ph},
  url           = {https://arxiv.org/abs/2611.32943},
}
```

## License

Original FABO material is dual-licensed under **MPL-2.0 OR LGPL-3.0-only**, at your choice. See [LICENSE](LICENSE) for scope and full license texts. Third-party components retain their own licenses.

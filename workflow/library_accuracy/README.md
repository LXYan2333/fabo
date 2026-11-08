# Standalone accuracy and reference storage

This opt-in workflow does not alter numerical selections, molecular benchmarks, or manuscript results. It targets RN64(i/1000000), i=0,...,1000000000, and requested ranges [0,N], N=0,...,12. A small configuration can scan a prefix for testing. Production scans must explicitly configure the complete adapter matrix; preparation does not infer missing implementations.

## Coverage

The CPU suite contains original Simint, FABO, LibintX, VSR, and Laikov. The CUDA suite contains original QUICK, FABO, LibintX, VSR, and GANSU. Each is built separately for N=0,...,12 under strict and fast-math flags. FABO uses a dedicated [0,N] allocation, never QUICK's family mapping. The CPU suite defaults to native gather; `software_gather: true` additionally builds the software policy. No application or molecular calculation is run.

The standalone adapters reuse the existing benchmark implementations. QUICK's original `gpu_fmt.h` and Simint's original `boys_F_split` are included directly. LibintX SIMD output is zero-initialized as required by its accumulation API. Original source files and generated coefficient tables are retained and hashed. The new wrappers only marshal input/output storage and initialize tables.

The native reference sources were recovered from branch `main`, files `workflow/reference/taylor_boys_reference_v2.cc` and `accuracy_reference_v3.h`. They contain no FABO numerical-model dependency. Reference intervals enclose rounding and Taylor remainder; implementation maxima describe sampled inputs only. The collector computes absolute, relative, and ULP-error intervals against unrounded references, with ULP spacing at the correctly rounded reference. It shares reference evaluations across all loaded adapters, retains sum/max bounds, and refines retained witnesses directly at 512-bit MPFR. It reports bounds rather than claiming an exact extremizing input when intervals overlap. Means are accumulated in binary128 with outward bounds and merged with directed 80-digit decimal arithmetic. Reports display upper bounds alongside machine-readable lower bounds; they do not claim exact error values.

## Build and prepare

Use GCC with MPFR/GMP/quadmath development headers and libraries:

```sh
python -m workflow.library_accuracy.build --output .work/accuracy/scan --cxx g++
.work/accuracy/scan --table .work/accuracy/reference.bin 12 24 0.25 1000 256 8
python -m workflow.library_accuracy.adapters --order 4 --output .work/accuracy/fabo4.cc
```

The reference-table command is an offline construction, not a scan; do not repeat it per shard. `build` accepts repeatable `--include` and `--lib` paths. Verify it with `scan --check-reference REFERENCE.bin`, which compares 1040 accelerated reference intervals against direct 512-bit MPFR. `adapters --cuda` emits a CUDA adapter; `--software` selects CPU software gather.

For the complete matrix, copy and edit `profiles/cpu.json` or `profiles/cuda.json`, then run:

```sh
python -m workflow.library_accuracy.suite --config BUILD.json --output BUILD_DIRECTORY
python -m workflow.library_accuracy prepare --config BUILD_DIRECTORY/scan-config.json --run RUN
```

The CPU build exports Highway revision `9ca61efcab7f54c244cc211e573324e6a29ffa17` and applies the same gather workaround as the NWChem comparison. Simint is exported at `38b24bb040c647e4acc0e040457180b574089c58` from a checkout of <https://github.com/simint-chem/simint-generator.git>. Existing verified exports can be supplied with `simint_snapshot`, pointing to a directory containing `skel/`. The VSR/Laikov ports are exported from this repository's retained `728ec72` revision. LibintX uses the pinned submodule, and GANSU uses the archived release under `third_party/gansu/upstream`. Keep these dependencies available when reproducing builds. `built.json` records compiler versions, commands, dependency hashes, and adapter identities. For Conda toolchains lacking a libmvec linker stub in their sysroot, set `libmvec` to the host's full library path.

CPU adapters use GCC, AVX-512, and `HWY_COMPILE_ONLY_STATIC`; the profiles use Sapphire Rapids. CUDA uses NVCC and `sm_120`. These are explicit profiles, not claims of other-target qualification. CUDA strict mode uses `--fmad=false`, while its fast mode uses `--use_fast_math`. CPU strict mode uses `-fno-fast-math -ffp-contract=off`; fast mode uses `-ffast-math -ffp-contract=fast`. Explicit FMAs remain fused. Adapter objects are linked without fast-math startup objects, and the collector forbids fast-math compilation.

An adapter exports `extern "C" void boys_accuracy(size_t count, const double* x, double* out)`. Output is order-major, `out[n*count+i]`, with precisely `(N+1)*count` values. All input lengths, including partial SIMD vectors and CUDA blocks, must be supported. Exceptions or CUDA failures invalidate the shard. The collector checks the host floating-point environment after every call. Fast-math flags apply only to adapter compilation, not the reference, collector, or executable startup.

Configuration contains `scanner`, `reference_table`, `total` (default 1000000001), `batch` (default 1024), `shard_size` (default 1000000), and `adapters`. Each adapter has a unique `id`, `path` to a shared library, `N`, `platform`, `backend`, and `mode` (`strict` or `fast`). Suite builds produce this configuration automatically. Shared libraries, coefficient files, build records, and the scanner/reference table are hashed; altered artifacts cannot resume an existing run. Absolute paths identify local installations; relocate a build tree by generating a new scan configuration and preparing a new run. CUDA comparator tables are resolved relative to their shared libraries, not an author's original workspace.

```sh
python -m workflow.library_accuracy prepare --config CONFIG.json --run RUN
python -m workflow.library_accuracy pilot --run RUN
python -m workflow.library_accuracy scan --run RUN --shard 0
python -m workflow.library_accuracy report --run RUN
python -m workflow.library_accuracy storage --run STORAGE_REPORT
python -m pytest workflow/library_accuracy/tests -q
```

The pilot samples up to 1031 inputs at each end and the midpoint of the configured grid and an additional globally permuted batch. This exercises partial SIMD vectors/CUDA blocks and mixed-domain lanes. Its output is separate from production shards. `layout: mixed` selects a bijective permutation of the entire grid for an optional separate full scan; do not merge its samples into adjacent-layout means. The collector checks output guards and immutable inputs. Only compact statistics and witnesses are saved: no dense reference/output cache is written. Nonfinite outputs invalidate corresponding mean/max summaries, while counts remain available. Pooled summaries weight all returned orders and inputs equally. Shard merge checks exact, nonoverlapping coverage and all configured adapter/order/metric combinations. A successful pilot is required before production scanning.

## Cluster execution

`python -m workflow.library_accuracy.cluster --run RUN --python PYTHON --partition PARTITION` prepares scripts without submitting. Add `--node NODE --gpu --workers 8` for CUDA and `--submit` only after validation. Each GPU allocation can run eight independent CPU scan workers sharing its device, avoiding a one-core reference bottleneck; GPU allocations themselves are serialized. CPU worker groups can run in parallel using `--concurrency`. An array and dependent report run without a laptop controller. Scratch uses `SLURM_TMPDIR` or `/tmp`; compact results return to the run directory. No GDS or timing wrapper is used. Small pilot timings estimate scan cost, not evaluator speed.

At first execution, the run atomically binds CPU model/features/microcode, kernel, resolved shared-library hashes, and (for CUDA) GPU model, compute capability, driver, and device selection. Later workers reject incompatible environments. Hostnames and allocation sizes are not numerical identities; otherwise compatible nodes can share a run. Use separate runs for different architectures or runtime libraries. The collector enforces RN-even, disabled FTZ/DAZ, and masked traps and checks these controls after every adapter call. Preloads and library-audit injection are rejected.

`python -m workflow.library_accuracy.pilot_job --config BUILD.json --output PILOT` builds the scanner, generates/checks the reference table, builds adapters, and runs only the bounded pilot inside an allocation. Add `reference_include` and `reference_lib` arrays to locate MPFR/GMP development files. It never submits the dense scan. The test suite is pytest; set `FABO_ACCURACY_SCANNER` and `FABO_ACCURACY_REFERENCE` to enable native enclosure and known-error tests.

Storage reports include all 25 FABO models, main and tail bytes, coefficients, correction bytes, and padding. The metadata are checked against generated constants and the 1 MiB per-model limit. No comparator storage or physical cache-residency claims are made. Reports write CSV/JSON, PDF, and a storage LaTeX table under the requested output directory, not into the manuscript.

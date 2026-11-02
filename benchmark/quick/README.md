# QUICK additive-grid variant

`fabo_additive` replaces only the two Boys call sites in QUICK's GPU two-electron energy helpers. It uses the bundled numerical selections, not the previous recurrence-patch/exp-dictionary implementation. `official` is the unchanged Boys control. The restored comparator source files remain available separately; this preparation command currently exposes these two variants only.

QUICK is pinned to revision `730af1533da8912ce5874852561e63b5907f9d7a`. Prepare independent disposable trees, leaving the submodule untouched:

```sh
git submodule update --init third_party/quick
python -m workflow.quick.prepare --variant official --probe --output .work/quick-official
python -m workflow.quick.prepare --variant fabo_additive --probe --output .work/quick-additive
```

Preparation performs no numerical search, build, benchmark, or cluster submission. The destination must not exist. `fabo-variant.json` records the upstream revision, selected numerical identities and copied/patched source checksums. Source and coefficient data are embedded in the prepared tree; binaries do not need runtime table files or paths to the author's workspace.

Build each tree using QUICK's CUDA build procedure, with matching compiler, architecture and arithmetic options. For example, on a machine with the supported CUDA toolkit and QUICK's documented build dependencies:

```sh
cmake -S .work/quick-additive -B .work/quick-additive-build \
  -DCUDA=ON -DMPI=OFF -DENABLEF=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build .work/quick-additive-build --parallel 1
```

Both prepared variants use C++17; existing CUDA optimization flags are preserved. CUDA toolkit support/architecture selection remains QUICK's responsibility. This patch targets CUDA, not HIP. `ENABLEF` is a build option, not a second binding generator option.

FABO runtime precondition assertions are opt-in (`FAST_BOYS_ENABLE_ASSERTS=1`) and disabled by default, even if QUICK does not define `NDEBUG`. No QUICK source/flag workaround is needed to remove these FABO checks from timing builds. This does not change QUICK's own assertion policy. Define the macro consistently for diagnostic builds; compile-time checks remain active in all builds.

SP uses the `[0,4]` table. Ordinary SPD uses `[0,8]`; with `ENABLEF`, SPD and SPDF share the same `[0,12]` allocation because the SPD-labelled helper can also request order 12. The shared compact large-argument table handles inputs above the main domain. Host table definitions live in a separate host translation unit; CUDA integral translation units see only lightweight model definitions and device pointers. Upload occurs on QUICK's selected device during device initialization, outside integral/Fock timing, with device-context-lifetime allocations.

Each lane passes its own runtime maximum order to the evaluator. Results go directly into `YVerticalTemp[n * (gridDim.x * blockDim.x)]` from the lane-specific pointer. There is no result copy, temporary coefficient array, warp reduction, shared-memory setup, function-pointer dispatch, or per-Boys-call initialization. Partial/divergent warps are allowed. Screening, contraction, integral accumulation, one-electron evaluation and gradient Boys paths are unchanged. Consequently this is an energy-path experiment, not a replacement of every Boys evaluator in QUICK.

Without `--probe`, the executable follows normal QUICK SCF control flow. The optional probe adds the retained fixed-density one-update harness: `FABO_QUICK_MODE=prepare` writes the hcore fixture at `FABO_FIXTURE`; `run` loads it and reports Fock/iteration times; `check` writes numerical outputs without timing. Use the official variant to prepare the fixture, then share it across variants for the same input and build configuration. `FABO_WARMUP` controls warmup (default 1, forced to 0 in check mode). With no mode environment variable, even a probe-enabled binary runs normal QUICK SCF. No timing or accuracy results are implied by source preparation or compilation.

```sh
python -m pytest workflow/quick/tests -q
# On an allocated SM120 GPU (adjust -arch for the device):
nvcc -std=c++17 -O3 -arch=sm_120 --fmad=false -Iinclude -Ibenchmark/quick \
  benchmark/quick/additive_conformance.cu benchmark/quick/additive_host.cc -o binding-spd
./binding-spd
# Repeat the same compile/run with -DENABLEF and a different output name.
```

Tests check both ENABLEF mappings, heterogeneous runtime endpoints, strided outputs/sentinels, host conformance against the direct evaluator, fail-closed source contexts, and preparation provenance. GPU runtime validation is a separate check; host tests alone do not certify CUDA integration.

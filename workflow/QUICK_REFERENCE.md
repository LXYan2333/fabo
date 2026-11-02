# Correctly-rounded Boys reference in QUICK

## Availability in this branch

The standalone reference-data helper and CUDA reference sources are retained, but the historical molecular `reference-check` orchestration is not implemented in this branch. In particular, `quick_gpu_agent.py`, `quick_gpu.smk`, the reference profiles, and the old unittest suite are not present. The method and completed-run descriptions below document that archived workflow, not a currently runnable reference backend.

The supported QUICK preparation entry point is `python -m workflow.quick.prepare`, with variants `official` and `fabo_additive`; see `benchmark/quick/README.md`. Preparation does not build, benchmark, or run a molecular reference comparison. Current regression tests use pytest:

```sh
.venv/bin/python -m pytest workflow/quick/tests -q
```

The standalone helper uses the current `workflow.additive.reference` directed-MPFR implementation. From the repository root its supported commands are:

```sh
.venv/bin/python -m workflow.scripts.quick_reference_data --help
.venv/bin/python -m workflow.scripts.quick_reference_data generate OUTPUT.bin
.venv/bin/python -m workflow.scripts.quick_reference_data fixtures FIXTURES.bin
.venv/bin/python -m workflow.scripts.quick_reference_data resolve OVERRIDES.bin --requests REQUESTS.bin
```

The output parent directory must exist. `generate` constructs the binary128 table, `fixtures` constructs standalone exact-rounded test values, and `resolve` consumes binary `(x_bits, order)` requests and writes binary `(x_bits, order, result_bits)` overrides. These utilities do not launch QUICK or provide the missing replay controller. The remaining sections preserve the archived reference design; its orchestration sources and profiles can be inspected at commit `c3c578806a02dc7e00cf076a0be83a3ba25aa6d4` (branch `fresh-start`). Reusing that orchestration requires its matching source tree, dependencies and environment; its historical run identities are not validations of the current FABO binding.

This is an untimed diagnostic, not an additional performance backend. It replaces the same two GPU two-electron Boys call sites as the other substitutions. Official one-electron integrals, screening preparation, integral recurrence, accumulation, diagonalization and energy arithmetic remain unchanged. Consequently the resulting molecular matrices are a reference for the Boys substitution, not correctly-rounded molecular observables.

## Numerical contract

`benchmark/quick/reference_boys.h` accepts orders 0–12 and every nonnegative binary64 argument, including subnormals and positive infinity. Negative finite values, negative infinity and NaNs invalidate the update; negative zero is treated as zero. No finite-domain asymptotic shortcut is assumed exact. A result is accepted only when the endpoints of its error interval round to the same binary64 number, including gradual underflow. An unresolved interval invokes adaptive directed MPFR through the replay mechanism below; exceeding resource limits fails the calculation rather than accepting an uncertain value.

CUDA 13.4's device binary128 API requires compute capability at least 10.0 and a compatible host compiler; the configured RTX 5090 D is supported. We use explicit `__nv_fp128_add/sub/mul/div/fma/sqrt` operations, not binary64 intermediates or a claim that extra precision alone implies correct rounding. NVIDIA documents round-to-nearest arithmetic and correctly-rounded quad square root: [quad math API](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__QUAD.html) and [floating-point accuracy](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/mathematical-functions.html). Standalone conformance is compiled both strictly and with QUICK's actual `--use_fast_math` CUDA flags.

For `0 <= x <= 128`, 513 quarter-spaced nodes store correctly-rounded binary128 values of orders 0–36. MPFR directed intervals at 256 bits must agree on each serialized binary128 value. The degree-24 factorial-Horner Taylor expansion evaluates each requested order independently. The index is selected using explicit binary64 operations, but displacement is subtracted in binary128: index rounding near `x=1/8` can otherwise invalidate exact-subtraction reasoning. The maximum displacement is less than 0.126. Values are stored as exact little-endian IEEE binary128 encodings, without decimal or binary64 intermediates. The table, reciprocals and square-root constant together occupy 304112 bytes.

Let `u=2^-113`, `r<0.126`, and `A=F_n(x_i)`. Since `F_(n+k)(x_i) <= A`, the absolute coefficient sum is at most `A*exp(r)`. Taylor's integral remainder is at most `A*exp(r)*r^25/25! < A*2^-158`. Stored-value/reciprocal rounding and the 24 multiplies plus 24 FMAs are bounded conservatively by `gamma_100*exp(r)*A`, where `gamma_100=100u/(1-100u)`. Allowing the first cell, intermediate subnormal displacement products and endpoint rounding, this is still much smaller than the implemented radius `RN128(A)*2^-88`. Intermediate Taylor states remain positive and normal; underflow of tiny displacement products contributes far less than this radius. The loose radius deliberately trades a few more MPFR fallbacks for a simple safety margin.

For `x>128`, the complete Gaussian integral starts from `sqrt(pi)/(2*sqrt(x))` and uses binary128 recurrence to the requested order. For `n<=12`, the omitted integral from 1 to infinity is bounded by `exp(-x)/(2*(x-max(n-1/2,0))) < exp(-x)`. We bound it without a transcendental evaluation by `2^-floor(23*x/16)` up to 8192, and by `2^-8192` thereafter; `23/16 < log2(e)`. The interval radius is this tail bound plus the computed complete integral times `2^-88`, comfortably exceeding arithmetic and constant-rounding errors. Binary128 covers the intermediate complete-integral range through order 12 even at the largest finite binary64 argument. Lower endpoints are clipped to zero before binary64 conversion.

## Ambiguous rounding and replay

An ambiguous `(x bits, order)` is checked against an exact MPFR override table. Otherwise the GPU queues it and produces only a provisional value. At the synchronization following Fock construction, any unresolved request terminates the process with status 86 **before diagonalization or output acceptance**. The driver deduplicates requests, computes directed MPFR intervals with increasing precision (256 through 8192 bits), and accepts a binary64 value only when both endpoints round identically. It restarts the update from the same archived `P0`. These discarded attempts are recorded, not counted as timing repetitions or valid reference updates. Queue overflow, invalid inputs, an unresolved MPFR result, or exhausted replay budget is a hard failure. No inaccurate fallback is accepted.

The device reference routine is out of line to avoid replicating binary128 arithmetic throughout QUICK's already large integral kernel. Its table and optional overrides are uploaded once before the update. There are no host callbacks inside a GPU kernel. The base conda environment is not modified: the profile names a separate Python environment containing `gmpy2==2.3.1` for construction and fallback.

## Archived workflow and reports

The `reference-check` stage verifies the pinned completed performance manifest, exact fixture bytes, environment and external runtime libraries. It builds official QUICK, the current LibintX substitution and the binary128 reference in separate binaries. For each archived molecular/basis case it runs one accepted untimed update per backend with zero warmup, using the same `P0`; opaque-zero and Horner surrogates are excluded. The water-dimer/STO-3G case runs first as a smoke test. Existing performance results are neither modified nor replaced.

```sh
git show c3c578806a02dc7e00cf076a0be83a3ba25aa6d4:workflow/scripts/quick_gpu_agent.py
git show c3c578806a02dc7e00cf076a0be83a3ba25aa6d4:workflow/profiles/slater2-quick-reference.json
```

In the archived tree, the same stage was available through `workflow/quick_gpu.smk` with `profile` and `stage=reference-check`, with host paths configured in the profile. `reference-summary.json` and `REFERENCE.md` report signed energy differences (hartree), maximum absolute and Frobenius Fock/density differences, fixture/output hashes and the reference identity. The energy remains `E_nuc + 0.5*sum(P0*(Hcore+F[P0]))`; density differences concern the single updated density, not SCF convergence. GPU atomic accumulation may itself vary between runs and is not made correctly rounded by replacing Boys values.

Standalone MPFR fixtures cover every node and nearest-cell boundary with neighboring binary64 arguments, every requested order, mixed inputs, random arguments, normal/subnormal inputs, positive infinity and extreme finite arguments. Table generation and conformance records are separate from the molecular outputs. Passing these sampled tests supplements, but does not replace, the per-call interval acceptance rule. Completion manifests hash accepted matrices and the exact table, fallback and build records; a partial run is not reported complete.

A separate host-bridge conformance test compiles the actual initialization and synchronization hooks with QUICK/LibXC's `min`/`max` macros present. It verifies normal initialization, unresolved-request serialization and exit status 86, plus hard failures for queue overflow and invalid arguments, before compiling the full QUICK executable. The reference header temporarily hides those macros only while including standard-library headers and restores them afterward; QUICK's own macro definitions and integral code are unchanged.

## Archived repeated untimed comparisons

`slater2-quick-reference-repeats.json` requests ten fresh-process updates for each of the three numerical backends on all twenty archived cases (600 accepted updates). It pins reference run `5450c8d0d565971f` by completion-manifest and source-archive hashes. The stage verifies its extracted numerical sources, build options, binaries, tables, basis files, GPU/toolchain and resolved runtime dependencies before reusing anything. It does not rebuild or modify that run. `reference_probe.repetitions` defaults to one; repeated runs require the explicit `reuse_reference` object. A changed environment or artifact is an error, not an implicit replacement.

One exclusive pc008 allocation runs the molecular processes serially, rotating backend order each round. Every process reads exactly the same archived P0 fixture for its case and performs one accepted update, with no warmup, timing samples or profiler. Water/STO-3G completes all repetitions and statistics first as a smoke test. Each repetition starts with a private copy of its case's previously certified MPFR overrides. Additional ambiguous calls trigger the same fail-closed MPFR replay; discarded attempts do not count as repetitions. Per-attempt records include the override hash used by that process, while accepted records identify the resulting table and fixture. Complete repetitions are hash-verified on resume; incomplete attempts are retained, and a fresh process restarts from P0 rather than continuing a partial molecular state. The fallback budget applies to each invocation of an unfinished repetition.

Initial override copies and MPFR updates use same-directory temporary files, flushed before atomic replacement. An interrupted copy or resolver leaves the previous complete table unchanged (or no published table during initialization). Leftover temporary files are not used on resume. This orchestration safeguard does not change the reference arithmetic or archived results.

The postprocessor uses 256-bit MPFR arithmetic on exact binary64 matrix and energy observations. It reports energy mean, sample standard deviation and range, elementwise Fock/updated-density mean and sample standard deviation, maximum absolute and Frobenius differences of backend and reference means, and matrix variability. Frobenius dispersion is `sqrt(sum(elementwise sample variances))`; the maximum mean-difference witness includes row/column indices and both local sample standard deviations. Energy differences include the descriptive combined standard error `sqrt((s_backend^2+s_reference^2)/R)`, assuming independent samples; this is not an accuracy or significance gate. Sample standard deviations use denominator `R-1` (undefined for R=1). Comparisons are computed before serialization of aggregate arrays to binary128. Actual updated density matrices are averaged, not orbitals or densities reconstructed from the average Fock matrix; these means never become new initial densities.

The resulting mean reference-backend matrices are not exact molecular observables. Repetition characterizes accumulation variability and reduces sampling variability of a mean, but does not remove systematic bias or certify the rest of QUICK's binary64 computation. Previously completed single updates and performance repetitions are not included in this dataset.

```sh
git show c3c578806a02dc7e00cf076a0be83a3ba25aa6d4:workflow/profiles/slater2-quick-reference-repeats.json
```

The archived agent supported resuming an interrupted immutable run. `reference-repeats/CASE/round-RR/BACKEND/` contains accepted-result and completion records plus all attempt directories. `statistics/` within each case stores little-endian binary128 mean and sample-SD arrays, each containing Fock followed by updated density in Fortran column-major order, and `summary.json` with scalar statistics and witnesses. Raw matrices and aggregate arrays stay on the cluster (approximately 0.72 GB and 0.29 GB respectively for this twenty-case, ten-repetition workload); only compact records are fetched. Undefined R=1 SD array entries are quiet NaNs.

On the cluster, regenerate statistics/reports without launching QUICK using the reference Python environment and the archived script. Replace `RUN` with the directory printed in the submission receipt:

```sh
/export/home/lxyan2/fast-boys-fresh/reference-env/bin/python RUN/bundle/workflow/scripts/quick_reference_statistics.py RUN/results
```

The postprocessor reuses verified complete statistics; `--report-only` regenerates only the combined JSON/CSV and `REFERENCE-REPEATS.md`. The run's source-archive and completion manifest, raw outputs and aggregate hashes identify exactly which binaries, observations and statistics were used. Preserve the pinned upstream run when moving or backing up the repeated-run directory: its binaries and reference tables are referenced, not duplicated.

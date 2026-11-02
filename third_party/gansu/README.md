# GANSU Boys backend for QUICK

The upstream subset in `upstream/` is copied unchanged from the latest stable release found on 2026-10-29: [GANSU v2026.8.10](https://github.com/Yasuaki-Ito/GANSU/releases/tag/v2026.8.10), commit `0b000a6cbcc5f5a630940ac1c2ba7f7ac2b8f132`. File hashes, repository and paper identities are in `provenance.json`; the BSD-3-Clause license is retained. A full checkout of that tag provides the remaining application and build sources; no GANSU application build is required here.

Reference: Y. Ito, S. Tsuji, K. Nakano and A. Kasagi, *GANSU: A GPU-Native Quantum Chemistry Framework for Efficient Hartree–Fock and Post-HF Calculations*, Eng **7**, 205 (2026), DOI [10.3390/eng7050205](https://doi.org/10.3390/eng7050205), Section 5.2. The comparison uses the released incremental device evaluator, not the paper's standalone sorted bulk workload or GANSU's complete integral engine.

## Released algorithm and table

The pinned code returns `F0..Fn`. At zero it evaluates `1/(2j+1)`; below `A_TR*n+B_TR` it uses degree-5 gridded Taylor interpolation; otherwise it computes F0 using sqrt, adds erf and exp when `x < A_RS*n+B_RS`, and applies the published upward recurrence. The explicit round-to-nearest reciprocal, sqrt and FMA intrinsics are retained. The Maclaurin alternative is commented out upstream and is not enabled by this adapter. Parameters and table values are not refitted or retuned.

The released table has 30,720 binary64 values (245,760 bytes = 240 KiB), 1,024 nodes per stored order, spacing 1/32, and stored orders 0..29. This differs from the article's description of a 65.5 KB table with spacing 1/8. We follow the pinned implementation. The complete upstream table, including unused entries for QUICK's orders 0..12, is preserved with its original order-major layout and decimal literals. `gansu_table.cc` serializes those literals with the configured C++ compiler; it does not recompute their mathematical values. The binary is native-endian for the same build/runtime target.

## Binding and execution

`benchmark/quick/gansu_adapter.py` mechanically generates `gansu_boys.h`: it namespaces the parameters, changes output stores to `boys[j*stride]`, and threads that stride through the incremental helpers. Arithmetic, iteration limits, branch predicates and table indexing are otherwise unchanged. QUICK passes its actual per-thread maximum `I+J+K+L` and lane-offset output pointer, with stride `gridDim.x*blockDim.x`. Mixed orders, mixed branches and partially active warps require no collective operation. No temporary result sequence, copy-back, coefficient copying, per-call transfer or indirect function dispatch is introduced.

The full table is copied once to GPU global memory before timed work, using `FABO_GANSU_TABLE`; the allocation has process lifetime. The same QUICK kernels, flags, screening, fixed trajectories and measurement schedule apply to the other backends. QUICK's normal `--use_fast_math` compilation remains enabled. Strict adapter checks use `--fmad=false` to compare directly against the unmodified upstream header; explicitly requested upstream FMAs remain fused. A separate fast-math check records differences under the timing flags. These checks establish adapter conformance, not a dense accuracy certificate for the timing executable.

## Reproduction

```sh
.venv/bin/python benchmark/quick/gansu_adapter.py --check
.venv/bin/python -m pytest -q workflow/tests/test_quick_gansu.py
```

Add `"gansu"` to `scf_comparison.backends` in a frozen-comparison profile, for example `["official", "fabo", "libintx_gpu", "vsr", "gansu", "half"]`. The existing `scf-compare` stage verifies provenance, imports the original table and runs CUDA conformance before compiling/timing QUICK. It neither repeats FABO tuning nor changes previous result identities. The check can also run alone:

```sh
.venv/bin/python workflow/scripts/quick_gpu_agent.py run --config <profile.json> --geometry benchmark/quick/fixtures/uracil-dimer.xyz --stage gansu-check --local .work/quick-gansu-check
```

The standalone stage requires `gansu` in `scf_comparison.backends` and the usual site/toolchain/target settings; it performs no molecular timing. Results include upstream provenance, table and executable hashes, compiler commands, strict/fast conformance records and a content-addressed completion manifest. Host regression tests compare every order 0..12 against the original implementation at grid ties and branch boundaries, check guarded strided stores and sample independent MPFR references. CUDA checks add mixed requests and partial warps. Full QUICK integration and molecular performance must be reported only after their corresponding runs complete.

Initial checks: the host MPFR sample's maximum absolute error was `7.336070019758311e-15`. Slater2 job `2119879`, bundle `fdcc2a3ea7c98727`, ran on pc003 (RTX 4080, sm_89), NVCC 13.4.92. For 4,099 CUDA inputs and each requested order 0..12, strict and fast builds both matched the upstream evaluator bitwise; output guards, mixed requests, partial warps and the exact QUICK initialization/call hook passed. The table SHA-256 was `40395e5297e04f285e3432b8dd4efb83dfebfc829b8f122442b745749227761d`. Records are under `.work/quick-gansu-check-20261029/fdcc2a3ea7c98727/results/` and the matching remote `quick-gansu-check/fdcc2a3ea7c98727/results/`. These checks did not compile the complete QUICK application or measure molecular performance.

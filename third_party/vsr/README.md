# Supplied Vikhamar-Sandberg–Repisky evaluator

The source of `coefficients.txt` and `benchmark.zip` is the authors' [JCP supplementary-material collection, DOI 10.60893/figshare.jcp.c.8390929](https://doi.org/10.60893/figshare.jcp.c.8390929). The user provided local copies and identified this source. Small relevant archive members and the coefficient file are preserved verbatim in `supplied/`; SHA-256 identities are in `provenance.json`. The complete original ZIP is retained locally at `.work/third-party-vsr/benchmark.zip` (ignored). Its unrelated 286 MB Ishida table is not extracted or added to Git. The retained Makefile documents the authors' `nvc -O3 -fast -acc` build, but is not the QUICK build recipe.

Reference: R. Vikhamar-Sandberg and M. Repisky, *Efficient Boys function evaluation using minimax approximation*, J. Chem. Phys. **164**, 154111 (2026), DOI 10.1063/5.0316073. The publisher lists the [benchmark source](https://doi.org/10.60893/figshare.jcp.31890538.v1) and [minimax coefficients](https://doi.org/10.60893/figshare.jcp.31890535.v1) by Rasmus Vikhamar-Sandberg and Michal Repisky under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The retained upstream files are unmodified; the CUDA sequence adapter, CPU Highway port, coefficient formatting, and F0 heading correction are FABO adaptations. The original supplemental material is not relicensed under FABO's MPL/LGPL choice.

## Documented transcription correction

In `coefficients.txt`, `4.59649054199579770E+11` appears as the last F0 numerator entry. Table II of the paper puts it at the beginning of the denominator. Without this correction, the supplied ratio at zero is approximately 2.04 instead of 1. The importer checks this exact layout and moves only this entry in memory. The supplied file remains unchanged; other decimal values are retained as supplied. The middle-region F0 coefficients and both boundaries come directly from `minimax.c` and `constants.h`. The importer cross-checks all lower-region F12 coefficients against `minimax.c`.

## QUICK CUDA port

`benchmark/quick/vsr_boys.h` is our CUDA sequence adapter, not an author-supplied CUDA kernel. It preserves Algorithm 1: rational F_N seed and downward recurrence below 11.899848152108484; the supplied rational F0 seed and exponential-aware upward recurrence below 28.989337738820740; then the supplied sqrt/div asymptotic recurrence. These global boundaries are not retuned for QUICK's lower requested orders. The supplied demonstration fixes N=12; the port selects the supplied coefficient set for QUICK's actual runtime maximum N in 0..12, including the ENABLEF path. It neither starts unnecessarily from F12 nor computes unused output orders.

Numerator and denominator use ordinary Horner evaluation and direct division. A seed switch selects constant-coefficient expressions; a shared fallthrough downward sequence exposes constant divisors without duplicating the ERI kernels. Upward recurrence follows the supplied formula. Normal compiler FMA contraction is allowed under QUICK's common build flags. There is no independently introduced approximate reciprocal, cutoff change, table refit, or arithmetic-DAG tuning. Exponential evaluation is omitted when unused (N=0 and the asymptotic branch). The adapter accepts QUICK's finite nonnegative active inputs without adding a clamp.

Each result goes directly to QUICK's strided `YVerticalTemp`, with no sequence temporary, copy-back loop, coefficient copying, global function pointer, or host/device transfer per call. All coefficients are compiler constants. `vsr_adapter.py` modifies only a disposable build tree, leaving the original QUICK and previously archived bindings intact. Compiler-generated register pressure, switch lowering and instruction scheduling are not claimed to be optimal. This is a straightforward CUDA port of the algorithm; timings must not be labelled as the authors' original OpenACC executable.

Regenerate/check the header with:

```sh
.venv/bin/python benchmark/quick/vsr_generate.py
.venv/bin/python benchmark/quick/vsr_generate.py --check
.venv/bin/python -m pytest -q workflow/tests/test_quick_vsr.py
```

The host regression compares all 13 outputs at N=12 bitwise against the supplied C benchmark under noncontracting arithmetic, checks requested-order/strided-write bounds, and compares sampled results for N=0..12 against 256-bit MPFR values. These samples are not a continuous error certificate and do not establish a one-ULP guarantee. CUDA conformance checks partial blocks, mixed orders and regions, output guards, and the unchanged supplied order-12 arithmetic. Strict compilation requires bitwise agreement with that supplied arithmetic; fast-math differences are reported separately rather than treated as a numerical-accuracy certificate.

To include VSR in a frozen-winner comparison, add `"vsr"` to `scf_comparison.backends`, e.g. `["official", "fabo", "libintx_gpu", "vsr", "half"]`. The existing `scf-compare` workflow bundles the supplied files, verifies generated constants, and runs strict/fast CUDA adapter checks before building or timing QUICK. No new FABO search is required. Original comparison records remain independent and immutable.

The adapter checks can also be submitted alone with `quick_gpu_agent.py submit --config <profile.json> --geometry benchmark/quick/fixtures/uracil-dimer.xyz --stage vsr-check`. The profile must include `vsr` in `scf_comparison.backends` and the usual target/site settings. This stage does not build the complete QUICK executable or run molecular timings.

Initial validation: host noncontracting arithmetic sampled 18 arguments (including both boundaries and their binary64 neighbors), every requested N=0..12, and all requested outputs; the maximum sampled absolute error against MPFR was 4.3670622673630535e-14. Slater2 job 2119867, bundle `d57f101a55903108`, tested 2053 CUDA inputs on pc003 (RTX 4080, sm_89), using NVCC 13.4.92. Strict N=12 output matched the supplied arithmetic bitwise. Fast math had 119 differing outputs, maximum difference 4 ULPs and maximum absolute difference 1.1102230246251565e-16; mixed-order, finite-output and guard checks passed in both modes. These are adapter/regression checks, not a dense CUDA accuracy scan or a complete QUICK build/performance result. Records reside under `.work/quick-vsr-check-20261029/d57f101a55903108/` and the matching remote `quick-vsr-check/d57f101a55903108/results/` directory.

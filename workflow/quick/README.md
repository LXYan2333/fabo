# QUICK calibration and fixed-length backend comparison

This restores the official-QUICK iteration probe from `fresh-start` commit `c3c578806a02dc7e00cf076a0be83a3ba25aa6d4`, without its old numerical search or hardware-tuning framework. It determines the SCF trajectory length for later benchmarks; it does not benchmark alternate Boys implementations or choose a winner.

## Protocol

The default profile runs all 66 equilibrium S66 dimers (`1.00`) with `6-31G*` and `def2-SVP`: 132 cases, serially on one exclusively allocated GPU. XYZ coordinate strings are copied unchanged and interpreted in angstrom. Inventory validation requires all 528 original S66x8 dimers; only selected separations are copied. No molecules are synthesized, and every selected case must converge before the iteration plan is ready.

The calculation uses pinned QUICK 26.03, original GPU Boys, neutral closed-shell RHF, official SAD initial guess and normal restricted DIIS/screening. Defaults are `SCF=200` and `DENSERMS=1e-6`. Both original density tests (`PRMS < pmaxrms` and `PCHANGE < 100*pmaxrms`), QUICK's minimum-cycle rule and iteration-limit handling remain intact. The recorded count is the number of completed DIIS/Fock iterations. There is no molecular warmup, repetition or forced zero convergence threshold, and this is not the former fixed-hcore single-iteration probe.

The instrumentation saves the initial SAD matrices, orbitals, one-electron data and screening state to `initial.bin`. It records each iteration's Fock-build/complete-iteration wall time with GPU synchronization, energy and density-change diagnostics. The Fock timer encloses QUICK's `scf_operator(deltaO)`, not just Boys evaluation. `scf_seconds` measures the DIIS loop; `process_seconds` includes setup, SAD and teardown. The harness stops after the loop, before subsequent final-result processing. These are calibration observations, not convergence-time claims for an unmodified end-to-end executable.

The `--scf-training` patch also supports replay with `FABO_SCF_TRAINING=fixed`, `FABO_SCF_STATE=...`, and `FABO_SCF_STEPS=K`. It restores the archived state, skips a second SAD solve, retains DIIS/screening and stops after exactly K iterations. It writes `replayed-initial.bin` for the comparison controller to verify byte-for-byte. Calibration never uses fixed mode. Additional separations need their own official calibration; equilibrium counts are not automatically reused for other geometries. Backend comparison is described below; this workflow does not tune numerical parameters.

## Prepare and submit explicitly

Adjust `workflow/quick/profiles/s66-rtx5090d.json` for the node, compiler/toolkit paths and limits. Defaults: Slater2 pc008, one GPU, 16 CPUs, 96 GiB, exclusive eight-hour allocation, and QUICK `blackwell2` (SM120). `enable_f=false`; `def2-TZVP` requires `enable_f=true`. Bases and separation labels are explicit choices, never automatically reduced to meet a runtime target. Compilation retains QUICK CUDA arithmetic flags, uses internal BLAS/LAPACK, and disables profiling. Configure commands, cache, available compile commands and installed-file hashes are retained.

```sh
.venv/bin/python -m workflow.quick.calibrate prepare \
  --config workflow/quick/profiles/s66-rtx5090d.json \
  --dataset /home/lxyan/Code/cpp/simd_eri/benchmark/s66x8 \
  --output .work/quick-s66-calibration
```

Preparation exports a clean pinned QUICK tree, adds common build flags and SCF instrumentation, freezes input hashes and writes `run.sbatch`. It performs no compilation or molecular calculation. The bundled controller needs only Python's standard library. Transfer to a **new** run directory and submit from there:

```sh
ssh Slater2 'mkdir -p /export/home/lxyan2/fast-boys-additive/quick-s66-calibration'
rsync -a .work/quick-s66-calibration/ Slater2:/export/home/lxyan2/fast-boys-additive/quick-s66-calibration/
ssh Slater2 'cd /export/home/lxyan2/fast-boys-additive/quick-s66-calibration && sbatch run.sbatch'
```

Do not rsync over a running/completed run. Slurm continues independently of the laptop. Builds, compiler temporary files and molecular scratch use `$SLURM_TMPDIR`, then `$TMPDIR`, then `/tmp`. Only the `quick.cuda` target is built; the GPU executable, shared libraries and basis data are exported to `install/`, avoiding unrelated CPU executables that do not link the GPU timer hooks. These artifacts and completed cases are published to shared storage. Failed cases retain logs but receive no completion marker. Interrupted exports are preserved as `install-incomplete-*`. There is a ten-second post-build wait and no timing-acceptance gate; iteration count is the primary output.

Resume by resubmitting `run.sbatch`. Verified builds and completed cases are reused; changes to frozen inputs, installed files, linked libraries, GPU/node or completed artifacts are rejected. Nonconverged cases remain explicit and prevent a ready iteration plan; use a new run/configuration to investigate them. Never treat partial calibration as the complete workload.

## Results and tests

- `CALIBRATION.md`: per-case iterations, convergence and timings.
- `calibration.json`: full records, basis identities and initial-state hashes.
- `iteration-plan.json`: converged-case counts, nonconverged cases and `ready` flag.
- `calibration/CASE/`: input/output, logs, `initial.bin`, per-iteration CSV and checksum-verified completion.
- `run.json`, `build.json`, `environment.json`, `complete-scf-calibrate.json`: input/build/runtime/completion provenance.

```sh
.venv/bin/python -m pytest workflow/quick/tests -q
```

Tests cover geometry coverage, checked patching, result parsing, resume rejection after changes, bundle independence, and compiled Fortran state round trips/fixed counts. An actual QUICK GPU build and molecular smoke test remain separate checks. The binary128 molecular-reference workflow in `workflow/QUICK_REFERENCE.md` remains archival and is distinct from this official iteration calibration.

## Compare five Boys implementations

`workflow.quick.compare` compares original QUICK, the current additive-grid FABO evaluator, LibintX's GPU sequence evaluator, our CUDA port of Vikhamar-Sandberg–Repisky, and GANSU. It uses separate executables with direct, strided device calls, not a global function pointer or temporary output sequence. LibintX and GANSU tables are generated from their pinned sources, hashed and uploaded once during QUICK initialization. VSR uses the supplied coefficients and the documented F0 transcription correction; see `third_party/vsr/README.md` for provenance and the unresolved redistribution-license status. No synthetic zero/half backend or previous FABO implementation is restored here.

The supplied profile reuses corrected official calibration `6d3038d19552d85c`, pinned by completion SHA-256. Import verifies the QUICK revision, exact SCF hook sources/state format, configuration, geometry identity, explicit `BASIS=` input, actual basis hashes, converged counts, and initial-state bytes. The earlier archives lacking `BASIS=` are incompatible and rejected. Historical calibration timings are never substituted for new comparator timings. Imported files remain independently usable if the upstream run is subsequently moved; preserve their provenance marker. The archive path in the profile is site-specific and should be adjusted when relocating the archive, keeping its checksum unchanged.

Each fresh process replays the same saved official SAD initial state for that case, then runs exactly the official converged iteration count, retaining normal DIIS, density updates and screening. This is a fixed-length SCF trajectory, not repeated fixed-density Fock updates or a convergence-speed comparison. The default is five repetitions, no molecular warmup. Cases run serially; backend order rotates by round and case. The Fock metric is accumulated `scf_operator` wall time over the trajectory. Reports also give SCF-loop and whole-process time, median, MAD/median and CV, retaining every repetition. Geometric-mean ratios weight cases equally and use `T_method/T_official`; values below one are faster. Final energy differences are observed diagnostics against official QUICK, not an exact molecular reference or numerical acceptance gate.

Strict (`--fmad=false`) and fast-math CUDA adapter checks precede all molecular runs. FABO is checked against the same host evaluator, including mixed per-thread orders and partially active blocks; this is a binding-conformance check, not a new dense one-ULP scan. Comparator checks use their original source arithmetic. Full QUICK builds retain the upstream CUDA optimization flags for every backend. Standalone conformance executables and full QUICK executables are different artifacts; passing the former is not a claim of dense accuracy certification for the latter.

```sh
.venv/bin/python -m workflow.quick.compare prepare \
  --config workflow/quick/profiles/compare-rtx5090d.json \
  --dataset /home/lxyan/Code/cpp/simd_eri/benchmark/s66x8 \
  --output .work/quick-comparison-smoke --smoke
```

`--smoke` explicitly selects the equilibrium water dimer for each configured basis, with one repetition, and labels results as smoke evidence. Omit it and use a new output directory to prepare the full 132-case, five-repetition comparison. Preparation does not submit jobs. `--eigen` selects host Eigen headers for LibintX's author coefficient generator; the headers are copied into the frozen bundle. No numerical search is run. Transfer the bundle to a new remote directory, import calibration on the login node, and submit:

```sh
ssh Slater2 'mkdir -p /export/home/lxyan2/fast-boys-additive/quick-comparison-smoke'
rsync -az .work/quick-comparison-smoke/ Slater2:/export/home/lxyan2/fast-boys-additive/quick-comparison-smoke/
ssh Slater2 'cd /export/home/lxyan2/fast-boys-additive/quick-comparison-smoke/bundle && python3 -m workflow.quick.compare import --run ..'
ssh Slater2 'cd /export/home/lxyan2/fast-boys-additive/quick-comparison-smoke && sbatch run.sbatch'
```

One serial build per variant runs concurrently with the others, up to `build_workers` and the CPU allocation. All compilation and molecular scratch use node-local temporary storage. Timing starts only after all builds finish. No build is run concurrently with molecular timing. Slurm owns the controller, so laptop disconnection does not interrupt it. Resume by resubmitting the same bundle; changed inputs, build dependencies, GPU/node/toolkit, states and accepted samples are rejected. Review `environment.json`, `variants/*/build.json`, compiler logs and `conformance/results.json`. Completion requires every configured case/backend/round; missing cases are not silently dropped.

Results are `samples.json`, `summary.json`, `COMPARISON.md` and per-sample CSV/log records under `samples/`. The replayed initial state is verified on node-local storage and only its checksum is saved per sample; the identical initial matrices are archived once per case under `calibration/`, avoiding a large duplicate for every backend/repetition. `complete-compare.json` binds the results to the frozen inputs and builds. Regenerate a plot from completed saved results (Matplotlib required only for plotting):

```sh
.venv/bin/python -m workflow.quick.compare plot --run .work/quick-comparison-smoke
```

This writes `comparison.pdf`; it does not rerun timings. Keep calibration import, CUDA adapter validation, molecular smoke, and full comparison completion distinct when reporting readiness.

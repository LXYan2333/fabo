# QUICK S66 iteration calibration

This restores the official-QUICK iteration probe from `fresh-start` commit `c3c578806a02dc7e00cf076a0be83a3ba25aa6d4`, without its old numerical search or hardware-tuning framework. It determines the SCF trajectory length for later benchmarks; it does not benchmark alternate Boys implementations or choose a winner.

## Protocol

The default profile runs all 66 equilibrium S66 dimers (`1.00`) with `6-31G*` and `def2-SVP`: 132 cases, serially on one exclusively allocated GPU. XYZ coordinate strings are copied unchanged and interpreted in angstrom. Inventory validation requires all 528 original S66x8 dimers; only selected separations are copied. No molecules are synthesized, and every selected case must converge before the iteration plan is ready.

The calculation uses pinned QUICK 26.03, original GPU Boys, neutral closed-shell RHF, official SAD initial guess and normal restricted DIIS/screening. Defaults are `SCF=200` and `DENSERMS=1e-6`. Both original density tests (`PRMS < pmaxrms` and `PCHANGE < 100*pmaxrms`), QUICK's minimum-cycle rule and iteration-limit handling remain intact. The recorded count is the number of completed DIIS/Fock iterations. There is no molecular warmup, repetition or forced zero convergence threshold, and this is not the former fixed-hcore single-iteration probe.

The instrumentation saves the initial SAD matrices, orbitals, one-electron data and screening state to `initial.bin`. It records each iteration's Fock-build/complete-iteration wall time with GPU synchronization, energy and density-change diagnostics. The Fock timer encloses QUICK's `scf_operator(deltaO)`, not just Boys evaluation. `scf_seconds` measures the DIIS loop; `process_seconds` includes setup, SAD and teardown. The harness stops after the loop, before subsequent final-result processing. These are calibration observations, not convergence-time claims for an unmodified end-to-end executable.

The `--scf-training` patch also supports later replay with `FABO_SCF_TRAINING=fixed`, `FABO_SCF_STATE=...`, and `FABO_SCF_STEPS=K`. It restores the archived state, skips a second SAD solve, retains DIIS/screening and stops after exactly K iterations. It writes `replayed-initial.bin` for a future benchmark controller to verify byte-for-byte. Calibration never uses fixed mode. Additional separations need their own official calibration; equilibrium counts are not automatically reused for other geometries. Full variant-comparison/tuning orchestration is not part of this stage.

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

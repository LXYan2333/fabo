# QUICK single-update comparison

This experiment is separate from the fixed-length SCF trajectories in `compare.py`. Official QUICK 26.03 constructs its default superposition-of-atomic-densities (SAD) guess once per workload. The fixture freezes P0, Hcore, overlap and the orthogonalizer. Every timing and reference process reads exactly the same fixture, performs one full F[P0] build, diagonalizes and constructs P1. There is no convergence trajectory, density-difference Fock update or molecular warmup. Ordinary QUICK integral screening remains enabled; all backends see the same input density and screening settings. The scope of replacement is the two GPU energy-integral Boys call sites, not one-electron or screening preparation routines.

The default workload is S66 system 17 (uracil dimer at equilibrium), translated along z by 3.4 Angstrom per copy, with def2-SVP and ENABLEF disabled. Test eight copies, then sixteen if the official Fock build takes less than two seconds. Select the first reaching that target, or report explicitly that the largest candidate did not reach it. This is workload sizing, not Boys tuning. Preparation records source geometry, all translated coordinates, basis hashes and dimensions. No timing results from previous SAD/hcore experiments are merged.

Five backends (official QUICK, FABO, LibintX, Vikhamar-Sandberg-Repisky and GANSU) run in rotating order for five repetitions. Each run is a fresh process on the exclusively allocated GPU node. Builds use node-local scratch, six concurrent serial variant builds, and finish before any measurements. The timers bracket synchronized scf_operator and the complete Fock-plus-diagonalization/density update, respectively. Initial preparation, matrix export and energy diagnostics are outside both intervals. The scalar energy is Ecore + 0.5 sum(P0 * (Hcore + F[P0])); it is not an energy evaluated at P1.

The sixth backend is untimed. It uses the retained binary128 Boys interval evaluator and adaptive directed-MPFR fallback, accepting a binary64 result only when both enclosure endpoints round identically. Strict and fast-math standalone conformance tests and fail-closed host-bridge tests run before molecular work. An unresolved call aborts the update before diagonalization; its request list is resolved by MPFR and the same fixture is replayed in a fresh process. Failed attempts do not count toward the five accepted reference repetitions. Invalid inputs, queue overflow and exhausted replay limits fail the workflow. No reference time is included in the performance table.

The elementwise average of the five reference Fock and P1 matrices, and the average reference energy, define the empirical comparison reference. This is not an exact molecular solution: integral recurrence, GPU accumulation and eigensolver arithmetic remain binary64. Raw observations and reference standard deviations are retained. Matrix averaging is centered on the first observation, with the mean stored as two binary64 parts (hi + lo) to retain sub-ulp mean offsets. Energy differences are also computed using centered observations. No density is reconstructed from an averaged Fock matrix, and reference means are never fed back as initial densities.

## Run and reproduce

```sh
.venv/bin/python -m workflow.quick.fixed_density prepare \
  --config workflow/quick/profiles/fixed-density-rtx5090d.json \
  --dataset /path/to/s66x8 --run /path/to/new-run
# Transfer the prepared directory to Slater2; submit from that directory:
sbatch run.sbatch
# Regenerate reports from completed records without executing QUICK:
cd /path/to/run/bundle
python -m workflow.quick.fixed_density report --run /path/to/run
```

The configured reference Python needs NumPy and gmpy2. The GPU requires CUDA binary128 support (the configured pc008/SM120 and CUDA 13.4 meet this requirement). Sources, generated coefficient tables, compiler commands, runtime-library hashes, GPU/toolkit identity and per-update completion manifests are archived. Cached updates must match their backend, repetition, timing mode, basis and exact fixture identity as well as their raw file hashes. An interrupted run can reuse verified completed builds/updates; it never accepts a partial update. Failed attempts are retained under new sequence numbers on retry, and pending MPFR transactions are completed before another Fock build. The reference attempt limit applies to each invocation of an unfinished repetition. GPU work is managed by Slurm, independently of the submitting laptop.

`timing-summary.json` is written before the repeated reference begins; `summary.json` and `complete.json` appear only after all reference updates succeed. `samples/RR/BACKEND/outputs.bin` contains Fock followed by P1, each an n-by-n column-major little-endian binary64 matrix. `fixtures/CASE/fixture.bin` begins with three little-endian int32 values (n, reduced basis dimension, electron count), followed by P0, Hcore, S (n-by-n) and X (n-by-reduced), in the same binary64 layout. `fixture-info.txt` additionally records Ecore. Replay hashes verify the actual decoded fixture fields. `reference-mean/{hi,lo,sd}.bin` has the same two-matrix layout as outputs.bin. Every accepted sample retains energy, matrices and raw logs; rejected reference attempts and override tables are separate.

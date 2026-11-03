# NWChem / Simint single-update comparison

This workflow compares five compiled Boys implementations, not trained configurations. It uses equilibrium S66 systems 1, 17, 24 and 34, spherical 6-31G*, def2-SVP and cc-pVDZ, and five rotating-order repetitions. Current integration is x86-64 AVX-512 only. Numerical models and table data are unchanged; the GCC native-gather workaround is described below.

## Preparation and execution

Copy `nwchem_compare.json` into a run-specific configuration and resolve every source, dataset, compiler and dependency path on the machine running each stage. `prepare` requires the pinned NWChem, Simint, LibintX and Highway repositories and this repository's legacy commit; it exports source snapshots, patches disposable sources and freezes the current headers and workload. Sequential ILP64 MKL must be installed on the build/timing nodes. NumPy is required for sample validation and reporting, Matplotlib for reporting, and pytest for development tests.

```sh
python -m workflow.nwchem_compare prepare --config my-nwchem.json --run /shared/comparison
```

Run the following on c023, in a Slurm allocation with at least eight CPUs and sufficient memory. Builds and intermediate integral source files use `/tmp`. The common NWChem core is built once; variants are relinked independently. No build runs on c021.

```sh
python -m workflow.nwchem_compare build --run /shared/comparison
```

Then run smoke and benchmark sequentially on an exclusively allocated c021, with the configured core in the allocation's CPU set:

```sh
python -m workflow.nwchem_compare smoke --run /shared/comparison
python -m workflow.nwchem_compare benchmark --run /shared/comparison
python -m workflow.nwchem_compare report --run /shared/comparison
```

These are stage commands, not automatic submissions. After transferring the prepared run and this workflow to Heitler, generate batch scripts using `python -m workflow.nwchem_cluster --run /shared/comparison --repo /path/to/fast_boys`. Submit `build.sbatch`, then `smoke.sbatch` after a successful build, and inspect the smoke results before submitting `benchmark.sbatch`. The last script also generates the report. Builds use c023; measurements exclusively allocate c021. No submission is implicit. Existing completed samples are verified before reuse; failed samples have no completion marker. Use a new output directory when inputs, libraries or binaries change.

## What is measured

An untimed original-backend preparation saves NWChem's atomic-guess orbital state. Each measurement restores it and verifies both the serialized replay and reconstructed input density. NWChem still performs its normal untimed atomic-guess Fock construction before the saved orbitals are restored; this setup is outside the measured interval and the Fock-capture hook. The measured comparison performs one energy/Fock evaluation and one orbital diagonalization/update, even if the initial state meets a convergence threshold. It then exits, without the next energy evaluation or canonicalization. Thus the single-update count describes the measured phase, not the entire process. Full-rank, closed-shell replicated-Fock calculations are required; unsupported paths fail rather than silently switching solvers.

The primary interval is the two-electron `fock_2e` call. Nested total-Fock and complete-update times are recorded too. Copies needed to retain P0/F[P0] are common to all backends, outside the primary JK interval but inside the complete-update interval. Binary matrix export and formation of the diagnostic P1 from the updated occupied orbitals occur after the timer. Thus complete-update time covers the native orbital update, not this additional diagnostic reconstruction. No molecular warmup or convergence training is performed.

`density-in.bin`, `fock.bin` and `density-out.bin` contain headerless column-major binary64 values; dimensions and solver information are in `scf-protocol.txt`. Energy is NWChem's E[P0], not E[P1]. Reported differences are relative to original Simint, not an exact reference. Raw outputs for every repetition are retained. Repeated original energies provide an environmental repeatability diagnostic. Ratios are original JK median / backend JK median; values below one are retained.

## MKL and compilation

Automatic MKL dispatch is retained. MKL_CBWR and MKL_ENABLE_INSTRUCTIONS are explicitly unset, thread counts are one, and MKL_DYNAMIC is false. An untimed helper records MKL version, CNR settings, detected automatic branch, verbose BLAS information and mapped-library hashes. Each actual NWChem process also records MKL settings and loaded-library mappings after timing; the controller hashes these files. CNR branch identification is a diagnostic, not a guarantee that every BLAS/LAPACK routine uses one identical instruction set. These records identify the observed environment but do not promise architecture-independent bitwise results. Verbose logging is disabled during measurements. Existing user/system nwchemrc files are fingerprinted, and input explicitly sets local scratch and permanent directories.

Generated Simint C++ translation units for all five backends share GCC optimization and architecture settings (`-O3 -ffast-math -fopenmp-simd -DNDEBUG -march=sapphirerapids`). Laikov's supplied coefficient support is built as GNU C. LibintX retains its native experimental SIMD, including the output initialization required by its accumulating evaluator; its tables initialize before measurement. VSR and Laikov use their archived Highway ports and libmvec. The Sapphire Rapids Highway target defaults to native FABO gather; a compile test verifies this choice without overriding the production default.

Preparation applies `benchmark/nwchem/highway_gather.patch` to the pinned Highway export used by every backend. This contains the native-gather changes from Highway PR #3519 (local source commits `278be1b6` and `1d3324fb`): an opaque all-active mask retains the zero merge source and avoids GCC's false destination dependency. The patch, resulting headers and provenance are hashed in the prepared archive. FABO also carries the same workaround for users of unpatched Highway. Software gathers are unchanged; this is a code-generation workaround, not a new arithmetic strategy or mitigation-state experiment.

## Verification status

Local tests cover generated bindings under GCC, source patch anchors, the position of the one-update stop, Fortran-hook syntax, sample dimensions/finiteness, artifact hashes, environment controls and input generation. Native/software gather comparisons and GCC assembly checks cover AVX2 and AVX-512; the patched shared Highway export is also tested directly. A complete NWChem build and molecular smoke test must still pass on the configured cluster before timing results are accepted. No benchmark results are supplied by this implementation.

The profile explicitly selects Conda GCC/G++ 14.4 rather than Clang: Heitler's Clang 19.1.7 / libstdc++ 14.4.0 rejects LibintX's native experimental-SIMD comparison with `static_assert(is_same_v<long long, long>)`. All variants switch together; no backend-specific compiler substitution or SIMD scalarization is used. The build preflight checks the configured compiler before expensive builds. Preparation requires the pinned LibintX checkout (or a locally prepared snapshot); that checkout was not present at its configured Heitler path during inspection.

`prepare` can run locally after adjusting its source/dataset paths, then its output can be transferred to Heitler. Later stages use the exported sources, not those original checkout paths. Compiler, MKL and MPI paths must name the remote toolchain. The prepared archive includes source snapshots, workflow code, frozen FABO headers and input hashes. Summaries preserve all five repetitions in JSON, report seconds for JK/Fock/complete-update timers and differences in Hartree or matrix units, and plot JK medians; these are neither convergence times nor errors relative to an exact molecular solution.

```sh
python -m pytest -q workflow/tests/test_nwchem_compare.py
```

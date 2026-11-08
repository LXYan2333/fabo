# NWChem--Simint CPU fixed-density performance records

This package contains the latest completed CPU comparison, Heitler c021 job 177804, run `full-library-simd-additions-20261106`. The source snapshot recorded in `reuse.json` includes incremental tail powers and simplified SIMD coordinate preparation, subsequently committed as `2249432`. All timings were newly measured; initial-state fixtures and correctly rounded reference observations were reused from the preceding run.

`results.json` retains all 300 observations, including the individual two-electron (`jk_seconds`), full Fock and complete-update timings. Paper plots use the arithmetic mean of `jk_seconds`, the `fock_2e` interval. `summary.json` is the original median-based export, not the plotted mean. The plot generator checks its medians against the observations before deriving means and sample standard deviations. All cases have five rotating-order, single-threaded, fresh-process repetitions, one fixed-density update per process, and no warmup. The workloads comprise eight water dimers and single uracil, benzene and pentane dimers, each with three bases.

`complete.json` authenticates the original summary, reuse manifest, and `reference-summary.json`, which contains molecular differences from the correctly rounded Boys backend and repeatability results. `download-manifest.json` records the checksums of the individual observations and configuration files, verified against remote `sha256sum` during retrieval. `selected-cases.json` contains geometry identities and stack sizes; `config.json` records the experiment configuration. The full source, build and matrix archive remains on Heitler at `/export/home/yanlongxiang/fast-boys-nwchem/full-library-simd-additions-20261106/run`. This local package reproduces timing and molecular-difference reports, not the complete molecular experiment.

Regenerate the four figures and complete three-decimal mean-time table without running NWChem:

```sh
.venv/bin/python -m workflow.scripts.plot_nwchem_performance --records data/benchmarks/nwchem-fixed-density-20261106 --output overleaf-paper2/figure --tables overleaf-paper2/tables
```

PDFs are written to `figure/`; the LaTeX table, full-precision mean/dispersion CSV and provenance JSON are written to `tables/`. The renderer is shared with the QUICK figure generator, but the timing scopes, stack sizes, raw observations and provenance remain separate. See `workflow/NWCHEM_FIXED_DENSITY.md` for the execution and reference protocol.

`matrix-absolute.json` extends the completed reference comparison with the mean absolute difference over every matrix element, including zeros and both symmetric halves. It uses the first saved output of each bitwise-reproducible backend and verifies the consumed matrix hashes and agreement with the original maximum differences. No relative matrix errors are computed. The source reference-report hash, matrix hashes, accumulation precision and reduction code hashes are retained. To repeat this post-processing against the full execution archive, run from the repository root:

```sh
python -m workflow.scripts.nwchem_molecular_metrics --run /path/to/full-library-simd-additions-20261106/run --output /path/to/new-matrix-absolute.json
```

`matrix-absolute.manifest.json` authenticates the compact reduction against the remote original, verified on 2026-11-08. The exporter requires this checksum before reading measurements. Future reductions write a matching `.manifest.json` automatically; retain it with the report. The manifest protects against accidental edits, not coordinated changes to both files. Run the reducer from this repository so its `molecular_metrics` and `record_manifest` helpers are available.

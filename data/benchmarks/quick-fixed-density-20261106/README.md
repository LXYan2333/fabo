# QUICK GPU fixed-density performance records

These are the completed records from Slater2 pc008 job 2129618, run `full-library-20261106`, identity `613674703e51e70d27b74c76c72ded488ff7566c8cce082ed0d5d2f8b6bcf015`. They cover four S66 dimer stacks, three bases and five timed Boys implementations. All 300 Fock-build observations are retained in `summary.json`, together with complete-iteration observations and molecular comparison summaries. The correctly rounded reference is untimed and is not a bar in the performance plots.

`complete.json` authenticates the summary, fixture/reference reuse manifest, and conformance-only include-path repair record. `reuse.json` identifies the source snapshot, executable manifests, initial states and reused reference observations. All timed samples were newly measured in this run. The complete execution archive, including matrices and binaries, remains at `/export/home/lxyan2/fast-boys-additive/full-library-20261106` on Slater2; this small local package reproduces the timing figures, not the complete molecular experiment. Its numerical tables and CUDA evaluator correspond to the shared-coordinate implementation incorporated in commit `1bd9365`.

Each observation is one synchronized full Fock build from the same saved SAD density, without molecular warmup. Backend order rotates over five fresh-process repetitions. The figures show arithmetic means in seconds, with sample-standard-deviation error bars. Existing workflow CSV exports use medians; the figure generator instead reads the five original samples. Timings are not SCF convergence times or isolated Boys-function timings. See `workflow/quick/FIXED_DENSITY.md` for the experiment protocol.

Regenerate the four figures and the 60-row mean/dispersion CSV without running a benchmark:

```sh
.venv/bin/python workflow/scripts/plot_quick_performance.py --records data/benchmarks/quick-fixed-density-20261106 --output overleaf-paper2/figure --tables overleaf-paper2/tables
```

The generator checks completion hashes, run identities, all 12 cases, all five timed backends and all five repetitions before plotting. PDFs are written to `figure/`; the LaTeX table, full-precision CSV and provenance JSON are written to `tables/`. Raw records are unchanged.

## Molecular differences of means

`molecular-means.manifest.json` authenticates the compact reduction file against the remote original, verified on 2026-11-08. The molecular exporter checks this checksum before reading measurements. Future reductions write the companion manifest automatically; retain it alongside the JSON report. It protects against accidental changes, not coordinated edits to both data and manifest.

The original summary's matrix differences are maxima over individual repetitions relative to the reference mean. They are not differences between the two mean matrices. `molecular-means.json` supplies the latter statistics for the paper: maximum and mean absolute elementwise differences, derived from all five stored matrices for every backend, centered on the archived reference mean's high and low parts. The mean includes all n*n entries, including zeros and both symmetric halves. No relative matrix errors are calculated. Every consumed matrix and sample-result checksum is verified. This reduction does not rerun QUICK or alter any original observations. The energy statistic is the existing centered difference of five-run means. The report also retains reference-repeat standard deviations, accumulation precision, and case-level source hashes. The schema-2 absolute-statistics reduction was performed in `matrix-absolute-20261107` on Slater2; the earlier max-only reduction remains archived separately as `molecular-means-20261107`.

To repeat the matrix reduction, access the full execution archive on Slater2 and choose a new output directory:

```sh
python -m workflow.scripts.quick_molecular_means --run /path/to/full-library-20261106 --output /path/to/new-mean-report
```

To regenerate the paper's molecular table and complete casewise CSV from the compact local reports alone:

```sh
.venv/bin/python -m workflow.scripts.report_molecular_accuracy --gpu data/benchmarks/quick-fixed-density-20261106 --cpu data/benchmarks/nwchem-fixed-density-20261106 --output overleaf-paper2/tables
```

The tables summarize the largest casewise maximum and mean absolute differences separately for each engine and backend; the JSON provenance retains the maximizing case for every statistic. A mean is taken over matrix entries within one case, not pooled across cases. The two engines have different geometries/stack sizes and numerical pipelines. Neither report is a comparison with an exact or converged molecular solution.

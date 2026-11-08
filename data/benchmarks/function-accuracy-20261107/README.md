# Completed function-accuracy scans

The CPU and CUDA directories retain all per-output and pooled statistics for the completed [0,1000] scan at RN64(i/1000000), i=0,...,1000000000, requested ranges [0,N], N=0,...,12, under strict and fast-math compilation. These are sampled implementation errors against unrounded reference intervals, not continuous-domain guarantees.

Each `complete.json` authenticates `accuracy.json` and identifies its run recipe and execution environment. `run.json` preserves the recipe, adapter commands and hashes, source hashes, reference-table identity, grid, and shard layout. `execution.json` records the actual processor/device and loaded-library environment. `built.json` retains compiler versions, configuration, commands, and dependency hashes; `scan.build.json` records the strict collector build. `download-manifest.json` authenticates these four metadata files against checksums retrieved from the clusters on 2026-11-08. The report exporter checks those hashes, recomputes the run/execution identities, and links the build and grid to the completed measurements. Original metadata and paths are retained unchanged.

## Full artifacts and retrieval

The compact package is sufficient for report regeneration. Binaries, reference tables, adapter sources, dependencies, and individual scan shards remain in the author-managed cluster archives below; access requires cluster credentials. This is not a self-contained binary/source reproduction bundle.

| Platform | Host and archive root | Jobs |
|---|---|---|
| CPU | `Heitler:/export/home/yanlongxiang/fast-boys-additive/library-accuracy-full-20261107` | Prepare 177807; scan 177808; report 177809 |
| CUDA | `Slater2:/export/home/lxyan2/fast-boys-additive/library-accuracy-full-20261107` | Prepare 2129786; scan 2129787; report 2129788 |

Within each root, `repo/` is the source snapshot, `results/suite/` holds compiled adapters and dependency exports, `results/scan` is the collector, `results/reference.bin` is the reference table, and `results/run/` holds run metadata, pilot records, shards under `scan/`, and final reports. The compact copies map `run.json` and `execution.json` from `results/run/`, `built.json` from `results/suite/`, and `scan.build.json` from `results/`. Retrieve required files with `scp` using these host/path pairs; retain their directory layout and verify their hashes against the saved metadata. Historical absolute paths describe provenance, not required destinations for report regeneration.

## Regeneration versus rerunning

Regenerate figures and tables from this relocatable compact archive, without executing any evaluator:

```sh
.venv/bin/python -m workflow.scripts.report_function_accuracy --records data/benchmarks/function-accuracy-20261107 --figures /tmp/fabo-accuracy-report/figure --tables /tmp/fabo-accuracy-report/tables
```

Building adapters, reference preparation, and new scans are separate operations documented in `workflow/library_accuracy/README.md`. A rerun with relocated binaries or a new environment creates a new run identity; it does not replace these historical records. The original `complete.json` also lists hashes of report-format artifacts not included here (CSV, LaTeX, and PDFs); they can be retrieved from the cluster or regenerated as new reports.

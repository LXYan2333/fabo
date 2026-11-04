# Fixed-density QUICK branch probabilities

`branch_probe.py` restores the family-level diagnostic from commit `7062ced`, using the current fixed-density suite's selected geometries and saved SAD fixtures. It builds a separate instrumented FABO executable and does not modify or replace benchmark measurements. Only the replayed Fock build is observed; initialization and SAD construction are excluded.

For each QUICK family and maximum requested order, the records retain active participation, input histograms, main/tail splits, and the probability that all active lanes satisfy `x > t` or `x < t`. Equality fails both strict predicates. Full (32 lanes) and partial cohorts are reported separately. A cohort is the active mask at a Boys call, not necessarily a complete physical warp; instrumentation can affect scheduling.

Thresholds are integer-spaced through 1000 and logarithmic (16 samples per decade) through 1e10. The plots mark 117 and the main-table endpoint 1e7. Invalid arguments are counted separately and excluded from branch-probability denominators. Histogram heights are normalized by bin width.

Run on an exclusively allocated GPU node, using a completed fixed-density suite as parent:

```sh
python workflow/quick/branch_probe.py --parent /path/to/completed-suite --run /path/to/new-probe --systems 1
```

The runner uses the parent's bundled build/replay utilities, checks the parent inputs and fixtures, builds in node-local temporary storage, and runs a synthetic CUDA counter/oracle test before collecting molecular observations. The current adapter supports ENABLEF=OFF and sm_120. Build and diagnostic execution are not performance measurements.

Each case produces `family-counters.csv`, `report/branches.csv`, `report/histogram.csv`, `report/summary.json`, and `plots/{alltrue,mixed,inputs,requests}.pdf`. All-true and mixed plots include aggregate and maximum-request-order views. JSON preserves full/partial denominators and provenance. The saved reports can be replotted without CUDA:

```sh
python workflow/scripts/plot_quick_family.py /path/to/case/report/summary.json --output /path/to/plots
```

The counter implementation and report transformations were recovered from Git; old training/anchor-selection dependencies were intentionally not restored. Host regression tests are in `workflow/tests/test_quick_family.py`.

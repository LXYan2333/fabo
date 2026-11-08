# Upward recurrence: one-million-sample passing windows

Completed on Heitler c021–c024, 2026-11-07: preparation 177872, scan array 177873, report 177874. Numerical identity: `596d186a3e9462fb2b2eb0f34dfb09490ede6f9cbac368cd97b9655b8f492323`. The domain contains one billion positive samples through 1000, at spacing 1e-6. All reconstructed outputs through each N=1,...,12 must pass the selected true-value ULP gate. Zero is not a recurrence input.

`shards.tar.gz` contains all 4000 compact shard summaries, not dense outputs. The first/last chain failures suffice to reconstruct the first million-point window because each shard is shorter than that window. `boundaries.json` and CSV retain every order/tolerance result, including absent windows. `run.json` records the compiler, source identities, and reference/scanner hashes; `execution.json` records the runtime. Absolute paths in those provenance records describe the historical run, not requirements for report regeneration. The original report PDF and hashes are retained; the paper plot shows only found windows, with the starting argument on a logarithmic horizontal axis and the requested maximum order on the vertical axis.

From the repository root, regenerate the paper figure without numerical computation:

```sh
python -m workflow.upward_recurrence_limits plot --run data/diagnostics/upward-recurrence-limits --output overleaf-paper2/figure/upward-recurrence-limits.pdf
```

This verifies the boundary-record checksum, checks shard identities and full coverage, repeats the reduction, and compares its output with the saved boundaries before plotting. See workflow/upward_recurrence_limits/README.md for rebuilding the reference and repeating the numerical scan. The old [0,128] experiment is not substituted for this dataset. The window includes its first sample and spans 0.999999; later arguments need not pass.

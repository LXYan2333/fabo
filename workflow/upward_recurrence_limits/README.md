# Upward-recurrence passing windows

This independent diagnostic scans x=RN64(i/10^6), i=1,...,10^9. For each requested maximum order N=1,...,12 and tolerance 1,2,4,8,16 ULP, it finds the earliest window containing one million consecutive passing samples, including its first sample. All reconstructed outputs F1,...,FN must pass. The window spans 0.999999 in x. It is not a safe suffix or an all-binary64 accuracy certificate. Zero is excluded because upward recurrence is undefined there.

The arithmetic is the original recurrence probe's scaled-FMA organization: t=RN64(x+x), rho=RN64(1/t), q=RN64(E*rho), a_n=RN64((2n-1)*rho), f_n=FMA(a_n,f_(n-1),-q). F0 and E=exp(-x) are correctly rounded binary64 values. The exponential is allowed to underflow correctly to zero. No approximate reciprocal or asymptotic replacement is introduced. Strict compilation disables implicit contraction; explicit FMA remains fused. RN-even and gradual underflow are enforced.

The native reference and gate classifiers are adapted from Git branch main's workflow/reference/recurrence_ulp_probe.cc and rounded_reference_v3.h. MPFR-directed degree-12 Taylor reference tables at width 1/16 accelerate binary128 evaluation. Ambiguous rounding/gate decisions use direct MPFR through 4096 bits; unresolved decisions fail. ULP is spacing at the correctly rounded mathematical Boys value, not integer distance to that rounded value. The existing accuracy_reference_v3.h provides the reference infrastructure.

Each 250000-point shard stores the first/last chain failure for each (N,tolerance). Every shard is shorter than the qualifying window, so no qualifying window can be wholly inside one shard; joining exact passing prefixes/suffixes therefore finds the earliest window without dense storage. Missing coverage or incompatible records invalidate the report. Persistent results are compact JSON; reference tables are shared, and per-worker scratch is temporary.

```sh
python -m workflow.upward_recurrence_limits prepare --run RUN --cxx g++ --prefix /path/to/mpfr-prefix --workers 8
python -m workflow.upward_recurrence_limits pilot --run RUN
python -m workflow.upward_recurrence_limits cluster --run RUN --workers 16 --submit
python -m workflow.upward_recurrence_limits report --run RUN
python -m pytest workflow/upward_recurrence_limits -q
```

Preparation requires a new run directory and builds the scanner/reference tables. The pilot checks low, moderate, and high arguments, including exponential underflow. Cluster defaults target Heitler's compatible c021–c024 group; scan and report jobs survive laptop disconnection. Reporting alone never submits work. Copy the completed upward-recurrence-limits.pdf to overleaf-paper2/figure/ after checking complete.json. Do not reuse the older [0,128] suffix-boundary plot as this result. No finite boundary is fabricated if no full window exists within [0,1000].

The completed portable dataset is in `data/diagnostics/upward-recurrence-limits`. Regenerate and verify its figure using `python -m workflow.upward_recurrence_limits plot --run data/diagnostics/upward-recurrence-limits --output overleaf-paper2/figure/upward-recurrence-limits.pdf`. This command does not require the original executable, reference tables, cluster paths, or a new scan.

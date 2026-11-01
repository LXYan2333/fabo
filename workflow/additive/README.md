# Fully materialized additive-grid construction

This is a new numerical method, not a continuation of the exponential-aligned catalog. It stores correctly rounded Boys coefficients and one unsigned next-up output-correction byte per requested order. There are no recurrence patches, materialization choices, exponential dictionary, or runtime exponential evaluation. The mathematical MPFR reference generator still uses exponentials offline.

## Contract and selection

For Q=2^b and B=(2Q-m)2^e, compute y=RN64(x+B), round its unsigned encoding right by s=52-b with ties toward the larger key, reconstruct Y, then x_ref=RN64(Y-B) and h=RN64(x_ref-x). The first node is zero. Table rows include every selected endpoint node, even one beyond the domain. Actual cell boundaries are binary-searched using rounded addition, not ideal midpoint assumptions.

The default family enumerates b=4…12, e=-16…4, every m=1…2^b, requested ranges [0,N] for N=0…24, and degrees 1…12. Each output gets its own minimum qualified degree. Candidates are ordered by maximum degree, actual eight-byte-aligned row storage, degree vector, then (b,e,m). Storage includes all coefficients through max(n+p_n), output corrections, and row padding. The budget is 1 MiB per requested range. No maximum-degree monotonicity assumption is made; every lower degree has a failure witness. An unresolved degree prevents a minimum claim for that grid. Any unresolved grid prevents an unconditional minimum claim for the family.

The target is distance to the true Boys value divided by the binary64 spacing at its correctly rounded value, not integer distance to a rounded-only reference. Absolute and relative targets are also supported. Explicit binary64 rounding and FMA are modeled with exact rational arithmetic. MPFR directed intervals enclose mathematical references; qualification samples cell boundaries, reference points, interior points and neighboring binary64 values, then refines near maxima. This is not a continuous-domain error certificate. Fast-math checks are diagnostic and do not replace strict qualification.

The next-up constant is bits(F_n(x_ref))+1. The byte represents a positive correction: codes 0…128 encode (1/2+code/256) ULP, and codes 129…192 encode (1+(code-128)/128) ULP. Factorial Horner evaluates the nonconstant terms; the final operations are next_up + FMA(h,tail,-correction). The lowest stored order is prebiased in the serialized payload; other coefficient words remain ordinary rounded values because lower outputs consume them. The scalar oracle starts with ordinary coefficients and performs the equivalent bit increment at output assembly. Unsupported correction exponent ranges are reported as unresolved, not accepted.

## Local development

Use pytest, not unittest. No new package was needed in the existing local environment. The production environment specification pins Python 3.12.15, gmpy2 2.3.2, MPFR 4.2.2 and GMP 6.3.0; the default profile rejects other producer versions. The smoke profile deliberately permits the existing local environment and records it in the identity. Before freezing an installed environment, save its exact package resolution with `conda list --explicit`; the YAML is not an explicit binary-package lock. Plotting and pytest versions do not determine rounded mathematical data.

```sh
conda env create -f workflow/additive/environment.yml
conda activate fabo-additive
conda list --explicit > environment-explicit.txt
python -m pytest -q
python -m workflow.additive.search --config workflow/additive/profiles/smoke.json --output .work/additive-smoke --workers 2
python -m workflow.additive.artifacts .work/additive-smoke/summary.json --output .work/additive-smoke/figures --tables
```

The last command regenerates selected binary tables, checks their SHA-256 hashes, and plots degree vectors, storage, sampled error margins and reference spacing. It does not repeat the search. The payload format is little-endian coefficient words followed by correction bytes and zero padding to eight bytes. Metadata gives exact hex domain and offset, key range, degrees, highest reference order, layout and minimum-order prebias. Coefficients are regenerated at exact binary64 reference coordinates.

## Cluster execution

Copy this source directory and the profile to a frozen checkout on Heitler. Run the following on the login node, using the actual installed producer Python and shared output paths. This prepares scripts only unless `--submit` is supplied.

```sh
python -m workflow.additive.cluster --repo "$PWD" --config workflow/additive/profiles/default.json --output /absolute/shared/additive-run --python /absolute/path/to/fabo-additive/bin/python
# Add --submit after inspecting the prepared commands.
```

Defaults request partition 6526Y, c021–c028, 128 grid shards, at most 32 concurrent eight-worker allocations, 32 GiB per allocation and 24 hours per job. These are configurable. A dependent merge runs after all array tasks succeed; no laptop controller is required. Within each grid the QUICK ranges 4/8/12 are evaluated first and per-order results are reused across larger ranges. This is not a promise of publishing globally optimal GPU selections before every grid shard finishes. There is no hardware training or timing in this workflow.

Expanded reference data are bounded in-process caches. Journals are written in node-local scratch and published on job exit; sudden node loss can lose that shard's unpublished progress. Resubmitting the same identity resumes published complete records and discards only an interrupted final append. Retry failed/time-limited tasks explicitly; the dependent merge will not accept incomplete coverage. Do not run two writers for the same shard. No previous expanded-cache data are required.

## Portable results and provenance

Keep `summary.json`, the exact configuration, producer versions, source snapshot and payload hashes for publication; these are compact regeneration recipes, not compressed expanded tables. `records.jsonl` is a resumable run-local attempt ledger and need not enter Git. The summary preserves winner witnesses, lower-degree failures, rejection counts, coverage status and window-edge warnings. Aggregation streams journals rather than loading the entire history.

The directed Boys and exact-rounding helpers were selectively extracted from branch fresh-start, commit c3c5788. The new grid, degree search and fully materialized row layout have their own identity. CPU/GPU compilation and hardware conformance remain separate consumers; this workflow does not certify arbitrary compiler reassociation. The prior exponential-free large-argument model is not retuned or emitted here, and the main-domain metadata does not claim qualification beyond its endpoint. No previous main-grid acceptance results are imported.

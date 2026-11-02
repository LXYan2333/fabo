# Additive-grid numerical construction

## Numerical contract

Runtime uses y=RN64(x+B), unsigned half-up rounded-right-shift quantization with s=52-b, x_ref=RN64(Y-B), and h=RN64(x_ref-x). All Boys coefficients are materialized; there are no recurrence patches or runtime exponentials. The one-byte next-up output correction and strict factorial-Horner DAG are unchanged.

Offsets are represented directly by offset_code: B=from_bits64(offset_code<<s). All nonnegative finite aligned offsets are considered geometrically, including zero and subnormal offsets. There is no spacing-exponent window. Metadata stores the exact hexadecimal offset, code, key range, degrees and storage layout. Legacy (b,e,m) metadata remains readable and produces the same coefficient payload.

Qualification uses exact-rational binary64 arithmetic and directed MPFR references. The 1-ULP gate measures distance to the true Boys value, scaled by the spacing at its correctly rounded value. Cell endpoints, neighbors, reference points, interior samples and refined maxima are checked. This is sampled qualification, not a continuous-domain proof. Fast-math checks are separate diagnostics.

## Budget-guided search

The default profile searches [0,N] for N=0…24 on [0,10^7], b=4…12, under 1 MiB per range. maximum_degree defaults to12 and is a hard Taylor-degree cap, not a cap on coefficient order N+P. No automatic degree expansion is permitted.

For each (range,b), try common degree P in ascending order. Its row size is round_up_8(8*(N+P-L+1)+(N-L+1)). Find the smallest budget-fitting offset by bisection over offset codes. Row-count monotonicity is checked in bounded NumPy chunks, with endpoint comparisons to the exact arithmetic oracle. If that check fails, use exact geometry-only scanning instead.

Screen every required output before any full qualification, testing high orders first. The first qualified common degree starts offset shrinking: exponential index steps, bisection of the passing/nonpassing bracket, then one neighborhood sweep (default radius4). Failures do not prove all larger offsets fail. Retain only fully qualified offsets and keep the largest passing one encountered.

Freeze the resulting grid and minimize each output degree independently by ascending tests through P. Freed storage is not refilled. Compare candidates across b by maximum actual degree, actual table bytes, degree vector and stable grid key. Unresolved probes remain explicit; they cannot establish degree minimality. Results are the best qualified selections found by this staged search, not global optima. Explicit exhaustive mode remains available for bounded fixtures.

## Storage and reproduction

Rows contain little-endian binary64 coefficient words, unsigned output-correction bytes, and zero padding to eight bytes. The lowest stored coefficient is prebiased to next-up; others remain ordinary rounded coefficients because lower outputs consume them. The coefficient range ends at max(n+p_n), not N+max(p_n).

Expanded data stay in bounded memory. summary.json stores selected recipes, witnesses and payload checksums. state.json records completed probes and resumable decisions; records.jsonl contains final task results. None contains expanded tables. Node-local metadata is published after completed probes and on exit. A lost node can require repeating its current unfinished probe, not completed published probes.

The exact Python/gmpy2/MPFR/GMP producer versions are checked by the production profile. NumPy is also recorded in the numerical run identity; the environment file pins a wheel compatible with the cluster OS. Geometry verification uses only binary64 addition and integer operations, not NumPy transcendental routines.

```sh
python -m pytest -q
python -m workflow.additive.search --config workflow/additive/profiles/smoke.json --output .work/additive-smoke --workers 2
python -m workflow.additive.artifacts .work/additive-smoke/summary.json --output .work/additive-smoke/figures --tables
```

The existing smoke profile is an explicitly bounded exhaustive regression fixture. Tests also exercise the guided job script and resume/merge path. The artifacts command regenerates selected tables and verifies checksums without repeating the search. It also creates degree, storage, error and grid-spacing plots. Omit --tables to avoid retaining expanded binary tables.

## CUDA header generation

`python -m workflow.additive.headers RUN/summary.json --output .work/generated/include --ranges 0-4 0-8 0-12` emits exact payload initializers and lightweight model headers with incremental scalar coefficient loads. It consumes the frozen summary without rerunning numerical selection. Omit `--ranges` to emit all models; `--workers 4` regenerates independent models in four processes with bounded row caches. The manifest preserves the numerical identity separately from the generated implementation identity. The completed `[0,N]`, N=0–24 selections are bundled in `include`, with their reproducible source summary at `data/numerical/additive-1ulp-summary.json`. See `include/fast_boys/README.md` for the static/runtime range API, allocation lifetime, compact large-argument fallback, and conformance commands. Expanded generated headers remain regenerable artifacts rather than numerical cache entries.

## Cluster execution

Run the launcher from a frozen checkout on Heitler, using the pinned producer:

```sh
python -m workflow.additive.cluster --repo "$PWD" --config workflow/additive/profiles/default.json --output /absolute/shared/run --python /absolute/producer/bin/python
# Inspect prepared scripts, then repeat with --submit.
```

Guided mode creates one single-CPU, 2-GiB task per (range,b):225 tasks by default on c021–c028. The default concurrency cap is256; an explicit --concurrency is honored. QUICK ranges ending at4/8/12 are ordered first. Tasks request one node; eligible hosts are enforced by excluding other partition nodes, not by requesting all hosts.

Each allocation has a24-hour limit. An afterany finalizer retries incomplete tasks at most twice, preserving completed probes, then merges only complete matching identities and coverage. An exhausted retry limit creates incomplete.json and reports failure. Numerical no-candidate outcomes are completed results, not infrastructure failures to retry. The controller does not require the laptop to stay connected. Do not submit concurrent writers to the same run.

The older exhaustive source/results remain archival; their metadata are not silently relabeled as guided-search results. The large-argument method is not retuned here. Nothing in the bounded-domain summary qualifies inputs beyond its endpoint.

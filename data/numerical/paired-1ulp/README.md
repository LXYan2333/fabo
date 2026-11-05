# Paired one-ULP numerical selections

`summary.json` is the unchanged final result of Heitler run `paired-20261104`: 318 completed tasks, 171 qualified task selections, 147 no-candidate outcomes, 25 selected ranges `[0,N]` through N=24, and zero unresolved checks. The task counts are not counts of individual degree/grid probes. The array's longest task took 26:43:36 and final aggregation took 00:02:55; these are wall times, not total CPU cost. Full checkpoints remain at `/export/home/yanlongxiang/fast-boys-additive/runs/paired-20261104` on Heitler.

The numerical identity is `8b3bc332afa8b3aa26856e5aab5de3c3aea6fd1d4be3e148fede633f3537d8e2`. The downloaded summary SHA-256 is `b38973cbecd92d340d0b2fee6e0eeab4dc46c6e672f048dde0b7c5a9c0a3e1ca`. `config.json`, `identity.json`, and `producer/workflow/additive/` preserve the exact configuration and Python producer sources, independently of subsequent implementation changes. The producer environment used Python 3.12.15, gmpy2 2.3.2, MPFR 4.2.2, GMP 6.3.0, and NumPy 2.2.6. `producer/workflow/additive/environment.yml` records the pinned numerical dependencies.

The one-ULP gate is sampled against directed reference enclosures; it is not a continuous-domain proof or a global optimality claim. Main and tail share order-dependent Taylor degrees and have a combined 1 MiB budget per configured range. Each tail stores materialized complete-integral coefficients, normalized to `[1,4)`, and uses exact exponent scaling with gradual underflow. The main interval is `[0,C]`; the tail interval is `(C,DBL_MAX]`. Frozen canonical payload hashes identify the coefficients and unsigned next-up corrections independently of the emitted interleaved layout.

Regenerate the current CUDA and SIMD headers from the repository root, without repeating selection:

```sh
python -m workflow.additive.headers data/numerical/paired-1ulp/summary.json --output .work/paired-generated/include
python -m workflow.additive.simd_headers --include .work/paired-generated/include
```

Generation checks both canonical payload hashes. The current emitters/runtime are intentionally separate from the archived numerical producer; `include/manifest.json` and `include/simd-manifest.json` identify emitted data and implementation sources. Regeneration under another Python environment is acceptable only when every frozen payload hash matches. The source snapshot predates review fixes to the far-tail qualifier's domain guard, QUICK conformance checker, and diagnostic replay imports; these fixes do not change arithmetic used in this completed search.

To repeat numerical construction rather than header emission, use the archived producer in its pinned environment and the original `config.json`. From this directory:

```sh
PYTHONPATH="$PWD/producer" python -m workflow.additive.cluster --repo "$PWD/producer" --config "$PWD/config.json" --output /absolute/path/to/new-run --python /absolute/path/to/pinned/python --nodes c021,c022,c023,c024,c025,c026,c027,c028 --submit
```

This launches a new search; it is not required to consume these results. The removed fixed-domain summary and shared compact-tail archive remain available in Git at `ab6b87f:data/numerical/`. Historical standalone materialized-tail diagnostics require that historical archive and catalog; they do not describe this selected implementation.

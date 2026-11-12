# Vikhamar-Sandberg--Repisky minimax Boys function

This is a Highway implementation of Algorithm 1 from Rasmus
Vikhamar-Sandberg and Michal Repisky, "Efficient Boys function evaluation
using minimax approximation," *J. Chem. Phys.* **164**, 154111 (2026),
<https://doi.org/10.1063/5.0316073>.

The implementation uses the paper's regions, rational approximations, and
recurrences directly. Its SIMD algorithm is expressed with Highway. The paper
used its compiler/OpenACC math implementation. This project independently
chooses glibc libmvec for vector `exp` on GCC/x86: `exp` calls its 2-, 4-, or
8-lane entry point directly, while a one-lane tag uses scalar libm. This is not
the authors' math runtime and is not claimed to reproduce its performance.
The interface accepts a Highway tag and vector and returns the same vector
type:

```cpp
namespace hn = hwy::HWY_NAMESPACE;
const hn::CappedTag<double, 4> d;
const auto values =
    fast_boys::benchmark::vikhamar_sandberg_repisky::boys<24>(d, x);
```

Changing the tag changes the tested vector length without an adapter. The
correctness driver exercises caps of 1, 2, 4, and 8 lanes. The paper guarantees
maximum absolute error `5e-14` for orders through 32.

Algorithm 1 selects one of three regions for each input. A homogeneous SIMD
vector therefore executes only that region's rational approximation and
recurrence. For a vector whose lanes cross region boundaries, Highway has no
masked form of every required operation (notably the libmvec `exp` call), so
the implementation substitutes safe in-domain inputs, evaluates all three
candidate paths, and blends the outputs lane by lane. This mixed-lane policy is
a property of this Highway port, not a claim made by the authors.

Region C uses the paper's semi-infinite-interval expression and asymptotic
recurrence. The common library benchmark covers `x` through 60, so this is also
the method used beyond the `x` range emphasized by the authors' performance
experiments; no external large-`x` method is substituted.

`source/coefficients.h` is generated from the checked-in publisher Appendix D
HTML beside the generator:

```text
benchmark/third_party_boys_impl/vikhamar_sandberg_repisky_minimax/source/
APPENDIX D: COEFFICIENTS OF MINIMAX APPROXIMATIONS OF BOYS FUNCTIONS.html
```

Regenerate it from the repository root with:

```sh
python3 \
  benchmark/third_party_boys_impl/vikhamar_sandberg_repisky_minimax/source/generate_coefficients.py \
  'benchmark/third_party_boys_impl/vikhamar_sandberg_repisky_minimax/source/APPENDIX D: COEFFICIENTS OF MINIMAX APPROXIMATIONS OF BOYS FUNCTIONS.html' \
  benchmark/third_party_boys_impl/vikhamar_sandberg_repisky_minimax/source/coefficients.h
```

The article and its tabulated coefficients are published under CC BY 4.0. The
authors' ancillary build uses `-O3 -fast -acc` with nvc and
`-O3 -ffast-math -fopenacc` with GCC. This explicit Highway implementation
does not use OpenACC; its private flags retain the documented GCC optimization
and fast-math policy and select the benchmark host ISA:

```text
-O3 -ffast-math -march=<FAST_BOYS_BENCHMARK_ARCHITECTURE>
```

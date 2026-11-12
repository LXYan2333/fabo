# Laikov global approximation

This target integrates Dimitri N. Laikov, "Global approximation to the Boys
functions for vectorized computation," *J. Chem. Phys.* **163**, 024104
(2025), <https://doi.org/10.1063/5.0275063>.

The publisher's supplementary C source and a saved copy of Table I are kept
unchanged under `source/`. The supplied program is a scalar test implementation;
the paper states that the dataset can generate fully unwound code that can be
vectorized. This target translates the author's double-precision root-factor
algorithm (`t:2 z:2 c:-2`) from `t_fpn.c` to Highway. The adapter retains the
author's coefficient selection and binary128-to-binary64 conversion from
`cpqn2` in `t_fn.c`.

The Highway tag controls the native vector length:

```cpp
namespace hn = hwy::HWY_NAMESPACE;
const hn::CappedTag<double, 4> d;
const auto values = fast_boys::benchmark::laikov::boys<24>(d, x);
```

Table I reports finite-precision maximum relative errors as negative binary
logarithms. The correctness driver tests each requested order against its
reported `epsilon_bar_n` value over the project benchmark domain `0 <= x <=
31` for caps of 1, 2, 4, and 8 lanes. It also reports the worst absolute error
for comparison with other targets.

The supplied makefile uses `gcc -O2`; the coefficient library and Highway
caller receive `-O2` privately. The benchmark additionally selects its
explicitly selected benchmark architecture. SIMD operations are explicit
Highway calls and vector `exp` uses the matching glibc libmvec ABI, so this does
not rely on automatic loop vectorization on `exp`.

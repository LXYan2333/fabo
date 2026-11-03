"""Direct fixed-order bindings; no per-call backend dispatch."""
BACKENDS = ('original', 'fabo', 'libintx', 'vsr', 'laikov')

def header(n, backend):
    if backend not in BACKENDS[1:] or not 0 <= n <= 8:
        raise ValueError('unsupported backend/order')
    lines = ['#pragma once', '#include "fast_boys/simd_config.h"',
             '#include "hwy/highway.h"', '#include "simint/vectorization/vectorization.h"',
             'static_assert(SIMINT_SIMD_LEN == 8);']
    if backend == 'fabo':
        lines += ['#include "fast_boys/selected_simd.h"',
                  f'#include "fast_boys/models/data_0_{n}.h"', '#include "fast_boys/models/tail_data.h"', '#include "shared_tail.h"']
    elif backend == 'libintx':
        lines += ['#include <libintx/simd.h>', '#include <libintx/boys/chebyshev.h>', '#include <cstring>']
    else:
        folder = 'vikhamar_sandberg_repisky_minimax/source' if backend == 'vsr' else 'laikov_global_approximation'
        lines += [f'#include "{folder}/boys.h"']
    lines += [f'namespace fabo_nw_{backend}_{n} {{', 'namespace hn=hwy::HWY_NAMESPACE;']
    if backend == 'libintx':
        lines += [f'inline const auto& evaluator=libintx::boys::chebyshev<{n}>();']
    if backend == 'fabo':
        lines += ['namespace fb=fast_boys::simd::HWY_NAMESPACE;',
                  f'inline constexpr fast_boys::BoysTable<fast_boys::selected::Model<{n}>> table;',
                  'inline constexpr auto& tail = fast_boys_nw_shared_tail::table;']
    lines += ['HWY_INLINE void evaluate(SIMINT_DBLTYPE x, SIMINT_DBLTYPE* __restrict__ out) {']
    if backend == 'fabo':
        names=','.join(f'f{i}' for i in range(n+1))
        lines += [f'fb::V {names};', 'const auto e=fb::make_evaluator(table.view(),tail.view());',
                  f'e.template evaluate<0,{n}>(fb::V{{x}},{names});']
        lines += [f'out[{i}]=f{i}.raw;' for i in range(n+1)]
    elif backend == 'libintx':
        lines += ['using V=libintx::simd_t<double>;', 'static_assert(sizeof(V)==sizeof(x));',
                  'V vx(x);', f'V values[{n+1}]{{}};',
                  f'evaluator.template compute<{n}>(vx,values);']
        for i in range(n+1):
            lines += [f'const auto r{i}=std::experimental::__data(values[{i}]);',
                      f'std::memcpy(out+{i}, &r{i}, sizeof(SIMINT_DBLTYPE));']
    else:
        ns='vikhamar_sandberg_repisky' if backend=='vsr' else 'laikov'
        lines += ['const hn::ScalableTag<double> d;',
                  f'auto values=fast_boys::benchmark::{ns}::boys<{n}>(d,hn::VFromD<decltype(d)>{{x}});']
        lines += [f'out[{i}]=values[{i}].raw;' for i in range(n+1)]
    return '\n'.join(lines+['}', '}', ''])

SHARED_TAIL = '''#pragma once
#include "fast_boys/models/tail_data.h"
namespace fast_boys_nw_shared_tail {
inline constexpr fast_boys::BoysTable<fast_boys::selected::Tail> table;
}
'''

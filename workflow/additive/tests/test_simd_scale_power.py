"""Incremental tail powers preserve absolute orders, including subsets."""
import subprocess

import pytest

from workflow.additive.simd_headers import scale_power_next, scale_power_setup
from workflow.additive.tests.test_simd_portability import compile_source
from workflow.additive.tests.simd_support import require_host_isa


@pytest.mark.parametrize('flags', [
    ['-DHWY_COMPILE_ONLY_SCALAR'],
    ['-DHWY_COMPILE_ONLY_STATIC', '-march=haswell', '-maes'],
    ['-DHWY_COMPILE_ONLY_STATIC', '-march=icelake-server'],
])
def test_incremental_scale_powers(tmp_path, flags):
    require_host_isa(flags, execute=True)
    functions = []
    calls = []
    for model_first, first, last in [(0, 0, 0), (0, 0, 24), (0, 7, 24),
                                    (0, 24, 24), (2, 2, 5), (2, 3, 4)]:
        name = f'check_{model_first}_{first}_{last}'
        body = scale_power_setup(model_first)
        for n in range(model_first, 25):
            body += [f' if constexpr(First<={n} && {n}<=Last) {{',
                     f' if(hn::GetLane(scale_power)!={2*n+1}*scalar_k) return false;',
                     ' }', scale_power_next(n)]
        functions.append(f'''
bool {name}(unsigned scalar_k) {{
 namespace fb=fast_boys::simd::HWY_NAMESPACE;
 constexpr int First={first},Last={last};
 const auto k=fb::detail::Ops<fb::D>::SU(scalar_k);
 {chr(10).join(body)}
 return true;
}}
''')
        calls.append(f'if(!{name}(k)) return 1;')
    source = '''
#include "fast_boys/simd.h"
namespace hn=hwy::HWY_NAMESPACE;
''' + '\n'.join(functions) + '''
int main() {
 for(unsigned k=0;k<=511;++k) {
''' + '\n'.join(calls) + '''
 }
}
'''
    exe = compile_source(tmp_path, source, flags=flags, link=True)
    subprocess.run([exe], check=True)

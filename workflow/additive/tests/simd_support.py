"""Host ISA checks for native (not cross-compiled) SIMD test executables."""
from pathlib import Path
import platform

import pytest


WESTMERE = frozenset('sse2 ssse3 sse41 sse42 popcnt aes pclmulqdq'.split())
HASWELL = WESTMERE | frozenset('avx avx2 fma f16c bmi1 bmi2'.split())
ICELAKE = HASWELL | frozenset('avx512f avx512dq avx512cd avx512bw avx512vl avx512ifma avx512vbmi avx512vbmi2 avx512vnni avx512bitalg avx512vpopcntdq gfni vaes vpclmulqdq'.split())
REQUIRED = {'x86-64': frozenset({'sse2'}), 'westmere': WESTMERE,
            'haswell': HASWELL, 'icelake-server': ICELAKE}


def require_host_isa(flags, *, execute):
    arch = next((flag[7:] for flag in flags if flag.startswith('-march=')), None)
    if arch not in REQUIRED:
        return  # Scalar/default-host or an explicitly cross-compiled target.
    if platform.machine().lower() not in ('x86_64', 'amd64', 'i386', 'i686'):
        pytest.skip('x86-specific test requires an x86 host compiler')
    if not execute:
        return  # Assembly/compile-only tests need no matching runtime CPU.
    path = Path('/proc/cpuinfo')
    if not path.exists():
        pytest.skip('cannot verify OS-enabled x86 ISA flags on this host')
    # Intersect logical CPUs so a migrating test cannot reach a weaker core.
    flags_per_cpu = [set(line.split(':', 1)[1].replace('_', '').split())
                     for line in path.read_text().splitlines()
                     if line.split(':', 1)[0].strip() == 'flags']
    if not flags_per_cpu:
        pytest.skip('CPU ISA flags unavailable')
    missing = REQUIRED[arch] - set.intersection(*flags_per_cpu)
    if missing:
        pytest.skip('unsupported runtime ISA: ' + ', '.join(sorted(missing)))

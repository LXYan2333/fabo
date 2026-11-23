"""Check host optimization barriers without executing FMA instructions."""
import platform
from pathlib import Path
import shutil
import subprocess

import pytest


INCLUDE = Path(__file__).resolve().parents[3] / 'include'
pytestmark = pytest.mark.skipif(platform.machine() != 'x86_64', reason='x86 codegen probe')
SOURCE = r'''
#include "fast_boys/detail/binary64.h"
using O = fast_boys::detail::Binary64;
extern "C" double separate(double a, double b, double c) {
  return O::add(O::mul(a, b), c);
}
extern "C" double fused(double a, double b, double c) {
  return O::fma(a, b, c);
}
'''


@pytest.mark.parametrize('compiler', ['g++', 'clang++'])
@pytest.mark.parametrize('mode', ['-ffp-contract=fast', '-ffast-math'])
def test_scalar_fence_codegen(compiler, mode):
    if not shutil.which(compiler):
        pytest.skip(f'{compiler} unavailable')
    asm = subprocess.run([compiler, '-x', 'c++', '-std=c++17', '-O3', '-mfma',
                          mode, '-I', str(INCLUDE), '-S', '-o', '-', '-'],
                         input=SOURCE, text=True, capture_output=True, check=True).stdout
    separate = asm.split('separate:', 1)[1].split('ret', 1)[0]
    fused = asm.split('fused:', 1)[1].split('ret', 1)[0]
    assert 'vmulsd' in separate and 'vaddsd' in separate and '%rsp' not in separate
    assert 'vfmadd' in fused


@pytest.mark.parametrize('compiler', ['g++', 'clang++'])
def test_extended_precision_build_is_rejected(compiler):
    if not shutil.which(compiler):
        pytest.skip(f'{compiler} unavailable')
    cmd = [compiler, '-x', 'c++', '-std=c++17', '-mfpmath=387', '-fsyntax-only']
    # A driver named g++ can be Clang. Check the requested evaluation mode
    # without any FABO headers, so a FABO regression cannot trigger the skip.
    probe = subprocess.run([*cmd, '-'], input='#include <cfloat>\nstatic_assert(FLT_EVAL_METHOD == 2);',
                           text=True, capture_output=True)
    if probe.returncode:
        pytest.skip(f'{compiler} does not select extended precision with -mfpmath=387')
    result = subprocess.run([*cmd, '-I', str(INCLUDE), '-'],
                            input=SOURCE, text=True, capture_output=True)
    assert result.returncode and 'FABO requires binary64 intermediate precision' in result.stderr

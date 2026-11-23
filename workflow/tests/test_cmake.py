"""Package-consumer tests; no numerical search or benchmark is run."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run(*args, ok=True):
    result = subprocess.run([str(a) for a in args], text=True, capture_output=True)
    if ok:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
    return result.stdout + result.stderr


@pytest.fixture(autouse=True)
def require_cmake():
    if not shutil.which('cmake'):
        pytest.skip('CMake required')


@pytest.fixture(scope='module')
def highway(tmp_path_factory):
    source = Path(os.environ.get('FABO_HIGHWAY_ROOT', ROOT / 'third_party/workflow/highway'))
    if not (source / 'CMakeLists.txt').exists():
        pytest.skip('Set FABO_HIGHWAY_ROOT to a Highway >=1.4 source tree')
    root = tmp_path_factory.mktemp('hwy-package')
    run('cmake', '-S', source, '-B', root / 'build',
        f'-DCMAKE_INSTALL_PREFIX={root / "install"}', '-DCMAKE_BUILD_TYPE=Release',
        '-DHWY_ENABLE_TESTS=OFF', '-DHWY_ENABLE_EXAMPLES=OFF', '-DHWY_ENABLE_CONTRIB=OFF')
    run('cmake', '--build', root / 'build', '--parallel', '2')
    run('cmake', '--install', root / 'build')
    return source, root / 'install'


CORE = '''#include "fast_boys/selected.h"
#include "fast_boys/models/data_0_4.h"
#include "fast_boys/scalar.h"
static constexpr fast_boys::BoysTable<fast_boys::selected::Model<4>> table{};
int main() {
  auto full = fast_boys::scalar::evaluate<0,4>(table.view(), 0.);
  auto subset = fast_boys::scalar::evaluate<2,3>(table.view(), 0.);
  static_assert(std::is_same_v<decltype(full), std::array<double,5>>);
  static_assert(std::is_same_v<decltype(subset), std::array<double,2>>);
  if (full[0] != 1. || subset[0] != 1./5 || subset[1] != 1./7 ||
      subset[0] != full[2] || subset[1] != full[3]) return 1;
  volatile double x = 1. + 0x1p-27, y = 1. - 0x1p-27;
  return fast_boys::detail::Binary64::fma(x, y, -1.) != -0x1p-54;
}
'''
SIMD = '''#include "fast_boys/simd_config.h"
#include "fast_boys/selected_simd.h"
#include "fast_boys/models/data_0_0.h"
static constexpr fast_boys::BoysTable<fast_boys::selected::Model<0>> table{};
HWY_BEFORE_NAMESPACE();
namespace smoke { namespace HWY_NAMESPACE {
namespace fb = fast_boys::simd::HWY_NAMESPACE;
namespace hn = hwy::HWY_NAMESPACE;
int check() {
  fb::V a, b;
  fb::make_evaluator<true>(table.view()).evaluate<0,0>(fb::D(), hn::Zero(fb::D()), a);
  fb::make_evaluator<false>(table.view()).evaluate<0,0>(fb::D(), hn::Zero(fb::D()), b);
  return !(hn::AllTrue(fb::D(), hn::Eq(a,b)) && hn::GetLane(a) == 1.0);
}
} }
HWY_AFTER_NAMESPACE();
int main() { return smoke::HWY_NAMESPACE::check(); }
'''


def consumer(root, setup, target, source, *, prefixes=(), execute=True):
    root.mkdir()
    (root / 'main.cc').write_text(source)
    (root / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.23)
project(consumer LANGUAGES CXX)
{setup}
add_executable(smoke main.cc)
target_link_libraries(smoke PRIVATE {target})
''')
    run('cmake', '-S', root, '-B', root / 'build',
        '-DCMAKE_PREFIX_PATH=' + ';'.join(map(str, prefixes)))
    run('cmake', '--build', root / 'build', '--parallel', '2')
    if execute:
        run(root / 'build/smoke')


def test_core_install_and_header_inventory(tmp_path):
    build, prefix = tmp_path / 'build', tmp_path / 'install'
    run('cmake', '-S', ROOT, '-B', build, '-DFABO_ENABLE_SIMD=OFF',
        f'-DCMAKE_INSTALL_PREFIX={prefix}')
    run('cmake', '--install', build)
    expected = {p.relative_to(ROOT / 'include') for p in (ROOT / 'include').rglob('*')
                if p.suffix in ('.h', '.cuh')}
    actual = {p.relative_to(prefix / 'include') for p in (prefix / 'include').rglob('*')
              if p.is_file()}
    assert actual == expected
    for relative in expected:
        assert (prefix / 'include' / relative).read_bytes() == (ROOT / 'include' / relative).read_bytes()
    moved = tmp_path / 'relocated'
    prefix.rename(moved)
    consumer(tmp_path / 'consumer', 'find_package(fabo CONFIG REQUIRED)',
             'fabo::fabo', CORE, prefixes=[moved])
    result = run('cmake', '-S', tmp_path / 'consumer', '-B', tmp_path / 'missing',
                 f'-DCMAKE_PREFIX_PATH={moved}', '-DCMAKE_DISABLE_FIND_PACKAGE_fabo=TRUE', ok=False)
    assert 'REQUIRED' in result
    (tmp_path / 'consumer/CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.23)
project(missing LANGUAGES CXX)
find_package(fabo CONFIG REQUIRED COMPONENTS cuda)
''')
    assert 'cuda' in run('cmake', '-S', tmp_path / 'consumer', '-B', tmp_path / 'missing-component',
                         f'-DCMAKE_PREFIX_PATH={moved}', ok=False)


def test_simd_package_and_parent_target(tmp_path, highway):
    source, hwy_prefix = highway
    consumer(tmp_path / 'parent', f'''set(HWY_ENABLE_TESTS OFF CACHE BOOL "" FORCE)
set(HWY_ENABLE_EXAMPLES OFF CACHE BOOL "" FORCE)
set(HWY_ENABLE_CONTRIB OFF CACHE BOOL "" FORCE)
set(HWY_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
add_subdirectory("{source}" highway)
if(NOT TARGET hwy::hwy)
  add_library(hwy::hwy ALIAS hwy)
endif()
add_subdirectory("{ROOT}" fabo)
''', 'fabo::simd', SIMD)
    run('cmake', '-S', ROOT, '-B', tmp_path / 'build',
        f'-DCMAKE_PREFIX_PATH={hwy_prefix}', f'-DCMAKE_INSTALL_PREFIX={tmp_path / "install"}')
    run('cmake', '--install', tmp_path / 'build')
    moved = tmp_path / 'relocated'
    (tmp_path / 'install').rename(moved)
    consumer(tmp_path / 'installed', 'find_package(fabo CONFIG REQUIRED COMPONENTS simd)',
             'fabo::simd', SIMD, prefixes=[moved, hwy_prefix])
    # A SIMD-enabled installation still permits dependency-free core use.
    consumer(tmp_path / 'core', 'find_package(fabo CONFIG REQUIRED)',
             'fabo::fabo', CORE, prefixes=[moved])
    check_missing_backend(tmp_path, moved, 'simd', 'hwy')


def check_missing_backend(tmp_path, prefix, component, dependency):
    source = tmp_path / f'optional-{component}'
    consumer(source, f'''set(CMAKE_DISABLE_FIND_PACKAGE_{dependency} TRUE)
find_package(fabo CONFIG REQUIRED OPTIONAL_COMPONENTS {component})
if(fabo_{component}_FOUND OR TARGET fabo::{component})
  message(FATAL_ERROR "unexpected backend without its dependency")
endif()
''', 'fabo::fabo', CORE, prefixes=[prefix])
    with (source / 'CMakeLists.txt').open('a') as out:
        out.write(f'find_package(fabo CONFIG REQUIRED COMPONENTS {component})\n')
    result = run('cmake', '-S', source, '-B', source / 'build', ok=False)
    assert f'FABO {component} requires' in result


def test_dispatch_with_scalar_fallback(tmp_path, highway):
    _, prefix = highway
    consumer(tmp_path / 'dispatch', f'''find_package(hwy 1.4 CONFIG REQUIRED)
add_subdirectory("{ROOT}" fabo)
include_directories("${{CMAKE_CURRENT_SOURCE_DIR}}")
''', 'fabo::simd', r'''
#include "fast_boys/simd_config.h"
#undef HWY_TARGET_INCLUDE
#define HWY_TARGET_INCLUDE "main.cc"
#include "hwy/foreach_target.h"
#include "fast_boys/selected_simd.h"
#include "fast_boys/models/data_0_4.h"
HWY_BEFORE_NAMESPACE();
namespace app { namespace HWY_NAMESPACE {
namespace fb = fast_boys::simd::HWY_NAMESPACE;
namespace hn = hwy::HWY_NAMESPACE;
int64_t Run(double x, double* result) {
  using M = fast_boys::selected::Model<4>;
  static constexpr fast_boys::BoysTable<M> table{};
  fb::V a, b;
  fb::make_evaluator(table.view()).evaluate<2,3>(fb::D(), hn::Set(fb::D(), x), a, b);
  result[0] = hn::GetLane(a);
  result[1] = hn::GetLane(b);
  return HWY_TARGET;
}
} }
HWY_AFTER_NAMESPACE();
#if HWY_ONCE
namespace app {
HWY_EXPORT(Run);
int Check() {
  const auto targets = hwy::SupportedAndGeneratedTargets();
  for (auto target : targets) {
    hwy::SetSupportedTargetsForTest(target);
    for (double x : {0., 0.125, 50., 1e100}) {
      double actual[2];
      if (HWY_DYNAMIC_DISPATCH(Run)(x, actual) != target) return 1;
      static constexpr fast_boys::BoysTable<fast_boys::selected::Model<4>> table{};
      const auto expected = fast_boys::scalar::evaluate<2,3>(table.view(), x);
      if (std::memcmp(actual, expected.data(), sizeof(actual))) return 2;
    }
  }
  return 0;
}
}
int main() { return app::Check(); }
#endif
''', prefixes=[prefix])


def test_missing_dependency(tmp_path):
    result = run('cmake', '-S', ROOT, '-B', tmp_path / 'build',
                 '-DCMAKE_DISABLE_FIND_PACKAGE_hwy=TRUE', ok=False)
    assert 'hwy' in result and 'REQUIRED' in result


def test_cuda_compile(tmp_path):
    toolkit = os.environ.get('CUDAToolkit_ROOT')
    nvcc = str(Path(toolkit) / 'bin/nvcc') if toolkit else shutil.which('nvcc')
    if not nvcc or not Path(nvcc).exists():
        pytest.skip('Set CUDAToolkit_ROOT for CUDA compile/link smoke test')
    source = tmp_path / 'consumer'
    source.mkdir()
    (source / 'main.cu').write_text('''#include "fast_boys/cuda.cuh"
#include "fast_boys/cuda/upload.cuh"
#include "fast_boys/selected.h"
#include "fast_boys/models/data_0_4.h"
using M = fast_boys::selected::Model<4>;
__global__ void kernel(fast_boys::TableView<M> table, double x, double* out) {
  fast_boys::cuda::make_evaluator(table).evaluate<0,4>(x, out);
}
void upload(const fast_boys::BoysTable<M>& table) {
  fast_boys::cuda::DeviceTable<M> device(table);
}
int main() { return 0; }
''')
    (source / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.23)
project(smoke LANGUAGES CXX CUDA)
set(FABO_ENABLE_SIMD OFF CACHE BOOL "" FORCE)
set(FABO_ENABLE_CUDA ON CACHE BOOL "" FORCE)
set(FABO_ENABLE_INSTALL ON CACHE BOOL "" FORCE)
add_subdirectory("{ROOT}" fabo)
add_executable(smoke main.cu)
target_link_libraries(smoke PRIVATE fabo::cuda)
''')
    run('cmake', '-S', source, '-B', tmp_path / 'build', f'-DCMAKE_CUDA_COMPILER={nvcc}',
        '-DCMAKE_CUDA_ARCHITECTURES=80', f'-DCMAKE_INSTALL_PREFIX={tmp_path / "install"}')
    run('cmake', '--build', tmp_path / 'build', '--parallel', '2')
    run('cmake', '--install', tmp_path / 'build')
    moved = tmp_path / 'relocated'
    (tmp_path / 'install').rename(moved)
    (source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.23)
project(smoke LANGUAGES CXX CUDA)
find_package(fabo CONFIG REQUIRED COMPONENTS cuda)
add_executable(smoke main.cu)
target_link_libraries(smoke PRIVATE fabo::cuda)
''')
    run('cmake', '-S', source, '-B', tmp_path / 'installed-build',
        f'-DCMAKE_CUDA_COMPILER={nvcc}', '-DCMAKE_CUDA_ARCHITECTURES=80',
        f'-DCMAKE_PREFIX_PATH={moved}')
    run('cmake', '--build', tmp_path / 'installed-build', '--parallel', '2')
    check_missing_backend(tmp_path, moved, 'cuda', 'CUDAToolkit')

"""Checked, energy-only Boys replacement in a disposable pinned QUICK tree."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
VARIANTS = ('official', 'fabo_additive')
PIN = '730af1533da8912ce5874852561e63b5907f9d7a'


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('QUICK patch context changed: '+old[:100])
    return text.replace(old, new)


def patch(root, variant, probe=False, training=False):
    root = Path(root).resolve()
    if variant not in VARIANTS:
        raise ValueError('unsupported variant: '+variant)
    if probe and training:
        raise ValueError('choose fixed-density probe or SCF training, not both')
    if root == (ROOT/'third_party/quick').resolve():
        raise ValueError('do not patch the upstream submodule; prepare a disposable tree')
    if (root/'fabo-variant.json').exists():
        raise ValueError('already patched; use a fresh QUICK tree')
    files = {}

    def edit(name, old, new, count=1):
        text = files.get(name)
        if text is None:
            text = (root/name).read_text()
        files[name] = replace(text, old, new, count)

    # Common language mode, including the official control; retain QUICK's
    # arithmetic/architecture flags, removing only earlier C++ standard flags.
    cmake = 'src/gpu/cuda/CMakeLists.txt'
    marker = "#sadly FindCUDA doesn't support OBJECT libraries, so we have to use a static cuda_add_library"
    prelude = '''set(CMAKE_CXX_STANDARD 17)
list(FILTER CUDA_NVCC_FLAGS EXCLUDE REGEX "^-std=")
list(APPEND CUDA_NVCC_FLAGS "-std=c++17")
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/..")
'''
    edit(cmake, marker, prelude+'\n'+marker)
    manifest = {'schema': 1, 'variant': variant, 'quick_revision': PIN,
                'probe': probe, 'scf_training': training,
                'scope': 'GPU two-electron energy Boys calls; gradients and one-electron paths unchanged'}
    copies = {}
    if variant == 'fabo_additive':
        numerical = json.loads((ROOT/'include/manifest.json').read_text())
        for n in (4, 8, 12):
            model = numerical['models'][f'0-{n}']
            record = model['record']
            if record['first'] != 0 or record['last'] != n or record['status'] != 'qualified':
                raise ValueError('invalid selected QUICK model')
        if not numerical['tail']['matches_main_target']:
            raise ValueError('tail target differs from main model')
        manifest['numerical_identity'] = numerical['numerical_identity']
        manifest['models'] = {k: numerical['models'][k] for k in ('0-4', '0-8', '0-12')}
        manifest['tail'] = numerical['tail']
        header = 'src/gpu/gpu_get2e_subs.h'
        edit(header, '#include "gpu_fmt.h"', '''#include "gpu_fmt.h"
#include "additive_binding.cuh"
#undef FABO_QUICK_FAMILY_MAX
#if defined(int_sp)
#define FABO_QUICK_FAMILY_MAX 4
#elif defined(int_spd)
#define FABO_QUICK_FAMILY_MAX 8
#else
#define FABO_QUICK_FAMILY_MAX 12
#endif''')
        edit(header, 'FmT(I + J + K + L, AB * CD * ABCD',
             'FaboQuickFmT<FABO_QUICK_FAMILY_MAX>(I + J + K + L, AB * CD * ABCD', 2)
        edit('src/gpu/cuda/gpu_get2e.cu', '#include <cuda.h>',
             '#include <cuda.h>\n#include "../additive_runtime.cuh"')
        edit('src/gpu/cuda/gpu.cu', '#include "gpu.h"',
             '#include "gpu.h"\nextern "C" void fabo_quick_boys_init_();')
        edit('src/gpu/cuda/gpu.cu', '    PRINTDEBUG("FINISH GPU INIT");',
             '    fabo_quick_boys_init_();\n    PRINTDEBUG("FINISH GPU INIT");')
        edit(cmake, marker, 'list(APPEND QUICK_CUDA_SOURCE ../additive_host.cc)\n'+marker)
        for name in ('additive_boys.cuh','additive_binding.cuh','additive_runtime.cuh','additive_host.cc'):
            copies[Path('src/gpu')/name] = HERE/name
        # Lightweight catalog includes every model definition, but only the
        # three family payloads and shared tail enter the host initializer.
        base = ROOT/'include/fast_boys'
        for path in base.rglob('*'):
            if path.is_file() and path.suffix in ('.h','.cuh') and 'models' not in path.relative_to(base).parts:
                copies[Path('src/gpu/fast_boys')/path.relative_to(base)] = path
        model_files = [f'catalog_{numerical["catalog"]["id"]}.h', 'tail_data.h']
        model_files += [f'{m["id"]}/model.h' for m in [*numerical['models'].values(),numerical['tail']]]
        model_files += [f'data_0_{n}.h' for n in (4,8,12)]
        model_files += [f'{m["id"]}/data.h' for m in [*manifest['models'].values(),numerical['tail']]]
        for name in model_files:
            copies[Path('src/gpu/fast_boys/models')/name] = base/'models'/name
    if probe or training:
        edit('src/gpu/cuda/gpu_get2e.cu', '#include <cuda.h>',
             '#include <cuda.h>\n#include "../probe_runtime.h"')
        copies[Path('src/gpu/probe_runtime.h')] = HERE/'probe_runtime.h'
    if training:
        from benchmark.quick.patch_scf_training import patch_training
        patch_training(root, lambda path, old, new: edit(str(path.relative_to(root)), old, new))
    if probe:
        edit('src/main.f90', '    if (quick_method%SAD) SAFE_CALL(getSadGuess(ierr))',
             '''    block
      character(len=32) :: fabo_mode
      call get_environment_variable("FABO_QUICK_MODE", fabo_mode)
      if (len_trim(fabo_mode) > 0) quick_method%SAD = .false.
    end block
    if (quick_method%SAD) SAFE_CALL(getSadGuess(ierr))''')
        edit('src/modules/quick_scf_module.f90', '     done = .false.',
             '''     block
       character(len=32) :: fabo_mode
       call get_environment_variable("FABO_QUICK_MODE", fabo_mode)
       if (len_trim(fabo_mode) > 0) then
         call fabo_probe_iteration(trim(fabo_mode))
         stop 0
       endif
     end block
     done = .false.''')
        edit('src/modules/quick_scf_module.f90', 'end module quick_scf_module',
             (HERE/'probe_iteration.f90').read_text()+'\nend module quick_scf_module')
    # Validate every context/input before touching the destination source.
    manifest['copied_sources'] = {str(dst): hashlib.sha256(src.read_bytes()).hexdigest()
                                  for dst,src in copies.items()}
    for name,text in files.items():
        (root/name).write_text(text)
    for dst,src in copies.items():
        (root/dst).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,root/dst)
    manifest['patched_sources'] = {name: hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()}
    (root/'fabo-variant.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

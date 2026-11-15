"""Generate a local clangd database; not a benchmark build configuration."""

import argparse
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def generate(highway, cuda, *, compiler='clang++-22', cpu_arch='native',
             gpu_arch='sm_120', output=None):
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise ValueError('Clang compiler not found: ' + compiler)
    highway, cuda = Path(highway).resolve(), Path(cuda).resolve()
    if not (highway / 'hwy/highway.h').is_file():
        raise ValueError('Highway root must contain hwy/highway.h')
    # Conda packages use the target include directory; runfile installs use include/.
    cuda_include = next((p for p in (cuda / 'targets/x86_64-linux/include', cuda / 'include')
                         if (p / 'cuda_runtime.h').is_file()), None)
    if cuda_include is None:
        raise ValueError('CUDA runtime headers not found')
    if not (cuda_include / 'curand_mtgp32_kernel.h').is_file():
        raise ValueError('Clang CUDA parsing requires cuRAND headers (Conda: libcurand-dev)')
    common = [compiler_path, '-std=c++17', '-I' + str(ROOT / 'include')]
    cpu_flags = [*common, '-x', 'c++', '-I' + str(highway),
                 '-DHWY_COMPILE_ONLY_STATIC', '-march=' + cpu_arch, '-ffp-contract=off']
    cuda_flags = [*common, '-x', 'cuda', '--cuda-path=' + str(cuda),
                  '--cuda-gpu-arch=' + gpu_arch, '--cuda-device-only',
                  '-I' + str(cuda_include)]
    rows = []

    def add(path, flags):
        rows.append(dict(directory=str(ROOT), file=str(path),
                         arguments=[*flags, '-fsyntax-only', str(path)]))

    add(ROOT / 'tools/clangd/simd.cc', cpu_flags)
    add(ROOT / 'tools/clangd/cuda.cu', cuda_flags)
    # Explicit commands avoid unrelated filename-based guesses on direct opens.
    # Shared .h headers get a CPU context; the CUDA TU also parses them as CUDA.
    for path in sorted((ROOT / 'include/fast_boys').rglob('*')):
        if path.is_file() and path.suffix in ('.h', '.cuh'):
            add(path, cuda_flags if path.suffix == '.cuh' else cpu_flags)
    output = Path(output) if output is not None else ROOT / 'build/compile_commands.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + '\n')
    return output, len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--highway', type=Path, default=ROOT / 'third_party/workflow/highway')
    parser.add_argument('--cuda', type=Path, required=True)
    parser.add_argument('--compiler', default='clang++-22')
    parser.add_argument('--cpu-arch', default='native')
    parser.add_argument('--gpu-arch', default='sm_120')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/compile_commands.json')
    args = parser.parse_args()
    path, count = generate(args.highway, args.cuda, compiler=args.compiler,
                           cpu_arch=args.cpu_arch, gpu_arch=args.gpu_arch, output=args.output)
    print(f'Wrote {count} editor compilation commands to {path}')

# Editor translation units

Open **`simd.cc`** for CPU/Highway diagnostics or **`cuda.cu`** for CUDA diagnostics, then navigate to the relevant header. Both instantiate the `[0,4]` evaluator without embedding its large table initializer. The CUDA file also instantiates the runtime-last-order overload. These files are parsing/instantiation examples, not executables or performance benchmarks.

Generate the ignored local compilation database from the repository root:

```sh
.venv/bin/python -m workflow.scripts.generate_compile_commands \
  --highway /path/to/highway \
  --cuda /path/to/cuda-toolkit \
  --compiler clang++-22 --cpu-arch native --gpu-arch sm_120
```

The generator writes `build/compile_commands.json`, which clangd discovers automatically from this source tree. The tracked `.clangd` adds the editor-only `__CLANGD__` definition; it does not override database discovery. The generator replaces any old database at its output path, so use a separate build directory for unrelated projects. If using `--output` outside the standard discovery locations, configure clangd's `--compile-commands-dir` accordingly. Paths are machine-specific and the generated database is not committed. No library, benchmark, numerical model, or table is rebuilt. Restart the clangd language server after replacing an old database.

Clang's CUDA parser needs the CUDA runtime, driver, CCCL, and cuRAND headers (including `curand_mtgp32_kernel.h`), even though FABO does not call cuRAND. For the Conda CUDA installation, the latter is provided by `libcurand-dev`. The generator accepts the Conda `targets/x86_64-linux/include` layout as well as a conventional `include` directory. It uses Clang CUDA flags, not an NVCC command or fake CUDA preprocessor definitions. A toolkit newer than Clang's supported range may produce a version warning; Clang parsing does not replace NVCC compilation or device tests.

Explicit entries give `.cuh` headers the CUDA device context and `.h` headers the CPU context when opened directly. Shared `.h` files are also parsed in CUDA context through `cuda.cu`. One clangd header view cannot simultaneously represent every ISA and host/device macro configuration. Select a different CPU/GPU target by regenerating the database; these editor flags do not change the archived experimental builds. Large `data.h` payloads are not included by the two editor translation units.

Check the setup without linking or running code:

```sh
clangd-22 --check=tools/clangd/simd.cc
clangd-22 --check=tools/clangd/cuda.cu
clangd-22 --check=include/fast_boys/detail/cuda/arithmetic.cuh
```

Clangd's direct-header `--check` also exercises refactoring actions. With CUDA attribute macros, Clangd 22 can report `tweak: DefineOutline` or `tweak: SpecialMembers` failures even when parsing succeeds; these are refactoring-test failures, not C++ diagnostics. The two source-file checks above are the primary setup smoke tests.

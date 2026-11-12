# Comparator sources used by the FABO comparisons

This index covers the CPU and GPU comparators used in the current paper. The custom ports, bindings, and required coefficient snapshots are tracked on `main`; readers do not need the private working directories or the `legacy-v3` branch. These are benchmark integrations, not part of the public FABO evaluator API.

## CPU SIMD

| Implementation | Port or upstream evaluator | Integration and data |
| --- | --- | --- |
| VSR | [Highway port](cpu/vikhamar_sandberg_repisky_minimax/source/boys.h) | [Coefficient header](cpu/vikhamar_sandberg_repisky_minimax/source/coefficients.h), [coefficient extractor](cpu/vikhamar_sandberg_repisky_minimax/source/generate_coefficients.py), and the saved supplementary coefficient appendix in the same directory |
| Laikov | [Highway port](cpu/laikov_global_approximation/boys.h) | [Coefficient adapter](cpu/laikov_global_approximation/adapter.c), [adapter interface](cpu/laikov_global_approximation/adapter.h), and the author's C sources/coefficient arrays under [source/](cpu/laikov_global_approximation/source/) |
| LibintX | Pinned upstream `third_party/libintx/src/libintx/boys/chebyshev.h`; no separate Highway port | [NWChem bindings](../nwchem/bindings.py) and the standalone adapter generator below |
| Original Simint | Pinned upstream generator's `skel/simint/boys/boys.h` | [Simint replacement hook](../nwchem/simint_binding.py); upstream retrieval is described below |
| FABO | [SIMD evaluator and models](../../include/fast_boys/) | [NWChem bindings](../nwchem/bindings.py) |

The common standalone CPU/CUDA accuracy adapter generator is [workflow/library_accuracy/suite.py](../../workflow/library_accuracy/suite.py). NWChem build/replay instructions are in [workflow/NWCHEM_FIXED_DENSITY.md](../../workflow/NWCHEM_FIXED_DENSITY.md); standalone build settings and dependency revisions are in [workflow/library_accuracy/README.md](../../workflow/library_accuracy/README.md). The VSR/Laikov CPU paths are include roots beneath `benchmark/ports/cpu/`; these ports use Highway and x86 vector math from libmvec, not a portable scalar replacement for those dependencies.

### Exact retained CPU snapshot

All 23 regular files in `cpu/` (excluding the new manifest) are unchanged copies from commit `728ec72e9dae8b3897265500860e9340139c70b1`, originally under `benchmark/third_party_boys_impl/`. [cpu/manifest.json](cpu/manifest.json) gives their SHA-256 hashes and original path prefix. This is the historical source identity, not a claim that every experiment used the current driver or compiler.

The snapshot preserves its original README/CMake files for provenance; their legacy harness instructions are not the active application build recipe. Use the workflow documents linked above. The old optional VSR `source/minimax` fitting-tool submodule is not required to compile or run the supplied coefficients and is not vendored here; its URL and pinned revision are retained in the manifest. No fitting or numerical search is needed.

Both CPU workflows now copy this checked-in snapshot through [workflow/comparator_ports.py](../../workflow/comparator_ports.py), verifying its checksums. The historical `legacy/...` directory name in prepared NWChem runs is retained for layout compatibility; it no longer requires a legacy Git checkout. Explicit archived `ports_snapshot` overrides in the standalone builder retain their existing meaning.

## CUDA / QUICK

These files were already tracked and remain beside the QUICK integration:

| Implementation | Port | Coefficients, upstream source, and checks |
| --- | --- | --- |
| VSR | [vsr_boys.h](../quick/vsr_boys.h) | [vsr_coefficients.h](../quick/vsr_coefficients.h), [vsr_generate.py](../quick/vsr_generate.py), [supplied source and provenance](../../third_party/vsr/README.md), [conformance test](../quick/vsr_conformance.cu) |
| LibintX | [libintx_boys.h](../quick/libintx_boys.h) | [libintx_table.cc](../quick/libintx_table.cc) generates coefficients from the pinned upstream submodule; [conformance test](../quick/libintx_conformance.cu) |
| GANSU | [gansu_boys.h](../quick/gansu_boys.h) | [gansu_adapter.py](../quick/gansu_adapter.py), [gansu_table.cc](../quick/gansu_table.cc), [gansu_runtime.h](../quick/gansu_runtime.h), [upstream snapshot](../../third_party/gansu/README.md), [conformance test](../quick/gansu_conformance.cu) |
| Original QUICK | Pinned upstream `third_party/quick/src/gpu/gpu_fmt.h` | Original evaluator from the QUICK submodule |
| FABO | [CUDA evaluator and models](../../include/fast_boys/) | [QUICK patch generator](../quick/patch_quick.py) |

The custom comparator integration uses [comparator_binding.cuh](../quick/comparator_binding.cuh) and [comparator_runtime.cuh](../quick/comparator_runtime.cuh). See [third_party/README.md](../../third_party/README.md) for upstream pins, licenses, and submodule initialization. Simint is obtained from `https://github.com/simint-chem/simint-generator.git` at `38b24bb040c647e4acc0e040457180b574089c58`; its generator and original Boys evaluator are not FABO-authored ports.

## Availability and licensing

The repository supplies the custom source files; the SI compact archive need not duplicate them. Archived run/source manifests in the accompanying data continue to identify the exact historical builds. The SI reporting-code commit predates this source-packaging addition: use a checkout containing this index when rebuilding comparators, while retaining the documented reporting commit for reproducing the verified reports.

Third-party notices and provenance remain attached to their sources. FABO's top-level license choices do not relicense third-party code or data. In particular, the supplied VSR package has no included software license; see its [redistribution notice](../../third_party/vsr/README.md). Confirm redistribution permission before public release. Laikov's original supplementary README is preserved with its sources; no additional upstream license is asserted here.

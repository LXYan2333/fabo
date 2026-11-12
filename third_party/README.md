# Third-party dependencies

For all CPU/CUDA comparator ports and their application bindings, see [benchmark/ports/README.md](../benchmark/ports/README.md). The retained VSR and Laikov Highway source snapshots are tracked in `benchmark/ports/cpu/`; they no longer require exporting the legacy branch.

## QUICK

`quick/` is a Git submodule of [merzlab/QUICK](https://github.com/merzlab/QUICK), pinned to stable release [QUICK-26.03](https://github.com/merzlab/QUICK/releases/tag/QUICK-26.03), commit `730af1533da8912ce5874852561e63b5907f9d7a`. This was the upstream latest release on 2026-10-23. The submodule has no moving-branch tracking setting.

Initialize the pinned source after cloning this repository:

```sh
git submodule update --init --recursive third_party/quick
```

QUICK is licensed under MPL-2.0; see its upstream license and README for citation and build instructions. This addition does not patch QUICK, build it, or launch calculations.

## LibintX

`libintx/` is pinned to `dd5bb8b9536c913afea3260a1ef68dae4ce1dc0e` from [ValeevGroup/libintx](https://github.com/ValeevGroup/libintx). This is the inspected revision, not a claim about the latest upstream release. Initialize it with `git submodule update --init third_party/libintx`. Its source is LGPL-3.0; retain the upstream LICENSE and COPYING with redistributed sources.

The QUICK adapter in `benchmark/quick/libintx_boys.h` derives from LibintX's GPU sequence evaluator and asymptotic sequence helper. It changes output addressing to QUICK's strided layout but retains the coefficient layout and arithmetic. The pinned upstream source is not patched. Coefficients are produced by its original generator; the original GPU sequence function is included unchanged in the separate conformance executable.

## Vikhamar-Sandberg–Repisky (VSR)

User-supplied coefficient and benchmark files are preserved in [vsr/supplied](vsr/supplied), with hashes, the documented F0 heading correction, licensing status, and QUICK CUDA port details in [vsr/README.md](vsr/README.md). The complete original ZIP is retained locally under `.work/third-party-vsr/`, not in Git. No numerical coefficients are refitted for this integration.

## GANSU

The Boys implementation, parameters, original lookup table and BSD-3-Clause license from stable GANSU `v2026.8.10` are preserved in [gansu/upstream](gansu/upstream). See [gansu/README.md](gansu/README.md) for the pinned revision, paper/release distinctions, direct-stride QUICK binding, and conformance workflow.

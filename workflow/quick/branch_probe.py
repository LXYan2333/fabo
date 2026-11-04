"""Restore family-level threshold diagnostics on a saved fixed-density suite.

This instrumented executable is never a timing sample. The parent experiment,
its selected geometries, and its SAD fixtures are read-only.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RECOVERED_FROM = '7062ced'


def settings():
    # Preserve the earlier linear-then-logarithmic diagnostic, extending through
    # the main/tail boundary and beyond. Equality fails both strict predicates.
    edges = sorted(set([float(i) for i in range(1, 1001)] +
                       [10.0 ** (3 + i / 16) for i in range(1, 113)]))
    return dict(grouping='family', families=[4, 8], request_limits={'4': 4, '8': 8},
                domain_end=1e7, histogram_edges=edges,
                thresholds=sorted(set([0., 117., 1e7, *edges])))


def config_header(data):
    lines = ['#pragma once', '#define FABO_FAMILY_DOMAIN_END '+float(data['domain_end']).hex(),
             '#define FABO_FAMILY_SPD_REQUEST_LIMIT 8']
    for name, macro, key in [('fabo_hist_edges', 'FABO_HIST_EDGES', 'histogram_edges'),
                             ('fabo_thresholds', 'FABO_THRESHOLDS', 'thresholds')]:
        lines += [f'#define {macro} {len(data[key])}',
                  f'static __device__ const double {name}[] = {{',
                  ',\n'.join(float(v).hex() for v in data[key]), '};']
    return '\n'.join(lines)+'\n'


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError('diagnostic patch context mismatch: '+str(path))
    path.write_text(text.replace(old, new))


def patch(source, header, data):
    shutil.copyfile(header, source/'src/gpu/family_probe.h')
    (source/'src/gpu/fabo_warp_config.h').write_text(config_header(data))
    replace_once(source/'src/gpu/additive_binding.cuh', '#include "additive_boys.cuh"',
                 '#include "family_probe.h"\n#include "additive_boys.cuh"')
    replace_once(source/'src/gpu/additive_binding.cuh',
                 '  using Model = typename FaboQuickFamily<FamilyMax>::Model;',
                 '  FaboObserveFamily<FamilyMax>(last, x);\n  using Model = typename FaboQuickFamily<FamilyMax>::Model;')
    replace_once(source/'src/gpu/probe_runtime.h', '#include <time.h>',
                 '#include <time.h>\n#define FABO_WARP_PROBE 1\n#include "family_probe.h"')
    # Start after initialization and fixture replay; stop after the only Fock
    # build, before diagonalization. No SAD/setup Boys calls enter the counts.
    path = source/'src/modules/quick_scf_module.f90'
    replace_once(path, '      call scf_operator(.false.)\n      call fabo_probe_sync()',
                 '      call fabo_warp_begin()\n      call scf_operator(.false.)\n      call fabo_probe_sync()\n      call fabo_warp_end()')


CONFORMANCE = r'''
#include <cuda_runtime.h>
#include "family_probe.h"
__global__ void probe_test() {
  unsigned lane = threadIdx.x;
  FaboFamilyObserveMask<4>(0xffffffffU, lane % 5, double(lane));
  __syncwarp();
  unsigned mask = 0x80000011U;
  if (mask & (1U << lane))
    FaboFamilyObserveMask<4>(mask, lane == 31 ? 4 : 0,
      lane == 0 ? 0.0 : lane == 4 ? 1e7 : __longlong_as_double(__double_as_longlong(1e7)+1));
  __syncwarp();
  if (lane == 7) FaboFamilyObserveMask<8>(1U<<7, 8, 117.0);
  __syncwarp();
  if (lane == 2) FaboFamilyObserveMask<8>(1U<<2, 2, -1.0);
}
int main() { FaboFamilyBegin(true); probe_test<<<1,32>>>(); FaboFamilyEnd(); }
'''


def archived_command(parent, script, arguments):
    # A fresh isolated interpreter prevents already-imported workflow packages
    # (including those loaded by python -m) from overriding the frozen bundle.
    bootstrap = ('import runpy,sys; bundle,script=sys.argv[1:3]; '
                 'sys.path.insert(0,bundle); sys.argv=sys.argv[2:]; '
                 'runpy.run_path(script,run_name="__main__")')
    return [sys.executable, '-I', '-c', bootstrap, str(parent/'bundle'),
            str(script), *arguments]


def execute(parent, root, systems):
    subprocess.run(archived_command(parent, Path(__file__).resolve(),
        ['--bundled-worker', '--parent', str(parent), '--run', str(root),
         '--systems', *map(str, systems)]), check=True)


def execute_bundled(parent, root, systems):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
    from workflow.quick import calibrate as c, fixed_density as f
    for module in (c, f):
        if not Path(module.__file__).resolve().is_relative_to((parent/'bundle').resolve()):
            raise ValueError('build/replay utility is not from the archived bundle')
    import quick_family_probe as family
    import plot_quick_family as plotting
    saved = f.verify(parent)
    if saved['recipe']['config']['enable_f']:
        raise ValueError('this diagnostic runner currently supports the SPD suite')
    selections = [s for s in f.validate_selections(parent, saved) if s['case']['system'] in systems]
    if {s['case']['system'] for s in selections} != set(systems):
        raise ValueError('requested system is missing from the selected benchmark')
    root.mkdir(parents=True, exist_ok=True)
    # Do not reuse counters/builds under a changed diagnostic source or parent.
    driver = Path(__file__).resolve().parents[2]
    files = [Path(__file__), driver/'benchmark/quick/family_probe.h',
             driver/'workflow/scripts/quick_family_probe.py', driver/'workflow/scripts/plot_quick_family.py']
    recipe = dict(parent_identity=saved['identity'], parent=str(parent), selections=selections,
                  settings=settings(), recovered_from=RECOVERED_FROM,
                  sources={str(p.relative_to(driver)): c.sha(p) for p in files})
    identity = c.identity(recipe)
    record = dict(identity=identity, recipe=recipe)
    if (root/'run.json').exists() and json.loads((root/'run.json').read_text()) != record:
        raise ValueError('diagnostic identity changed; use a fresh directory')
    c.write_json(root/'run.json', record)
    variant = root/'variant'
    variant.mkdir(exist_ok=True)
    if not (variant/'source').exists():
        shutil.copytree(parent/'variants/fabo_additive/source', variant/'source')
        patch(variant/'source', files[1], recipe['settings'])
    config = dict(saved['recipe']['config'], build_jobs=8)
    build_record = dict(identity=identity, recipe=dict(config=config))
    c.write_json(variant/'run.json', build_record)
    c.write_json(root/'environment.json', dict(host=c.subprocess.check_output(['hostname'], text=True),
        gpu=c.subprocess.check_output(['nvidia-smi', '--query-gpu=name,uuid,driver_version', '--format=csv,noheader'], text=True),
        nvcc=c.subprocess.check_output([config['cuda']+'/bin/nvcc', '--version'], text=True)))
    with tempfile.TemporaryDirectory(prefix='fabo-branch-', dir=os.environ.get('SLURM_TMPDIR', '/tmp')) as temp:
        scratch = Path(temp)
        binary, env = c.build(variant, build_record, scratch)
        test = scratch/'conformance'; test.mkdir()
        (test/'test.cu').write_text(CONFORMANCE)
        c.command([config['cuda']+'/bin/nvcc', '-std=c++17', '-O3', '-arch=sm_120',
                   '-I'+str(variant/'source/src/gpu'), test/'test.cu', '-o', test/'test'], root/'conformance-build.log')
        c.command([test/'test'], root/'conformance-run.log', cwd=test)
        import math
        groups = [(4, [(i%5, float(i)) for i in range(32)]),
                  (4, [(0, 0.), (0, 1e7), (4, math.nextafter(1e7, math.inf))]),
                  (8, [(8, 117.)]), (8, [(2, -1.)])]
        if family.read_counters(test/'family-counters.csv', recipe['settings']) != family.oracle_counts(groups, recipe['settings']):
            raise ValueError('GPU explicit-mask counters disagree with host oracle')
        shutil.copyfile(test/'family-counters.csv', root/'conformance-counters.csv')
        for selection in selections:
            case = selection['case']; dest = root/'cases'/case['id']
            dest.mkdir(parents=True, exist_ok=True)
            # Intentionally do not interpret these instrumented runs as timings.
            local = scratch/case['id']; local.mkdir()
            fixture = parent/'fixtures'/case['id']/'fixture.bin'
            shutil.copyfile(fixture, local/'fixture.bin')
            (local/'input.in').write_text(c.input_text(parent, config, case))
            runtime = env | dict(QUICK_BASIS=str(variant/'install/basis'), FABO_QUICK_MODE='check',
                                 FABO_FIXTURE=str(local/'fixture.bin'), FABO_WARMUP='0', FABO_INITIAL_GUESS='sad')
            print('probe start', case['id'], flush=True)
            c.command([binary, 'input.in'], local/'process.log', cwd=local, env=runtime, timeout=7200)
            if c.sha(local/'replayed-fixture.bin') != selection['fixture_sha256']:
                raise ValueError('diagnostic density/Hcore replay mismatch')
            f.verify_basis_output(local, variant/'install', case['basis'])
            for name in ('input.in','input.out','process.log','family-counters.csv','requests.csv','check-energy.txt'):
                shutil.copyfile(local/name, dest/name)
            result = family.summarize(dest/'family-counters.csv', recipe['settings'])
            family.verify_projection(result, dest/'requests.csv')
            result['provenance'] = dict(mode='fixed_density', diagnostic_identity=identity,
                parent_identity=saved['identity'], fixture_sha256=selection['fixture_sha256'], case=case)
            family.write_report(result, dest/'report')
            plotting.plot(dict(settings=recipe['settings'], families=family.views(result),
                               provenance=result['provenance'], weighting='cohorts for branches; lanes for inputs'), dest/'plots')
            c.write_json(dest/'complete.json', dict(identity=identity, counter_sha256=c.sha(dest/'family-counters.csv')))
            print('probe complete', case['id'], flush=True)
        c.write_json(root/'complete.json', dict(identity=identity, cases=[s['case']['id'] for s in selections]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--systems', type=int, nargs='+', default=[1])
    parser.add_argument('--bundled-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    runner = execute_bundled if args.bundled_worker else execute
    runner(args.parent.resolve(), args.run.resolve(), args.systems)


if __name__ == '__main__':
    main()

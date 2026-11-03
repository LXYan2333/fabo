"""Fixed-length QUICK backend comparison from frozen official SAD trajectories."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile

from benchmark.quick.patch_quick import ROOT, PIN, VARIANTS
from . import calibrate as c
from .archive import checked_import
from .comparators import prepare_tables, conformance
from .prepare import prepare as prepare_quick
from .scf_records import read_result, verify_basis_output
from .s66 import inventory, cases, sha

LIBINTX_PIN = 'dd5bb8b9536c913afea3260a1ef68dae4ce1dc0e'
EXTRA_DEFAULTS = dict(variants=list(VARIANTS), rounds=5, build_workers=5,
                      cuda_arch='sm_120', calibration_root='', calibration_sha256='')
SAMPLE_FILES = ('input.in','input.out','process.log',
                'scf-summary.txt','scf-iterations.csv','result.json')


def settings(raw):
    if set(raw)-{'calibration','comparison'}: raise ValueError('unknown comparison configuration section')
    config=c.settings(raw.get('calibration',{}))
    supplied=raw.get('comparison',{})
    if set(supplied)-set(EXTRA_DEFAULTS): raise ValueError('unknown comparison option')
    spec=EXTRA_DEFAULTS|supplied
    variants=spec['variants']
    if (not isinstance(variants,list) or len(variants)<2 or variants[0]!='official' or
            any(v not in VARIANTS for v in variants) or len(set(variants))!=len(variants)):
        raise ValueError('unique supported variants, official first, required')
    if type(spec['rounds']) is not int or spec['rounds']<3: raise ValueError('at least three comparison rounds required')
    if type(spec['build_workers']) is not int or not 1<=spec['build_workers']<=config['slurm']['cpus']:
        raise ValueError('build workers exceed allocation')
    if not re.fullmatch(r'sm_[0-9]+[a-z]?',spec['cuda_arch']): raise ValueError('invalid CUDA architecture')
    if not Path(spec['calibration_root']).is_absolute() or not re.fullmatch(r'[0-9a-f]{64}',spec['calibration_sha256']):
        raise ValueError('absolute calibration archive path and completion SHA-256 required')
    return config,spec


def bundle_sources(output, eigen):
    # Keep all source/coefficients needed to rebuild adapters, including upstream
    # oracles. Do not bundle old parameter-search machinery or unrelated files.
    for directory in ('workflow/quick','benchmark/quick'):
        for p in (ROOT/directory).iterdir():
            if p.is_file() and p.suffix in ('.py','.h','.cuh','.cu','.cc','.f90'):
                dest=output/'bundle'/directory/p.name; dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,dest)
    upstream=ROOT/'third_party/libintx'
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()!=LIBINTX_PIN or subprocess.check_output(['git','-C',str(upstream),'status','--porcelain'],text=True).strip():
        raise ValueError('LibintX must be the clean pinned revision')
    for directory in ('third_party/libintx/src','third_party/vsr/supplied','third_party/gansu/upstream'):
        shutil.copytree(ROOT/directory,output/'bundle'/directory)
    if not (eigen/'Eigen/Core').is_file(): raise ValueError('Eigen headers required for LibintX coefficient generator')
    shutil.copytree(eigen,output/'bundle/third_party/eigen3')
    from benchmark.quick.vsr_generate import generate
    if generate(ROOT/'third_party/vsr/supplied')!=(ROOT/'benchmark/quick/vsr_coefficients.h').read_text():
        raise ValueError('stale generated VSR coefficients')
    from benchmark.quick.gansu_adapter import generate as gansu_generate
    if gansu_generate(ROOT/'third_party/gansu/upstream')!=(ROOT/'benchmark/quick/gansu_boys.h').read_text():
        raise ValueError('stale generated GANSU adapter')


def prepare_run(output,dataset,raw,smoke=False,eigen=Path('/usr/include/eigen3')):
    config,spec=settings(raw)
    rows=inventory(dataset); selected=cases(rows,config['bases'],config['separations'])
    if smoke: selected=[r for r in selected if r['system']==1 and r['separation']=='1.00']
    if not selected: raise ValueError('empty smoke selection')
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    for variant in spec['variants']:
        prepare_quick(output/'variants'/variant/'source',variant,training=True)
    bundle_sources(output,eigen)
    for item in rows:
        if any(case['geometry']==item['geometry'] for case in selected):
            dst=output/item['geometry']; dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(item['source'],dst)
    script=c.slurm_script(config).replace('fabo-s66-calibrate','fabo-quick-compare').replace('workflow.quick.calibrate execute','workflow.quick.compare execute')
    (output/'run.sbatch').write_text(script)
    inputs={str(p.relative_to(output)):sha(p) for dirname in ('bundle','variants','workloads')
            for p in sorted((output/dirname).rglob('*')) if p.is_file()}
    inputs['run.sbatch']=sha(output/'run.sbatch')
    recipe={'schema':1,'quick_revision':PIN,'libintx_revision':LIBINTX_PIN,'config':config,
            'comparison':spec,'cases':selected,'purpose':'smoke' if smoke else 'comparison',
            'rounds':1 if smoke else spec['rounds'],'input_hashes':inputs,
            'protocol':'fixed official SAD trajectory lengths; no molecular warmup; rotate backend order by round and case'}
    saved={'identity':c.identity(recipe),'recipe':recipe}; c.write_json(output/'run.json',saved)
    # One serial build per variant, scheduled concurrently. Child identities bind
    # builds to the complete comparison recipe, including generated payloads.
    for variant in spec['variants']:
        child={'parent':saved['identity'],'variant':variant,'config':config|{'build_jobs':1}}
        c.write_json(output/'variants'/variant/'run.json',{'identity':c.identity(child),'recipe':child})
    return output/'run.json'


def verify(root):
    saved=c.verify_inputs(root)
    recipe=saved['recipe']
    settings({'calibration':recipe['config'],'comparison':recipe['comparison']})
    for variant in recipe['comparison']['variants']:
        child=json.loads((root/'variants'/variant/'run.json').read_text())
        expected={'parent':saved['identity'],'variant':variant,'config':recipe['config']|{'build_jobs':1}}
        if child!={'identity':c.identity(expected),'recipe':expected}: raise ValueError('changed variant build identity')
    return saved


def schedule(cases,variants,rounds):
    for r in range(rounds):
        for i,case in enumerate(cases):
            shift=(r+i)%len(variants)
            for variant in variants[shift:]+variants[:shift]: yield r,case,variant


def sample(root,saved,case,reference,variant,round_,build,scratch):
    binary,env=build; config=saved['recipe']['config']
    directory=root/'samples'/f'{round_:02d}'/case['id']/variant; marker=directory/'complete.json'
    if marker.exists():
        record=json.loads(marker.read_text())
        if record['identity']!=saved['identity'] or set(record['files'])!=set(SAMPLE_FILES):
            raise ValueError('sample identity/manifest mismatch')
        for name,digest in record['files'].items():
            if sha(directory/name)!=digest: raise ValueError('changed fixed-SCF sample')
        result=json.loads((directory/'result.json').read_text())
        if (result['case']!=case['id'] or result['variant']!=variant or result['round']!=round_ or
                result['iterations']!=reference['iterations'] or result['fixture_sha256']!=reference['fixture_sha256'] or
                result['replayed_initial_sha256']!=reference['fixture_sha256']):
            raise ValueError('cached sample differs from fixed trajectory')
        return result
    directory.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sample-',dir=scratch) as temp:
        local=Path(temp); (local/'input.in').write_text(c.input_text(root,config,case))
        state=local/'initial.bin'; shutil.copyfile(root/'calibration'/case['id']/'initial.bin',state)
        if sha(state)!=reference['fixture_sha256']: raise ValueError('changed replay fixture')
        runtime=env|{'QUICK_BASIS':str(root/'variants'/variant/'install/basis'),
                     'FABO_SCF_TRAINING':'fixed','FABO_SCF_STATE':str(state),
                     'FABO_SCF_STEPS':str(reference['iterations'])}
        if variant in ('libintx_gpu','gansu'): runtime['FABO_COMPARATOR_TABLE']=str(root/'tables'/(variant+'.bin'))
        try:
            wall=c.command([binary,'input.in'],local/'process.log',cwd=local,env=runtime,
                           timeout=config['calculation_timeout_seconds'])
            result=read_result(local,True,reference['iterations'],wall)
            basis=verify_basis_output(local,root/'variants'/variant/'install',case['basis'])
            if basis!=reference['basis'] or result['dimensions']!=reference['dimensions']:
                raise ValueError('fixed-SCF basis/dimensions differ from calibration')
            replay_sha256=sha(local/'replayed-initial.bin')
            if replay_sha256!=reference['fixture_sha256']:
                raise ValueError('initial-state replay differs from calibration')
            result.update(case=case['id'],variant=variant,round=round_,basis=basis,
                          fixture_sha256=reference['fixture_sha256'],replayed_initial_sha256=replay_sha256)
            c.write_json(local/'result.json',result)
            for name in SAMPLE_FILES: shutil.copyfile(local/name,directory/name)
        except Exception:
            for name in ('input.in','input.out','process.log','scf-summary.txt','scf-iterations.csv'):
                if (local/name).exists(): shutil.copyfile(local/name,directory/('failed-'+name))
            raise
    c.write_json(marker,{'identity':saved['identity'],'files':{name:sha(directory/name) for name in SAMPLE_FILES}})
    return result


def statistics_for(values):
    if not values or any(not math.isfinite(x) or x<=0 for x in values): raise ValueError('invalid timing samples')
    median=statistics.median(values)
    return {'samples':values,'median':median,
            'mad_over_median':statistics.median(abs(x-median) for x in values)/median,
            'cv':statistics.stdev(values)/statistics.mean(values) if len(values)>1 else None}


def summarize(saved,rows):
    recipe=saved['recipe']; variants=recipe['comparison']['variants']
    expected={(r,case['id'],v) for r,case,v in schedule(recipe['cases'],variants,recipe['rounds'])}
    keys=[(r['round'],r['case'],r['variant']) for r in rows]
    if len(set(keys))!=len(keys) or set(keys)!=expected: raise ValueError('incomplete/duplicate timing coverage')
    cases_out=[]
    for case in recipe['cases']:
        timings={}; energies={}
        for v in variants:
            samples=sorted((r for r in rows if r['case']==case['id'] and r['variant']==v),key=lambda r:r['round'])
            timings[v]={k:statistics_for([r[k] for r in samples]) for k in ('fock_seconds','scf_seconds','process_seconds')}
            energies[v]=[r['final_energy_hartree'] for r in samples]
        cases_out.append({'case':case['id'],'basis':case['basis'],'timings':timings,
                          'final_energy_hartree':energies,
                          'median_energy_difference_from_official':{v:statistics.median(energies[v])-statistics.median(energies['official']) for v in variants}})
    scores={v:math.exp(statistics.mean(math.log(r['timings'][v]['fock_seconds']['median']/r['timings']['official']['fock_seconds']['median']) for r in cases_out)) for v in variants}
    return {'identity':saved['identity'],'purpose':recipe['purpose'],'cases':cases_out,
            'fock_ratio_geomean':scores,'ratio_definition':'T_method / T_official; lower is faster',
            'units':'seconds per fixed-length SCF trajectory; Fock time summed over all iterations',
            'rounds':recipe['rounds'],'warmup':0}


def report(root,saved,rows):
    summary=summarize(saved,rows); c.write_json(root/'samples.json',rows); c.write_json(root/'summary.json',summary)
    lines=['# QUICK fixed-length backend comparison','',summary['units']+'.', '',
           f'Purpose: {summary["purpose"]}; repetitions: {summary["rounds"]}; no molecular warmup. Ratios are T_method/T_official; lower is faster. Dispersion is MAD/median and sample standard deviation/mean (CV). Energy differences are diagnostics, not accuracy qualification.','',
           '| Case | Backend | Fock median (s) | SCF-loop median (s) | Fock ratio | MAD/median | CV | Median energy difference (Eh) |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in summary['cases']:
        ref=row['timings']['official']['fock_seconds']['median']
        for v,t in row['timings'].items():
            f=t['fock_seconds']; cv='n/a' if f['cv'] is None else f'{f["cv"]:.4f}'
            lines.append(f'| {row["case"]} | {v} | {f["median"]:.6f} | {t["scf_seconds"]["median"]:.6f} | {f["median"]/ref:.4f} | {f["mad_over_median"]:.4f} | {cv} | {row["median_energy_difference_from_official"][v]:.6e} |')
    (root/'COMPARISON.md').write_text('\n'.join(lines)+'\n')


def execute(root):
    root=Path(root).resolve()
    with (root/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        saved=verify(root); recipe=saved['recipe']; config=recipe['config']; spec=recipe['comparison']
        calibration=checked_import(root,saved); references={r['case']:r for r in calibration['rows']}
        marker=root/'complete-compare.json'; completed=marker.exists()
        if completed:
            record=json.loads(marker.read_text())
            if record['identity']!=saved['identity']: raise ValueError('comparison identity mismatch')
            for name,digest in record['files'].items():
                if sha(root/name)!=digest: raise ValueError('changed completed comparison artifact: '+name)
        environment={'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,uuid,driver_version','--format=csv,noheader'],text=True).strip(),
                     'node':os.uname().nodename,'nvcc':subprocess.check_output([config['cuda']+'/bin/nvcc','--version'],text=True)}
        path=root/'environment.json'
        if path.exists() and json.loads(path.read_text())!=environment: raise ValueError('comparison environment changed')
        if not path.exists(): c.write_json(path,environment)
        with tempfile.TemporaryDirectory(prefix='fabo-compare-',dir=os.environ.get('SLURM_TMPDIR',os.environ.get('TMPDIR','/tmp'))) as tmp:
            scratch=Path(tmp)
            prepare_tables(root,config,scratch)
            conformance(root,saved,scratch)
            def build_variant(variant):
                child=root/'variants'/variant; build_scratch=scratch/variant; build_scratch.mkdir()
                return variant,c.build(child,json.loads((child/'run.json').read_text()),build_scratch)
            with ThreadPoolExecutor(max_workers=spec['build_workers']) as pool:
                builds=dict(pool.map(build_variant,spec['variants']))
            # All compiler processes have exited before any molecular timing.
            rows=[]
            for r,case,v in schedule(recipe['cases'],spec['variants'],recipe['rounds']):
                rows.append(sample(root,saved,case,references[case['id']],v,r,builds[v],scratch))
                print(f'round {r+1}: {case["id"]} {v}: Fock {rows[-1]["fock_seconds"]:.6f} s',flush=True)
            if completed: return  # Verification never rewrites completed summaries.
            report(root,saved,rows)
        names=['run.json','environment.json','imported-calibration.json','summary.json','samples.json','COMPARISON.md','tables/complete.json','conformance/complete.json']
        names += [str(p.relative_to(root)) for p in (root/'samples').rglob('complete.json')]
        names += ['variants/'+v+'/build.json' for v in spec['variants']]
        c.write_json(marker,{'identity':saved['identity'],'files':{name:sha(root/name) for name in names}})


def plot(root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary=json.loads((root/'summary.json').read_text()); cases_=summary['cases']
    bases=sorted({r['basis'] for r in cases_})
    fig,axes=plt.subplots(len(bases),1,squeeze=False,figsize=(10,3*len(bases)))
    for ax,basis in zip(axes[:,0],bases):
        rows=[r for r in cases_ if r['basis']==basis]
        for v in rows[0]['timings']:
            ax.plot(range(len(rows)),[r['timings'][v]['fock_seconds']['median']/r['timings']['official']['fock_seconds']['median'] for r in rows],'.-',label=v)
        ax.set(title=basis,xlabel='Case index (summary.json order)',ylabel='Fock T_method / T_official')
        ax.legend(); ax.grid(alpha=.2)
    fig.suptitle('QUICK '+summary['purpose']); fig.tight_layout(); fig.savefig(root/'comparison.pdf'); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare'); p.add_argument('--config',type=Path,required=True); p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--eigen',type=Path,default=Path('/usr/include/eigen3'))
    p.add_argument('--smoke',action='store_true',help='water dimer at equilibrium, one repetition; not a full benchmark')
    for action in ('import','execute','plot'):
        p=sub.add_parser(action); p.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='prepare': print(prepare_run(args.output,args.dataset,json.loads(args.config.read_text()),args.smoke,args.eigen))
    elif args.action=='import':
        root=args.run.resolve(); checked_import(root,verify(root))
    elif args.action=='execute': execute(args.run)
    else: plot(args.run.resolve())


if __name__=='__main__': main()

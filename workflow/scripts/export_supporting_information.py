"""Report-only SI exporter. Never executes an evaluator or submits work."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

from workflow.scripts.plot_quick_performance import load_records as quick
from workflow.scripts.plot_quick_performance import molecule_label, SYSTEMS
from workflow.scripts.plot_nwchem_performance import load_records as nwchem
from workflow.scripts.report_function_accuracy import load_records as accuracy
from workflow.scripts.report_molecular_accuracy import load as molecular


def csv_write(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        w.writeheader()
        w.writerows(rows)


def escape(value):
    return str(value).replace('_', r'\_').replace('%', r'\%').replace('&', r'\&')


BACKEND_NAMES = {
    'official': 'QUICK', 'original': 'Simint', 'simint': 'Simint',
    'quick': 'QUICK', 'fabo': 'FABO', 'fabo_additive': 'FABO',
    'fabo_software': 'FABO (software)', 'libintx': 'LibintX',
    'libintx_gpu': 'LibintX', 'vsr': 'VSR', 'laikov': 'Laikov', 'gansu': 'GANSU',
}


def backend_name(value):
    return BACKEND_NAMES[value]


def table(path, caption, heads, rows, *, group_columns=1):
    rows=list(rows)
    cols = 'l' * len(heads)
    header = ' & '.join(heads) + r' \\ \midrule'
    label = 'tab:' + path.stem.lower()
    text = [r'\begin{longtable}{' + cols + '}', r'\caption{' + caption + r'}\label{' + label + r'}\\',
            r'\toprule', header, r'\endfirsthead', r'\toprule', header, r'\endhead',
            r'\midrule\multicolumn{' + str(len(heads)) + r'}{r}{Continued on next page}\\\endfoot',
            r'\bottomrule\endlastfoot']
    if len(rows)<=25:
        text.insert(0, r'\Needspace{' + str(len(rows)+7) + r'\baselineskip}')
    for i,row in enumerate(rows):
        # Let longtable paginate; a forced midpoint break left most of a page empty.
        same_case=(len(rows)==60 and i+1<len(rows) and row[:group_columns]==rows[i+1][:group_columns])
        text.append(' & '.join(escape(v) for v in row) + (r' \\*' if same_case else r' \\'))
    path.write_text('\n'.join(text + [r'\end{longtable}', '']))


def generate(output, application_inputs=Path('overleaf-si/data/application-inputs')):
    data, tables, figures = (output / x for x in ('data', 'tables', 'figures'))
    for p in (data,tables,figures):
        p.mkdir(parents=True,exist_ok=True)
    if application_inputs.resolve() != (data/'application-inputs').resolve():
        shutil.copytree(application_inputs, data/'application-inputs', dirs_exist_ok=True, symlinks=True)
    root=Path('data/benchmarks')
    gpu=root/'quick-fixed-density-20261106'; cpu=root/'nwchem-fixed-density-20261106'
    timing={'GPU':quick(gpu)[1], 'CPU':nwchem(cpu)}
    case_labels = {(platform, r['case']): (molecule_label(SYSTEMS[r['system']][0], r['copies']), r['basis'])
                   for platform, rows in timing.items() for r in rows}
    errors=accuracy(root/'function-accuracy-20261107')
    mol,means=molecular(gpu,cpu)
    variability=[dict(case=c['case']['id'],energy_sd=c['reference_energy_sd'],
                      fock_sd_max=c['reference_matrix_sd_max']['fock'],density_sd_max=c['reference_matrix_sd_max']['density']) for c in means['cases']]
    csv_write(data/'reference-variability.csv',variability)
    table(tables/'reference-variability.tex','QUICK reference-repeat dispersion: energy sample SD and largest elementwise sample SD of each matrix.',
          ['Molecule','Basis','Energy SD (hartree)','Max Fock SD (hartree)','Max density SD'],
          [(*case_labels['GPU',r['case']],*[f'{r[k]:.3e}' for k in ('energy_sd','fock_sd_max','density_sd_max')]) for r in variability])
    csv_write(data/'function-accuracy.csv',errors)
    csv_write(data/'molecular-differences.csv',mol)
    csv_write(data/'timing-summary.csv',[dict(platform=p,**r) for p,rows in timing.items() for r in rows])
    raw=[]
    for case in json.loads((gpu/'summary.json').read_text())['cases']:
        for backend,v in case['variants'].items():
            if 'timing' not in v: continue
            for repetition,t in enumerate(v['timing']['fock_seconds']['samples']):
                raw.append(dict(platform='GPU',case=case['case']['id'],backend=backend,repetition=repetition,seconds=t))
    for r in json.loads((cpu/'results.json').read_text()):
        raw.append(dict(platform='CPU',case=r['case'],backend=r['backend'],repetition=r['round'],seconds=r['jk_seconds']))
    assert len(raw)==600 and len({(r['platform'],r['case'],r['backend'],r['repetition']) for r in raw})==600
    csv_write(data/'timing-observations.csv',raw)
    ratios=[]
    for platform,rows in timing.items():
        base='fabo_additive' if platform=='GPU' else 'fabo'
        reference={r['case']:r['mean_seconds'] for r in rows if r['backend']==base}
        for backend in sorted({r['backend'] for r in rows}-{base}):
            values=[r['mean_seconds']/reference[r['case']] for r in rows if r['backend']==backend]
            assert len(values)==12
            ratio=math.exp(sum(map(math.log,values))/12)
            ratios.append(dict(platform=platform,backend=backend,geometric_mean_ratio=ratio,speedup_percent=100*(ratio-1)))
        table(tables/f'timings-{platform}.tex',f'{platform} timings in seconds; arithmetic means and sample standard deviations of five observations.',
              ['Molecule','Basis','Backend','Mean (s)','SD (s)'],[(*case_labels[platform,r['case']],backend_name(r['backend']),f"{r['mean_seconds']:.3f}",f"{r['sd_seconds']:.3f}") for r in rows], group_columns=2)
        table(tables/f'molecular-{platform}.tex',f'{platform} casewise differences from the correctly rounded Boys backend. Energy and Fock quantities are in hartree; density entries are dimensionless. Matrix means include every element.',
              ['Molecule','Basis','Backend',r'$|\Delta E|$',r'$\max|\Delta F|$',r'$\mathrm{mean}|\Delta F|$',r'$\max|\Delta P|$',r'$\mathrm{mean}|\Delta P|$'],
              [(*case_labels[platform,r['case']],backend_name(r['backend']),*[f'{r[k]:.2e}' for k in ('energy','fock','fock_mean_absolute','density','density_mean_absolute')]) for r in mol if r['platform']==platform], group_columns=2)
    csv_write(data/'geometric-speedups.csv',ratios)
    table(tables/'speedups.tex','Geometric means of comparator/FABO mean-time ratios over 12 cases.',
          ['Platform','Comparator','Ratio','Speedup (percent)'],[(r['platform'],backend_name(r['backend']),f"{r['geometric_mean_ratio']:.6f}",f"{r['speedup_percent']:.2f}") for r in ratios])
    summary=json.loads(Path('data/numerical/paired-1ulp/summary.json').read_text())
    rows=[]
    for n in range(25):
        w=summary['winners'][f'0-{n}']; s=w['storage']; t=w['tail']['storage']
        assert s['table_bytes']+t['table_bytes']==w['combined_table_bytes']<=1048576
        rows.append(dict(N=n,degrees=';'.join(map(str,w['degrees'])),highest_order=s['highest_reference_order'],C_hex=w['grid']['domain_end'],offset_hex=w['grid']['offset'],main_bits=w['grid']['b'],tail_bits=w['tail']['retained_bits'],main_rows=w['grid']['row_count'],tail_rows=t['row_count'],row_bytes=s['row_bytes'],padding=s['padding_bytes_per_row'],main_bytes=s['table_bytes'],tail_bytes=t['table_bytes'],total_bytes=w['combined_table_bytes']))
    csv_write(data/'models.csv',rows)
    table(tables/'models.tex',r'Selected models: $H=\max_{0\leq n\leq N}(n+p_n)$ is the highest stored reference order. Storage includes coefficients, corrections and padding; full vectors and hexadecimal parameters are in data/models.csv.',
          ['$N$','$H$','$b_g$','$b_t$','Main rows','Tail rows','Row bytes','Total bytes'],[[r[k] for k in ('N','highest_order','main_bits','tail_bits','main_rows','tail_rows','row_bytes','total_bytes')] for r in rows])
    witnesses=[]
    for platform in ('cpu','cuda'):
        for mode in ('strict','fast'):
            for backend in sorted({r['backend'] for r in errors if r['platform']==platform}):
                for metric in ('absolute','relative','ulp'):
                    subset=[r for r in errors if (r['platform'],r['mode'],r['backend'],r['metric'])==(platform,mode,backend,metric) and r['n']!='all']
                    from decimal import Decimal
                    witness=dict(max(subset,key=lambda r:Decimal(r['max_hi'])))
                    # Only retained witness references are evaluated; no adapter
                    # call and no dense scan. Preserve the original observations.
                    from workflow.additive.reference import enclosure
                    lo,hi,_=enclosure(witness['n'],float.fromhex(witness['witness_x_hex']),512,100000)
                    witness.update(reference_lower=str(lo),reference_upper=str(hi),reference_precision=512)
                    witnesses.append(witness)
    csv_write(data/'maximum-witnesses.csv',witnesses)
    table(tables/'witnesses.tex','Largest reported upper bounds on sampled ULP error by implementation and arithmetic mode. Exact witnesses and all error measures are in data/maximum-witnesses.csv.',
          ['Platform','Mode','Backend','$N$','$n$','$x$','ULP upper'],[(r['platform'],r['mode'],backend_name(r['backend']),r['N'],r['n'],f"{r['witness_x']:.6f}",f"{float(r['max_hi']):.7g}") for r in witnesses if r['metric']=='ulp'])
    # Dimensions come from accepted output records, not basis-name heuristics.
    workloads=[]
    for c in json.loads((gpu/'summary.json').read_text())['cases']:
        assert c['dimensions'][0]==c['dimensions'][1]
        sample=data/'application-inputs/quick/samples'/c['case']['id']/'00/official'
        saved=json.loads((sample/'result.json').read_text())
        workloads.append(dict(platform='GPU',case=c['case']['id'],basis=c['basis']['name'],
                              copies=c['case']['copies'],dimension=c['dimensions'][0],
                              rank=c['dimensions'][1],electrons=c['dimensions'][2],
                              geometry='data/application-inputs/quick/'+c['case']['geometry'],
                              basis_file='data/application-inputs/quick/basis/'+c['basis']['file'],basis_sha256=c['basis']['sha256'],
                              input=str((sample/'input.in').relative_to(output)),fixture_sha256=saved['fixture_sha256']))
    for c in json.loads((cpu/'matrix-absolute.json').read_text())['results']:
        if c['backend']!='original': continue
        n=math.isqrt(c['fock']['elements'])
        assert n*n==c['fock']['elements']
        sample=data/'application-inputs/nwchem/measurements'/c['case']['id']/'0-original'
        log=(sample/'nwchem.log').read_text()
        completed=json.loads((sample/'complete.json').read_text())
        assert hashlib.sha256((sample/'nwchem.log').read_bytes()).hexdigest()==completed['nwchem.log']
        closed=int(re.search(r'closed shells\s*=\s*(\d+)',log)[1])
        assert int(re.search(r'open shells\s*=\s*(\d+)',log)[1])==0
        basis={'6-31G*':'6-31gs','def2-SVP':'def2-svp','cc-pVDZ':'cc-pvdz'}[c['case']['basis']]
        workloads.append(dict(platform='CPU',case=c['case']['id'],basis=c['case']['basis'],
                              copies=c['case']['copies'],dimension=n,rank=n,
                              electrons=2*closed,geometry='data/application-inputs/nwchem/'+c['case']['geometry'],
                              basis_file='data/application-inputs/nwchem/basis/'+basis,
                              input=str((sample/'input.nw').relative_to(output)),fixture_sha256=completed['initial.bin']))
    assert len(workloads)==24
    csv_write(data/'workloads.csv',workloads)
    table(tables/'workloads.tex','Accepted workload dimensions. QUICK uses Cartesian functions; NWChem uses spherical functions. The orbital rank equals the basis dimension in these cases.',
          ['Platform','Molecule','Basis','AO dimension','Electrons'],[(r['platform'],*case_labels[r['platform'],r['case']],r['dimension'],r['electrons']) for r in workloads])
    csv_write(data/'backend-names.csv',[dict(identifier=k,display=v) for k,v in BACKEND_NAMES.items()])
    # Supply the exact scanner/qualification-adjacent code, authenticated against
    # the completed scan's recipe, rather than labelling all current HEAD as used.
    source_index=[]
    recipe=json.loads((root/'function-accuracy-20261107/cpu/run.json').read_text())['recipe']
    for name,digest in recipe['sources'].items():
        src=Path(name)
        if hashlib.sha256(src.read_bytes()).hexdigest()!=digest:
            raise ValueError('Archived scan source differs: '+name)
        dst=data/'methods/function-accuracy'/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        source_index.append(dict(purpose='function accuracy',file=str(dst.relative_to(output)),sha256=digest,
                                 identity='data/records/benchmarks/function-accuracy-20261107/cpu/run.json'))
    for name in ('export_supporting_information','plot_quick_performance','plot_nwchem_performance',
                 'report_function_accuracy','report_molecular_accuracy','quick_molecular_means',
                 'nwchem_molecular_metrics','molecular_metrics','record_manifest'):
        src=Path('workflow/scripts')/(name+'.py')
        dst=data/'methods/reporting'/src
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        source_index.append(dict(purpose='report reduction',file=str(dst.relative_to(output)),
                                 sha256=hashlib.sha256(src.read_bytes()).hexdigest(),identity='postprocessing snapshot'))
    csv_write(data/'method-sources.csv',source_index)
    for src in [root,Path('data/numerical/paired-1ulp'),Path('data/diagnostics/upward-recurrence-limits')]:
        shutil.copytree(src,data/'records'/src.relative_to('data'),dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('nonuniform-grid-remainder.pdf','upward-recurrence-limits.pdf','results-function-accuracy-fast.pdf'):
        shutil.copy2(Path('overleaf-paper2/figure')/name,figures/name)
    for name in ('nonuniform-grid-remainder.csv','nonuniform-grid-remainder.json'):
        shutil.copy2(Path('overleaf-paper2/tables')/name,data/name)
    for name in ('manifest.json','simd-manifest.json'):
        shutil.copy2(Path('include')/name,data/name)
    shutil.copy2('overleaf-paper2/aipsamp.bib',output/'references.bib')
    manifest={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in (data,tables,figures) for p in sorted(folder.rglob('*')) if p.is_file()}
    (output/'data-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Exported {len(errors)} accuracy rows, {len(raw)} timings, {len(mol)} molecular rows and 25 models.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('overleaf-si'))
    parser.add_argument('--application-inputs',type=Path,default=Path('overleaf-si/data/application-inputs'))
    args=parser.parse_args()
    generate(args.output,args.application_inputs)

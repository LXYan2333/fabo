import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import tarfile
from workflow.library_accuracy.core import ROOT,sha,save,identity,csv_write
from workflow.library_accuracy.environment import bind
from .core import FINAL,WINDOW,reduce_windows,plot

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('stage',choices=['prepare','pilot','scan','cluster','report','plot'])
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--cxx',default='g++');p.add_argument('--prefix',type=Path)
    p.add_argument('--group',type=int,default=0);p.add_argument('--workers',type=int,default=8)
    p.add_argument('--partition',default='6526Y');p.add_argument('--exclude',default='c025,c026,c027,c028')
    p.add_argument('--submit',action='store_true')
    p.add_argument('--output',type=Path)
    a=p.parse_args();root=a.run.resolve()
    if a.workers<1 or a.group<0:raise ValueError('invalid workers/group')
    if a.stage=='plot':
        if a.output is None:raise ValueError('plot requires --output')
        complete=json.loads((root/'complete.json').read_text())
        if sha(root/'boundaries.json')!=complete['files']['boundaries.json']:raise ValueError('changed results')
        expected=json.loads((root/'boundaries.json').read_text())
        records={}
        with tarfile.open(root/'shards.tar.gz','r|gz') as archive:
            for member in archive:
                if not member.isfile():continue
                index=int(Path(member.name).stem)
                if index in records:raise ValueError('duplicate archive shard')
                d=json.load(archive.extractfile(member))
                if d['identity']!=complete['identity'] or d['execution']!=complete['execution']:raise ValueError('mixed archive')
                records[index]=d
        if reduce_windows(records[i] for i in sorted(records))!=expected:raise ValueError('archive reduction differs')
        plot(expected,a.output);return
    if a.stage=='prepare':
        root.mkdir(parents=True,exist_ok=False)
        cmd=[a.cxx,'-std=c++17','-fext-numeric-literals','-O2','-fno-fast-math','-ffp-contract=off','-fno-lto',str(ROOT/'benchmark/upward_recurrence/scan.cc')]
        if a.prefix:cmd += [f'-I{a.prefix}/include',f'-L{a.prefix}/lib',f'-Wl,-rpath,{a.prefix}/lib']
        cmd += ['-lmpfr','-lgmp','-lquadmath','-ldl','-pthread','-o',str(root/'scan')]
        subprocess.run(cmd,check=True)
        subprocess.run([str(root/'scan'),'--tables',str(root/'boys.tbl'),str(root/'exp.tbl'),str(a.workers)],check=True)
        recipe=dict(protocol='upward-window-v1',final=FINAL,window=WINDOW,denominator=1000000,
                    command=cmd,compiler=subprocess.check_output([a.cxx,'--version'],text=True),
                    sources={str(f.relative_to(ROOT)):sha(f) for folder in ('benchmark/upward_recurrence','benchmark/library_accuracy','workflow/upward_recurrence_limits','workflow/library_accuracy') for f in (ROOT/folder).glob('*') if f.is_file()},
                    files={f.name:sha(f) for f in (root/'scan',root/'boys.tbl',root/'exp.tbl')})
        save(root/'run.json',dict(identity=identity(recipe),recipe=recipe));return
    record=json.loads((root/'run.json').read_text());recipe=record['recipe']
    if identity(recipe)!=record['identity'] or any(sha(root/k)!=v for k,v in recipe['files'].items()):raise ValueError('changed run artifacts')
    def scan(begin,end,dest):
        execution=bind(root,dict(scanner=str(root/'scan'),adapters=[]))
        if dest.exists():
            old=json.loads(dest.read_text())
            if (old['identity'],old['execution'],old['begin'],old['end'])!=(record['identity'],execution,begin,end):raise ValueError('stale shard')
            return
        with tempfile.TemporaryDirectory(prefix='fabo-upward-',dir=os.environ.get('SLURM_TMPDIR','/tmp')) as tmp:
            output=Path(tmp)/'scan.json'
            subprocess.run([str(root/'scan'),'--scan',str(root/'boys.tbl'),str(root/'exp.tbl'),str(begin),str(end),str(output)],check=True)
            data=json.loads(output.read_text());data.update(identity=record['identity'],execution=execution)
            save(dest,data)
    if a.stage=='pilot':
        subprocess.run([str(root/'scan'),'--check',str(root/'boys.tbl'),str(root/'exp.tbl')],check=True)
        dest=root/'pilot';dest.mkdir(exist_ok=True)
        for begin in (1,1_000_000,127_999_000,745_000_000,999_999_000):scan(begin,min(begin+1000,FINAL+1),dest/f'{begin}.json')
        save(root/'pilot-complete.json',dict(identity=record['identity']));return
    if a.stage=='scan':
        if json.loads((root/'pilot-complete.json').read_text())['identity']!=record['identity']:raise ValueError('pilot missing')
        dest=root/'shards';dest.mkdir(exist_ok=True)
        def one(i):scan(1+i*250000,min(1+(i+1)*250000,FINAL+1),dest/f'{i}.json')
        if a.group*a.workers>=4000:raise ValueError('group outside domain')
        with ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(one,range(a.group*a.workers,min((a.group+1)*a.workers,4000))))
        return
    if a.stage=='cluster':
        q=shlex.quote;groups=(4000+a.workers-1)//a.workers
        common=f'#!/bin/bash\nset -euo pipefail\ncd {q(str(ROOT))}\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n'
        (root/'array.sh').write_text(common+f'{q(sys.executable)} -m workflow.upward_recurrence_limits scan --run {q(str(root))} --workers {a.workers} --group "$SLURM_ARRAY_TASK_ID"\n')
        (root/'report.sh').write_text(common+f'{q(sys.executable)} -m workflow.upward_recurrence_limits report --run {q(str(root))}\n')
        cmd=['sbatch','--parsable','--nodes=1',f'--cpus-per-task={a.workers}','--mem=16G','--time=240',f'--partition={a.partition}',f'--exclude={a.exclude}',f'--output={root}/slurm-%A_%a.log']
        array=cmd+[f'--array=0-{groups-1}%8',str(root/'array.sh')]
        if not a.submit:print(shlex.join(array));return
        job=subprocess.check_output(array,text=True).strip().split(';')[0]
        report=subprocess.check_output(cmd+[f'--dependency=afterok:{job}',str(root/'report.sh')],text=True).strip()
        save(root/'jobs.json',dict(array=job,report=report));return
    execution=identity(json.loads((root/'execution.json').read_text()))
    def shards():
        for i in range(4000):
            d=json.loads((root/'shards'/f'{i}.json').read_text())
            if d['identity']!=record['identity'] or d['execution']!=execution:raise ValueError('incompatible shard')
            yield d
    rows=reduce_windows(shards());save(root/'boundaries.json',rows);csv_write(root/'boundaries.csv',rows)
    plot(rows,root/'upward-recurrence-limits.pdf')
    save(root/'complete.json',dict(identity=record['identity'],execution=execution,inputs=FINAL,files={name:sha(root/name) for name in ('boundaries.json','boundaries.csv','upward-recurrence-limits.pdf')}))

if __name__=='__main__':main()

"""Prepare a Slurm array and dependent report; submit only on explicit request."""
import argparse
import json
import shlex
import subprocess
from pathlib import Path
from .core import ROOT,save

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--python',required=True)
    p.add_argument('--partition',required=True);p.add_argument('--node');p.add_argument('--exclude');p.add_argument('--gpu',action='store_true')
    p.add_argument('--concurrency',type=int,default=8);p.add_argument('--minutes',type=int,default=240);p.add_argument('--submit',action='store_true')
    p.add_argument('--workers',type=int,default=1,help='independent scan processes per allocation; use e.g. 8 on a GPU node')
    a=p.parse_args();root=a.run.resolve();record=json.loads((root/'run.json').read_text())
    if a.concurrency<1 or a.minutes<1 or a.workers<1:raise ValueError('invalid resources')
    q=shlex.quote
    common=f'cd {q(str(ROOT))}\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n'
    script=root/'array.sh'
    script.write_text('#!/bin/bash\nset -euo pipefail\n'+common+f'{q(a.python)} -m workflow.library_accuracy.group --run {q(str(root))} --workers {a.workers} --group "$SLURM_ARRAY_TASK_ID"\n')
    report=root/'report.sh'
    report.write_text('#!/bin/bash\nset -euo pipefail\n'+common+f'{q(a.python)} -m workflow.library_accuracy report --run {q(str(root))}\n')
    command=['sbatch','--parsable','--nodes=1','--ntasks=1',f'--cpus-per-task={a.workers}',f'--mem={4*a.workers}G',f'--partition={a.partition}',f'--time={a.minutes}',f'--output={root}/slurm-%A_%a.log']
    if a.node:command+=['--nodelist='+a.node]
    if a.exclude:command+=['--exclude='+a.exclude]
    groups=(len(record['recipe']['shards'])+a.workers-1)//a.workers
    array=command+[f'--array=0-{groups-1}%{1 if a.gpu else a.concurrency}']
    if a.gpu:array+=['--gpus=1']
    array+=[str(script)]
    if not a.submit:
        print(shlex.join(array));return
    job=subprocess.check_output(array,text=True).strip().split(';')[0]
    merge=subprocess.check_output(command+['--dependency=afterok:'+job,str(report)],text=True).strip()
    save(root/'jobs.json',dict(array=job,report=merge,command=array))
if __name__=='__main__':main()

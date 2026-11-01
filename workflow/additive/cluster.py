"""Prepare a detached Slurm array and dependent merge; submit only with --submit."""
import argparse
from pathlib import Path
import shlex
import subprocess
from .search import atomic_json, identity, validate
import json


def node_restriction(partition, allowed):
    """--nodelist is an allocation request, not a pool of eligible hosts."""
    available=set(subprocess.check_output(['sinfo','-h','-N','-p',partition,'-o','%N'],text=True).split())
    requested=set(allowed.split(','))
    if not requested <= available:
        raise ValueError('requested nodes not in partition: '+','.join(sorted(requested-available)))
    excluded=available-requested
    return ['--exclude='+','.join(sorted(excluded))] if excluded else []


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--python',required=True)
    p.add_argument('--shards',type=int,default=128)
    p.add_argument('--concurrency',type=int,default=32)
    p.add_argument('--workers',type=int,default=8)
    p.add_argument('--nodes',default='c021,c022,c023,c024,c025,c026,c027,c028')
    p.add_argument('--partition',default='6526Y')
    p.add_argument('--submit',action='store_true')
    a=p.parse_args()
    if min(a.shards,a.concurrency,a.workers)<1:
        p.error('positive resource counts required')
    config=json.loads(a.config.read_text())
    validate(config)
    for field in (a.nodes,a.partition):
        if any(c.isspace() for c in field):
            p.error('invalid scheduler name')
    root=a.output.resolve()
    root.mkdir(parents=True,exist_ok=True)
    config_path=root/'config.json'
    if config_path.exists() and json.loads(config_path.read_text())!=config:
        raise ValueError('existing campaign has different configuration')
    atomic_json(config_path,config)
    q=shlex.quote
    repo=q(str(a.repo.resolve()))
    python=q(a.python)
    command=f'{python} -m workflow.additive.search --config {q(str(config_path))}'
    script='''#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
'''+f'cd {repo}\n'+f'run_root={q(str(root))}\n'+'''destination="$run_root/shard-$SLURM_ARRAY_TASK_ID"
mkdir -p "$destination"
# Expanded coefficient arrays are only bounded in-process caches. Journals and
# metadata use node-local scratch and are published on normal/error termination.
scratch=$(mktemp -d "${SLURM_TMPDIR:-/tmp}/fabo-additive.XXXXXXXX")
publish() { rsync -a "$scratch/" "$destination/"; }
trap publish EXIT
rsync -a "$destination/" "$scratch/"
'''+command+f' --workers {a.workers} --shards {a.shards} --shard "$SLURM_ARRAY_TASK_ID" --output "$scratch"\n'
    # Source identity is recomputed on the remote producer; use one frozen checkout.
    (root/'array.sh').write_text(script)
    (root/'merge.sh').write_text('#!/bin/bash\nset -euo pipefail\n'+f'cd {repo}\n'+command+f' --merge --shards {a.shards} --output {q(str(root))}\n')
    restriction=node_restriction(a.partition,a.nodes) if a.submit else []
    common=['sbatch','--parsable','--partition='+a.partition,'--nodes=1','--ntasks=1',*restriction,'--time=24:00:00']
    array=common+[f'--array=0-{a.shards-1}%{a.concurrency}',f'--cpus-per-task={a.workers}','--mem=32G','--output='+str(root/'array-%A_%a.log'),str(root/'array.sh')]
    if not a.submit:
        print(shlex.join(array))
        print('Submission will validate eligible nodes and exclude other partition hosts: '+a.nodes)
        print('Prepared only; rerun with --submit on the cluster login node.')
        return
    job=subprocess.check_output(array,text=True).strip().split(';')[0]
    merge=subprocess.check_output(common+['--dependency=afterok:'+job,'--cpus-per-task=1','--mem=8G','--output='+str(root/'merge-%j.log'),str(root/'merge.sh')],text=True).strip()
    atomic_json(root/'jobs.json',dict(array=job,merge=merge))
    print('array',job,'merge',merge)


if __name__=='__main__':
    main()

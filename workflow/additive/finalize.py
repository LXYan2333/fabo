"""Slurm-dependent aggregation with at most two retries of incomplete tasks."""
import json
from pathlib import Path
import subprocess
import sys
from .search import atomic_json, identity


def main():
    root=Path(sys.argv[1])
    spec=json.loads((root/'submission.json').read_text())
    config=json.loads((root/'config.json').read_text())
    expected=identity(config)
    missing=[]
    for i in range(spec['shards']):
        path=root/f'shard-{i}'/'summary.json'
        try:
            record=json.loads(path.read_text())
            complete=record.get('complete') and record.get('identity')==expected
        except (OSError,ValueError):
            complete=False
        if not complete:
            missing.append(i)
    if not missing:
        subprocess.run([spec['python'],'-m','workflow.additive.search','--config',str(root/'config.json'),
                        '--output',str(root),'--merge','--shards',str(spec['shards'])],check=True)
        return
    if spec['attempt']>=spec['maximum_retries']:
        atomic_json(root/'incomplete.json',dict(tasks=missing,attempt=spec['attempt']))
        raise SystemExit('Incomplete tasks remain after retry limit')
    command=[arg for arg in spec['array'] if not arg.startswith('--array=')]
    command.insert(-1,'--array='+','.join(map(str,missing))+'%'+str(spec['concurrency']))
    job=subprocess.check_output(command,text=True).strip().split(';')[0]
    spec['attempt']+=1
    atomic_json(root/'submission.json',spec)
    merge=subprocess.check_output(spec['common']+['--dependency=afterany:'+job,'--cpus-per-task=1',
             '--mem=8G','--output='+str(root/'merge-%j.log'),str(root/'merge.sh')],text=True).strip()
    atomic_json(root/'jobs.json',dict(array=job,merge=merge,attempt=spec['attempt']))


if __name__=='__main__':
    main()

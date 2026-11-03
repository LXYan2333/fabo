"""Write Slurm stage scripts for a prepared comparison; never submit implicitly."""
import argparse
import json
from pathlib import Path
import shlex


def write_scripts(run, repo, config):
    run,repo=Path(run).resolve(),Path(repo).resolve()
    q=shlex.quote
    for stage in ('build','smoke','size','benchmark','reference'):
        building=stage=='build'
        node=config['build_node' if building else 'timing_node']
        partition=config.get('partition','6526Y')
        if any(c.isspace() for c in node+partition) or '\n' in str(run):
            raise ValueError('invalid scheduler path/name')
        command=[config['python'],'-m','workflow.nwchem_compare',stage,'--run',str(run)]
        script=['#!/bin/bash',f'#SBATCH --job-name=fabo-nw-{stage}',
                f'#SBATCH --partition={partition}',f'#SBATCH --nodelist={node}',
                '#SBATCH --nodes=1','#SBATCH --ntasks=1',
                f'#SBATCH --cpus-per-task={config["build_workers"] if building else 1}',
                '#SBATCH --mem=64G','#SBATCH --time=24:00:00',
                f'#SBATCH --output={q(str(run/(stage+"-%j.log")))}']
        if not building:script.append('#SBATCH --exclusive')
        script+=['set -euo pipefail',f'cd {q(str(repo))}',shlex.join(command)]
        if stage=='benchmark':
            script.append(shlex.join([config['python'],'-m','workflow.nwchem_compare','report','--run',str(run)]))
        (run/(stage+'.sbatch')).write_text('\n'.join(script)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    a=p.parse_args()
    write_scripts(a.run,a.repo,json.loads((a.run/'config.json').read_text()))
    print('Scripts prepared only. Submit build -> smoke -> size -> benchmark -> reference with afterok dependencies.')


if __name__=='__main__':main()

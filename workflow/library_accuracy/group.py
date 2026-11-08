"""Run bounded shard workers inside one allocation, sharing its GPU if present."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--group',type=int,required=True);p.add_argument('--workers',type=int,required=True)
    a=p.parse_args();count=len(json.loads((a.run/'run.json').read_text())['recipe']['shards'])
    if a.workers<1 or a.group<0:raise ValueError('invalid worker group')
    shards=range(a.group*a.workers,min(count,(a.group+1)*a.workers))
    def one(index):subprocess.run([sys.executable,'-m','workflow.library_accuracy','scan','--run',str(a.run),'--shard',str(index)],check=True)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(one,shards))
if __name__=='__main__':main()

"""Bounded build/reference/adapter pilot, suitable for an allocated Slurm node."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from .core import save
from .suite import build, validated_coverage

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();config=json.loads(a.config.read_text())
    _,orders=validated_coverage(config)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    scanner=out/'scan';cmd=[sys.executable,'-m','workflow.library_accuracy.build','--cxx',config['cxx'],'--output',str(scanner)]
    for path in config.get('reference_include',[]):cmd+=['--include',path]
    for path in config.get('reference_lib',[]):cmd+=['--lib',path]
    subprocess.run(cmd,check=True)
    table=out/'reference.bin'
    subprocess.run([str(scanner),'--table',str(table),str(max(orders)),'24','0.25','1000','256',str(config.get('workers',2))],check=True)
    subprocess.run([str(scanner),'--check-reference',str(table)],check=True)
    config.update(scanner=str(scanner),reference_table=str(table))
    build(config,out/'suite')
    subprocess.run([sys.executable,'-m','workflow.library_accuracy','prepare','--config',str(out/'suite/scan-config.json'),'--run',str(out/'run')],check=True)
    subprocess.run([sys.executable,'-m','workflow.library_accuracy','pilot','--run',str(out/'run')],check=True)
    save(out/'complete.json',dict(status='pilot-complete',full_scan_launched=False))
if __name__=='__main__':main()

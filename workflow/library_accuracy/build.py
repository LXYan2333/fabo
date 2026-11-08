"""Build the strict scanner. User-supplied include/library flags are explicit."""
import argparse
import subprocess
from pathlib import Path
from .core import ROOT,save,sha

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cxx',default='g++');p.add_argument('--include',action='append',default=[]);p.add_argument('--lib',action='append',default=[])
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    command=[a.cxx,'-std=c++17','-O2','-fno-fast-math','-ffp-contract=off','-fno-lto',*[f'-I{x}' for x in a.include],str(ROOT/'benchmark/library_accuracy/scan.cc'),*[f'-L{x}' for x in a.lib],*[f'-Wl,-rpath,{x}' for x in a.lib],'-lmpfr','-lgmp','-lquadmath','-ldl','-pthread','-o',str(a.output)]
    subprocess.run(command,check=True)
    save(a.output.with_suffix('.build.json'),dict(command=command,compiler=subprocess.check_output([a.cxx,'--version'],text=True),sha256=sha(a.output)))
if __name__=='__main__':main()

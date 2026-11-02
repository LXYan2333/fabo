"""Export the pinned QUICK source and apply the selected Boys binding."""
import argparse
import subprocess
import tarfile
from pathlib import Path

from benchmark.quick.patch_quick import ROOT, PIN, VARIANTS, patch


def prepare(output, variant, probe=False, upstream=None, training=False):
    output=Path(output).resolve()
    upstream=Path(upstream or ROOT/'third_party/quick').resolve()
    if variant not in VARIANTS:
        raise ValueError('unsupported variant')
    if probe and training:
        raise ValueError('choose fixed-density probe or SCF training, not both')
    revision=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
    if revision!=PIN:
        raise ValueError('QUICK revision differs from the pinned source')
    if subprocess.check_output(['git','-C',str(upstream),'status','--porcelain'],text=True).strip():
        raise ValueError('QUICK submodule is dirty; export only a clean pinned tree')
    output.mkdir(parents=True,exist_ok=False)
    # Stream the pinned source; no second tarball or expanded source cache.
    with subprocess.Popen(['git','-C',str(upstream),'archive',PIN],stdout=subprocess.PIPE) as proc:
        with tarfile.open(fileobj=proc.stdout,mode='r|') as archive:
            archive.extractall(output,filter='data')
        if proc.wait():
            raise RuntimeError('QUICK git archive failed')
    return patch(output,variant,probe,training)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',choices=VARIANTS,required=True)
    parser.add_argument('--output',type=Path,required=True,help='new disposable QUICK source directory')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--probe',action='store_true',help='add optional fixed-density one-update harness')
    mode.add_argument('--scf-training',action='store_true',help='record official convergence or replay a fixed-length SCF trajectory')
    args=parser.parse_args()
    prepare(args.output,args.variant,args.probe,training=args.scf_training)
    print(args.output/'fabo-variant.json')


if __name__=='__main__':
    main()

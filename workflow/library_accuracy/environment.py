"""Execution compatibility, independent of hostname and allocation size."""
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
from .core import sha,identity

def capture(recipe):
    cpu={}
    for line in Path('/proc/cpuinfo').read_text().split('\n\n')[0].splitlines():
        key,_,value=line.partition(':')
        if key.strip() in ('vendor_id','cpu family','model','model name','stepping','microcode','flags'):cpu[key.strip()]=value.strip()
    libs={}
    for binary in [recipe['scanner'],*[r['path'] for r in recipe['adapters']]]:
        result=subprocess.run(['ldd',binary],text=True,capture_output=True,check=True)
        if 'not found' in result.stdout:raise RuntimeError('unresolved runtime library: '+result.stdout)
        for path in re.findall(r'(/[^\s()]+)',result.stdout):
            if Path(path).is_file():libs[Path(path).name]=sha(path)
    gpu=None
    if any(r.get('platform')=='cuda' for r in recipe['adapters']):
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,compute_cap','--format=csv,noheader'],text=True).strip()
        if not gpu:raise RuntimeError('no visible GPU inventory')
    if os.environ.get('LD_PRELOAD') or os.environ.get('LD_AUDIT'):
        raise RuntimeError('preloaded libraries are not allowed in the scan')
    return dict(machine=platform.machine(),kernel=platform.release(),cpu=cpu,libraries=libs,gpu=gpu,
                cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),rounding='RN-even',host_ftz=False,host_daz=False)

def bind(root,recipe):
    current=capture(recipe);path=root/'execution.json'
    # Bind only once even when many array elements start simultaneously.
    with tempfile.NamedTemporaryFile(mode='w',dir=root,delete=False) as f:
        json.dump(current,f,sort_keys=True);temp=Path(f.name)
    try:
        try:os.link(temp,path)
        except FileExistsError:pass
    finally:temp.unlink()
    if json.loads(path.read_text())!=current:
        raise RuntimeError('execution environment differs; use a separate run')
    return identity(current)

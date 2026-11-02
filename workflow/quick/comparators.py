"""Prepare author tables and run untimed adapter checks, outside molecular timers."""
import json
from pathlib import Path
import shutil

from .calibrate import command, clean_environment, write_json
from .s66 import sha


def prepare_tables(root, config, scratch):
    bundle=root/'bundle'; src=bundle/'benchmark/quick'; out=root/'tables'
    out.mkdir(exist_ok=True); marker=out/'complete.json'
    if marker.exists():
        for name,digest in json.loads(marker.read_text()).items():
            if sha(out/name)!=digest: raise ValueError('changed comparator table: '+name)
        return
    for variant,source,includes in (
        ('libintx_gpu','libintx_table.cc',['third_party/libintx/src','third_party/eigen3']),
        ('gansu','gansu_table.cc',['third_party/gansu/upstream'])):
        executable=scratch/(variant+'-table')
        command([config['cxx'],'-std=c++20','-O2',*[('-I'+str(bundle/p)) for p in includes],
                 src/source,'-o',executable],out/(variant+'-build.log'),env=clean_environment())
        command([executable,out/(variant+'.bin')],out/(variant+'-generate.log'),env=clean_environment())
    expected={'libintx_gpu.bin':8*13*819*8,'gansu.bin':30720*8}
    if any((out/name).stat().st_size!=size for name,size in expected.items()):
        raise ValueError('wrong comparator table size')
    write_json(marker,{name:sha(out/name) for name in expected})


def conformance(root, saved, scratch):
    config=saved['recipe']['config']; spec=saved['recipe']['comparison']
    bundle=root/'bundle'; src=bundle/'benchmark/quick'; out=root/'conformance'
    out.mkdir(exist_ok=True); marker=out/'complete.json'
    if marker.exists():
        record=json.loads(marker.read_text())
        if record['identity']!=saved['identity']: raise ValueError('changed conformance identity')
        for name,digest in record['files'].items():
            if sha(out/name)!=digest: raise ValueError('changed conformance record')
        return
    supplied=bundle/'third_party/vsr/supplied'
    original=(supplied/'minimax.c').read_text()
    if original.count('void minimax(')!=1: raise ValueError('VSR oracle context changed')
    (scratch/'vsr_supplied_device.h').write_text(original.replace('void minimax(', '__device__ void VsrSuppliedDevice(',1))
    api=scratch/'libintx/gpu/api'; api.mkdir(parents=True)
    (api/'config.h').write_text('#define LIBINTX_GPU_API_CUDA 1\n')
    records={}
    for variant in spec['variants']:
        if variant=='official': continue
        if variant=='fabo_additive':
            source=src/'additive_conformance.cu'
            extra=[root/'variants/fabo_additive/source/src/gpu/additive_host.cc']
            includes=[root/'variants/fabo_additive/source/src/gpu']; args=[]; strict=[]
        elif variant=='libintx_gpu':
            source=src/'libintx_conformance.cu'; extra=[]
            includes=[scratch,bundle/'third_party/libintx/src']; args=[root/'tables/libintx_gpu.bin']; strict=[]
        elif variant=='vsr':
            source=src/'vsr_conformance.cu'; extra=[]
            includes=[supplied,scratch]; args=[]; strict=['-DFABO_VSR_STRICT_CHECK']
        else:
            source=src/'gansu_conformance.cu'; extra=[]
            includes=[bundle/'third_party/gansu/upstream/include']; args=[root/'tables/gansu.bin']; strict=['-DFABO_GANSU_STRICT_CHECK']
        for mode,flags in [('strict',['--fmad=false',*strict]),('fast',['--use_fast_math'])]:
            name=variant+'-'+mode; executable=scratch/name
            standard='-std=c++20' if variant=='libintx_gpu' else '-std=c++17'
            cmd=[config['cuda']+'/bin/nvcc','-ccbin',config['cxx'],standard,'-O3',
                 '-arch='+spec['cuda_arch'],*flags,'-I'+str(src),
                 *['-I'+str(p) for p in includes]]
            if config['enable_f'] and variant=='fabo_additive': cmd+=['-DENABLEF']
            cmd += [source,*extra,'-o',executable]
            command(cmd,out/(name+'-build.log'),env=clean_environment())
            command([executable,*args],out/(name+'.log'),env=clean_environment(),timeout=300)
            records[name]={'command':list(map(str,cmd)), 'binary_sha256':sha(executable),
                           'output':(out/(name+'.log')).read_text()}
    write_json(out/'results.json',records)
    write_json(marker,{'identity':saved['identity'],'files':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p!=marker}})

"""The conformance probe must use the built variant, not an adjacent old binding."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from workflow.quick import comparators as c


def test_additive_checker_uses_variant_headers(tmp_path, monkeypatch):
    compiler=shutil.which('c++')
    if not compiler: pytest.skip('C++ preprocessor unavailable')
    root=tmp_path/'run';src=root/'bundle/benchmark/quick';src.mkdir(parents=True)
    gpu=root/'variants/fabo_additive/source/src/gpu';gpu.mkdir(parents=True)
    scratch=tmp_path/'scratch';scratch.mkdir()
    supplied=root/'bundle/third_party/vsr/supplied';supplied.mkdir(parents=True)
    (supplied/'minimax.c').write_text('void minimax() {}\n')
    checker='#include "additive_runtime.cuh"\nint selected = VARIANT_BINDING;\n'
    (src/'additive_conformance.cu').write_text(checker)
    (src/'additive_runtime.cuh').write_text('#error stale bundled runtime selected\n')
    (src/'additive_binding.cuh').write_text('#error stale bundled binding selected\n')
    (gpu/'additive_runtime.cuh').write_text('#include "additive_binding.cuh"\n')
    (gpu/'additive_binding.cuh').write_text('#define VARIANT_BINDING 123\n')
    (gpu/'additive_host.cc').write_text('')
    builds=[]
    def command(args,log,**kwargs):
        args=list(map(str,args))
        if '-o' in args:
            builds.append(args)
            paths=[a for a in args if a.startswith('-I')]
            source=Path(args[args.index('-o')-2])
            assert source==scratch/'additive_conformance.cu'
            assert paths[0]=='-I'+str(gpu)
            result=subprocess.run([compiler,'-E','-P','-x','c++',*paths,str(source)],
                                  text=True,capture_output=True,check=True)
            assert 'int selected = 123;' in result.stdout
            Path(args[args.index('-o')+1]).write_bytes(b'fake compiled checker')
        Path(log).write_text('PASS\n')
    monkeypatch.setattr(c,'command',command)
    saved=dict(identity='fixture',recipe=dict(config=dict(cuda='/cuda',cxx=compiler,enable_f=False),
        comparison=dict(variants=['fabo_additive'],cuda_arch='sm_120')))
    c.conformance(root,saved,scratch)
    assert len(builds)==2
    assert (src/'additive_conformance.cu').read_text()==checker
    assert json.loads((root/'conformance/complete.json').read_text())['identity']=='fixture'

import json
import pytest
from workflow.library_accuracy.suite import cpu_source,cuda_source,BACKENDS
from workflow.library_accuracy import environment
from workflow.library_accuracy import pilot_job

@pytest.mark.parametrize('backends,orders',[
    (['fabo'],[-1]), (['fabo'],[240]), (['fabo'],[]),
    (['fabo','simint'],[24]),
])
def test_invalid_pilot_coverage_stops_before_build(tmp_path,monkeypatch,backends,orders):
    config=tmp_path/'config.json'
    config.write_text(json.dumps(dict(platform='cpu',backends=backends,orders=orders)))
    out=tmp_path/'pilot'
    monkeypatch.setattr(pilot_job.sys,'argv',['pilot','--config',str(config),'--output',str(out)])
    monkeypatch.setattr(pilot_job.subprocess,'run',lambda *a,**kw:pytest.fail('unexpected subprocess'))
    with pytest.raises(ValueError,match='invalid coverage'):
        pilot_job.main()
    assert not out.exists()

@pytest.mark.parametrize('n',range(13))
@pytest.mark.parametrize('backend',BACKENDS['cpu'])
def test_cpu_order_coverage(n,backend):
    source=cpu_source(n,backend)
    assert 'boys_accuracy' in source
    if backend=='libintx':assert f'values[{n+1}]{{}}' in source # upstream uses +=
    if backend=='simint':assert f'boys_F_split(values,_mm512_load_pd(buf),{n})' in source

@pytest.mark.parametrize('n',range(13))
@pytest.mark.parametrize('backend',BACKENDS['cuda'])
def test_cuda_order_coverage(n,backend,tmp_path):
    source=cuda_source(n,backend,tmp_path/'table.bin' if backend in ('libintx','gansu') else None)
    assert 'boys_accuracy' in source
    if backend!='fabo':assert 'cudaMemcpy2D' in source # pitched partial final block
    if backend=='quick':assert '#include "gpu_fmt.h"' in source
    assert str(tmp_path) not in source

def test_environment_binding(tmp_path,monkeypatch):
    current={'cpu':'a','libraries':{'libm':'first'}}
    monkeypatch.setattr(environment,'capture',lambda _:current.copy())
    first=environment.bind(tmp_path,{})
    assert environment.bind(tmp_path,{})==first
    current['libraries']={'libm':'changed'}
    with pytest.raises(RuntimeError,match='environment differs'):environment.bind(tmp_path,{})

def test_optional_software_gather():
    assert 'make_evaluator<true>' in cpu_source(4,'fabo_software')

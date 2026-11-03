import json
from pathlib import Path
import struct

import numpy as np
import pytest

from benchmark.quick.patch_quick import patch
from workflow.quick.tests.test_binding import source_tree
from workflow.quick import fixed_density as f


def fixture(root):
    case={'id':'test','basis':'def2-SVP'}
    saved=dict(identity='test',recipe=dict(experiment=dict(rounds=5,max_reference_attempts=3,reference_python='python'),cases=[case]))
    folder=root/'fixtures/test';folder.mkdir(parents=True)
    (folder/'fixture.bin').write_bytes(struct.pack('<iii',1,1,2)+bytes(32))
    selection=dict(case=case,dimensions=[1,1,2],basis={'name':'DEF2-SVP'},fixture_sha256=f.sha(folder/'fixture.bin'))
    for name in ('fixture-info.txt','input.in','input.out','process.log'):
        (folder/name).write_text('fixture')
    (folder/'fixture.json').write_text(json.dumps(selection))
    f.complete(folder,'test')
    (root/'selected-case.json').write_text(json.dumps(selection))
    return saved,selection


def observation(folder,value,untimed):
    value=float(value)
    folder.mkdir(parents=True,exist_ok=True)
    np.array([value,value],dtype='<f8').tofile(folder/'outputs.bin')
    for name in ('input.in','input.out','process.log'):
        (folder/name).write_text('sample')
    if untimed:
        (folder/'check-energy.txt').write_text(repr(value))
    else:
        (folder/'timings.csv').write_text(f'iteration,fock_seconds,iteration_seconds,energy_diagnostic\n1,.1,.2,{value!r}\n')


def cached_sample(root,selection,v,r,value=1.):
    p=root/'samples'/f'{r:02d}'/v
    observation(p,value,v=='reference')
    if v=='reference':(p/'overrides.bin').write_bytes(b'')
    data=f.read_sample(p,1,v=='reference')
    data.update(variant=v,round=r,basis=selection['basis'],fixture_sha256=selection['fixture_sha256'],
                replay_sha256=selection['fixture_sha256'],overrides_sha256=f.sha(p/'overrides.bin') if v=='reference' else None)
    (p/'result.json').write_text(json.dumps(data));f.complete(p,'test')
    return p


def test_reference_patch_is_untimed_and_fail_closed(tmp_path):
    root=source_tree(tmp_path)
    with pytest.raises(ValueError,match='untimed'):
        patch(root,'reference',training=True)
    manifest=patch(root,'reference',probe=True)
    assert manifest['variant']=='reference'
    text=(root/'src/gpu/gpu_get2e_subs.h').read_text()
    assert text.count('FaboReferenceFmT(I + J + K + L,')==2
    runtime=(root/'src/gpu/probe_runtime.h').read_text()
    assert 'fabo_reference_check();' in runtime
    assert '#define FABO_QUICK_REFERENCE 1' in (root/'src/gpu/cuda/gpu_get2e.cu').read_text()
    main=(root/'src/main.f90').read_text()
    assert "trim(fabo_mode) == 'prepare' .and. trim(fabo_guess) == 'sad'" in main
    probe=(root/'src/modules/quick_scf_module.f90').read_text()
    assert probe.index('p0 = quick_qm_struct%dense') < probe.index('quick_qm_struct%dense = 0.0d0')
    assert probe.index("file='replayed-fixture.bin'") < probe.index('call fabo_probe_clock(begin_time)')


def test_fixture_dimensions_and_outputs(tmp_path):
    p=tmp_path/'fixture.bin'
    p.write_bytes(struct.pack('<iii',2,1,2)+bytes(8*(3*4+2)))
    assert f.fixture_dimensions(p)==(2,1,2)
    p.write_bytes(p.read_bytes()+b'\0')
    with pytest.raises(ValueError):f.fixture_dimensions(p)
    out=tmp_path/'outputs.bin'
    np.arange(8,dtype='<f8').tofile(out)
    assert f.read_outputs(out,2).shape==(2,4)
    with pytest.raises(ValueError):f.read_outputs(out,3)
    np.full(8,np.nan).tofile(out)
    with pytest.raises(ValueError):f.read_outputs(out,2)


def test_untimed_rejects_timing_and_nonfinite(tmp_path):
    np.ones(2,dtype='<f8').tofile(tmp_path/'outputs.bin')
    (tmp_path/'check-energy.txt').write_text('-1.25')
    assert not f.read_sample(tmp_path,1,True)['timed']
    (tmp_path/'timings.csv').write_text('iteration,fock_seconds,iteration_seconds,energy_diagnostic\n1,.1,.2,-1.25\n')
    with pytest.raises(ValueError,match='unexpectedly'):f.read_sample(tmp_path,1,True)
    assert f.read_sample(tmp_path,1,False)['fock_seconds']==.1


def test_means_use_all_reference_repetitions_and_keep_subulp_offsets(tmp_path):
    from benchmark.quick.patch_quick import VARIANTS
    saved,selection=fixture(tmp_path)
    one=np.nextafter(1.,2.)
    for v in (*VARIANTS,'reference'):
        for r in range(5):
            value=one if v=='reference' and r==4 else 1.
            cached_sample(tmp_path,selection,v,r,value)
    f.report(tmp_path,saved,True)
    result=json.loads((tmp_path/'summary.json').read_text())
    assert 'timing' not in result['variants']['reference']
    assert result['variants']['official']['energy_mean_difference']==-(one-1)/5
    lo=np.fromfile(tmp_path/'reference-mean/lo.bin',dtype='<f8')
    assert lo[0]==(one-1)/5
    assert result['reference_matrix_sd_max']['density']>0
    assert result['variants']['official']['max_matrix_difference_from_reference_mean']['density']==(one-1)/5


@pytest.mark.parametrize('field,value',[('variant','vsr'),('round',4),('timed',False),
    ('fixture_sha256','wrong'),('replay_sha256','wrong'),('basis',{}),('overrides_sha256','wrong')])
def test_cached_sample_rejects_wrong_semantic_identity(tmp_path,field,value):
    saved,selection=fixture(tmp_path)
    p=cached_sample(tmp_path,selection,'official',0)
    row=json.loads((p/'result.json').read_text());row[field]=value
    (p/'result.json').write_text(json.dumps(row));f.complete(p,'test')
    with pytest.raises(ValueError,match='semantic identity'):
        f.run_sample(tmp_path,saved,selection['case'],selection,'official',0,None,tmp_path)


def test_required_sample_files_and_selected_fixture(tmp_path):
    saved,selection=fixture(tmp_path)
    p=cached_sample(tmp_path,selection,'official',0)
    (p/'outputs.bin').unlink();f.complete(p,'test')
    with pytest.raises(ValueError,match='file set'):
        f.checked_sample(p,saved,selection,'official',0)
    assert f.selected_case(tmp_path,saved)==selection
    selection['dimensions']=[2,2,2]
    (tmp_path/'selected-case.json').write_text(json.dumps(selection))
    with pytest.raises(ValueError,match='fixture identity'):f.selected_case(tmp_path,saved)


def test_failed_timed_attempt_is_retried_without_overwriting(tmp_path,monkeypatch):
    saved,selection=fixture(tmp_path)
    attempt=tmp_path/'samples/00/official/attempts/00';attempt.mkdir(parents=True)
    (attempt/'process.log').write_text('old failure')
    calls=[]
    def invoke(root,saved,case,v,mode,fixture,build,local,overrides):
        calls.append(mode);observation(local,1.,False)
        (local/'replayed-fixture.bin').write_bytes(fixture.read_bytes())
        return selection['basis']
    monkeypatch.setattr(f,'invoke',invoke)
    row=f.run_sample(tmp_path,saved,selection['case'],selection,'official',0,None,tmp_path)
    assert row['timed'] and calls==['run']
    assert (attempt/'process.log').read_text()=='old failure'


@pytest.mark.parametrize('already_replaced',[False,True])
def test_resume_pending_mpfr_transaction(tmp_path,monkeypatch,already_replaced):
    saved,_=fixture(tmp_path)
    destination=tmp_path/'samples/00/reference'
    attempt=destination/'attempts/00';attempt.mkdir(parents=True)
    (attempt/'attempt.json').write_text(json.dumps({'exit_code':86}))
    (attempt/'reference-unresolved.bin').write_bytes(struct.pack('<QQ',0,0))
    encoded=struct.pack('<QQQ',0,0,0x3ff0000000000000)
    (destination/'overrides.bin').write_bytes(encoded if already_replaced else b'')
    calls=[]
    def command(args,*unused,**kwargs):
        calls.append(args);Path(args[4]).write_bytes(encoded)
    monkeypatch.setattr(f.c,'command',command)
    f.resolve_pending(tmp_path,saved,destination)
    assert len(calls)==(0 if already_replaced else 1)
    assert (destination/'overrides.bin').read_bytes()==encoded
    assert (attempt/'resolved.json').exists()
    f.resolve_pending(tmp_path,saved,destination)
    assert len(calls)==(0 if already_replaced else 1)

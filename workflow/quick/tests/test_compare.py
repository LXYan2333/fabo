import json
from pathlib import Path
import shutil

import pytest
from benchmark.quick.patch_quick import ROOT, PIN
from workflow.quick import calibrate as c
from workflow.quick import compare as b
from workflow.quick import archive as a
from workflow.quick.s66 import sha


def config():
    return {'comparison':{'calibration_root':'/archive','calibration_sha256':'a'*64}}


def test_settings_schedule_and_summary():
    conf,spec=b.settings(config())
    assert spec['rounds']==5
    assert conf['enable_f'] is False
    for bad in ({'rounds':1},{'build_workers':17},{'variants':['gansu','official']},
                {'variants':['official','official']},{'calibration_sha256':'bad'}, {'cuda_arch':'bad'}):
        with pytest.raises(ValueError): b.settings({'comparison':config()['comparison']|bad})
    cases=[{'id':'a','basis':'6-31G*'},{'id':'b','basis':'def2-SVP'}]; variants=['official','gansu']
    schedule=list(b.schedule(cases,variants,3))
    assert [v for r,case,v in schedule if r==0]==['official','gansu','gansu','official']
    saved={'identity':'test','recipe':{'cases':cases,'rounds':3,'purpose':'comparison','comparison':{'variants':variants}}}
    rows=[dict(case=case['id'],variant=v,round=r,fock_seconds=1 if v=='official' else 2,
               scf_seconds=3,process_seconds=4,final_energy_hartree=-1.) for r,case,v in schedule]
    result=b.summarize(saved,rows)
    assert result['fock_ratio_geomean']['gansu']==2
    assert result['cases'][0]['timings']['official']['fock_seconds']['cv']==0
    with pytest.raises(ValueError,match='coverage'): b.summarize(saved,rows[:-1])
    with pytest.raises(ValueError,match='coverage'): b.summarize(saved,rows+[rows[0]])


def fixture(tmp_path):
    root=tmp_path/'run'; root.mkdir()
    geometry=root/'water.xyz'; geometry.write_text('2\nwater fixture\nH 0 0 0\nH 0 0 1\n')
    case={'id':'water','basis':'6-31G*','geometry':'water.xyz','sha256':sha(geometry)}
    basis=root/'variants/official/source/basis'; basis.mkdir(parents=True)
    (basis/'6-31GD.BAS').write_text('basis'); (basis/'basis_link').write_text('link')
    origin=tmp_path/'origin'; origin.mkdir(); directory=origin/'calibration/water'; directory.mkdir(parents=True)
    (directory/'initial.bin').write_bytes(b'state')
    (directory/'input.in').write_text(c.input_text(root,c.settings({}),case))
    row={'case':'water','variant':'official','fixed':False,'converged':True,'iterations':10,
         'fixture_sha256':sha(directory/'initial.bin'),
         'basis':{'name':'6-31G*','file':'6-31GD.BAS','sha256':sha(basis/'6-31GD.BAS'),'basis_link_sha256':sha(basis/'basis_link')}}
    c.write_json(directory/'case.json',case); c.write_json(directory/'result.json',row)
    for name in c.CASE_FILES:
        if not (directory/name).exists(): (directory/name).write_text('record')
    protocol=dict(schema=2,quick_commit=PIN,enable_f=False,max_scf_iterations=200,density_rms=1e-6,
                  sources={'benchmark/quick/'+name:sha(ROOT/'benchmark/quick'/name) for name in ('scf_training.f90','patch_scf_training.py')})
    c.write_json(origin/'scf-protocol.json',protocol); c.write_json(origin/'calibration.json',[row])
    marker={'identity':'old','artifacts':{str(p.relative_to(origin)):sha(p) for p in origin.rglob('*') if p.is_file()}}
    c.write_json(origin/'complete-scf-calibrate.json',marker)
    spec=config()['comparison']|{'calibration_root':str(origin),'calibration_sha256':sha(origin/'complete-scf-calibrate.json')}
    saved={'identity':'new','recipe':{'config':c.settings({}),'comparison':spec,'cases':[case]}}
    return root,origin,saved


def test_import_checks_all_states_and_survives_upstream_unavailable(tmp_path):
    root,origin,saved=fixture(tmp_path)
    record=a.checked_import(root,saved)
    assert record['rows'][0]['iterations']==10
    shutil.rmtree(origin)
    assert a.checked_import(root,saved)==record
    (root/'calibration/water/initial.bin').write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed imported'): a.checked_import(root,saved)


@pytest.mark.parametrize('field,value',[('iterations',99),('fixture_sha256','bad'),('basis',{})])
def test_import_rejects_metadata_only_change(tmp_path,field,value):
    root,origin,saved=fixture(tmp_path)
    record=a.checked_import(root,saved)
    record['rows'][0][field]=value
    c.write_json(root/'imported-calibration.json',record)
    with pytest.raises(ValueError,match='metadata'): a.checked_import(root,saved)


@pytest.mark.parametrize('name',['initial.bin','input.in','result.json'])
def test_import_rejects_corruption(tmp_path,name):
    root,origin,saved=fixture(tmp_path)
    (origin/'calibration/water'/name).write_text('corrupt')
    with pytest.raises(ValueError,match='changed calibration'): a.checked_import(root,saved)


def test_rejects_semantically_different_geometry(tmp_path):
    root,origin,saved=fixture(tmp_path)
    saved['recipe']['cases'][0]['sha256']='bad'
    with pytest.raises(ValueError,match='geometry/basis'): a.checked_import(root,saved)


def test_completed_sample_rejects_corruption(tmp_path):
    root=tmp_path; directory=root/'samples/00/water/gansu'; directory.mkdir(parents=True)
    reference={'iterations':10,'fixture_sha256':'fixture'}
    row={'case':'water','variant':'gansu','round':0,'iterations':10,
         'fixture_sha256':'fixture','replayed_initial_sha256':'fixture'}
    for name in b.SAMPLE_FILES: (directory/name).write_text('record')
    c.write_json(directory/'result.json',row)
    c.write_json(directory/'complete.json',{'identity':'run','files':{name:sha(directory/name) for name in b.SAMPLE_FILES}})
    saved={'identity':'run','recipe':{'config':{}}}
    assert b.sample(root,saved,{'id':'water'},reference,'gansu',0,(None,{}),None)==row
    with pytest.raises(ValueError,match='trajectory'):
        b.sample(root,saved,{'id':'water'},reference|{'iterations':99},'gansu',0,(None,{}),None)
    (directory/'result.json').write_text('changed')
    with pytest.raises(ValueError,match='changed fixed'): b.sample(root,saved,{'id':'water'},reference,'gansu',0,(None,{}),None)


def test_new_sample_verifies_replay_without_archiving_duplicate(tmp_path,monkeypatch):
    root,origin,saved=fixture(tmp_path)
    reference=a.checked_import(root,saved)['rows'][0]
    reference.update(dimensions=[2,2,2])
    case=saved['recipe']['cases'][0]
    def fake_command(args,log,*,cwd,env,timeout):
        assert env['FABO_SCF_TRAINING']=='fixed' and env['FABO_SCF_STEPS']=='10'
        assert sha(Path(env['FABO_SCF_STATE']))==reference['fixture_sha256']
        shutil.copyfile(env['FABO_SCF_STATE'],cwd/'replayed-initial.bin')
        (cwd/'input.out').write_text('output'); log.write_text('process log')
        (cwd/'scf-summary.txt').write_text('10 0 1\n3.0\n2 2 2\n')
        (cwd/'scf-iterations.csv').write_text('iteration,fock_seconds,iteration_seconds,energy_hartree,prms,pchange\n'+
                  ''.join(f'{i},0.1,0.2,-1.0,0.1,0.1\n' for i in range(1,11)))
        return 4.
    monkeypatch.setattr(c,'command',fake_command)
    monkeypatch.setattr(b,'verify_basis_output',lambda *args:reference['basis'])
    scratch=tmp_path/'scratch'; scratch.mkdir()
    result=b.sample(root,saved,case,reference,'official',0,(Path('/dummy/quick.cuda'),{}),scratch)
    assert result['iterations']==10
    assert result['replayed_initial_sha256']==reference['fixture_sha256']
    assert not list((root/'samples').rglob('*.bin'))
    assert b.sample(root,saved,case,reference,'official',0,(None,{}),None)==result

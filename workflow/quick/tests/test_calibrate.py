import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from benchmark.quick.patch_quick import ROOT, patch
from workflow.quick import calibrate as c
from workflow.quick.s66 import inventory, cases, SEPARATIONS
from workflow.quick.scf_records import read_result
from workflow.quick.tests.test_binding import source_tree


def dataset(tmp_path):
    root=tmp_path/'dataset'; (root/'dimers').mkdir(parents=True)
    for n in range(1,67):
        for label in SEPARATIONS:
            (root/'dimers'/f'{n:02d}_fixture_{label}.xyz').write_text('2\nfixture angstrom\nH 0 0 0\nH 0 0 1\n')
    return root


def test_inventory_and_settings(tmp_path):
    data=dataset(tmp_path); items=inventory(data)
    assert len(items)==528
    assert len(cases(items,['6-31G*','def2-SVP'],['1.00']))==132
    assert len(cases(items,['def2-SVP'],['0.90','2.00']))==132
    (data/'dimers/01_fixture_1.00.xyz').unlink()
    with pytest.raises(ValueError,match='exactly 66'):
        inventory(data)
    assert c.settings({})['max_scf_iterations']==200
    for bad in ({'bases':['def2-TZVP']}, {'enable_f':1}, {'separations':['1']},
                {'density_rms':0}, {'build_jobs':17}, {'warmup_iterations':2}):
        with pytest.raises(ValueError): c.settings(bad)


def test_training_patch_retains_diis_and_is_fail_closed(tmp_path):
    root=source_tree(tmp_path/'source')
    manifest=patch(root,'official',training=True)
    text=(root/'src/modules/quick_scf_module.f90').read_text()
    assert manifest['scf_training'] and not manifest['probe']
    assert '.not.fabo_scf_fixed .and. PRMS < quick_method%pmaxrms' in text
    assert 'if(.not.fabo_scf_fixed .and. jscf >= quick_method%iscf-1)' in text
    assert 'diisdone = fabo_scf_count >= fabo_scf_steps' in text
    assert 'call adjust_cutoff(PRMS,PCHANGE,quick_method,ierr)' in text
    assert text.count('call scf_operator(deltaO)')==1
    assert 'pmaxrms = 0' not in text
    assert (root/'src/gpu/gpu_get2e_subs.h').read_bytes()==(ROOT/'third_party/quick/src/gpu/gpu_get2e_subs.h').read_bytes()
    bad=source_tree(tmp_path/'bad')
    path=bad/'src/modules/quick_scf_module.f90'
    path.write_text(path.read_text().replace('     done = .false.','     ! changed context'))
    before={str(p):p.read_bytes() for p in bad.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='context changed'): patch(bad,'official',training=True)
    assert before=={str(p):p.read_bytes() for p in bad.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='not both'): patch(bad,'official',probe=True,training=True)


def test_prepare_portable_bundle(tmp_path,monkeypatch):
    data=dataset(tmp_path)
    def fake_prepare(dst,variant,training):
        assert variant=='official' and training
        dst.mkdir(); (dst/'source.txt').write_text('official fixture')
    monkeypatch.setattr(c,'prepare_quick',fake_prepare)
    root=tmp_path/'prepared'
    c.prepare_run(root,data,{})
    saved=c.verify_inputs(root)
    assert len(saved['recipe']['cases'])==132
    assert len(list((root/'workloads/s66x8').glob('*.xyz')))==66
    script=(root/'run.sbatch').read_text()
    assert '--exclusive' in script and '--gpus=1' in script and 'SLURM_SUBMIT_DIR' in script
    subprocess.run(['bash','-n',root/'run.sbatch'],check=True)
    # Bundle runs independently of the repository and its Python dependencies.
    env=dict(os.environ); env.pop('PYTHONPATH',None)
    result=subprocess.run([sys.executable,'-m','workflow.quick.calibrate','--help'],
                          cwd=root/'bundle',env=env,check=True,capture_output=True,text=True)
    assert 'execute' in result.stdout
    (root/'source/source.txt').write_text('changed')
    with pytest.raises(ValueError,match='changed prepared input'): c.verify_inputs(root)


def test_case_resume_and_report(tmp_path,monkeypatch):
    root=tmp_path/'run'; root.mkdir(); scratch=tmp_path/'scratch'; scratch.mkdir()
    basis=root/'install/basis'; basis.mkdir(parents=True)
    (basis/'basis_link').write_text(' | #def2-SVP | DEF2-SVP |\n')
    (basis/'DEF2-SVP').write_text('fixture basis')
    (root/'mol.xyz').write_text('2\nangstrom\nH 0 0 0\nH 0 0 1\n')
    case={'id':'fixture','basis':'def2-SVP','geometry':'mol.xyz'}
    saved={'identity':'test','recipe':{'config':c.settings({}),'cases':[case]}}
    calls=[]
    def fake_command(args,log,cwd,env,timeout):
        calls.append(args)
        assert env['FABO_SCF_TRAINING']=='calibrate' and env['FABO_SCF_STEPS']=='0'
        assert 'BASIS=def2-SVP' in (cwd/'input.in').read_text()
        assert 'DENSERMS=9.9999999999999995e-07' in (cwd/'input.in').read_text()
        (cwd/'scf-summary.txt').write_text('2 1 0\n3.0\n2 2 2\n')
        (cwd/'scf-iterations.csv').write_text('iteration,fock_seconds,iteration_seconds,energy_hartree,prms,pchange\n1,0.5,1,-1,0.1,0.1\n2,0.5,1,-2,0.01,0.01\n')
        (cwd/'input.out').write_text(f'BASIS SET = def2-SVP,\n | BASIS FILE = {basis}/DEF2-SVP\n')
        (cwd/'initial.bin').write_bytes(b'initial-state'); Path(log).write_text('fixture process')
        return 4.
    monkeypatch.setattr(c,'command',fake_command)
    row=c.calibration_case(root,saved,case,Path('/fake/quick.cuda'),{},scratch)
    assert row['iterations']==2 and row['fock_seconds']==1 and row['converged']
    assert c.calibration_case(root,saved,case,Path('/fake/quick.cuda'),{},scratch)==row
    assert len(calls)==1
    assert c.report(root,saved,[row])
    assert json.loads((root/'iteration-plan.json').read_text())['iterations']=={'fixture':2}
    assert not c.report(root,saved,[row|{'converged':False}])
    assert not json.loads((root/'iteration-plan.json').read_text())['iterations']
    (root/'calibration/fixture/initial.bin').write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed completed case'):
        c.calibration_case(root,saved,case,Path('/fake/quick.cuda'),{},scratch)


def test_result_rejects_wrong_count_and_nonfinite(tmp_path):
    (tmp_path/'scf-summary.txt').write_text('2 0 1\n3\n7 7 10\n')
    text='iteration,fock_seconds,iteration_seconds,energy_hartree,prms,pchange\n1,0.5,1,-1,0.1,0.1\n2,0.5,1,-1,0.1,0.1\n'
    (tmp_path/'scf-iterations.csv').write_text(text)
    assert read_result(tmp_path,True,2,4)['iterations']==2
    with pytest.raises(ValueError): read_result(tmp_path,True,1,4)
    (tmp_path/'scf-iterations.csv').write_text(text.replace('-1','NaN'))
    with pytest.raises(ValueError): read_result(tmp_path,True,2,4)


def test_build_only_cuda_and_resume(tmp_path,monkeypatch):
    root=tmp_path/'run'; root.mkdir(); scratch=tmp_path/'scratch'; scratch.mkdir()
    (root/'source/basis').mkdir(parents=True)
    (root/'source/basis/basis_link').write_text('fixture')
    saved={'identity':'fixture','recipe':{'config':c.settings({})}}
    calls=[]
    def fake_command(args,log,env):
        args=list(map(str,args)); calls.append(args)
        tree=scratch/'build'
        if '--build' not in args:
            tree.mkdir(); (tree/'CMakeCache.txt').write_text('fixture')
        else:
            assert args[args.index('--target')+1]=='quick.cuda'
            (tree/'quick.cuda').write_text('fake binary')
            (tree/'libquick_cuda.so').write_text('fake library')
    monkeypatch.setattr(c,'command',fake_command)
    monkeypatch.setattr(c,'dependencies',lambda *args: {})
    monkeypatch.setattr(c.time,'sleep',lambda *args: None)
    binary,env=c.build(root,saved,scratch)
    assert len(calls)==2 and binary.is_file()
    assert (root/'install/lib/libquick_cuda.so').is_file()
    c.build(root,saved,scratch)
    assert len(calls)==2
    binary.write_text('changed')
    with pytest.raises(ValueError,match='changed installed build'):
        c.build(root,saved,scratch)


def test_completed_resume_never_rewrites_summaries(tmp_path,monkeypatch):
    root=tmp_path/'run'; root.mkdir()
    rows=[{'case':name,'iterations':2,'converged':True,'fock_seconds':1.,
           'scf_seconds':2.,'process_seconds':3.} for name in ('first','second')]
    saved={'identity':'fixture','recipe':{'config':c.settings({}),
            'cases':[{'id':row['case']} for row in rows]}}
    c.report(root,saved,rows)
    c.write_json(root/'environment.json',{'gpu':'fixture GPU','node':os.uname().nodename})
    names=['calibration.json','iteration-plan.json','CALIBRATION.md','environment.json']
    c.write_json(root/'complete-scf-calibrate.json',{'identity':saved['identity'],
                 'files':{name:c.sha(root/name) for name in names}})
    names.append('complete-scf-calibrate.json')
    before={name:(root/name).read_bytes() for name in names}
    monkeypatch.setattr(c,'verify_inputs',lambda root:saved)
    monkeypatch.setattr(c,'build',lambda *args:(Path('/fake/quick.cuda'),{}))
    monkeypatch.setattr(c.subprocess,'check_output',lambda *args,**kwargs:'fixture GPU\n')
    calls=[]
    def interrupted(root,saved,case,*args):
        calls.append(case['id'])
        if case['id']=='second': raise KeyboardInterrupt()
        return rows[0]
    monkeypatch.setattr(c,'calibration_case',interrupted)
    with pytest.raises(KeyboardInterrupt): c.execute(root)
    assert calls==['first','second']
    assert {name:(root/name).read_bytes() for name in names}==before
    monkeypatch.setattr(c,'calibration_case',lambda root,saved,case,*args:next(r for r in rows if r['case']==case['id']))
    c.execute(root)
    assert {name:(root/name).read_bytes() for name in names}==before


def test_fortran_state_and_fixed_count(tmp_path):
    compiler=shutil.which('gfortran')
    if not compiler: pytest.skip('gfortran unavailable')
    stub=(Path(__file__).parent/'fixtures/scf_training_stub.f90').read_text()
    routines=(ROOT/'benchmark/quick/scf_training.f90').read_text()
    source=tmp_path/'check.f90'; source.write_text(stub.replace('! INSERT_PRODUCTION_ROUTINES',routines))
    exe=tmp_path/'check'
    subprocess.run([compiler,'-cpp','-ffree-line-length-none','-fcheck=all',source,'-o',exe],cwd=tmp_path,check=True,capture_output=True)
    env=c.clean_environment() | {'FABO_SCF_TRAINING':'calibrate','FABO_SCF_STATE':str(tmp_path/'initial.bin')}
    subprocess.run([exe],cwd=tmp_path,env=env,check=True,capture_output=True)
    saved=(tmp_path/'initial.bin').read_bytes()
    for steps in (1,2):
        subprocess.run([exe],cwd=tmp_path,env=env|{'FABO_SCF_TRAINING':'fixed','FABO_SCF_STEPS':str(steps)},check=True,capture_output=True)
        assert (tmp_path/'scf-summary.txt').read_text().split()[0]==str(steps)
        assert (tmp_path/'replayed-initial.bin').read_bytes()==saved
        (tmp_path/'replayed-initial.bin').unlink()
    (tmp_path/'initial.bin').write_bytes(saved+b'X')
    result=subprocess.run([exe],cwd=tmp_path,env=env|{'FABO_SCF_TRAINING':'fixed','FABO_SCF_STEPS':'1'},capture_output=True)
    assert result.returncode!=0

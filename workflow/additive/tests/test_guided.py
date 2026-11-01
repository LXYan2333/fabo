import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from workflow.additive.guided import first_fit, shrink, selection, geometry
from workflow.additive.model import Grid, from_metadata


def test_direct_offsets_and_legacy():
    legacy=Grid(7,-6,97)
    direct=from_metadata(legacy.metadata())
    assert direct.offset==legacy.offset
    for x in (0.,1.,1e7):
        assert direct.key(x)==legacy.key(x)
    for code in (0,1,127,128,129,0x7fefffffffffffff>>45):
        grid=Grid(7,offset_code=code)
        assert grid.key(0.)==code
        assert grid.node(code)==0.
    assert geometry(2,0.125)


def test_budget_plateaus_and_nonmonotone():
    rows=[9,9,7,7,2]
    assert first_fit(rows.__getitem__,4,7)==2
    assert first_fit(rows.__getitem__,4,1) is None
    rows=[9,2,7,1]
    assert first_fit(rows.__getitem__,3,2,False)==1


def test_shrink_islands_and_endpoint():
    assert shrink(0,100,lambda k:k<=11 or k==14,4)==14
    assert shrink(0,100,lambda k:True,4)==100
    assert shrink(0,100,lambda k:k==0,4)==0


def test_degree_cap_and_frozen_grid(monkeypatch):
    import workflow.additive.guided as guided
    config=json.loads((Path(__file__).parents[1]/'profiles/smoke.json').read_text())
    config.update(maximum_degree=3,strategy='budget_guided')
    monkeypatch.setattr(guided,'geometry',lambda *a:True)
    monkeypatch.setattr(guided,'first_fit',lambda *a:1000)
    monkeypatch.setattr(guided,'shrink',lambda start,*a:start)
    calls=[]
    def qualify(grid,n,p,**kw):
        calls.append(p)
        return dict(status='qualified' if p>=n+2 else 'failed',max_error_upper=0.5,witness='0x0.0p+0')
    monkeypatch.setattr(guided,'qualify',qualify)
    record=selection(0,1,2,config,{},lambda:None)
    assert record['degrees']==[2,3]
    assert record['grid']['offset_code']==1000
    assert max(calls)==3
    config['maximum_degree']=2
    record=selection(0,1,2,config,{},lambda:None)
    assert record['status']=='no_candidate_within_cap'


def test_guided_job_resume_merge(tmp_path):
    config=json.loads((Path(__file__).parents[1]/'profiles/smoke.json').read_text())
    config.update(strategy='budget_guided',requested_ranges=[[0,0]],retained_bits=[2],maximum_degree=1)
    path=tmp_path/'config.json'
    path.write_text(json.dumps(config))
    root=tmp_path/'run'
    subprocess.run([sys.executable,'-m','workflow.additive.cluster','--repo',str(Path.cwd()),'--config',str(path),
                    '--output',str(root),'--python',sys.executable],check=True,capture_output=True)
    env=dict(os.environ,SLURM_ARRAY_TASK_ID='0',SLURM_TMPDIR=str(tmp_path))
    subprocess.run(['bash',str(root/'array.sh')],env=env,check=True,capture_output=True)
    before=(root/'shard-0'/'state.json').read_bytes()
    subprocess.run(['bash',str(root/'array.sh')],env=env,check=True,capture_output=True)
    assert (root/'shard-0'/'state.json').read_bytes()==before
    subprocess.run([sys.executable,'-m','workflow.additive.finalize',str(root)],check=True,capture_output=True)
    assert json.loads((root/'summary.json').read_text())['complete']


def test_guided_multiple_tasks_per_shard(tmp_path):
    config=json.loads((Path(__file__).parents[1]/'profiles/smoke.json').read_text())
    config.update(strategy='budget_guided',maximum_degree=1)
    path=tmp_path/'config.json'
    path.write_text(json.dumps(config))
    root=tmp_path/'run'
    cmd=[sys.executable,'-m','workflow.additive.search','--config',str(path)]
    subprocess.run(cmd+['--output',str(root/'shard-0')],check=True,capture_output=True)
    subprocess.run(cmd+['--output',str(root),'--merge'],check=True,capture_output=True)
    assert sum(json.loads((root/'summary.json').read_text())['counts'].values())==2


def test_unresolved_summary(tmp_path):
    from workflow.additive.search import summarize
    summarize(tmp_path,'id',{},[dict(results=[dict(status='no_candidate_within_cap',unresolved=3)])],True)
    assert json.loads((tmp_path/'summary.json').read_text())['unresolved']==3


def test_retry_limit_and_command(tmp_path,monkeypatch):
    from workflow.additive import finalize
    spec=dict(shards=1,attempt=0,maximum_retries=2,array=['sbatch','--array=0-0%1','array.sh'],
              common=['sbatch'],concurrency=1,python=sys.executable)
    (tmp_path/'submission.json').write_text(json.dumps(spec))
    (tmp_path/'config.json').write_text('{}')
    monkeypatch.setattr(sys,'argv',['finalize',str(tmp_path)])
    monkeypatch.setattr(finalize,'identity',lambda c:'identity')
    calls=[]
    monkeypatch.setattr(subprocess,'check_output',lambda cmd,**kw:(calls.append(cmd) or '123\n'))
    finalize.main()
    assert '--array=0%1' in calls[0]
    assert '--dependency=afterany:123' in calls[1]
    spec['attempt']=2
    (tmp_path/'submission.json').write_text(json.dumps(spec))
    with pytest.raises(SystemExit,match='retry limit'):
        finalize.main()
    assert json.loads((tmp_path/'incomplete.json').read_text())['tasks']==[0]

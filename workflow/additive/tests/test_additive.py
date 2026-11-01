import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import gmpy2 as g
import pytest
from workflow.additive.model import Grid, storage, evaluate_order, row_data
from workflow.additive.reference import (bits64, rn64, from_bits, fma64,
    correction_code, residual_value, ulp)
from workflow.additive.search import candidate, score, payload_rows, validate


@pytest.fixture
def config():
    return json.loads((Path(__file__).parents[1]/'profiles/smoke.json').read_text())


@pytest.mark.parametrize('b,e,m', [(2,-3,1),(3,-4,8),(7,-6,97)])
def test_geometry(b,e,m):
    grid = Grid(b,e,m,2.0)
    assert grid.node(grid.keys.start) == 0
    assert grid.key(-0.0) == grid.key(0.0)
    for key in grid.keys:
        a, z = grid.cell(key)
        assert grid.key(a) == grid.key(z) == key
        if a > 0:
            assert grid.key(math.nextafter(a, 0.0)) == key-1
        assert grid.node(key) >= 0


def test_quantizer_tie_and_endpoint():
    grid = Grid(2,-3,4,0.08)
    assert grid.key(0.0625) == grid.keys.start+1
    assert grid.node(grid.keys.stop-1) > grid.domain_end
    # The addition rounds: an adjacent x below the ideal tie can still map up.
    assert grid.key(math.nextafter(0.0625, 0.0)) == grid.key(0.0625)
    with pytest.raises(ValueError):
        grid.key(float('nan'))


def test_exact_arithmetic_and_corrections():
    assert bits64(rn64(g.mpq(1,2**1075))) == 0
    assert bits64(rn64(g.mpq(3,2**1075))) == 2
    assert fma64(1+2**-27, 1-2**-27, -1.0) == -2**-54
    for hi in (1.0, math.nextafter(1.0,0.0), 0.125):
        for fraction in (g.mpq(-1,4), g.mpq(0), g.mpq(1,4)):
            true = g.mpq(hi)+fraction*ulp(hi)
            code = correction_code(hi,true)
            assert 0 <= code <= 192
            reconstructed = g.mpq(from_bits(bits64(hi)+1))-g.mpq(residual_value(hi,code))
            assert abs(reconstructed-true) <= ulp(hi)/256


def test_storage_and_score():
    grid = Grid(2,-3,1,0.125)
    size = storage(grid, 3, [8,1,1])
    assert size['highest_reference_order'] == 11
    assert size['row_bytes'] == 80
    a = dict(degrees=[4,3], storage=dict(table_bytes=100), grid=grid.metadata())
    b = dict(degrees=[5,1], storage=dict(table_bytes=50), grid=grid.metadata())
    assert score(a) < score(b)


def test_high_order_domain_endpoint():
    from workflow.additive.qualify import measure
    lower, upper = measure(Grid(7,-6,97),1e7,24,12,'ulp',1)
    assert 0 <= lower <= upper <= 1


def test_overflow_rejects_candidate_not_shard():
    from workflow.additive.qualify import qualify
    grid=Grid(2,32,1)
    result=qualify(grid,0,64,keys=[grid.keys.start])
    assert result['status']=='failed'
    assert 'nonfinite' in result['reason']


def test_candidate_regeneration(config):
    validate(config)
    record = candidate((0,Grid(2,-3,1,0.125),config))
    for model in record['results']:
        assert model['status'] == 'qualified'
        first = b''.join(payload_rows(model))
        row_data.cache_clear()
        assert hashlib.sha256(first).digest() == hashlib.sha256(b''.join(payload_rows(model))).digest()
        assert len(first) == model['storage']['table_bytes']
        for degree, proof in zip(model['degrees'],model['qualification']):
            assert len(proof['lower_degree_failures']) == degree-1


def test_degree_nonmonotonic_and_unresolved(config, monkeypatch):
    import workflow.additive.search as search
    def fake(grid,n,p,**kw):
        return dict(status='qualified' if p in (2,4) else 'failed', witness=0.0.hex())
    monkeypatch.setattr(search,'qualify',fake)
    result = candidate((0,Grid(2,-3,1,0.125),config))
    assert result['results'][1]['degrees'] == [2,2]
    monkeypatch.setattr(search,'qualify',lambda *a,**kw: dict(status='unresolved'))
    assert candidate((0,Grid(2,-3,1,0.125),config))['results'][0]['status'] == 'unresolved'


def test_compiled_dag(tmp_path):
    compiler = shutil.which('clang++')
    if not compiler:
        pytest.skip('clang++ unavailable: compiled conformance not tested')
    grid = Grid(2,-3,1,0.125)
    cases = []
    expected = []
    for n,p in ((0,8),(1,8),(3,7)):
        for key in grid.keys:
            a,b = grid.cell(key)
            for x in (a,b,(a+b)/2):
                r = grid.node(grid.key(x))
                hi,codes = row_data(r,n+p,n,n)
                coeff = ','.join(v.hex() for v in hi[n:n+p+1])
                cases.append('{double c[]={'+coeff+'}; emit('+','.join((x.hex(),r.hex(),str(p),str(codes[n])))+',c);}')
                expected.append(bits64(evaluate_order(grid,x,n,p)))
    source = '''#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
void emit(double x,double r,int p,int code,const double* c){
 double h=r-x,t=c[p];
 for(int k=p-1;k>0;--k){double inv=1.0/(k+1); double a=h*inv; t=std::fma(a,t,c[k]);}
 auto bits=std::bit_cast<std::uint64_t>(c[0]);
 int exponent=int((bits>>52)&2047)-1023-52;
 double u=std::ldexp(1.0,exponent);
 double correction=u*(code<=128?0.5+code/256.0:1.0+(code-128)/128.0);
 double v=std::bit_cast<double>(bits+1)+std::fma(h,t,-correction);
 std::printf("%llu\\n",(unsigned long long)std::bit_cast<std::uint64_t>(v));
}
int main(){'''+'\n'.join(cases)+'}\n'
    path = tmp_path/'conformance.cc'
    path.write_text(source)
    for mode,flags in [('strict',['-fno-fast-math','-ffp-contract=off']),('fast',['-ffast-math'])]:
        binary=tmp_path/mode
        subprocess.run([compiler,'-std=c++20','-O2',*flags,str(path),'-o',str(binary)],check=True,capture_output=True)
        actual=list(map(int,subprocess.check_output([str(binary)],text=True).splitlines()))
        if mode=='strict':
            assert actual==expected
        else:
            (tmp_path/'fast-diagnostic.json').write_text(json.dumps({'differing_cases':sum(a!=b for a,b in zip(actual,expected)),'cases':len(expected)}))


def test_shards_merge_and_resume(tmp_path, config):
    import sys
    path=tmp_path/'config.json'
    path.write_text(json.dumps(config))
    root=tmp_path/'run'
    common=[sys.executable,'-m','workflow.additive.search','--config',str(path),'--shards','2']
    for shard in range(2):
        out=root/f'shard-{shard}'
        cmd=common+['--shard',str(shard),'--output',str(out)]
        subprocess.run(cmd,check=True,capture_output=True)
        journal=out/'records.jsonl'
        before=journal.read_bytes()
        with journal.open('ab') as stream:
            stream.write(b'{"interrupted":')
        subprocess.run(cmd,check=True,capture_output=True)
        assert journal.read_bytes()==before
    subprocess.run(common+['--merge','--output',str(root)],check=True,capture_output=True)
    summary=json.loads((root/'summary.json').read_text())
    assert summary['complete'] and len(summary['winners'])==2
    assert summary['counts']['qualified']==8


def test_budget_and_version_guard(config):
    config['budget_bytes']=1
    result=candidate((0,Grid(2,-3,1,0.125),config))
    assert all(r['status']=='budget_lower_bound' for r in result['results'])
    config['producer']={'python':'not-the-producer'}
    with pytest.raises(ValueError,match='producer version mismatch'):
        validate(config)


def test_cluster_dry_run(tmp_path, config):
    import sys
    path=tmp_path/'config.json'
    path.write_text(json.dumps(config))
    root=tmp_path/'prepared'
    subprocess.run([sys.executable,'-m','workflow.additive.cluster','--repo',str(Path.cwd()),
                    '--config',str(path),'--output',str(root),'--python',sys.executable],check=True,capture_output=True)
    assert not (root/'jobs.json').exists()
    subprocess.run(['bash','-n',str(root/'array.sh')],check=True)
    subprocess.run(['bash','-n',str(root/'merge.sh')],check=True)


def test_eligible_nodes_are_not_requested_all_at_once(monkeypatch):
    from workflow.additive.cluster import node_restriction
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**kw:'c020\nc021\nc022\nc029\n')
    assert node_restriction('6526Y','c021,c022')==['--exclude=c020,c029']
    with pytest.raises(ValueError,match='not in partition'):
        node_restriction('6526Y','c021,c028')


def test_dispatch_refills_without_waiting_for_straggler(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import workflow.additive.search as search
    third_started=Event()
    def work(index):
        if index==0:
            assert third_started.wait(timeout=5)
        elif index==2:
            third_started.set()
        return index
    monkeypatch.setattr(search,'candidate',work)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(search.completed_tasks(pool,range(3),2))==[0,1,2]

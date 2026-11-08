import json
from pathlib import Path
import pytest
from workflow.library_accuracy.core import partitions,merge,storage,ROOT

def row(n=0):
    return dict(id='cpu-strict-fabo',N=0,n=n,metric='absolute',invalid=0,sum_lo='0.5',sum_hi='0.6',max_lo='0.4',max_hi='0.5',witness_x=0.0)

def test_partitions():
    assert partitions(9,4)==[(0,4),(4,4),(8,1)]
    with pytest.raises(ValueError):partitions(1,0)

def test_merge():
    shards=[dict(first=i,count=1,rows=[row()]) for i in range(2)]
    result=merge(shards,2)
    assert result[0]['mean_lo']=='0.5'
    assert result[0]['mean_hi']=='0.6'
    assert result[1]['n']=='all'
    assert result[1]['witness_n']==0
    assert result[1]['witness_x']==0.0
    with pytest.raises(ValueError):merge(shards,3)
    with pytest.raises(ValueError):merge([shards[0],shards[0]],2)

def test_invalid_not_discarded():
    r=row();r['invalid']=1
    result=merge([dict(first=0,count=1,rows=[r])],1)
    assert result[0]['mean_hi'] is None
    assert result[1]['status']=='nonfinite-output'

def test_storage_matches_headers():
    rows=storage(ROOT/'data/numerical/paired-1ulp/summary.json',ROOT/'include')
    assert len(rows)==25
    for r in rows:
        assert r['total_bytes']==sum(r[k] for k in ('coefficient_bytes','correction_bytes','padding_bytes'))
        assert r['total_bytes']<=2**20

@pytest.mark.parametrize('n',range(13))
@pytest.mark.parametrize('cuda',[False,True])
def test_dedicated_adapter(n,cuda):
    from workflow.library_accuracy.adapters import source
    text=source(n,cuda)
    assert f'selected::Model<{n}>' in text
    assert f'evaluate<0,{n}>' in text
    assert 'FaboQuickFamily' not in text
    assert 'boys_accuracy' in text

def test_inconsistent_coverage_rejected():
    a=dict(first=0,count=1,rows=[row()])
    b=dict(first=1,count=1,rows=[])
    with pytest.raises(ValueError):merge([a,b],2)

def test_duplicate_rows_rejected():
    with pytest.raises(ValueError):merge([dict(first=0,count=1,rows=[row(),row()])],1)

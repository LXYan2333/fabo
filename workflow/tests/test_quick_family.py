"""Family counter conservation, strict predicates, projection and integration."""
import csv
import copy
import inspect
import json
import math
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workflow/scripts'))
sys.path.insert(0,str(ROOT/'benchmark/quick'))
import quick_family_probe as family

DATA=dict(grouping='family',families=[4,8,12],domain_end=10.,
          histogram_edges=[1.,2.,10.,117.,1000.],thresholds=[0.,1.,2.,10.,117.,1000.])


def write_counts(path,counts):
    with path.open('w') as stream:
        writer=csv.writer(stream);writer.writerow(family.FIELDS)
        writer.writerow(['schema',0,'whole',-1,0,0,2])
        writer.writerows([*key,count] for key,count in sorted(counts.items()))
        writer.writerow(['complete',0,'whole',-1,0,0,len(counts)])


def fixtures():
    return [(4,[(i%5,float(i)) for i in range(32)]),
            (4,[(0,-0.),(2,math.nextafter(10.,0)),(3,10.),(4,math.nextafter(10.,math.inf))]),
            (8,[(8,117.)]),(8,[(1,0.),(2,1.),(8,1001.)]),
            (12,[(1,float('nan')),(2,float('inf')),(3,-1.),(12,3.)])]


def test_branch_counts_against_direct_predicates(tmp_path):
    groups=fixtures();path=tmp_path/'family-counters.csv'
    write_counts(path,family.oracle_counts(groups,DATA))
    result=family.summarize(path,DATA)
    for f in result['families']:
        for row in f['branches']:
            selected=[g for n,g in groups if n==f['family'] and max(k for k,x in g)==row['maximum']
                      and (len(g)==32)==row['full'] and all(math.isfinite(x) and x>=0 for k,x in g)]
            assert row['valid_groups']==len(selected)
            for b in family.branch_rows(row,DATA):
                for suffix,predicate in [('gt',lambda x:x>b['threshold']),('lt',lambda x:x<b['threshold'])]:
                    truths=[[predicate(x) for k,x in g] for g in selected]
                    assert b['all_'+suffix]==sum(all(v) for v in truths)
                    assert b['none_'+suffix]==sum(not any(v) for v in truths)
                    assert b['mixed_'+suffix]==sum(any(v) and not all(v) for v in truths)
                    assert (b['p_all_'+suffix] is None)==(not selected)
    family.write_report(result,tmp_path/'report')
    family.verify_projection(result,tmp_path/'report/requests.csv')
    rows=family.request_rows(result)
    assert result['families'][2]['histogram'][-1]==3


@pytest.mark.parametrize('damage',['truncated','duplicate','bad_family','bad_count','missing_count'])
def test_counter_corruption_rejected(tmp_path,damage):
    counts=family.oracle_counts(fixtures(),DATA);path=tmp_path/'counter.csv'
    if damage=='missing_count':
        del counts[next(k for k in counts if k[0]=='minimum')]
    write_counts(path,counts)
    lines=path.read_text().splitlines()
    if damage=='truncated':lines.pop()
    if damage=='duplicate':
        lines.insert(-1,lines[2]);lines[-1]='complete,0,whole,-1,0,0,'+str(len(counts)+1)
    if damage=='bad_family':lines[2]=lines[2].replace(',4,',',16,',1)
    if damage=='bad_count':lines[2]=','.join(lines[2].split(',')[:-1]+['-1'])
    path.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError):family.summarize(path,DATA)


def test_sparse_masks_order_diversity_and_domain_partition():
    groups=[(4,[(0,0.),(4,1e8)]),(4,[(1,1.),(1,2.),(1,3.)])]
    result=family.summarize_counts(family.oracle_counts(groups,DATA),DATA)
    f=result['families'][0];whole=f['scopes']['whole']['rows']
    assert whole[4]['minimum'][0]==1 and whole[4]['distinct'][2]==1
    assert whole[1]['distinct'][1]==1
    assert f['scopes']['bounded']['rows'][0]['participation'][1]==1
    assert f['scopes']['tail']['rows'][4]['participation'][1]==1
    views=family.views(result)
    assert views[0]['split']==[.5,0,.5]
    assert views[1]['maximum']==[None]*9


def test_aggregate_pooled_equal_case_missing_and_modes(tmp_path):
    cases=[]
    for name,groups in [('large',[(4,[(0,0.)])]*10),('small',[(4,[(4,1.)])]),('absent',[(8,[(8,1.)])])]:
        path=tmp_path/(name+'.csv');write_counts(path,family.oracle_counts(groups,DATA))
        cases.append(dict(id=name,counters=path,provenance=dict(mode='fixed_density')))
    pooled=family.aggregate(cases,DATA,tmp_path/'aggregate')
    assert family.views(pooled)[0]['maximum'][0]==10/11
    equal=json.loads((tmp_path/'aggregate/equal-case.json').read_text())
    assert equal['families'][0]['maximum']==[.5,0,0,0,.5]
    assert equal['families'][0]['absent_cases']==['absent']
    cases[0]['provenance']['mode']='scf_replay'
    with pytest.raises(ValueError,match='cannot pool'):family.aggregate(cases,DATA,tmp_path/'bad')


def test_compact_replay_report_and_projection_mismatch(tmp_path):
    result=family.summarize_counts(family.oracle_counts(fixtures(),DATA),DATA)
    family.write_report(result,tmp_path,detailed=False)
    assert not (tmp_path/'views.json').exists()
    assert not (tmp_path/'branches.csv').exists()
    saved=json.loads((tmp_path/'summary.json').read_text())
    assert family.views(saved)==family.views(result)
    path=tmp_path/'requests.csv'
    path.write_text(path.read_text().replace(',32,1',',32,2'))
    with pytest.raises(ValueError,match='projection'):family.verify_projection(result,path)

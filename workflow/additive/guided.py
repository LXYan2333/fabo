"""Checkpointed budget-guided search; passing probes do not prove optimality."""
import json
import os
import time
from pathlib import Path
from .model import Grid, storage
from .qualify import qualify
from .search import identity, atomic_json, summarize
from .checkpoint import copy_metadata


def tasks(config):
    priority=config.get('priority_orders',[4,8,12])
    ranges=sorted(config['requested_ranges'],key=lambda r:(priority.index(r[1]) if r[1] in priority else len(priority)+r[1],r[0]))
    return [(first,last,b) for first,last in ranges for b in sorted(set(config['retained_bits']))]


def geometry(b,end):
    """Verify monotonic endpoint row counts in bounded binary64 chunks.

    Cross-check chunk endpoints against the exact-rational indexing oracle;
    nonconforming host arithmetic or nonmonotonic geometry uses exact scanning.
    """
    import numpy as np
    s=52-b
    stop=(0x7fefffffffffffff>>s)+1
    previous=None
    for start in range(0,stop,65536):
        code=np.arange(start,min(stop,start+65536),dtype=np.uint64)
        offsets=(code<<s).view(np.float64)
        upper=((offsets+end).view(np.uint64)+(1<<(s-1)))>>s
        rows=(upper-code+1).astype(np.int64)
        for i in (0,-1):
            if int(rows[i])!=len(Grid(b,domain_end=end,offset_code=int(code[i])).keys):
                return False
        if (previous is not None and rows[0]>previous) or np.any(rows[1:]>rows[:-1]):
            return False
        previous=rows[-1]
    return True


def first_fit(row_count, maximum_code, row_limit, monotone=True):
    if not monotone:
        return next((k for k in range(maximum_code+1) if row_count(k)<=row_limit),None)
    if row_count(maximum_code)>row_limit:
        return None
    lo,hi=0,maximum_code
    while lo<hi:
        mid=(lo+hi)//2
        if row_count(mid)<=row_limit:
            hi=mid
        else:
            lo=mid+1
    return lo


def shrink(start,maximum,passes,radius):
    best=lo=start
    distance=1
    while lo<maximum:
        probe=min(maximum,start+distance)
        if passes(probe):
            best=lo=probe
            if probe==maximum:
                return probe
            distance*=2
        else:
            hi=probe
            break
    else:
        return best
    while hi-lo>1:
        mid=(lo+hi)//2
        if passes(mid):
            best=lo=mid
        else:
            hi=mid
    for probe in range(max(start,lo-radius),min(maximum,hi+radius)+1):
        if probe>best and passes(probe):
            best=probe
    return best


def selection(first,last,b,config,state,save):
    end=float(config['domain_end'])
    maximum=0x7fefffffffffffff>>(52-b)
    grid=lambda code: Grid(b,domain_end=end,offset_code=code)
    if 'monotone' not in state:
        state['monotone']=geometry(b,end)
        save()
    probes=state.setdefault('probes',{})
    def check(code,n,p,tier):
        name=f'{code}:{n}:{p}:{tier}'
        if name not in probes:
            current=grid(code)
            options=dict(metric=config['error']['metric'],limit=config['error']['limit'])
            if tier=='screen':
                keys=list(dict.fromkeys(current.keys.start+(len(current.keys)-1)*i//16 for i in range(17)))
                options.update(keys=keys,subdivisions=config['screen_subdivisions'])
            else:
                options.update(subdivisions=config['final_subdivisions'],refinement=config['refinement_rounds'])
            begin=time.monotonic()
            probes[name]=dict(qualify(current,n,p,**options),seconds=time.monotonic()-begin)
            state['last_probe']=dict(code=code,order=n,degree=p,tier=tier,status=probes[name]['status'])
            save()
        return probes[name]
    def passes(code,p):
        for tier in ('screen','full'):
            for n in range(last,first-1,-1):
                if check(code,n,p,tier)['status']!='qualified':
                    return False
        return True
    selected=None
    for p in range(config['minimum_degree'],config['maximum_degree']+1):
        state.update(phase='common_degree',degree=p)
        size=storage(grid(maximum),first,[p]*(last-first+1))['row_bytes']
        code=first_fit(lambda k:len(grid(k).keys),maximum,config['budget_bytes']//size,state['monotone'])
        if code is None:
            break
        if passes(code,p):
            selected=code,p
            break
    if selected is None:
        return dict(first=first,last=last,b=b,status='no_candidate_within_cap',
                    unresolved=sum(v['status']=='unresolved' for v in probes.values()))
    code,p=selected
    state.update(phase='shrink',common_degree=p,initial_offset_code=code)
    save()
    code=shrink(code,maximum,lambda k:passes(k,p),config.get('offset_neighborhood',4))
    state.update(phase='minimize_orders',selected_offset_code=code)
    save()
    degrees,proofs=[],[]
    for n in range(first,last+1):
        failures=[]
        for degree in range(config['minimum_degree'],p+1):
            proof=check(code,n,degree,'screen')
            if proof['status']=='qualified':
                proof=check(code,n,degree,'full')
            if proof['status']=='qualified':
                degrees.append(degree)
                proofs.append(dict(proof,lower_degree_failures=failures,
                    minimum_certified=all(f['status']=='failed' for f in failures)))
                break
            failures.append(dict(proof,degree=degree))
        else:
            raise RuntimeError('qualified common-degree incumbent was lost')
    size=storage(grid(code),first,degrees)
    if size['table_bytes']>config['budget_bytes']:
        raise RuntimeError('frozen-grid degree minimization exceeded budget')
    return dict(first=first,last=last,status='qualified',grid=grid(code).metadata(),
                common_degree=p,degrees=degrees,qualification=proofs,storage=size,
                unresolved=sum(v['status']=='unresolved' for v in probes.values()),
                search_policy='budget_guided; not globally optimal')


def run(args,config):
    task_function,select=tasks,selection
    if config.get('strategy')=='paired_budget_guided':
        from .paired import tasks as task_function, selection as select
    work=task_function(config)
    if args.workers!=1 or args.shards<1 or not 0<=args.shard<args.shards:
        raise ValueError('guided search requires one worker and valid shard indices')
    folder=args.output
    folder.mkdir(parents=True,exist_ok=True)
    run_id=identity(config)
    manifest=folder/'identity.json'
    if manifest.exists() and json.loads(manifest.read_text())['identity']!=run_id:
        raise ValueError('incompatible run identity')
    atomic_json(manifest,dict(identity=run_id,config=config))
    if args.merge:
        records=[]
        for index in range(args.shards):
            part=folder/f'shard-{index}'
            meta=json.loads((part/'summary.json').read_text())
            if meta['identity']!=run_id or not meta['complete']:
                raise ValueError('incomplete guided task')
            records.extend(json.loads(line) for line in (part/'records.jsonl').read_text().splitlines())
        if sorted(r['index'] for r in records)!=list(range(len(work))):
            raise ValueError('invalid guided task coverage')
        summarize(folder,run_id,config,records,True)
        return
    path=folder/'state.json'
    state=json.loads(path.read_text()) if path.exists() else {'tasks':{}}
    def save():
        atomic_json(path,state)
        destination=os.environ.get('FABO_CHECKPOINT_DIR')
        if destination:
            copy_metadata(folder,destination)
        print(json.dumps(dict(task=args.shard,progress=state.get('active',{}))),flush=True)
    records=[]
    for index,(first,last,b) in enumerate(work):
        if index%args.shards!=args.shard:
            continue
        item=state['tasks'].setdefault(str(index),{})
        def checkpoint():
            state['active']={k:v for k,v in item.items() if k not in ('probes','result')}
            save()
        if 'result' not in item:
            item['result']=select(first,last,b,config,item,checkpoint)
            checkpoint()
        records.append(dict(index=index,results=[item['result']]))
    journal=folder/'records.jsonl'
    temporary=journal.with_suffix('.tmp')
    temporary.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
    temporary.replace(journal)
    summarize(folder,run_id,config,records,True)
    save()

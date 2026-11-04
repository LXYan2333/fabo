"""Shared-budget search. Screens reject only measured failures; no timing search."""
import math
from . import tail
from .guided import first_fit, shrink, geometry
from .model import Grid, storage
from .qualify import qualify


def tasks(config):
    priority=config.get('priority_orders',[4,8,12])
    ranges=sorted(config['requested_ranges'],key=lambda r:(priority.index(r[1]) if r[1] in priority else len(priority)+r[1],r[0]))
    result=[]
    for first,last in ranges:
        for b in range(21):
            size=tail.storage(first,[config['minimum_degree']]*(last-first+1),b)
            if size['table_bytes']+size['row_bytes']>config['budget_bytes']: break
            result.append((first,last,b))
    return result


def selection(first,last,bt,config,state,save):
    error=config['error']; probes=state.setdefault('probes',{})
    def cached(key,call):
        if key not in probes:
            try: probes[key]=call()
            except ArithmeticError as exc: probes[key]=dict(status='unresolved',reason=str(exc))
            state['last_probe']=dict(key=key,status=probes[key].get('status'))
            save()
        return probes[key]
    def tail_result(n,p,full):
        model=tail.construct(n,n,p,bt)
        def test():
            if full:
                return tail.boundary(model,error,config['final_subdivisions'],config['refinement_rounds'])
            if not config.get('cheap_screen',True): return dict(status='qualified')
            # Sparse cells, with every quantizer seam represented by the full tier.
            count=model['storage']['row_count']
            indices=sorted({0,count-1,(count-1)//2}|{(count-1)*i//16 for i in range(17)})
            for i in indices:
                a,z=tail.cell(i,bt)
                for j in range(config['screen_subdivisions']+1):
                    u=a+(z-a)*j/config['screen_subdivisions']
                    r=tail.check_point(model,math.ldexp(u,24),error)
                    if r['status']!='qualified': return r
            return dict(status='qualified')
        return cached(f'tail:{n}:{p}:{full}',test)
    results=state.setdefault('main_results',{})
    for bm in config['retained_bits']:
        if str(bm) in results: continue
        selected=None
        for p in range(config['minimum_degree'],config['maximum_degree']+1):
            ts=tail.storage(first,[p]*(last-first+1),bt)
            if ts['table_bytes']+ts['row_bytes']>config['budget_bytes']: continue
            order=list(dict.fromkeys([last,first]+list(range(first,last+1))))
            if any(tail_result(n,p,False)['status']!='qualified' for n in order): continue
            tq=[tail_result(n,p,True) for n in range(first,last+1)]
            if any(q['status']!='qualified' for q in tq): continue
            end=max(float.fromhex(q['boundary']) for q in tq)
            remaining=config['budget_bytes']-ts['table_bytes']
            maximum=0x7fefffffffffffff>>(52-bm)
            grid=lambda code:Grid(bm,domain_end=end,offset_code=code)
            monotone=cached(f'geometry:{bm}:{end.hex()}',lambda:dict(value=geometry(bm,end)))['value']
            code=first_fit(lambda k:len(grid(k).keys),maximum,remaining//ts['row_bytes'],monotone)
            if code is None: continue
            def check(code,n,degree,full):
                def test():
                    if not full and not config.get('cheap_screen',True): return dict(status='qualified')
                    current=grid(code)
                    options=dict(metric=error['metric'],limit=error['limit'])
                    if full: options.update(subdivisions=config['final_subdivisions'],refinement=config['refinement_rounds'])
                    else:
                        keys=list(dict.fromkeys(current.keys.start+(len(current.keys)-1)*i//16 for i in range(17)))
                        options.update(keys=keys,subdivisions=config['screen_subdivisions'])
                    return qualify(current,n,degree,**options)
                return cached(f'main:{bm}:{end.hex()}:{code}:{n}:{degree}:{full}',test)
            if any(check(code,n,p,full)['status']!='qualified' for full in (False,True) for n in order): continue
            degrees=[]; proofs=[]; tail_proofs=[]
            for n in range(first,last+1):
                for degree in range(config['minimum_degree'],p+1):
                    tqn=tail_result(n,degree,False)
                    if tqn['status']=='unresolved': break
                    if tqn['status']!='qualified': continue
                    tqn=tail_result(n,degree,True)
                    if tqn['status']=='unresolved': break
                    # A previously qualified suffix also qualifies this later seam.
                    if tqn['status']!='qualified' or float.fromhex(tqn['boundary'])>end: continue
                    q=check(code,n,degree,False)
                    if q['status']=='qualified': q=check(code,n,degree,True)
                    if q['status']=='unresolved': break
                    if q['status']=='qualified':
                        degrees.append(degree); proofs.append(q); tail_proofs.append(tqn); break
                else: raise RuntimeError('lost common-degree incumbent')
                if len(degrees)!=n-first+1: break
            if len(degrees)!=last-first+1: continue
            def passes(k):
                return all(check(k,n,d,full)['status']=='qualified'
                           for full in (False,True) for n,d in zip(range(first,last+1),degrees))
            code=shrink(code,maximum,passes,config.get('offset_neighborhood',4))
            size=storage(grid(code),first,degrees)
            tm=tail.construct(first,last,degrees,bt,end)
            total=size['table_bytes']+tm['storage']['table_bytes']
            if total>config['budget_bytes']: raise RuntimeError('paired allocation exceeded budget')
            selected=dict(first=first,last=last,status='qualified',grid=grid(code).metadata(),
                          common_degree=p,degrees=degrees,storage=size,tail=tm,tail_qualification=tail_proofs,
                          combined_table_bytes=total,qualification=[check(code,n,d,True) for n,d in zip(range(first,last+1),degrees)],
                          search_policy='paired_budget_guided; sampled suffix; not globally optimal')
            break
        results[str(bm)]=selected or dict(status='no_candidate_within_cap',first=first,last=last)
        save()
    from .search import score
    accepted=[r for r in results.values() if r['status']=='qualified']
    result=dict(min(accepted,key=score)) if accepted else dict(first=first,last=last,status='no_candidate_within_cap')
    result['unresolved']=sum(q.get('status')=='unresolved' for q in probes.values())
    return result

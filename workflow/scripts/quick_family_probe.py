"""Versioned QUICK family-cohort counters and report-only transformations."""
import csv
import bisect
import hashlib
import json
import math
from pathlib import Path

SCOPES = ('whole', 'bounded', 'tail')
RANKS = ('min_lower', 'max_lower', 'min_upper', 'max_upper')
NAMES = {4: 'SP', 8: 'SPD', 12: 'SPDF'}
FIELDS = ['kind', 'family', 'scope', 'maximum', 'index', 'aux', 'count']


def request_limit(settings, family):
    limit = settings.get('request_limits', {}).get(str(family), family)
    if family not in NAMES or type(limit) is not int or limit not in (family, 12):
        raise ValueError('invalid family request limit')
    if family == 4 and limit != 4:
        raise ValueError('SP requests cannot exceed order four')
    return limit


def oracle_counts(groups, settings):
    """Integer-counter oracle for synthetic explicit-mask conformance fixtures."""
    counts = {}
    for family, group in groups:
        if not group or len(group)>32 or any(not 0<=n<=request_limit(settings,family) for n,x in group):
            raise ValueError('invalid oracle cohort')
        def add(kind, maximum=-1, index=0, aux=0, count=1, scope='whole'):
            key=(kind,family,scope,maximum,index,aux)
            counts[key]=counts.get(key,0)+count
        valid=lambda x: math.isfinite(x) and x>=0
        bounded=[(n,x) for n,x in group if valid(x) and x<=settings['domain_end']]
        tail=[(n,x) for n,x in group if valid(x) and x>settings['domain_end']]
        for scope,cohort in zip(SCOPES,(group,bounded,tail)):
            if not cohort:continue
            maximum=max(n for n,x in cohort)
            add('requests',maximum,len(cohort),scope=scope)
            add('minimum',maximum,min(n for n,x in cohort),scope=scope)
            add('distinct',maximum,len({n for n,x in cohort}),scope=scope)
            for n,x in cohort:add('lanes',maximum,n,scope=scope)
        for n,x in group:
            bin_index=len(settings['histogram_edges'])+2 if not valid(x) else 0 if x==0 else 1+bisect.bisect_right(settings['histogram_edges'],x)
            add('histogram',index=bin_index)
        maximum=max(n for n,x in group);full=int(len(group)==32)
        if not all(valid(x) for n,x in group):
            add('invalid',maximum,aux=full)
            continue
        add('split',index=len(group),aux=len(bounded))
        lower=[bisect.bisect_left(settings['thresholds'],x) for n,x in group]
        upper=[bisect.bisect_right(settings['thresholds'],x) for n,x in group]
        for kind,rank in zip(RANKS,(min(lower),max(lower),min(upper),max(upper))):
            add(kind,maximum,rank,full)
    return counts


def _validate_key(key, settings):
    kind, family, scope, maximum, index, aux = key
    if family not in NAMES or scope not in SCOPES:
        raise ValueError('unknown family/scope')
    if family not in settings['families']:
        raise ValueError('observed disabled family')
    if kind == 'histogram':
        ok = scope == 'whole' and maximum == -1 and aux == 0 and 0 <= index < len(settings['histogram_edges']) + 3
    elif kind == 'split':
        ok = scope == 'whole' and maximum == -1 and 1 <= index <= 32 and 0 <= aux <= index
    else:
        ok = 0 <= maximum <= request_limit(settings, family)
        if kind == 'requests':
            ok &= 1 <= index <= 32 and aux == 0
        elif kind in ('minimum', 'lanes'):
            ok &= 0 <= index <= maximum and aux == 0
        elif kind == 'distinct':
            ok &= 1 <= index <= maximum + 1 and aux == 0
        elif kind == 'invalid':
            ok &= scope == 'whole' and index == 0 and aux in (0, 1)
        elif kind in RANKS:
            ok &= scope == 'whole' and 0 <= index <= len(settings['thresholds']) and aux in (0, 1)
        else:
            ok = False
    if not ok:
        raise ValueError('invalid family counter key: ' + str(key))


def read_counters(path, settings):
    with Path(path).open() as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('wrong family counter columns')
        rows = list(reader)
    def metadata(kind, count):
        return dict(zip(FIELDS, [kind, '0', 'whole', '-1', '0', '0', str(count)]))
    if len(rows) < 2 or rows[0] != metadata('schema', 2) or rows[-1] != metadata('complete', len(rows) - 2):
        raise ValueError('incomplete or unsupported family counter file')
    result = {}
    for row in rows[1:-1]:
        key = (row['kind'], int(row['family']), row['scope'], int(row['maximum']), int(row['index']), int(row['aux']))
        count = int(row['count'])
        _validate_key(key, settings)
        if key in result or not 0 < count < 2**64:
            raise ValueError('duplicate/invalid family counter')
        result[key] = count
    return result


def decode_branches(rank_counts, valid, thresholds):
    if any(sum(values) != valid for values in rank_counts):
        raise ValueError('rank counter conservation failed')
    running = [0] * 4
    rows = []
    for i, threshold in enumerate(thresholds):
        running = [s + values[i] for s, values in zip(running, rank_counts)]
        counts = dict(all_gt=valid-running[0], none_gt=running[1],
                      all_lt=running[3], none_lt=valid-running[2])
        for suffix in ('gt', 'lt'):
            counts['mixed_' + suffix] = valid-counts['all_'+suffix]-counts['none_'+suffix]
        if min(counts.values()) < 0:
            raise ValueError('inconsistent branch ranks')
        rows.append({'threshold': threshold, **counts,
                     **{'p_'+k: v/valid if valid else None for k, v in counts.items()}})
    return rows


def summarize_counts(counts, settings):
    families = []
    for family in settings['families']:
        limit = request_limit(settings, family)
        def get(kind, scope='whole', maximum=-1, index=0, aux=0):
            return counts.get((kind, family, scope, maximum, index, aux), 0)
        scopes = {}
        for scope in SCOPES:
            rows = []
            for maximum in range(limit + 1):
                participation = [get('requests', scope, maximum, i) for i in range(33)]
                minimum = [get('minimum', scope, maximum, i) for i in range(limit+1)]
                distinct = [get('distinct', scope, maximum, i) for i in range(limit+2)]
                lanes = [get('lanes', scope, maximum, i) for i in range(limit+1)]
                cohorts = sum(participation)
                lane_calls = sum(i*c for i, c in enumerate(participation))
                if sum(minimum) != cohorts or sum(distinct) != cohorts or sum(lanes) != lane_calls:
                    raise ValueError('request/diversity conservation failed')
                if cohorts and lanes[maximum] < cohorts:
                    raise ValueError('cohort maximum missing from lane orders')
                rows.append(dict(maximum=maximum, participation=participation, minimum=minimum,
                                 distinct=distinct, lanes=lanes, cohorts=cohorts, lane_calls=lane_calls))
            scopes[scope] = dict(rows=rows, cohorts=sum(r['cohorts'] for r in rows),
                                 lane_calls=sum(r['lane_calls'] for r in rows))
        histogram = [get('histogram', index=i) for i in range(len(settings['histogram_edges'])+3)]
        if sum(histogram) != scopes['whole']['lane_calls']:
            raise ValueError('histogram/participation conservation failed')
        if scopes['bounded']['lane_calls'] + scopes['tail']['lane_calls'] + histogram[-1] != sum(histogram):
            raise ValueError('bounded/tail/invalid lane partition failed')
        branches = []
        for maximum, row in enumerate(scopes['whole']['rows']):
            for full in (0, 1):
                groups = row['participation'][32] if full else sum(row['participation'][1:32])
                invalid = get('invalid', maximum=maximum, aux=full)
                if invalid > groups:
                    raise ValueError('invalid cohorts exceed total')
                rank_counts = [[get(k, maximum=maximum, index=i, aux=full)
                                for i in range(len(settings['thresholds'])+1)] for k in RANKS]
                if any(sum(v)!=groups-invalid for v in rank_counts):
                    raise ValueError('rank counter conservation failed')
                prefix=[0]*4
                for values in zip(*rank_counts):
                    prefix=[a+b for a,b in zip(prefix,values)]
                    if prefix[0]<prefix[1] or prefix[2]<prefix[3] or prefix[0]<prefix[2] or prefix[1]<prefix[3]:
                        raise ValueError('inconsistent branch ranks')
                branches.append(dict(maximum=maximum, full=bool(full), groups=groups,
                                     valid_groups=groups-invalid, invalid_groups=invalid,
                                     ranks=[{str(i):c for i,c in enumerate(v) if c} for v in rank_counts]))
        split = [dict(active=a, bounded=b, tail=a-b, cohorts=get('split', index=a, aux=b))
                 for a in range(1,33) for b in range(a+1) if get('split', index=a, aux=b)]
        valid = sum(r['valid_groups'] for r in branches)
        if sum(r['cohorts'] for r in split) != valid:
            raise ValueError('domain split conservation failed')
        if sum(r['invalid_groups'] for r in branches) > histogram[-1]:
            raise ValueError('invalid group/lane counts disagree')
        if not histogram[-1]:
            for scope in ('bounded', 'tail'):
                if sum(r['cohorts'] for r in split if r[scope]) != scopes[scope]['cohorts'] or sum(r[scope]*r['cohorts'] for r in split) != scopes[scope]['lane_calls']:
                    raise ValueError('domain split/scope conservation failed')
        families.append(dict(family=family, request_limit=limit, name=NAMES[family], scopes=scopes,
                             histogram=histogram, branches=branches, split=split))
    return dict(schema=2, settings=settings, families=families,
                semantics='Instrumented active cohorts, not necessarily complete physical warps. Branch denominators exclude cohorts with invalid arguments.')


def summarize(path, settings):
    result = summarize_counts(read_counters(path, settings), settings)
    result['source_sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return result


def request_rows(result):
    return [dict(family=f['family'], scope=scope, maximum=r['maximum'], active=a, cohorts=count)
            for f in result['families'] for scope, data in f['scopes'].items()
            for r in data['rows'] for a, count in enumerate(r['participation']) if count]


def verify_projection(result, path):
    with Path(path).open() as stream:
        actual = [{k: v if k == 'scope' else int(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    key = lambda r: (r['family'], r['scope'], r['maximum'], r['active'])
    if sorted(actual, key=key) != sorted(request_rows(result), key=key):
        raise ValueError('request projection differs from family counters')


def normalized(values):
    total = sum(values)
    return [v/total for v in values] if total else [None]*len(values)


def branch_rows(row, settings):
    ranks=[[r.get(str(i),0) for i in range(len(settings['thresholds'])+1)] for r in row['ranks']]
    return decode_branches(ranks,row['valid_groups'],settings['thresholds'])


def views(result):
    """Plot/report probabilities, with cohort and lane denominators explicit."""
    output = []
    for f in result['families']:
        rows = f['scopes']['whole']['rows']
        limit = len(rows)-1
        maximum = normalized([r['cohorts'] for r in rows])
        active = normalized([sum(r['participation'][i] for r in rows) for i in range(33)])
        span = normalized([sum(r['minimum'][r['maximum']-i] for r in rows if r['maximum'] >= i)
                           for i in range(limit+1)])
        distinct = normalized([sum(r['distinct'][i] for r in rows) for i in range(limit+2)])
        split = normalized([sum(r['cohorts'] for r in f['split'] if predicate(r)) for predicate in (
            lambda r:r['tail']==0, lambda r:r['bounded']==0, lambda r:r['bounded']>0 and r['tail']>0)])
        branch_views = []
        for n in [-1, *range(limit+1)]:
            for activity in ('all', 'full', 'partial'):
                chosen = [r for r in f['branches'] if (n == -1 or r['maximum'] == n)
                          and (activity == 'all' or r['full'] == (activity == 'full'))]
                valid = sum(r['valid_groups'] for r in chosen)
                if valid:
                    ranks=[[sum(r['ranks'][k].get(str(i),0) for r in chosen)
                            for i in range(len(result['settings']['thresholds'])+1)] for k in range(4)]
                    decoded=decode_branches(ranks,valid,result['settings']['thresholds'])
                    probabilities={k:[b['p_'+k] for b in decoded] for k in ('all_gt','none_gt','mixed_gt','all_lt','none_lt','mixed_lt')}
                else:
                    probabilities={k:[None]*len(result['settings']['thresholds']) for k in ('all_gt','none_gt','mixed_gt','all_lt','none_lt','mixed_lt')}
                branch_views.append(dict(maximum=n, activity=activity, valid_groups=valid, **probabilities))
        output.append(dict(family=f['family'], name=f['name'], maximum=maximum, active=active, span=span,
                           distinct=distinct, split=split, histogram=normalized(f['histogram']), branches=branch_views))
    return output


def write_report(result, output, *, detailed=True):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    (output/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    if detailed:
        (output/'views.json').write_text(json.dumps({'settings':result['settings'], 'families':views(result),
            'weighting':'pooled cohorts for requests/branches; pooled lanes for input histogram',
            'provenance':result.get('provenance',{})}, indent=2)+'\n')
    with (output/'requests.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['family','scope','maximum','active','cohorts'])
        writer.writeheader();writer.writerows(request_rows(result))
    # Dense branch CSV is reserved for aggregate or explicitly requested reports.
    if detailed:
        keys=['family','maximum','activity','groups','valid_groups','invalid_groups','threshold',
              'all_gt','none_gt','all_lt','none_lt','mixed_gt','mixed_lt',
              'p_all_gt','p_none_gt','p_all_lt','p_none_lt','p_mixed_gt','p_mixed_lt']
        with (output/'branches.csv').open('w') as stream:
            writer=csv.DictWriter(stream,fieldnames=keys);writer.writeheader()
            for f in result['families']:
                for r in f['branches']:
                    for b in branch_rows(r,result['settings']):
                        writer.writerow(dict(family=f['family'],maximum=r['maximum'],activity='full' if r['full'] else 'partial',
                            **{k:r[k] for k in ('groups','valid_groups','invalid_groups')},**b))
    with (output/'histogram.csv').open('w') as stream:
        writer=csv.writer(stream);writer.writerow(['family','bin','count','lane_fraction','density_per_unit_x'])
        edges=[0,*result['settings']['histogram_edges']]
        for f in result['families']:
            total=sum(f['histogram'])
            for i,count in enumerate(f['histogram']):
                fraction=count/total if total else None
                width=edges[i]-edges[i-1] if 1<=i<len(edges) else None
                writer.writerow([f['family'],i,count,fraction,fraction/width if width and fraction is not None else None])
    lines=['# QUICK family-level cohort diagnostics','',result['semantics'],'',
           '| Family | Cohorts | Lane calls | Full cohorts | Invalid cohorts |', '|---|---:|---:|---:|---:|']
    for f in result['families']:
        whole=f['scopes']['whole']
        lines.append(f"| {f['name']} | {whole['cohorts']} | {whole['lane_calls']} | {sum(r['participation'][32] for r in whole['rows'])} | {sum(r['invalid_groups'] for r in f['branches'])} |")
    lines += ['', 'Requests are joint maximum-order/active-count histograms. Summary JSON retains minimum orders, distinct-order counts, lane orders conditioned on cohort maximum, and bounded/tail splits. Branch probabilities use valid whole cohorts; equality is false for both strict comparisons. Full/partial refers to the whole observed cohort, not a same-order subgroup.', '',
              'Input histograms use lane counts and actual bin widths. Zero, invalid, and overflow bins have probability mass, not finite-width density. Unobserved families and conditional groups have null probabilities.', '',
              'Instrumentation may change scheduling. These records do not predict speedup and are never timing samples. Fixed-density and calibrated-replay results must be reported separately.', '',
              'Provenance and compact branch-rank counts: `summary.json`; histograms and requests: `histogram.csv`, `requests.csv`. The original `family-counters.csv` remains in the measurement directory. Detailed reports additionally contain `branches.csv` and `views.json`; compact case reports can be expanded from their summary without rerunning QUICK.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def aggregate(cases, settings, output):
    """cases: [{id, counters, provenance}]; do not combine workload modes."""
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('empty/duplicate diagnostic cases')
    modes={c['provenance']['mode'] for c in cases}
    if len(modes)!=1:
        raise ValueError('cannot pool fixed-density and SCF-replay observations')
    totals={}; accumulators=None; sources=[]
    vector_keys=('maximum','active','span','distinct','split','histogram')
    branch_keys=('all_gt','none_gt','mixed_gt','all_lt','none_lt','mixed_lt')
    def accumulate(acc,key,values):
        if key not in acc:acc[key]=[0.0]*len(values);acc[key+'_observed_cases']=0
        if values[0] is None:return
        acc[key]=[a+v for a,v in zip(acc[key],values)]
        acc[key+'_observed_cases']+=1
    for case in cases:
        counts=read_counters(case['counters'],settings)
        result=summarize_counts(counts,settings)
        case_views=views(result)
        if accumulators is None:
            accumulators=[dict(family=r['family'],name=r['name'],absent_cases=[],branches=[
                dict(maximum=b['maximum'],activity=b['activity']) for b in r['branches']]) for r in case_views]
        for acc,row in zip(accumulators,case_views):
            if row['maximum'][0] is None:acc['absent_cases'].append(case['id'])
            for key in vector_keys:accumulate(acc,key,row[key])
            for bacc,b in zip(acc['branches'],row['branches']):
                for key in branch_keys:accumulate(bacc,key,b[key])
        for key,count in counts.items():totals[key]=totals.get(key,0)+count
        sources.append(dict(id=case['id'],sha256=hashlib.sha256(Path(case['counters']).read_bytes()).hexdigest(),
                            provenance=case['provenance']))
    pooled=summarize_counts(totals,settings);pooled['provenance']=dict(mode=modes.pop(),cases=sources)
    output=Path(output);write_report(pooled,output/'pooled')
    for row in accumulators:
        for key in vector_keys:
            count=row[key+'_observed_cases'];row[key]=[v/count if count else None for v in row[key]]
        for b in row['branches']:
            for key in branch_keys:
                count=b.pop(key+'_observed_cases');b[key]=[v/count if count else None for v in b[key]]
            b['observed_cases']=count
    (output/'equal-case.json').write_text(json.dumps(dict(settings=settings,families=accumulators,
        weighting='equal observed case within each family/conditional group; cohort-normalized branches and lane-normalized inputs',
        provenance=pooled['provenance']),indent=2)+'\n')
    (output/'README.md').write_text('# Family diagnostic aggregation\n\n`pooled/` weights observations by their counts. `equal-case.json` normalizes each case first and averages only observed cases for each conditional group; missing cases are listed or counted. Both retain source hashes and workload provenance. No timing weights are used.\n')
    return pooled

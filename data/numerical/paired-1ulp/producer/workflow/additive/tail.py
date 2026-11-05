"""Portable materialized tail: A_n(u), 1 <= u < 4, exact exponent scaling.

The tabulated function is the complete integral, NOT Boys evaluated at u.
There is no exponential dictionary and no timing or hardware-specific policy.
"""
from functools import lru_cache
import math

import gmpy2 as g

from .reference import (_context, _precisions, bits64, from_bits, rn64, fma64, mul64,
                        add64, correction_code, ulp, residual_value, error_interval)
from .model import evaluate_row


@lru_cache(maxsize=128)
def reference(u, highest, precision=256):
    with _context(precision, g.RoundDown):
        pi_lo = g.const_pi()
        root_lo = g.sqrt(g.mpfr(u))
    with _context(precision, g.RoundUp):
        pi_hi = g.const_pi()
        root_hi = g.sqrt(g.mpfr(u))
        hi = g.sqrt(pi_hi)/(2*root_lo)
    with _context(precision, g.RoundDown):
        lo = g.sqrt(pi_lo)/(2*root_hi)
    result = [(lo, hi)]
    for n in range(highest):
        with _context(precision, g.RoundDown):
            lo = lo*(2*n+1)/(2*g.mpfr(u))
        with _context(precision, g.RoundUp):
            hi = hi*(2*n+1)/(2*g.mpfr(u))
        result.append((lo, hi))
    return tuple(result)


def coefficients(u, highest, first_output=0, last_output=None):
    last_output = highest if last_output is None else last_output
    if not 0 <= first_output <= last_output <= highest:
        raise ValueError('invalid output correction range')
    for precision in _precisions(256, 4096):
        values, residuals = [], []
        for n, (lo, hi) in enumerate(reference(u, highest, precision)):
            a, b = rn64(lo), rn64(hi)
            if a != b:
                break
            if not first_output <= n <= last_output:
                values.append(a)
                residuals.append(None)
                continue
            l = correction_code(a, hi)
            r = correction_code(a, lo)
            if l != r:
                break
            if not 0 <= l <= 192:
                raise ArithmeticError('invalid normalized low part')
            values.append(a)
            residuals.append(l)
        else:
            return values, residuals
    raise ArithmeticError('unresolved asymptotic coefficient rounding')


def normalize(x):
    exponent = (bits64(x) >> 52)-1023
    k = exponent//2
    u = from_bits((bits64(x) & ((1 << 52)-1)) | ((1023+(exponent & 1)) << 52))
    return u, k


def scale(value, n, k):
    # Exact-rational independent oracle for the runtime integer decoder.
    return rn64(g.mpq(value)/g.mpq(2)**((2*n+1)*k))


def row_index(u, b):
    s = 52-b
    return ((bits64(u)+(1 << (s-1))) >> s)-(1023 << b)


def node(row, b):
    return from_bits(((1023 << b)+row) << (52-b))


def cell(row, b):
    s, base = 52-b, 1023 << b
    a = max(bits64(1.0), ((base+row) << s)-(1 << (s-1)))
    end = min(bits64(4.0), ((base+row+1) << s)-(1 << (s-1)))
    return from_bits(a), from_bits(end-1)


def storage(first, degrees, b):
    if not degrees or not 0 <= b <= 20 or first < 0 or any(not 1 <= p <= 64 for p in degrees):
        raise ValueError('invalid tail configuration')
    top=max(first+i+p for i,p in enumerate(degrees))
    if top>128: raise ValueError('tail reference orders above 128 are unsupported')
    words=top-first+1+(len(degrees)+7)//8
    return dict(highest_reference_order=top,row_words=words,row_bytes=8*words,
                row_count=2*(1<<b)+1,table_bytes=(2*(1<<b)+1)*8*words)


def construct(first,last,degree,b,minimum_x=1e7):
    degrees=[degree]*(last-first+1) if isinstance(degree,int) else list(degree)
    if len(degrees)!=last-first+1 or not 1<=minimum_x<=1e7:
        raise ValueError('invalid tail range or seam')
    return dict(first=first,last=last,degrees=degrees,retained_bits=b,
                minimum_x=minimum_x,storage=storage(first,degrees,b))


@lru_cache(maxsize=128)
def row_data(u,top,first,last):
    return coefficients(u,top,first,last)


def evaluate_normalized(model,u):
    r=node(row_index(u,model['retained_bits']),model['retained_bits'])
    hi,low=row_data(r,model['storage']['highest_reference_order'],model['first'],model['last'])
    return {n:evaluate_row(hi,low,r,u,n,p)
            for n,p in zip(range(model['first'],model['last']+1),model['degrees'])}


def payload_rows(model):
    """Canonical words: ordinary coefficients, prebiased minimum, correction bytes."""
    import struct
    first,last=model['first'],model['last']
    size=model['storage']
    for i in range(size['row_count']):
        hi,low=row_data(node(i,model['retained_bits']),size['highest_reference_order'],first,last)
        words=[bits64(v) for v in hi[first:size['highest_reference_order']+1]]
        words[0]+=1
        raw=struct.pack('<'+'Q'*len(words),*words)+bytes(low[first:last+1])
        yield raw+bytes(size['row_bytes']-len(raw))


def evaluate(model, x, first=None, last=None):
    first = model['first'] if first is None else first
    last = model['last'] if last is None else last
    if not model['first'] <= first <= last <= model['last']:
        raise ValueError('tail subset outside model')
    if x == math.inf:
        return {n:0.0 for n in range(first,last+1)}
    if not math.isfinite(x) or x <= model['minimum_x']:
        return {n:math.nan for n in range(first,last+1)}
    u,k = normalize(x)
    values = evaluate_normalized(model,u)
    return {n:scale(values[n],n,k) for n in range(first,last+1)}


def exponent_cases(u, n, interval, minimum_x):
    # Normal results scale exactly. Check the smallest admitted exponent (largest
    # omitted tail), all subnormal-transition classes, and the extreme endpoint.
    minimum = 0
    while math.ldexp(u,2*minimum) <= minimum_x:
        minimum += 1
    exponent = int(g.get_exp(interval[1]))-1
    return sorted({minimum,511} | {k for k in range(minimum,512)
                  if -1077 <= exponent-(2*n+1)*k <= -1020})


def true_interval(interval, n, k, precision=256):
    # For x > 1e7 and n <= 128, the omitted integral satisfies
    # 0 < A_n(x)-F_n(x) < 2^-10000000. This deliberately loose bound avoids exp.
    power = (2*n+1)*k
    with _context(precision,g.RoundDown):
        lo = max(g.mpfr(0),g.div_2exp(interval[0],power)-g.exp2(-10000000))
    with _context(precision,g.RoundUp):
        hi = g.div_2exp(interval[1],power)
    return lo,hi


def check_point(model,x,error):
    """Actual Boys reference near the switch; no asymptotic omission shortcut."""
    from .reference import enclosure
    u,k=normalize(x)
    maximum=0.0
    for n,v in evaluate_normalized(model,u).items():
        result=scale(v,n,k)
        for precision in _precisions(256,4096):
            if x>=n+1:
                alo,ahi=reference(u,n,precision)[n]
                power=(2*n+1)*k
                # Positive omitted tail <= exp(-x)/(2*(x-max(n-.5,0))).
                # This bounds the actual Boys function and avoids its series in
                # the broad clearly passing region. Only ambiguous points pay
                # for the direct reference below.
                with _context(precision,g.RoundUp):
                    omitted=g.exp(-g.mpfr(x))/(2*(g.mpfr(x)-max(g.mpfr(n)-g.mpfr('.5'),0)))
                    hi=g.div_2exp(ahi,power)
                with _context(precision,g.RoundDown):
                    lo=max(g.mpfr(0),g.div_2exp(alo,power)-omitted)
                try:
                    lower,upper=error_interval(result,lo,hi,error['metric'])
                    if upper<=error['limit']:
                        maximum=max(maximum,math.nextafter(float(upper),math.inf))
                        break
                    if lower>error['limit']:
                        return dict(status='failed',witness=x.hex(),order=n)
                except ArithmeticError:
                    pass
            lo,hi,_=enclosure(n,x,precision,100000)
            lower,upper=error_interval(result,lo,hi,error['metric'])
            if lower>error['limit']:
                return dict(status='failed',witness=x.hex(),order=n)
            if upper<=error['limit']:
                maximum=max(maximum,math.nextafter(float(upper),math.inf))
                break
        else:
            return dict(status='unresolved',witness=x.hex(),order=n)
    return dict(status='qualified',max_error_upper=maximum)


def boundary(model,error,interior=4,refinement_rounds=2):
    """Sampled safe suffix, not a continuous-domain certificate.

    Scan all sampled exponent bands before refining the rightmost failure.
    The >1e7 region is separately checked by qualify at its fixed anchor.
    """
    if model['minimum_x']!=1e7:
        raise ValueError('boundary discovery requires the 1e7 anchor')
    far=qualify(model,error,interior,refinement_rounds)
    if not far['passed']: return dict(status='failed',far=far)
    points={1.0,1e7}
    for u in sample_inputs(model,interior):
        for k in range(12):
            x=math.ldexp(u,2*k)
            if 1<=x<=1e7: points.add(x)
    checked={}
    def check(x):
        if x not in checked: checked[x]=check_point(model,x,error)
        return checked[x]['status']
    for x in sorted(points):
        if check(x)=='unresolved': return checked[x]
    for _ in range(refinement_rounds):
        failures=[x for x,r in checked.items() if r['status']=='failed']
        if not failures: break
        left=max(failures)
        right=min((x for x,r in checked.items() if x>left and r['status']=='qualified'),default=None)
        if right is None: return dict(status='failed',reason='no suffix before anchor')
        for j in range(1,17):
            x=rn64(g.mpq(left)+(g.mpq(right)-g.mpq(left))*j/17)
            if check(x)=='unresolved': return checked[x]
    left=max((x for x,r in checked.items() if r['status']=='failed'),default=0.0)
    for right in sorted(x for x,r in checked.items() if x>left and r['status']=='qualified'):
        neighbor=math.nextafter(right,math.inf)
        status=check(neighbor)
        if status=='unresolved': return checked[neighbor]
        if status=='qualified':
            return dict(status='qualified',boundary=right.hex(),far=far,samples=len(checked),
                        evidence='sampled suffix; directed reference intervals')
    return dict(status='failed',reason='switch neighbors failed')


def measured_error(value, lo, hi, metric):
    if not math.isfinite(value) or value < 0:
        return g.mpfr('inf')
    # Avoid giant exact-rational denominators for correctly underflowed results.
    if value == 0 and hi < g.mpq(2)**-1075:
        with _context(256,g.RoundUp):
            return g.mul_2exp(hi,1074) if metric == 'ulp' else hi if metric == 'absolute' else g.mpfr(1)
    return error_interval(value,lo,hi,metric)[1]


def sample_inputs(model, interior):
    samples = set()
    b=model['retained_bits']
    for i in range(model['storage']['row_count']):
        r={'u':node(i,b)}
        a,z=cell(i,b)
        samples.update([a,z])
        if r['u'] < 4:
            samples.add(r['u'])
        for j in range(1,interior+1):
            samples.add(rn64(g.mpq(a)+(g.mpq(z)-g.mpq(a))*j/(interior+1)))
    for x in [math.nextafter(1e7,math.inf), math.nextafter(1e7,0.0), 1e7,
              float.fromhex('0x1.fffffffffffffp+1023')]:
        samples.add(normalize(x)[0])
    return sorted(samples)


def qualify(model, error, interior=4, refinement_rounds=2):
    maximum=g.mpq(0)
    witness=None
    checks=0
    seen={}
    cells={}
    samples=sample_inputs(model,interior)
    for iteration in range(refinement_rounds+1):
        for u in samples:
            if u in seen:
                continue
            values=evaluate_normalized(model,u)
            refs=reference(u,model['last'])
            local=g.mpq(0)
            for n,value in values.items():
                for k in exponent_cases(u,n,refs[n],model['minimum_x']):
                    result=scale(value,n,k) if math.isfinite(value) and value>=0 else value
                    lo,hi=true_interval(refs[n],n,k)
                    e=measured_error(result,lo,hi,error['metric'])
                    checks+=1
                    local=max(local,e)
                    if witness is None or e>maximum:
                        maximum=e
                        witness={'u':u.hex(),'k':k,'x':math.ldexp(u,2*k).hex(),'order':n,'value':result.hex()}
            seen[u]=local
            i=row_index(u,model['retained_bits'])
            if i not in cells or local>cells[i][0]:
                cells[i]=(local,u)
        if maximum>error['limit']:
            break
        samples=[]
        ordered=sorted(seen)
        import bisect
        for _,u in cells.values():
            pos=bisect.bisect_left(ordered,u)
            for neighbor in ordered[max(0,pos-1):pos]+ordered[pos+1:pos+2]:
                if row_index(neighbor,model['retained_bits'])==row_index(u,model['retained_bits']):
                    samples.append(rn64((g.mpq(u)+g.mpq(neighbor))/2))
    # Direct higher-precision reference check at the worst sampled witness.
    if witness and math.isfinite(float(maximum)):
        u=float.fromhex(witness['u']); n=witness['order']; k=witness['k']
        lo,hi=true_interval(reference(u,n,512)[n],n,k,512)
        e=measured_error(float.fromhex(witness['value']),lo,hi,error['metric'])
        maximum=max(maximum,e)
        witness['reference_lower']=str(lo); witness['reference_upper']=str(hi)
    return {'passed':maximum<=error['limit'],
        'maximum_error_upper':math.nextafter(float(maximum),math.inf) if maximum else 0.0,
        'witness':witness,'normalized_samples':len(seen),'order_exponent_checks':checks,
        'refinement_rounds':iteration,'omitted_tail_bound':'2^-10000000',
        'scope':'sampled mantissas; normal scaling equivalence plus subnormal/zero exponent classes; directed reference enclosures'}


def truncation_estimate(last, degree, b):
    # Bound for the exact finite Taylor polynomial of u^(-n-1/2).
    # This is a prioritization diagnostic, not a rejection certificate.
    with _context(256,g.RoundUp):
        r=g.mpfr(1)/(2*(1<<b)); s=g.mpfr(last)+g.mpfr('.5')
        term=g.mpfr(1)
        for j in range(1,degree+2):
            term=term*(s+j-1)*r/j
        ratio=r*(s+degree+1)/(degree+2)
        return float(term/(1-ratio)*(1+r)**s) if ratio<1 else math.inf


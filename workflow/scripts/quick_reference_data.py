"""MPFR construction and adaptive fallback for the CUDA binary128 reference."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

import gmpy2 as g

# Support both `python -m workflow.scripts.quick_reference_data` and an explicit
# script path (including invocation outside the repository working directory).
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workflow.additive.reference import enclosure, rounded_bits

DEGREE, MAX_ORDER, ROWS = 24, 12, 513
COLUMNS = DEGREE + MAX_ORDER + 1


def quad_bits(value):
    """RN-even positive normal binary128; no decimal or binary64 intermediate."""
    with g.context(precision=113, round=g.RoundToNearest):
        q = g.mpfr(value)
    if not q:
        return 0
    if q < 0 or not g.is_finite(q):
        raise ValueError('expected nonnegative finite table value')
    with g.context(precision=113):
        exponent, fraction = g.frexp(q)
        significand = int(g.mul_2exp(fraction, 113))
    encoded = exponent - 1 + 16383
    if not 0 < encoded < 32767:
        raise ValueError('table value outside normal binary128 range')
    return (encoded << 112) + significand - (1 << 112)


def agreed_quad(lo, hi):
    a, b = quad_bits(lo), quad_bits(hi)
    if a != b:
        raise ArithmeticError('binary128 table rounding unresolved')
    return a.to_bytes(16, 'little')


def generate(path):
    data = bytearray()
    for row in range(ROWS):
        x = row / 4
        lo, hi, _ = enclosure(COLUMNS-1, x, 256, 4096, coarse=False)
        with g.context(precision=256, round=g.RoundDown):
            elo = g.exp(-g.mpfr(x))
        with g.context(precision=256, round=g.RoundUp):
            ehi = g.exp(-g.mpfr(x))
        values = [None] * COLUMNS
        values[-1] = agreed_quad(lo, hi)
        for n in range(COLUMNS-2, -1, -1):
            with g.context(precision=256, round=g.RoundDown):
                lo = (2*g.mpfr(x)*lo+elo)/(2*n+1)
            with g.context(precision=256, round=g.RoundUp):
                hi = (2*g.mpfr(x)*hi+ehi)/(2*n+1)
            values[n] = agreed_quad(lo, hi)
        data.extend(b''.join(values))
    for k in range(DEGREE+1):
        data.extend(quad_bits(g.mpq(1,k) if k else 0).to_bytes(16,'little'))
    with g.context(precision=256, round=g.RoundDown):
        lo = g.sqrt(g.const_pi())/2
    with g.context(precision=256, round=g.RoundUp):
        hi = g.sqrt(g.const_pi())/2
    data.extend(agreed_quad(lo,hi))
    path.write_bytes(data)
    record = {'rows': ROWS, 'columns': COLUMNS, 'degree': DEGREE,
              'max_order': MAX_ORDER, 'bytes': len(data),
              'sha256': hashlib.sha256(data).hexdigest(), 'precision_bits': 256,
              'mpfr': g.mpfr_version(), 'gmpy2': g.version(),
              'rounding': 'directed enclosures agree on RN-even binary128',
              'domain': [0,128], 'step': '0x1p-2'}
    path.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def correct(n, x):
    if type(n) is not int or not 0 <= n <= MAX_ORDER or math.isnan(x) or x < 0:
        raise ValueError('reference requires order 0..12 and nonnegative x')
    if math.isinf(x) and x > 0:
        return 0, 0
    for precision in (256,512,1024,2048,4096,8192):
        lo, hi, _ = enclosure(n,x,precision,32768,coarse=False)
        a, b = rounded_bits(lo), rounded_bits(hi)
        if a == b:
            return a, precision
    raise ArithmeticError(f'MPFR failed to resolve rounding for n={n}, x={x.hex()}')


def resolve(requests, destination):
    old = {}
    if destination.exists():
        old = {(x,n): value for x,n,value in struct.iter_unpack('<QQQ',destination.read_bytes())}
    values = dict(old)
    precision = 0
    for bits,n in set(struct.iter_unpack('<QQ',requests.read_bytes())):
        if n > MAX_ORDER:
            raise ValueError('reference order outside supported range')
        if (bits,n) in values:
            continue
        x = struct.unpack('<d',struct.pack('<Q',bits))[0]
        values[bits,n], p = correct(n,x)
        precision = max(precision,p)
    if values == old:
        raise RuntimeError('unresolved requests made no progress')
    destination.write_bytes(b''.join(struct.pack('<QQQ',x,n,v) for (x,n),v in sorted(values.items())))
    return {'resolved_total':len(values),'max_new_precision_bits':precision}


def fixtures(path):
    xs = {0.0, math.ldexp(1.,-1074), math.ldexp(1.,-1022), 128., 8192., math.inf,
          float.fromhex('0x1.fffffffffffffp+1023')}
    for row in range(ROWS):
        for x in (row/4, row/4+0.125):
            xs.update((x,math.nextafter(x,0.),math.nextafter(x,math.inf)))
    for x in (128.,256.,1024.,2048.,4096.,8192.):
        xs.update((x,math.nextafter(x,0.),math.nextafter(x,math.inf)))
    rng = random.Random(48217)
    xs.update(rng.uniform(0,256) for _ in range(200))
    xs.update(math.ldexp(rng.uniform(1,2),e) for e in range(-1022,1024,31))
    data = bytearray()
    for x in sorted(xs):
        for n in range(MAX_ORDER+1):
            value, _ = correct(n,x)
            data.extend(struct.pack('<dQQ',x,n,value))
    path.write_bytes(data)
    path.with_suffix('.json').write_text(json.dumps({'records':len(data)//24,'bytes':len(data),
        'sha256':hashlib.sha256(data).hexdigest(),'mpfr':g.mpfr_version(),
        'reference':'adaptive directed MPFR intervals at exact binary64 arguments'},indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=('generate','fixtures','resolve'))
    parser.add_argument('output',type=Path)
    parser.add_argument('--requests',type=Path)
    args = parser.parse_args()
    if args.action == 'resolve' and args.requests is None:
        parser.error('resolve requires --requests')
    if args.action == 'generate': generate(args.output)
    elif args.action == 'fixtures': fixtures(args.output)
    else: print(json.dumps(resolve(args.requests,args.output)))

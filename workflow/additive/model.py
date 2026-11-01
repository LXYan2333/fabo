"""Canonical additive nearest-node grid and fully materialized Taylor DAG."""
from dataclasses import dataclass
from functools import lru_cache
import math
import gmpy2 as g
from .reference import (add64, bits64, from_bits, reference_data, rn64,
                        mul64, fma64, assemble_output)


@dataclass(frozen=True)
class Grid:
    b: int
    e: int | None = None
    m: int | None = None
    domain_end: float = 1e7
    offset_code: int | None = None

    def __post_init__(self):
        if (type(self.b) is not int or not 1 <= self.b <= 20 or
                not math.isfinite(self.domain_end) or not 0 < self.domain_end <= 1e7):
            raise ValueError('invalid additive-grid configuration')
        if self.offset_code is None:
            if (type(self.e) is not int or not -64 <= self.e <= 32 or
                    type(self.m) is not int or not 1 <= self.m <= 2**self.b):
                raise ValueError('invalid legacy offset')
        elif (self.e is not None or self.m is not None or type(self.offset_code) is not int or
              not 0 <= self.offset_code <= (0x7fefffffffffffff >> self.shift)):
            raise ValueError('invalid aligned offset code')
        if bits64(add64(self.domain_end, self.offset)) + (1 << (self.shift-1)) >= 2**64:
            raise ValueError('quantizer addition overflows')

    @property
    def offset(self):
        if self.offset_code is not None:
            return from_bits(self.offset_code << self.shift)
        return math.ldexp(float(2*(1 << self.b)-self.m), self.e)

    @property
    def shift(self):
        return 52-self.b

    def key(self, x):
        if not math.isfinite(x) or not 0 <= x <= self.domain_end:
            raise ValueError('input outside main domain')
        return (bits64(add64(x, self.offset))+(1 << (self.shift-1))) >> self.shift

    @property
    def keys(self):
        return range(self.key(0.0), self.key(self.domain_end)+1)

    def node(self, key):
        return add64(from_bits(key << self.shift), -self.offset)

    def transition(self, key):
        """First binary64 input mapped to key or higher; monotone bit search."""
        if key <= self.keys.start:
            return 0.0
        if key >= self.keys.stop:
            return math.nextafter(self.domain_end, math.inf)
        left, right = 0, bits64(self.domain_end)
        while left < right:
            mid = (left+right)//2
            if self.key(from_bits(mid)) < key:
                left = mid+1
            else:
                right = mid
        return from_bits(left)

    def cell(self, key):
        if key not in self.keys:
            raise ValueError('invalid row key')
        return (self.transition(key), self.domain_end if key == self.keys.stop-1
                else math.nextafter(self.transition(key+1), -math.inf))

    def metadata(self):
        result = dict(b=self.b, offset=self.offset.hex(), offset_code=bits64(self.offset) >> self.shift,
                    domain_end=self.domain_end.hex(), shift=self.shift,
                    key_min=self.keys.start, key_max=self.keys.stop-1,
                    row_count=len(self.keys), quantizer='nearest-half-up')
        if self.offset_code is None:
            result.update(e=self.e, m=self.m)
        return result


def from_metadata(meta):
    if 'offset_code' in meta:
        return Grid(meta['b'], domain_end=float.fromhex(meta['domain_end']), offset_code=meta['offset_code'])
    return Grid(meta['b'], meta['e'], meta['m'], float.fromhex(meta['domain_end']))


@lru_cache(maxsize=128)
def row_data(x_ref, highest, first, last):
    return reference_data(x_ref, highest, first, last)


def evaluate_order(grid, x, n, degree):
    hi, codes = row_data(grid.node(grid.key(x)), n+degree, n, n)
    return evaluate_row(hi, codes, grid.node(grid.key(x)), x, n, degree)


def evaluate_row(hi, codes, x_ref, x, n, degree):
    h = add64(x_ref, -x)
    tail = hi[n+degree]
    for k in range(degree-1, 0, -1):
        tail = fma64(mul64(h, rn64(g.mpq(1, k+1))), tail, hi[n+k])
        if not math.isfinite(tail):
            raise FloatingPointError('nonfinite Taylor intermediate')
    return assemble_output(hi[n], codes[n], h, tail)


def storage(grid, first, degrees):
    highest = max(first+i+p for i, p in enumerate(degrees))
    coefficients = 8*(highest-first+1)
    corrections = len(degrees)
    stride = ((coefficients+corrections+7)//8)*8
    return dict(highest_reference_order=highest, coefficient_bytes_per_row=coefficients,
                correction_bytes_per_row=corrections,
                padding_bytes_per_row=stride-coefficients-corrections,
                row_bytes=stride, table_bytes=len(grid.keys)*stride)

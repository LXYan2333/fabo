"""Portable exact binary64 arithmetic and directed MPFR Boys references.

Extracted from fresh-start c3c5788; no runtime exponential or recurrence patches.
MPFR exponentials are used only to construct offline mathematical references.
"""
from functools import lru_cache
import math
import struct
import gmpy2 as g
SIGN = 1 << 63

def from_bits(bits):
    return struct.unpack(">d", struct.pack(">Q", bits))[0]

def rounded_bits(value):
    """Exact rational-to-binary64 RN-even, including gradual underflow."""
    # gmpy2 2.3.1/2.3.2 mpq.as_integer_ratio leaks both returned mpz
    # references. mpq also converts an MPFR input exactly, without rounding.
    rational = g.mpq(value)
    a, b = int(rational.numerator), int(rational.denominator)
    if a < 0:
        raise ValueError("only nonnegative values supported")
    if not a:
        return 0
    exponent = a.bit_length() - b.bit_length()
    below_power = a < (b << exponent) if exponent >= 0 else (a << -exponent) < b
    if below_power:
        exponent -= 1
    quantum = max(exponent - 52, -1074)
    numerator, denominator = (a, b << quantum) if quantum >= 0 else (a << -quantum, b)
    significand, remainder = divmod(numerator, denominator)
    if 2 * remainder > denominator or (2 * remainder == denominator and significand % 2):
        significand += 1
    if quantum == -1074 and significand < 2**52:
        return significand
    if significand == 2**53:
        significand >>= 1
        quantum += 1
    encoded_exponent = quantum + 52 + 1023
    if encoded_exponent >= 2047:
        return 0x7ff0000000000000
    return (encoded_exponent << 52) + significand - 2**52

def enclosure(n, x, precision, max_terms, coarse=False):
    """Enclose the integral at the exact input binary64 value.

    Large x: A_n=Gamma(n+1/2)/(2*x**(n+1/2)), with a bounded omitted tail.
    For x>=n+1, tail <= exp(-x)/(2*(x-max(n-1/2,0))) <= 2**(-x).
    Smaller x: positive series exp(-x)*sum_k (2*x)^k/prod_j(2*n+2*j+1).
    Decreasing term ratios give a geometric remainder bound once ratio<1.
    """
    if n < 0 or not math.isfinite(x) or x < 0 or precision < 128:
        raise ValueError("invalid order, input, or precision")
    def directed(mode, operation):
        with g.context(precision=precision, round=mode, emin=-1000000000,
                       emax=1000000000, trap_underflow=True, trap_overflow=True):
            return operation()
    def down(operation):
        return directed(g.RoundDown, operation)
    def up(operation):
        return directed(g.RoundUp, operation)
    xx = down(lambda: g.mpfr(x))  # precision >=128: exact conversion
    tail_bits = precision + 2048
    if x >= max(n + 1, tail_bits):
        sqrt_lo = down(lambda: g.sqrt(xx))
        sqrt_hi = up(lambda: g.sqrt(xx))
        lo = down(lambda: g.sqrt(g.const_pi()) / (2 * sqrt_hi))
        hi = up(lambda: g.sqrt(g.const_pi()) / (2 * sqrt_lo))
        for order in range(1, n + 1):
            lo = down(lambda: lo * (2 * order - 1) / (2 * xx))
            hi = up(lambda: hi * (2 * order - 1) / (2 * xx))
        lo = down(lambda: max(g.mpfr(0), lo - g.mul_2exp(g.mpfr(1), -tail_bits)))
        return lo, hi, "complete-integral-minus-bounded-tail"

    exp_lo = down(lambda: g.exp(-xx))
    exp_hi = up(lambda: g.exp(-xx))
    lower = down(lambda: exp_lo / (2 * n + 1))
    if coarse:
        raise ValueError("coarse subnormal classifier is not part of this reference API")
    lo = down(lambda: g.mpfr(1) / (2 * n + 1))
    hi = up(lambda: g.mpfr(1) / (2 * n + 1))
    total_lo, total_hi = lo, hi
    for k in range(1, max_terms + 1):
        lo = down(lambda: lo * (2 * xx) / (2 * n + 2 * k + 1))
        hi = up(lambda: hi * (2 * xx) / (2 * n + 2 * k + 1))
        total_lo = down(lambda: total_lo + lo)
        total_hi = up(lambda: total_hi + hi)
        ratio = up(lambda: 2 * xx / (2 * n + 2 * k + 3))
        if ratio < 1:
            denominator = down(lambda: 1 - ratio)
            remainder = up(lambda: hi * ratio / denominator)
            target = down(lambda: g.mul_2exp(total_hi, -precision + 16))
            if remainder <= target:
                return (down(lambda: exp_lo * total_lo),
                        up(lambda: exp_hi * (total_hi + remainder)), "positive-series")
    raise RuntimeError("series term budget exhausted; increase max_series_terms")

def bits64(value):
    return struct.unpack('<Q', struct.pack('<d', value))[0]

def rn64(value, *, negative_zero=False):
    """Round an exact rational to binary64 RN-even, with gradual underflow."""
    value = g.mpq(value)
    negative = value < 0 or (not value and negative_zero)
    return from_bits(rounded_bits(abs(value)) | (SIGN if negative else 0))

def _finite(*values):
    if any(type(v) is not float or not math.isfinite(v) for v in values):
        raise ValueError('recurrence operations require finite binary64 floats')

def mul64(a, b):
    """Exact product followed by one binary64 rounding, independent of host FMA."""
    _finite(a, b)
    return rn64(g.mpq(a)*g.mpq(b), negative_zero=bool((bits64(a)^bits64(b)) & SIGN))

def fma64(a, b, c):
    """Exact product-plus-addend followed by one binary64 rounding."""
    _finite(a, b, c)
    negative_zero = (a == 0 or b == 0) and c == 0 and ((bits64(a)^bits64(b)) & bits64(c) & SIGN)
    return rn64(g.mpq(a)*g.mpq(b)+g.mpq(c), negative_zero=bool(negative_zero))

def _precisions(initial, maximum):
    precision = initial
    while True:
        yield precision
        if precision == maximum:
            break
        precision = min(2*precision, maximum)

def _context(precision, rounding):
    return g.context(precision=precision, round=rounding,
                     emin=-1000000000, emax=1000000000,
                     trap_underflow=True, trap_overflow=True)

def _round_positive(value):
    # Avoid materializing a huge rational denominator for a tiny MPFR exp.
    # The equality case also rounds to zero (ties to even).
    if value <= g.mpq(1, 1 << 1075):
        return 0
    return rounded_bits(value)

def _boys(order, x, initial, maximum, max_terms):
    for precision in _precisions(initial, maximum):
        lo, hi, method = enclosure(order, x, precision, max_terms, coarse=False)
        # The large-x enclosure may extend below zero; the integral cannot.
        lo = max(lo, g.mpfr(0))
        a, b = _round_positive(lo), _round_positive(hi)
        if a == b and (x == 0 or lo > 0):
            return from_bits(a), precision, lo, hi, method
    raise ArithmeticError(f'MPFR precision budget exhausted for F_{order}({x.hex()})')

def add64(a, b):
    return rn64(g.mpq(a) + g.mpq(b))

def round_integer(value):
    """Exact signed rational, nearest integer with ties to even."""
    negative = value < 0
    # Avoid the leaking mpq.as_integer_ratio in gmpy2 2.3.1/2.3.2.
    rational = abs(g.mpq(value))
    a, b = int(rational.numerator), int(rational.denominator)
    q, r = divmod(a, b)
    q += 2*r > b or (2*r == b and q % 2 != 0)
    return -q if negative else q

def ulp(value):
    exponent = (bits64(value) >> 52) & 2047
    if exponent == 2047 or value < 0:
        raise ValueError('ULP requires finite nonnegative binary64')
    return g.mpq(2)**max(-1074, int(exponent)-1023-52)

@lru_cache(maxsize=128)
def reference_sequence(x, highest, precision=256):
    """Directed enclosures for all orders, reused across candidate lattices.

    One highest-order evaluation followed by interval downward recurrence.
    Values are exact binary64 coordinates, never decimal approximations.
    """
    _, _, lo, hi, _ = _boys(highest, x, precision, precision, 100000)
    with _context(precision, g.RoundDown):
        e_lo = g.exp(-g.mpfr(x)) if x < 1e5 else g.mpfr(0)
    with _context(precision, g.RoundUp):
        # For huge x a positive conservative exp enclosure avoids exponent overflow.
        e_hi = g.exp(-g.mpfr(x)) if x < 1e5 else g.mul_2exp(g.mpfr(1), -100000)
    intervals = [None]*(highest+1)
    intervals[highest] = (lo, hi)
    for n in range(highest-1, -1, -1):
        with _context(precision, g.RoundDown):
            lo = (2*g.mpfr(x)*lo+e_lo)/(2*n+1)
        with _context(precision, g.RoundUp):
            hi = (2*g.mpfr(x)*hi+e_hi)/(2*n+1)
        intervals[n] = lo, hi
    return tuple(intervals)

def reference_data(x, highest, first_output=0, last_output=None):
    """Round all reference coefficients, but encode only requested outputs.

    Non-output correction slots are None, never an apparently usable byte.
    The default preserves callers explicitly requesting corrections for all orders.
    """
    last_output = highest if last_output is None else last_output
    if not 0 <= first_output <= last_output <= highest:
        raise ValueError('invalid output correction range')
    for precision in _precisions(256, 4096):
        try:
            intervals = reference_sequence(x, highest, precision)
        except ArithmeticError:
            continue
        rounded, residuals = [], []
        for n, (lo, hi) in enumerate(intervals):
            a, b = rn64(lo), rn64(hi)
            if bits64(a) != bits64(b):
                break
            if not first_output <= n <= last_output:
                rounded.append(a)
                residuals.append(None)
                continue
            r_lo = correction_code(a, hi)
            r_hi = correction_code(a, lo)
            if r_lo != r_hi:
                break
            if not 0 <= r_lo <= 192:
                raise ArithmeticError('low-part code outside rounding residual range')
            rounded.append(a)
            residuals.append(r_lo)
        else:
            return rounded, residuals
    raise ArithmeticError(f'unresolved reference or residual rounding at {x.hex()}')

def taylor_reference(x, center, highest, degree=32, precision=256):
    """Bounded MPFR Taylor acceleration, followed by interval downward recurrence.

    Only F_highest(x) needs a Taylor evaluation. The remainder is bounded by
    min(1/(2m+1), Gamma(m+1/2)/(2*a^(m+1/2))) * |x-center|^degree/degree!,
    m=highest+degree, a=min(x,center). Both derivative bounds are upper bounds
    on the positive Boys integral. No binary64-rounded reference is substituted.
    """
    source = reference_sequence(center, highest+degree, precision)
    h = g.mpq(center)-g.mpq(x)
    lo, hi = source[highest+degree-1]
    for k in range(degree-2, -1, -1):
        lower_source, upper_source = source[highest+k]
        a, b = (lo, hi) if h >= 0 else (hi, lo)
        with _context(precision, g.RoundDown):
            next_lo = g.mpfr(h)*a/(k+1)+lower_source
        with _context(precision, g.RoundUp):
            next_hi = g.mpfr(h)*b/(k+1)+upper_source
        lo, hi = next_lo, next_hi
    m, left = highest+degree, min(x, center)
    with _context(precision, g.RoundUp):
        derivative = g.mpfr(1)/(2*m+1)
    if left > 0:
        with _context(precision, g.RoundDown):
            sqrt_left = g.sqrt(g.mpfr(left))
        with _context(precision, g.RoundUp):
            complete = g.sqrt(g.const_pi())/(2*sqrt_left)
            for n in range(1, m+1):
                complete = complete*(2*n-1)/(2*g.mpfr(left))
            derivative = min(derivative, complete)
    with _context(precision, g.RoundUp):
        remainder = derivative*g.mpfr(abs(h))**degree/math.factorial(degree)
        hi = hi+remainder
        e_hi = g.exp(-g.mpfr(x)) if x < 1e5 else g.mul_2exp(g.mpfr(1), -100000)
    with _context(precision, g.RoundDown):
        lo = max(g.mpfr(0), lo-remainder)
        e_lo = g.exp(-g.mpfr(x)) if x < 1e5 else g.mpfr(0)
    result = [None]*(highest+1)
    result[highest] = (lo, hi)
    for n in range(highest-1, -1, -1):
        with _context(precision, g.RoundDown):
            lo = (2*g.mpfr(x)*lo+e_lo)/(2*n+1)
        with _context(precision, g.RoundUp):
            hi = (2*g.mpfr(x)*hi+e_hi)/(2*n+1)
        result[n] = lo, hi
    return tuple(result)

def residual_value(hi, code):
    """Positive next-up correction; independent exact-rational decoder."""
    exponent = (bits64(hi) >> 52) & 2047
    if not 54 <= exponent <= 2046 or hi <= 0 or bits64(hi)+1 >= 0x7ff0000000000000:
        raise ValueError('unsupported next-up coefficient exponent')
    if type(code) is not int or not 0 <= code <= 192:
        raise ValueError('invalid next-up correction code')
    return rn64(ulp(hi)*(g.mpq(1,2)+g.mpq(code,256) if code <= 128 else g.mpq(1)+g.mpq(code-128,128)))

def correction_code(hi, reference):
    """Round directly from an exact value or directed MPFR endpoint."""
    try:
        residual_value(hi, 128)  # Validate the bit decoder's domain.
    except ValueError as exc:
        # A numerical representability failure, not a configuration/programming
        # error: candidate workers must record it rather than abort their pool.
        raise ArithmeticError('unrepresentable output correction: '+str(exc)) from exc
    delta = (g.mpq(from_bits(bits64(hi)+1))-g.mpq(reference))/ulp(hi)
    code = round_integer(256*(delta-g.mpq(1,2))) if delta <= 1 else 128+round_integer(128*(delta-1))
    if not 0 <= code <= 192:
        raise ArithmeticError('next-up correction outside rounding range')
    return code

def assemble_output(hi, code, h, tail):
    """Shared canonical rounded DAG for screening and full qualification."""
    correction = fma64(h, tail, -residual_value(hi, code))
    if not math.isfinite(correction):
        raise FloatingPointError('nonfinite final Taylor correction')
    return add64(from_bits(bits64(hi)+1), correction)

def error_interval(value, lo, hi, metric):
    lo, hi, value = g.mpq(lo), g.mpq(hi), g.mpq(value)
    lower = max(g.mpq(0), lo-value, value-hi)
    upper = max(abs(value-lo), abs(value-hi))
    if metric == 'absolute':
        return lower, upper
    if metric == 'relative':
        if lo <= 0:
            raise ArithmeticError('relative error reference interval includes zero')
        return lower/hi, upper/lo
    if metric == 'ulp':
        if bits64(rn64(lo)) != bits64(rn64(hi)):
            raise ArithmeticError('ULP reference rounding unresolved')
        quantum = ulp(rn64(lo))
        return lower/quantum, upper/quantum
    raise ValueError('unknown error metric')

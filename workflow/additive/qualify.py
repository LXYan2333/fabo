"""Sampled qualification, not a continuous-domain implementation-error proof."""
import math
import gmpy2 as g
from .model import evaluate_order
from .reference import _precisions, reference_sequence, taylor_reference, error_interval


def measure(grid, x, n, p, metric, limit):
    value = evaluate_order(grid, x, n, p)
    # Taylor intervals accelerate normal cases; direct MPFR resolves tight gates.
    for precision in _precisions(256, 4096):
        try:
            if precision == 256:
                lo, hi = taylor_reference(x, grid.node(grid.key(x)), n)[n]
                lower, upper = error_interval(value, lo, hi, metric)
                if upper <= limit or lower > limit:
                    return lower, upper
            lo, hi = reference_sequence(x, n, precision)[n]
            lower, upper = error_interval(value, lo, hi, metric)
            if upper <= limit or lower > limit:
                return lower, upper
        except ArithmeticError:
            continue
    raise ArithmeticError('unresolved error threshold at '+x.hex())


def samples(grid, key, subdivisions):
    a, b = grid.cell(key)
    points = {a, b}
    r = grid.node(key)
    if a <= r <= b:
        points.add(r)
    for j in range(1, subdivisions):
        points.add(a+(b-a)*(j/subdivisions))
    for x in (a, b, r):
        for toward in (-math.inf, math.inf):
            y = math.nextafter(x, toward)
            if 0 <= y <= grid.domain_end:
                points.add(y)
    return sorted(points)


def qualify(grid, n, p, metric='ulp', limit=1, subdivisions=4, refinement=0, keys=None):
    maximum, witness, count = g.mpq(0), 0.0, 0
    last_checked = 0.0
    def check(x):
        nonlocal maximum, witness, count, last_checked
        last_checked = x
        count += 1
        lower, upper = measure(grid, x, n, p, metric, g.mpq(limit))
        if upper >= maximum:
            maximum, witness = upper, x
        return lower > limit
    try:
        for key in grid.keys if keys is None else keys:
            for x in samples(grid, key, subdivisions):
                if check(x):
                    return dict(status='failed', witness=x.hex(), samples=count)
        for level in range(refinement):
            a, b = grid.cell(grid.key(witness))
            step = (b-a)/(subdivisions*2**(level+1))
            center = witness
            for x in (center-step, center+step, math.nextafter(center, 0.0),
                      math.nextafter(center, math.inf)):
                if 0 <= x <= grid.domain_end and check(x):
                    return dict(status='failed', witness=x.hex(), samples=count)
        # Recompute the saved maximum witness directly at >=512 bits.
        from .model import evaluate_order
        for precision in _precisions(512, 4096):
            lo, hi = reference_sequence(witness, n, precision)[n]
            lower, upper = error_interval(evaluate_order(grid, witness, n, p), lo, hi, metric)
            if upper <= limit:
                break
            if lower > limit:
                return dict(status='failed', witness=witness.hex(), samples=count)
        else:
            raise ArithmeticError('maximum witness unresolved')
        # Keep the displayed binary64 number an upper bound after serialization.
        reported = float(maximum)
        if g.mpq(reported) < maximum:
            reported = math.nextafter(reported, math.inf)
        return dict(status='qualified', max_error_upper=reported,
                    witness=witness.hex(), samples=count, evidence='sampled; directed reference enclosures')
    except FloatingPointError as exc:
        # Exact Boys values are finite on this domain. Overflow is therefore a
        # demonstrated candidate failure, not a failure of the entire shard.
        return dict(status='failed', witness=last_checked.hex(), reason=str(exc), samples=count)
    except ArithmeticError as exc:
        return dict(status='unresolved', reason=str(exc), samples=count)

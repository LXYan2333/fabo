from pathlib import Path

import gmpy2 as g
import pytest

from workflow.additive.reference import enclosure
from workflow.scripts.plot_grid_remainders import (
    agreement, boundaries, boys, calculate, load_model,
)


def test_current_main_model():
    winner, grid, degree, nodes, _ = load_model(
        Path('data/numerical/paired-1ulp/summary.json'), Path('include'))
    assert degree == 4
    assert len(nodes) == 3272
    assert winner['storage']['table_bytes'] == 157056
    assert grid.offset == 4.046875
    assert nodes[0] == 0 and nodes[-1] < g.mpq(grid.domain_end)
    end = g.mpq(grid.domain_end)
    uniform = [i*end/(len(nodes)-1) for i in range(len(nodes))]
    assert uniform[-1] == end
    assert all(b-a == end/(len(nodes)-1) for a,b in zip(uniform,uniform[1:]))
    assert [g.mpq(2)**e-g.mpq(grid.offset) for e in (3,4,5)] == [
        g.mpq('253/64'), g.mpq('765/64'), g.mpq('1789/64')]


@pytest.mark.parametrize('x', [0.0, 0.001, 3.953125, 11.953125, 27.953125, 34.5])
def test_analytic_reference_against_directed_series(x):
    with g.context(precision=512):
        values = boys(x, 5)
        for n, value in enumerate(values):
            low, high, _ = enclosure(n, x, 256, 10000)
            assert low <= value <= high


def test_boundaries_and_remainder():
    nodes = [g.mpq(0), g.mpq('1/256'), g.mpq('1/128')]
    end = g.mpq('5/512')
    points = list(boundaries(nodes,end))
    assert points == [(0,None,0),(g.mpq('1/512'),0,1),
                      (g.mpq('3/512'),1,2),(end,2,None)]
    low, high = [calculate(nodes,end,4,p) for p in (256,512)]
    assert agreement(low,high)
    assert not agreement(low[:-1],high)
    assert high[0]['maximum'] == 0
    assert high[0]['relative_one_ulp'] == g.mpfr(2)**-52
    assert high[-1]['maximum'] > 0
    for row in high:
        assert g.mpfr(2)**-53 < row['relative_one_ulp'] <= g.mpfr(2)**-52
        assert row['maximum'] == max(e for e in row['errors'] if e is not None)
        for error,bound in zip(row['errors'],row['bounds']):
            if error is not None:
                assert error <= bound


def test_binade_neighbor_precision():
    _,grid,degree,nodes,_ = load_model(
        Path('data/numerical/paired-1ulp/summary.json'),Path('include'))
    for edge in (g.mpq('253/64'),g.mpq('765/64'),g.mpq('1789/64')):
        i = nodes.index(edge)
        # Include zero to preserve the boundary helper's domain contract.
        selected = [nodes[0], *nodes[i-1:i+2]]
        assert agreement(calculate(selected,selected[-1],degree,256),
                         calculate(selected,selected[-1],degree,512))

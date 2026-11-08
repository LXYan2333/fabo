"""Compare mathematical Taylor remainders at matched-grid cell boundaries."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

import gmpy2 as g

from workflow.additive.model import from_metadata


def boys(x, highest):
    """High-precision analytic F0 and recurrence, not binary64 evaluation.

    Caller supplies the MPFR precision. Zero is exact; precision doubling
    checks cancellation in recurrence and in the final polynomial subtraction.
    """
    x = g.mpfr(x)
    if x == 0:
        return [g.mpfr(1) / (2*n+1) for n in range(highest+1)]
    root = g.sqrt(x)
    values = [g.sqrt(g.const_pi()) * g.erf(root) / (2*root)]
    exponential = g.exp(-x)
    for n in range(highest):
        values.append(((2*n+1)*values[-1]-exponential)/(2*x))
    return values


def load_model(summary, include):
    winner = json.loads(summary.read_text())['winners']['0-0']
    grid = from_metadata(winner['grid'])
    public = include / 'fast_boys/models/data_0_0.h'
    target = re.search(r'#include "([^"]+)"', public.read_text()).group(1)
    header = (include / target).with_name('model.h')
    source = header.read_text()
    for field, value in [('row_count', len(grid.keys)), ('retained_bits', grid.b),
                         ('main_table_bytes', winner['storage']['table_bytes'])]:
        assert re.search(r'\b'+field+r'\s*=\s*'+str(value)+r'\b', source), field
    assert f'offset={grid.offset.hex()}' in source
    assert f'domain_end={grid.domain_end.hex()}' in source
    degree = winner['degrees'][0]
    assert re.search(r'degrees\[\]\s*=\s*\{\s*'+str(degree)+r'\s*\}', source)
    assert winner['payload_sha256'] in source
    nodes = [g.mpq(grid.node(key)) for key in grid.keys]
    return winner, grid, degree, nodes, header


def boundaries(nodes, end):
    assert nodes[0] == 0 and nodes[-1] <= end
    assert all(a < b for a, b in zip(nodes, nodes[1:]))
    yield g.mpq(0), None, 0
    for i in range(len(nodes)-1):
        yield (nodes[i]+nodes[i+1])/2, i, i+1
    yield end, len(nodes)-1, None


def calculate(nodes, end, degree, precision):
    rows = []
    with g.context(precision=precision, round=g.RoundToNearest):
        coefficients = [boys(r, degree) for r in nodes]
        for boundary, left, right in boundaries(nodes, end):
            x = g.mpfr(boundary)
            truth = boys(x, 0)[0]
            errors, bounds = [], []
            for index in (left, right):
                if index is None:
                    errors.append(None)
                    bounds.append(None)
                    continue
                r = g.mpfr(nodes[index])
                h = r-x
                # Factorial Horner, in MPFR with mathematical coefficients.
                q = coefficients[index][degree]
                for j in range(degree-1, -1, -1):
                    q = coefficients[index][j]+h*q/(j+1)
                error = abs(truth-q)/truth
                if boundary == nodes[index]:
                    error = g.mpfr(0)
                bound = abs(h)**(degree+1)/math.factorial(degree+1)*boys(min(x,r),degree+1)[-1]/truth
                assert error <= bound*(1+g.mpfr('1e-30')) or error < g.mpfr(2)**(-precision//2)
                errors.append(error)
                bounds.append(bound)
            rows.append(dict(x=boundary, left=left, right=right, errors=errors,
                             bounds=bounds, maximum=max(e for e in errors if e is not None),
                             relative_one_ulp=g.mpfr(2)**(g.get_exp(truth)-53)/truth))
    return rows


def agreement(low, high):
    if len(low) != len(high):
        return False
    with g.context(precision=1024):
        return all(l['x'] == h['x'] and l['left'] == h['left'] and l['right'] == h['right']
                   for l,h in zip(low,high)) and all(a == b if not b else abs(a-b)/abs(b) <= g.mpfr('1e-10')
                   for l, h in zip(low, high)
                   for a, b in zip(l['errors'], h['errors']) if b is not None)


def generate(summary, include, figures, tables):
    winner, grid, degree, nodes, header = load_model(summary, include)
    end = g.mpq(grid.domain_end)
    uniform = [i*end/(len(nodes)-1) for i in range(len(nodes))]
    grids = {'nonuniform': nodes, 'uniform': uniform}
    results, precisions = {}, {}
    for name, centers in grids.items():
        low = calculate(centers, end, degree, 256)
        for precision in (512, 1024):
            high = calculate(centers, end, degree, precision)
            if agreement(low, high):
                results[name], precisions[name] = high, precision
                break
            low = high
        else:
            raise ArithmeticError('Precision comparison failed: '+name)
        print(name, 'verified at', precision, 'bits;', len(high), 'boundaries', flush=True)
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    records = []
    for name, rows in results.items():
        for i, row in enumerate(rows):
            record = dict(grid=name, boundary=i, x_exact=str(row['x']), x=float(row['x']))
            for side, index, error, bound in zip(('left','right'), (row['left'],row['right']), row['errors'], row['bounds']):
                record[side+'_reference_exact'] = '' if index is None else str(grids[name][index])
                record[side+'_relative_remainder'] = '' if error is None else format(error,'.40g')
                record[side+'_relative_bound'] = '' if bound is None else format(bound,'.40g')
            record['maximum_relative_remainder'] = format(row['maximum'],'.40g')
            record['relative_one_ulp'] = format(row['relative_one_ulp'],'.40g')
            records.append(record)
    csv_path = tables / 'nonuniform-grid-remainder.csv'
    with csv_path.open('w') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    binades = [g.mpq(2)**e-g.mpq(grid.offset) for e in range(-1074,1024)
               if 0 < g.mpq(2)**e-g.mpq(grid.offset) < end]
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7,4))
    for name, label, color, marker in [('uniform','Uniform grid','#E69F00','.'),('nonuniform','Nonuniform grid','#0072B2','.')]:
        rows = [r for r in results[name] if r['maximum'] > 0]
        ax.plot([float(r['x']) for r in rows],[float(r['maximum']) for r in rows],
                linestyle='none',marker=marker,markersize=2,color=color,label=label)
    rows = results['uniform']
    ax.plot([float(r['x']) for r in rows], [float(r['relative_one_ulp']) for r in rows],
            color='0.78', linewidth=1, label='1 ULP (relative)', zorder=1)
    for i,boundary in enumerate(binades):
        ax.axvline(float(boundary),color='0.65',linestyle='--',linewidth=.8,zorder=0,
                   label='Spacing doubles' if i == 0 else None)
    ax.set(xlabel=r'Argument $x$',ylabel=r'Relative Taylor remainder $|R_{0,p_0}|/F_0(x)$',
           yscale='log',xlim=(0,float(end)),title=f'{len(nodes):,} reference points per grid; Taylor degree {degree}')
    ax.legend(frameon=False,fontsize=9)
    ax.grid(axis='y',alpha=.15)
    fig.tight_layout()
    fig.savefig(figures/'nonuniform-grid-remainder.pdf')
    plt.close(fig)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    metadata = dict(model='[0,0]',degree=degree,reference_count=len(nodes),grid=winner['grid'],
        main_table_bytes=winner['storage']['table_bytes'],tail_included=False,
        uniform_grid='r_i = i*C/(reference_count-1), exact rational coordinates',
        boundaries='Exact adjacent-center midpoints plus domain endpoints; maximum of both neighboring polynomials',
        one_ulp_reference='2**(floor(log2(F0(x)))-52)/F0(x), evaluated at uniform-grid boundaries',
        excluded='Stored-coefficient rounding, low-part encoding, evaluator arithmetic and runtime-index rounding',
        precisions=precisions,agreement_relative_tolerance='1e-10',
        gmpy2=g.version(),mpfr=g.mpfr_version(),
        binade_boundaries=[str(x) for x in binades],
        maxima={name:format(max(r['maximum'] for r in rows),'.30g') for name,rows in results.items()},
        sources={str(p):sha(p) for p in (summary,header,Path('workflow/scripts/plot_grid_remainders.py'),Path('workflow/additive/model.py'))},
        data_sha256=sha(csv_path))
    (tables/'nonuniform-grid-remainder.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,default=Path('data/numerical/paired-1ulp/summary.json'))
    parser.add_argument('--include',type=Path,default=Path('include'))
    parser.add_argument('--figures',type=Path,default=Path('overleaf-paper2/figure'))
    parser.add_argument('--tables',type=Path,default=Path('overleaf-paper2/tables'))
    args = parser.parse_args()
    generate(args.summary,args.include,args.figures,args.tables)

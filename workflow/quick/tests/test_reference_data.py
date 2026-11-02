"""Retained reference utilities run without the old orchestration tree."""
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

import gmpy2 as g
import pytest

from workflow.additive.reference import bits64, rounded_bits
from workflow.scripts import quick_reference_data as ref

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('module', [False, True])
def test_reference_cli_help_and_missing_requests(tmp_path, module):
    command = ([sys.executable, '-m', 'workflow.scripts.quick_reference_data'] if module else
               [sys.executable, str(ROOT/'workflow/scripts/quick_reference_data.py')])
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    cwd = ROOT if module else tmp_path
    result = subprocess.run(command+['--help'], cwd=cwd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '{generate,fixtures,resolve}' in result.stdout
    result = subprocess.run(command+['resolve', str(tmp_path/'overrides.bin')],
                            cwd=cwd, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert 'resolve requires --requests' in result.stderr
    assert not (tmp_path/'overrides.bin').exists()


def test_correct_reference_specials_and_normal():
    for n in range(ref.MAX_ORDER+1):
        for x in (0., -0.):
            assert ref.correct(n, x)[0] == rounded_bits(g.mpq(1, 2*n+1))
        assert ref.correct(n, math.inf) == (0, 0)
    # Independent high-precision erf expression for F0(1).
    with g.context(precision=512):
        expected = rounded_bits(g.sqrt(g.const_pi())*g.erf(g.mpfr(1))/2)
    assert ref.correct(0, 1.)[0] == expected
    assert ref.correct(12, float.fromhex('0x1.fffffffffffffp+1023'))[0] == 0
    for n,x in ((-1,0.), (13,math.inf), (0,-1.), (0,math.nan), (0,-math.inf)):
        with pytest.raises(ValueError):
            ref.correct(n,x)


def test_resolve_cli(tmp_path):
    request = tmp_path/'requests.bin'
    output = tmp_path/'overrides.bin'
    pairs = [(bits64(0.), 0), (bits64(0.), 1), (bits64(math.inf), 12)]
    request.write_bytes(b''.join(struct.pack('<QQ', *p) for p in pairs+pairs))
    result = subprocess.run([sys.executable, '-m', 'workflow.scripts.quick_reference_data',
                             'resolve', str(output), '--requests', str(request)],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)['resolved_total'] == 3
    rows = list(struct.iter_unpack('<QQQ', output.read_bytes()))
    assert rows == [(pairs[0][0],0,bits64(1.)),
                    (pairs[1][0],1,rounded_bits(g.mpq(1,3))), (pairs[2][0],12,0)]
    saved = output.read_bytes()
    with pytest.raises(RuntimeError, match='no progress'):
        ref.resolve(request,output)
    assert output.read_bytes() == saved


def test_binary128_table_generation(tmp_path):
    path = tmp_path/'table.bin'
    record = ref.generate(path)
    raw = path.read_bytes()
    assert record['bytes'] == len(raw) == 304112
    assert json.loads(path.with_suffix('.json').read_text()) == record
    # At x=0 every Boys coefficient is exactly 1/(2n+1).
    for n in range(ref.COLUMNS):
        assert int.from_bytes(raw[16*n:16*(n+1)], 'little') == ref.quad_bits(g.mpq(1,2*n+1))
    # Check the far endpoint independently, not via the table's downward chain.
    for n in (0, 12, 36):
        lo, hi, _ = ref.enclosure(n, 128., 512, 4096)
        offset = 16*((ref.ROWS-1)*ref.COLUMNS+n)
        assert raw[offset:offset+16] == ref.agreed_quad(lo,hi)

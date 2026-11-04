import json
import math
from pathlib import Path
import struct
from fractions import Fraction

from workflow.additive.materialized_tail import bits,value,expand,coefficient_slot,correction_slot,generate

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/'data/numerical/compact-tail-1ulp.json'


def test_all_frozen_rows_and_codes():
    record=json.loads(ARCHIVE.read_text()); rows=expand(record); m=record['metadata']
    old=[int(w,16) for w in record['words']]; top=m['last']+m['degree']
    assert len(rows)==129 and len(rows[0])==328
    for i,packed in enumerate(rows):
        new=struct.unpack('<41Q',packed); prior=old[i*9:(i+1)*9]
        r=value(((1023<<m['retained_bits'])+i)<<(52-m['retained_bits']))
        g=prior[0]; assert new[coefficient_slot(top,m['last'])]==g
        for n in range(top-1,-1,-1):
            j=top-1-n; code=(prior[1+j//8]>>(8*(j%8)))&255
            patch=code if code<128 else code-256
            # Independent exact-rational oracle for each RN64 multiplication.
            product=float(Fraction(2*r)*Fraction(value(g)))
            raw=float(Fraction(product)*Fraction(float(Fraction(1,2*n+1))))
            g=bits(raw)+patch
            assert new[coefficient_slot(n,m['last'])]==g
        for n in range(m['last']+1):
            j=top+n
            assert (new[correction_slot(n)]>>(8*(n%8)))&255 == (prior[1+j//8]>>(8*(j%8)))&255


def test_generated_overlay_is_separate(tmp_path):
    result=generate(ROOT/'include',tmp_path,ARCHIVE)
    assert result['id']!=result['original_tail']
    text=(tmp_path/f'fast_boys/models/{result["id"]}/model.h').read_text()
    assert 'raw35' not in text
    assert 'table_bytes=42312' in text and ')*41;' in text
    simd=(tmp_path/f'fast_boys/models/{result["id"]}/simd-inl.h').read_text()
    assert 'patch35' not in simd
    assert 'First==0 || 12==12' in simd
    assert 'correction_from_word<0>(hi,row[0])' in text

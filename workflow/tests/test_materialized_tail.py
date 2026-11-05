import json
import math
from pathlib import Path
import struct
from fractions import Fraction
import pytest

from workflow.additive.materialized_tail import bits,value,expand,coefficient_slot,correction_slot,generate

ROOT=Path(__file__).resolve().parents[2]
from workflow.additive.tests.legacy_tail_fixture import record as legacy_tail_record


@pytest.fixture
def archive(tmp_path,monkeypatch):
    import workflow.additive.headers as headers
    path=tmp_path/'legacy-test-fixture.json'
    path.write_text(json.dumps(legacy_tail_record()))
    monkeypatch.setattr(headers,'TAIL',path)
    return path


def test_all_frozen_rows_and_codes():
    record=legacy_tail_record(); rows=expand(record); m=record['metadata']
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


def test_generated_overlay_is_separate(tmp_path,archive):
    from workflow.additive.headers import generate as generate_legacy
    from workflow.additive.model import Grid,storage
    from workflow.additive.search import payload_rows
    import hashlib
    grid=Grid(3,domain_end=1e7,offset_code=0)
    r=dict(first=0,last=0,degrees=[2],grid=grid.metadata(),status='qualified',minimum_order_prebiased=True,
           qualification=[dict(status='qualified',scope='fixture only')])
    r['storage']=storage(grid,0,r['degrees'])
    r['payload_sha256']=hashlib.sha256(b''.join(payload_rows(r))).hexdigest()
    base=tmp_path/'legacy'
    generate_legacy(dict(complete=True,identity='fixture',config=dict(error=dict(metric='ulp',limit=1)),winners={'0-0':r}),base)
    # The overlay only needs a catalog to substitute; it is not a live selection.
    (base/'fast_boys/selected_simd.h').write_text((base/'fast_boys/selected.h').read_text())
    result=generate(base,tmp_path,archive)
    assert result['id']!=result['original_tail']
    text=(tmp_path/f'fast_boys/models/{result["id"]}/model.h').read_text()
    assert 'raw35' not in text
    assert 'table_bytes=42312' in text and ')*41;' in text
    simd=(tmp_path/f'fast_boys/models/{result["id"]}/simd-inl.h').read_text()
    assert 'patch35' not in simd
    assert 'First==0 || 12==12' in simd
    assert 'correction_from_word<0>(hi,row[0])' in text

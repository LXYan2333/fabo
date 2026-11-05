"""Small legacy-decoder regression fixture, synthesized rather than archived.

This is not a production selection or a search result. It keeps the old decoder
tests independent of the removed shared-tail production metadata.
"""
from functools import lru_cache
import hashlib
import struct

import gmpy2 as g

from workflow.additive.tail import coefficients, node
from workflow.additive.reference import bits64, rn64, mul64, fma64


@lru_cache(maxsize=1)
def record():
    rows=[]
    for i in range(129):
        u=node(i,6)
        hi,low=coefficients(u,36,0,24)
        patches=[]
        for n in range(35,-1,-1):
            v=mul64(fma64(2*u,hi[n+1],0.),rn64(g.mpq(1,2*n+1)))
            delta=bits64(hi[n])-bits64(v)
            assert -128<=delta<=127
            patches.append(delta & 255)
        raw=struct.pack('<Q',bits64(hi[36]))+bytes(patches)+bytes(low[:25])
        rows.append(raw+bytes(72-len(raw)))
    raw=b''.join(rows)
    return dict(archive_commit='synthetic-test-fixture',metadata=dict(
        first=0,last=24,degree=12,retained_bits=6,minimum_x=1e7,
        definition_id='synthetic-test-fixture',accuracy_target=dict(metric='ulp',limit=1),
        qualification=dict(scope='fixture only; not production qualification'),
        storage=dict(row_count=129,row_words=9,allocated_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())),
        words=[f'{v:016x}' for v in struct.unpack('<'+'Q'*(len(raw)//8),raw)])

"""Diagnostic overlay: materialize the frozen compact tail, without a search."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from .headers import tail_source, write_model
from .simd_headers import wrap


def bits(x):
    return struct.unpack('<Q', struct.pack('<d', x))[0]


def value(x):
    return struct.unpack('<d', struct.pack('<Q', x))[0]


def coefficient_slot(n, last):
    return n + 1 + min(n // 8, last // 8)


def correction_slot(n):
    return 9 * (n // 8)


def expand(record):
    m = record['metadata']; first, last, degree = (m[k] for k in ('first', 'last', 'degree'))
    if first != 0:
        raise ValueError('diagnostic expects the shared zero-based tail')
    top = last + degree; old_stride = m['storage']['row_words']
    words = [int(w, 16) for w in record['words']]
    raw = b''.join(w.to_bytes(8, 'little') for w in words)
    if hashlib.sha256(raw).hexdigest() != m['storage']['sha256']:
        raise ValueError('compact payload hash mismatch')
    rows = []
    for i in range(m['storage']['row_count']):
        old = words[i*old_stride:(i+1)*old_stride]
        r = value(((1023 << m['retained_bits']) + i) << (52-m['retained_bits']))
        gs = [0] * (top+1); gs[top] = old[0]
        for n in range(top-1, -1, -1):
            j = top-1-n
            patch = (old[1+j//8] >> (8*(j%8))) & 255
            if patch >= 128: patch -= 256
            # Same separately rounded operations as the frozen runtime DAG.
            raw_value = math.fma(r+r, value(gs[n+1]), 0.0) * (1.0/(2*n+1))
            gs[n] = bits(raw_value) + patch
        new = [0] * (top+1+(last+8)//8)
        for n, g in enumerate(gs): new[coefficient_slot(n,last)] = g
        for n in range(last+1):
            j = top+n
            code = (old[1+j//8] >> (8*(j%8))) & 255
            new[correction_slot(n)] |= code << (8*(n%8))
        rows.append(struct.pack('<'+'Q'*len(new), *new))
    return rows


def cuda_source(record, ident, stride):
    m=record['metadata']; last=m['last']; top=last+m['degree']
    source=tail_source(record,ident)
    source=source.replace(f'table_bytes={m["storage"]["allocated_bytes"]}',f'table_bytes={len(record["words"])//m["storage"]["row_words"]*stride*8}')
    source=source.replace(f')*{m["storage"]["row_words"]};',f')*{stride};')
    start=source.index(f'    const double g{top}=')
    end=source.index('    const double a2=',start)
    source=source[:start]+''.join(f'    double g{n} FAST_BOYS_INDETERMINATE;\n' for n in range(top+1))+source[end:]
    for n in range(last+1):
        marker=f'    if constexpr(First<={n} && {n}<=Limit) {{\n'
        loads=''
        for j in range(n,n+m['degree']+1):
            loads+=f'      if constexpr(First=={n} || {j}=={n+m["degree"]}) g{j}=O::value(row[{coefficient_slot(j,last)}]);\n'
        source=source.replace(marker,marker+loads)
        j=top+n
        source=source.replace(f'correction_from_word<{j%8}>(hi,row[{1+j//8}])',
                              f'correction_from_word<{n%8}>(hi,row[{correction_slot(n)}])')
    return source


def simd_source(record, ident, stride):
    m=record['metadata']; last=m['last']; p=m['degree']; top=last+p; shift=52-m['retained_bits']
    body=[
        ' const auto bits=Bits(x);',
        ' const auto exponent=hn::Sub(hn::ShiftRight<52>(bits),SU(1023));',
        ' const auto k=hn::ShiftRight<1>(exponent);',
        ' const auto u=Float(hn::Or(hn::And(bits,SU(0xfffffffffffffULL)),hn::ShiftLeft<52>(hn::Add(SU(1023),hn::And(exponent,SU(1))))));',
        f' const auto key=hn::ShiftRight<{shift}>(hn::Add(Bits(u),SU(1ULL<<{shift-1})));',
        f' const auto row=MultiplyConstant<{stride},{m["storage"]["row_count"]-1}>(hn::Sub(key,SU({1023<<m["retained_bits"]})));',
        f' const auto r=Float(hn::ShiftLeft<{shift}>(key)),h=RoundedSub(r,u);']
    body += [f' V g{n} FAST_BOYS_INDETERMINATE;' for n in range(top+1)]
    body += [f' U w{i} FAST_BOYS_INDETERMINATE;' for i in range((last+8)//8)]
    body += [f' const auto a{j}=RoundedMul(h,S({float(1/j).hex()}));' for j in range(2,p+1)]
    for n in range(last+1):
        body += [f' if constexpr(First<={n} && {n}<=Last) {{']
        for j in range(n,n+p+1):
            body += [f' if constexpr(First=={n} || {j}=={n+p}) g{j}=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU({coefficient_slot(j,last)}))));']
        body += [f' if constexpr(First=={n} || {n%8}==0) w{n//8}=Gather<Software,M::word_count-1>(data,hn::Add(row,SU({correction_slot(n)})));',f' V q=g{n+p};']
        body += [f' q=Fma(a{j+1},q,g{n+j});' for j in range(p-1,0,-1)]
        body += [f' const auto hi=Bits(g{n});',
                 f' const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<{n%8}>(hi,w{n//8})));',
                 f' At<{n}-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<{2*n+1},511>(k)),At<{n}-First>(out...));',' }']
    return wrap(ident,f'fast_boys::models::m_{ident}::Model','TailKernel',body)


def generate(base, output, archive):
    base,output,archive=map(Path,(base,output,archive))
    record=json.loads(archive.read_text()); rows=expand(record); stride=len(rows[0])//8
    ident=hashlib.sha256(archive.read_bytes()+Path(__file__).read_bytes()+b'materialized-tail-interleaved8').hexdigest()
    old=json.loads((base/'manifest.json').read_text()); old_id=old['tail']['id']; old_catalog=old['catalog']['id']
    new_catalog=hashlib.sha256((old_catalog+ident).encode()).hexdigest()
    count,payload_sha=write_model(output,ident,cuda_source(record,ident,stride),rows,None)
    directory=output/'fast_boys/models'/ident
    (directory/'simd-inl.h').write_text(simd_source(record,ident,stride))
    catalog=(base/f'fast_boys/models/catalog_{old_catalog}.h').read_text().replace(old_id,ident).replace(old_catalog,new_catalog)
    (output/f'fast_boys/models/catalog_{new_catalog}.h').write_text(catalog)
    (output/'fast_boys/selected.h').write_text((base/'fast_boys/selected.h').read_text().replace(old_catalog,new_catalog))
    (output/'fast_boys/selected_simd.h').write_text((base/'fast_boys/selected_simd.h').read_text().replace(old_id,ident))
    (output/'fast_boys/models/tail_data.h').write_text(f'#pragma once\n#include "fast_boys/models/{ident}/data.h"\n')
    result=dict(kind='fully-materialized-tail-diagnostic',id=ident,original_tail=old_id,catalog=new_catalog,
                row_count=len(rows),row_words=stride,table_bytes=count,original_bytes=record['metadata']['storage']['allocated_bytes'],
                payload_sha256=payload_sha,source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                policy='Frozen grid, coefficients reconstructed offline with original RN64 DAG; unchanged output correction, Horner and scaling. No numerical search.')
    (output/'materialized-tail.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=Path('include'))
    parser.add_argument('--archive',type=Path,default=Path('data/numerical/compact-tail-1ulp.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(generate(args.base,args.output,args.archive),indent=2))

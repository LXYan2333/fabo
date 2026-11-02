"""Emit Highway companions from frozen metadata; never regenerate payloads."""
import argparse
import hashlib
import json
from pathlib import Path

from .headers import coefficient_word, correction_word


def wrap(ident,model,kind,body):
    guard='FAST_BOYS_SIMD_'+ident.upper()+'_H_'
    return '\n'.join([
        f'#if defined({guard}) == defined(HWY_TARGET_TOGGLE)',
        f'#ifdef {guard}',f'#undef {guard}','#else',f'#define {guard}','#endif',
        '#include "fast_boys/simd.h"',f'#include "fast_boys/models/{ident}/model.h"',
        'HWY_BEFORE_NAMESPACE();','namespace fast_boys { namespace simd { namespace HWY_NAMESPACE {',
        f'template<> struct {kind}<{model}> {{',f' using M={model};',
        ' template<int First,int Last,bool Software,class... Outputs>',
        ' static HWY_INLINE void run(const std::uint64_t* data,const V x,'+
        ('Mask active,' if kind=='TailKernel' else '')+'Outputs& HWY_RESTRICT ...out) {',
        ' using namespace detail;',*body,' }','};','} } }','HWY_AFTER_NAMESPACE();','#endif',''])


def main_kernel(entry):
    r=entry['record']; first,last=r['first'],r['last']; degrees=r['degrees']
    body=[
        ' const auto y=RoundedAdd(x,S(M::offset));',
        ' const auto key=hn::ShiftRight<M::discarded_bits>(hn::Add(Bits(y),SU(1ULL<<(M::discarded_bits-1))));',
        ' const auto ref=RoundedSub(Float(hn::ShiftLeft<M::discarded_bits>(key)),S(M::offset));',
        ' const auto h=RoundedSub(ref,x);',
        ' const auto row=MultiplyConstant<M::row_words,M::row_count-1>(hn::Sub(key,SU(M::key_min)));',
        ' static_assert(M::word_count-1<=INT64_MAX,"gather index exceeds signed range");']
    high=max(n+p for n,p in zip(range(first,last+1),degrees))
    body += [f' V c{n} FAST_BOYS_INDETERMINATE;' for n in range(first,high+1)]
    body += [f' V a{j} FAST_BOYS_INDETERMINATE;' for j in range(2,max(degrees)+1)]
    body += [f' U w{k} FAST_BOYS_INDETERMINATE;' for k in range((last-first+8)//8)]
    for n in range(first,last+1):
        p=degrees[n-first]; slot=(n-first)//8
        body += [f' if constexpr(First<={n} && {n}<=Last) {{']
        for j in range(n,n+p+1):
            off=coefficient_word(r,j)
            load=f'Gather<Software,M::word_count-1>(data,hn::Add(row,SU({off})))'
            if j==first: load=f'hn::Sub({load},SU(1))'
            body += [f' if constexpr({j}>M::high_before(First,{n})) c{j}=Float({load});']
        body += [f' if constexpr(First=={n} || {n}=={first+8*slot}) w{slot}=Gather<Software,M::word_count-1>(data,hn::Add(row,SU({correction_word(r,n)})));']
        for j in range(2,p+1):
            body += [f' if constexpr({j}>M::degree_before(First,{n})) a{j}=RoundedMul(h,S({float(1/j).hex()}));']
        body += [f' V q=c{n+p};']
        for j in range(p-1,0,-1):
            body += [f' q=Fma(a{j+1},q,c{n+j});']
        body += [f' const auto hi=Bits(c{n});',
                 f' At<{n}-First>(out...)=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<{(n-first)%8}>(hi,w{slot})));',' }']
    return wrap(entry['id'],entry['cpp_model'],'Kernel',body)


def tail_kernel(entry,metadata):
    first,last,p,b=(metadata[k] for k in ('first','last','degree','retained_bits'))
    top=last+p; stride=metadata['storage']['row_words']; shift=52-b
    body=[
        ' const auto bits=Bits(x);',
        ' const auto exponent=hn::Sub(hn::ShiftRight<52>(bits),SU(1023));',
        ' const auto k=hn::ShiftRight<1>(exponent);',
        ' const auto u=Float(hn::Or(hn::And(bits,SU(0xfffffffffffffULL)),hn::ShiftLeft<52>(hn::Add(SU(1023),hn::And(exponent,SU(1))))));',
        f' const auto key=hn::ShiftRight<{shift}>(hn::Add(Bits(u),SU(1ULL<<{shift-1})));',
        f' const auto row=MultiplyConstant<{stride},{metadata["storage"]["allocated_bytes"]//(8*stride)-1}>(hn::Sub(key,SU({1023<<b})));',
        f' const auto r=Float(hn::ShiftLeft<{shift}>(key)),h=RoundedSub(r,u),t=RoundedAdd(r,r);']
    for i in range(stride):
        body += [f' const auto w{i}=Gather<Software,M::word_count-1>(data,hn::Add(row,SU({i})));']
    body += [f' const auto g{top}=Float(w0);']
    for n in range(top-1,first-1,-1):
        i=top-1-n
        body += [f' const auto byte{n}=ByteAt<{i%8}>(w{1+i//8});',
                 f' const auto patch{n}=hn::Sub(hn::Xor(byte{n},SU(128)),SU(128));',
                 # Both operands are positive normal tail-reference values:
                 # FMA(t,g,0) equals rounded multiplication. Fence that product
                 # before reciprocal scaling, including under fast-math.
                 f' const auto g{n}=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g{n+1}),S({float(1/(2*n+1)).hex()}))),patch{n}));']
    body += [f' const auto a{j}=RoundedMul(h,S({float(1/j).hex()}));' for j in range(2,p+1)]
    for n in range(first,last+1):
        i=top-first+n-first
        body += [f' if constexpr(First<={n} && {n}<=Last) {{',f' V q=g{n+p};']
        body += [f' q=Fma(a{j+1},q,g{n+j});' for j in range(p-1,0,-1)]
        body += [f' const auto hi=Bits(g{n});',
                 f' const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<{i%8}>(hi,w{1+i//8})));',
                 f' At<{n}-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<{2*n+1},511>(k)),At<{n}-First>(out...));',' }']
    return wrap(entry['id'],entry['cpp_model'],'TailKernel',body)


def generate(include):
    include=Path(include)
    manifest=json.loads((include/'manifest.json').read_text())
    archive=Path(__file__).resolve().parents[2]/'data/numerical/compact-tail-1ulp.json'
    tail=json.loads(archive.read_text())
    if manifest['tail']['archive_definition']!=tail['metadata']['definition_id']:
        raise ValueError('tail metadata differs from emitted table')
    files={}
    for entry in manifest['models'].values():
        if entry['payload_layout'] != 'materialized-nextup-interleaved8-v2':
            raise ValueError('unsupported SIMD payload layout')
        if not entry['record']['minimum_order_prebiased']:
            raise ValueError('SIMD requires the next-up minimum-order coefficient')
        if min(entry['record']['degrees']) < 1:
            raise ValueError('SIMD requires positive Taylor degrees')
        files[f'fast_boys/models/{entry["id"]}/simd-inl.h']=main_kernel(entry)
    entry=manifest['tail']
    files[f'fast_boys/models/{entry["id"]}/simd-inl.h']=tail_kernel(entry,tail['metadata'])
    guard='FAST_BOYS_SELECTED_SIMD_H_'
    files['fast_boys/selected_simd.h']='\n'.join([
        f'#if defined({guard}) == defined(HWY_TARGET_TOGGLE)',f'#ifdef {guard}',
        f'#undef {guard}','#else',f'#define {guard}','#endif',
        '#include "fast_boys/simd.h"','#include "fast_boys/selected.h"',
        *[f'#include "{name}"' for name in files],'#endif',''])
    for name,text in files.items():
        path=include/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
    hashes={name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()}
    root=Path(__file__).resolve().parents[2]
    sources=['workflow/additive/simd_headers.py','include/fast_boys/simd.h',
             'include/fast_boys/simd_config.h','include/fast_boys/detail/simd/ops-inl.h']
    source_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}
    (include/'simd-manifest.json').write_text(json.dumps(dict(
        numerical_identity=manifest['numerical_identity'],
        numerical_manifest_sha256=hashlib.sha256((include/'manifest.json').read_bytes()).hexdigest(),
        sources=source_hashes,files=hashes),indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include',type=Path,default=Path('include'))
    generate(parser.parse_args().include)

"""Emit Highway companions from frozen metadata; never regenerate payloads."""
import argparse
import hashlib
import json
from pathlib import Path

from .headers import coefficient_word, correction_word


def scale_power_setup(first):
    # Advance outside the output guards so nonzero-start subsets retain the
    # absolute-order scale. All additions are exact unsigned integer arithmetic.
    return [' const auto two_k=hn::Add(k,k);', ' auto scale_power=k;'] + [
        ' scale_power=hn::Add(scale_power,two_k);' for _ in range(first)]


def scale_power_next(n):
    return f' if constexpr({n}<Last) scale_power=hn::Add(scale_power,two_k);'


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


def main_kernel(entry,combined=False):
    r=entry['record']; first,last=r['first'],r['last']; degrees=r['degrees']
    body=[
        ' const auto y=RoundedAdd(x,S(M::offset));',
        ' const auto key=hn::ShiftRight<M::discarded_bits>(hn::Add(Bits(y),SU(1ULL<<(M::discarded_bits-1))));',
        ' const auto ref=RoundedSub(Float(hn::ShiftLeft<M::discarded_bits>(key)),S(M::offset));',
        ' const auto h=RoundedSub(ref,x);',
        ' const auto row=MultiplyConstant<M::row_words,M::row_count-1>(hn::Sub(key,SU(M::key_min)));',
        ' static_assert(M::word_count-1<=INT64_MAX,"gather index exceeds signed range");']
    if combined:
        body=[' U row FAST_BOYS_INDETERMINATE;', ' U k FAST_BOYS_INDETERMINATE;',
              ' V h FAST_BOYS_INDETERMINATE;', ' PrepareCombinedCoordinates<M>(x,row,h,k);',
              ' static_assert(M::word_count-1<=INT64_MAX,"gather index exceeds signed range");']
        body += scale_power_setup(first)
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
        expr=f'RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<{(n-first)%8}>(hi,w{slot})))'
        body += [f' const auto hi=Bits(c{n});']
        if combined:
            body += [f' const auto value={expr};',f' At<{n}-First>(out...)=Scale(Bits(value),scale_power);']
        else:
            body += [f' At<{n}-First>(out...)={expr};']
        body += [' }']
        if combined:
            body += [scale_power_next(n)]
    return wrap(entry['id'],entry['cpp_model'],'Kernel',body)


def tail_kernel(entry,metadata):
    first,last,p,b=(metadata[k] for k in ('first','last','degree','retained_bits'))
    top=last+p; stride=metadata['storage']['row_words']; shift=52-b
    body=[
        ' const auto bits=Bits(x);',
        ' const auto x_biased_exponent=hn::ShiftRight<52>(bits);',
        ' const auto x_unbiased_exponent=hn::Sub(x_biased_exponent,SU(1023));',
        ' const auto k=hn::ShiftRight<1>(x_unbiased_exponent);',
        ' const auto u_biased_exponent=hn::Add(SU(1023),hn::And(x_unbiased_exponent,SU(1)));',
        ' const auto u=Float(hn::OrAnd(hn::ShiftLeft<52>(u_biased_exponent),bits,SU(0xfffffffffffffULL)));',
        f' const auto key=hn::ShiftRight<{shift}>(hn::Add(Bits(u),SU(1ULL<<{shift-1})));',
        f' const auto row=MultiplyConstant<{stride},{metadata["storage"]["allocated_bytes"]//(8*stride)-1}>(hn::Sub(key,SU({1023<<b})));',
        f' const auto r=Float(hn::ShiftLeft<{shift}>(key)),h=RoundedSub(r,u),t=RoundedAdd(r,r);']
    body += scale_power_setup(first)
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
                 f' At<{n}-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),scale_power),At<{n}-First>(out...));',' }',scale_power_next(n)]
    return wrap(entry['id'],entry['cpp_model'],'TailKernel',body)


def paired_tail_kernel(entry,main):
    # Reuse the materialized main polynomial emitter, replacing coordinates
    # and the final store. The two SIMD paths remain separate for now.
    source=main_kernel(dict(main,id=entry['id'],cpp_model=entry['cpp_model']))
    source=source.replace('struct Kernel<','struct TailKernel<').replace('const V x,Outputs&','const V x,Mask active,Outputs&')
    start=source.index(' const auto y='); end=source.index(' static_assert',start)
    source=source[:start]+''' const auto bits=Bits(x);
 const auto x_biased_exponent=hn::ShiftRight<52>(bits);
 const auto x_unbiased_exponent=hn::Sub(x_biased_exponent,SU(1023));
 const auto k=hn::ShiftRight<1>(x_unbiased_exponent);
 const auto u_biased_exponent=hn::Add(SU(1023),hn::And(x_unbiased_exponent,SU(1)));
 const auto u=Float(hn::OrAnd(hn::ShiftLeft<52>(u_biased_exponent),bits,SU(0xfffffffffffffULL)));
 const auto key=hn::ShiftRight<M::discarded_bits>(hn::Add(Bits(u),SU(1ULL<<(M::discarded_bits-1))));
 const auto h=RoundedSub(Float(hn::ShiftLeft<M::discarded_bits>(key)),u);
 const auto row=MultiplyConstant<M::row_words,M::row_count-1>(hn::Sub(key,SU(1023ULL<<M::retained_bits)));
'''+source[end:]
    r=main['record']
    source=source.replace(' static_assert', '\n'.join(scale_power_setup(r['first']))+'\n static_assert',1)
    for n in range(r['first'],r['last']+1):
        prefix=f' At<{n}-First>(out...)='
        start=source.index(prefix); end=source.index(';',start)
        expr=source[start+len(prefix):end]
        source=source[:start]+f' const auto value={expr};\n'+prefix+f'hn::IfThenElse(active,Scale(Bits(value),scale_power),At<{n}-First>(out...))'+source[end:]
        end=source.index('\n }',start)+len('\n }')
        source=source[:end]+'\n'+scale_power_next(n)+source[end:]
    return source


def generate(include):
    include=Path(include)
    manifest=json.loads((include/'manifest.json').read_text())
    combined=manifest.get('combined_table',False)
    archive=Path(__file__).resolve().parents[2]/'data/numerical/compact-tail-1ulp.json'
    tail=json.loads(archive.read_text()) if not combined and 'tails' not in manifest else None
    if not combined and 'tails' not in manifest and manifest['tail']['archive_definition']!=tail['metadata']['definition_id']:
        raise ValueError('tail metadata differs from emitted table')
    files={}
    for entry in manifest['models'].values():
        expected_layout='materialized-nextup-main-tail-v3' if combined else 'materialized-nextup-interleaved8-v2'
        if entry['payload_layout'] != expected_layout:
            raise ValueError('unsupported SIMD payload layout')
        if not entry['record']['minimum_order_prebiased']:
            raise ValueError('SIMD requires the next-up minimum-order coefficient')
        if min(entry['record']['degrees']) < 1:
            raise ValueError('SIMD requires positive Taylor degrees')
        files[f'fast_boys/models/{entry["id"]}/simd-inl.h']=main_kernel(entry,combined)
    if 'tails' in manifest:
        for key,entry in manifest['tails'].items():
            files[f'fast_boys/models/{entry["id"]}/simd-inl.h']=paired_tail_kernel(entry,manifest['models'][key])
    elif not combined:
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

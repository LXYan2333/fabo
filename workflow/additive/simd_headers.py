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


def wrap(ident,model,body):
    guard='FAST_BOYS_SIMD_'+ident.upper()+'_H_'
    return '\n'.join([
        f'#if defined({guard}) == defined(HWY_TARGET_TOGGLE)',
        f'#ifdef {guard}',f'#undef {guard}','#else',f'#define {guard}','#endif',
        '#include "fast_boys/simd.h"',f'#include "fast_boys/models/{ident}/model.h"',
        '#if HWY_NATIVE_FMA','HWY_BEFORE_NAMESPACE();','namespace fast_boys { namespace simd { namespace HWY_NAMESPACE {',
        f'template<> struct Kernel<{model}> {{',f' using M={model};',
        ' template<int First,int Last,bool Software,class D,class... Outputs>',
        ' static HWY_INLINE void run(D, const std::uint64_t* data,hn::VFromD<D> x,'+
        'Outputs& HWY_RESTRICT ...out) {',
        ' using Op=detail::Ops<D>; using V=hn::VFromD<D>;',
        *body,' }','};','} } }','HWY_AFTER_NAMESPACE();','#endif // HWY_NATIVE_FMA','#endif',''])


def main_kernel(entry):
    r=entry['record']; first,last=r['first'],r['last']; degrees=r['degrees']
    body=[' U row FAST_BOYS_INDETERMINATE;', ' U k FAST_BOYS_INDETERMINATE;',
              ' V h FAST_BOYS_INDETERMINATE;', ' Op::template PrepareCombinedCoordinates<M>(x,row,h,k);',
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
            load=f'Op::template Gather<Software,M::word_count-1>(data,hn::Add(row,Op::SU({off})))'
            if j==first: load=f'hn::Sub({load},Op::SU(1))'
            body += [f' if constexpr({j}>M::high_before(First,{n})) c{j}=Op::Float({load});']
        body += [f' if constexpr(First=={n} || {n}=={first+8*slot}) w{slot}=Op::template Gather<Software,M::word_count-1>(data,hn::Add(row,Op::SU({correction_word(r,n)})));']
        for j in range(2,p+1):
            body += [f' if constexpr({j}>M::degree_before(First,{n})) a{j}=Op::RoundedMul(h,Op::S({float(1/j).hex()}));']
        body += [f' V q=c{n+p};']
        for j in range(p-1,0,-1):
            body += [f' q=Op::Fma(a{j+1},q,c{n+j});']
        expr=f'Op::RoundedAdd(Op::Float(hn::Add(hi,Op::SU(1))),Op::FmaSub(h,q,Op::template CorrectionFromWord<{(n-first)%8}>(hi,w{slot})))'
        body += [f' const auto hi=Op::Bits(c{n});']
        body += [f' const auto value={expr};',f' Op::template At<{n}-First>(out...)=Op::Scale(Op::Bits(value),scale_power);']
        body += [' }']
        body += [scale_power_next(n)]
    return wrap(entry['id'],entry['cpp_model'],[' using U=typename Op::U;', *body])


def generate(include):
    include=Path(include)
    manifest=json.loads((include/'manifest.json').read_text())
    if manifest.get('combined_table') is not True:
        raise ValueError('combined-table catalog required; use the historical release for split tables')
    files={}
    for entry in manifest['models'].values():
        expected_layout='materialized-nextup-main-tail-v3'
        if entry['payload_layout'] != expected_layout:
            raise ValueError('unsupported SIMD payload layout')
        if not entry['record']['minimum_order_prebiased']:
            raise ValueError('SIMD requires the next-up minimum-order coefficient')
        if min(entry['record']['degrees']) < 1:
            raise ValueError('SIMD requires positive Taylor degrees')
        files[f'fast_boys/models/{entry["id"]}/simd-inl.h']=main_kernel(entry)
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
             'include/fast_boys/simd_config.h','include/fast_boys/detail/simd/ops-inl.h',
             'include/fast_boys/scalar.h','include/fast_boys/detail/binary64.h']
    source_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}
    (include/'simd-manifest.json').write_text(json.dumps(dict(
        numerical_identity=manifest['numerical_identity'],
        numerical_manifest_sha256=hashlib.sha256((include/'manifest.json').read_bytes()).hexdigest(),
        sources=source_hashes,files=hashes),indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include',type=Path,default=Path('include'))
    generate(parser.parse_args().include)

"""Emit portable model recipes/data and scalar-index CUDA evaluation stages.

Consumes frozen selections, never searches or changes their numerical identity.
Only payload regeneration uses MPFR. Device code contains no MPFR dependency.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import struct

import gmpy2 as g
from .model import from_metadata, storage
from .reference import rn64
from .search import payload_rows

ROOT = Path(__file__).resolve().parents[2]
TAIL = ROOT/'data/numerical/compact-tail-1ulp.json'
MAIN_LAYOUT = 'materialized-nextup-interleaved8-v2'


def coefficient_word(record, order):
    """One correction word precedes each block of up to eight output orders."""
    offset=order-record['first']
    code_words=(record['last']-record['first']+8)//8
    return offset+min(offset//8+1,code_words)


def correction_word(record, order):
    return 9*((order-record['first'])//8)


def interleaved_rows(record, rows):
    """Permute whole words; verify the frozen canonical bytes before publishing.

    Corrections beyond last are absent, so the remaining Taylor coefficients
    follow the final block without introducing extra words or padding.
    """
    count=record['storage']['highest_reference_order']-record['first']+1
    code_words=(record['last']-record['first']+8)//8
    checksum=hashlib.sha256(); row_count=0
    for row in rows:
        if len(row)!=record['storage']['row_bytes']:
            raise ValueError('canonical row size mismatch')
        checksum.update(row); row_count+=1
        words=[row[i:i+8] for i in range(0,len(row),8)]
        packed=[]
        for i in range(count):
            if i%8==0 and i//8<code_words:
                packed.append(words[count+i//8])
            packed.append(words[i])
        yield b''.join(packed)
    if row_count!=len(from_metadata(record['grid']).keys):
        raise ValueError('canonical row count mismatch')
    if checksum.hexdigest()!=record['payload_sha256']:
        raise ValueError('regenerated canonical payload differs from frozen SHA-256')


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def inv(n):
    return rn64(g.mpq(1,n)).hex()


def validate_record(record):
    first,last=record['first'],record['last']
    if type(first) is not int or type(last) is not int or not 0 <= first <= last:
        raise ValueError('invalid output range')
    degrees=record['degrees']
    if len(degrees)!=last-first+1 or any(type(p) is not int or not 1<=p<=64 for p in degrees):
        raise ValueError('invalid degrees')
    grid=from_metadata(record['grid'])
    if storage(grid,first,degrees)!=record['storage']:
        raise ValueError('storage does not match numerical recipe')
    if not record.get('minimum_order_prebiased') or record.get('status')!='qualified':
        raise ValueError('only qualified next-up/prebiased records can be emitted')
    if len(record['qualification'])!=len(degrees) or any(q['status']!='qualified' for q in record['qualification']):
        raise ValueError('missing order qualification')
    return grid


def main_source(record,ident,error,payload_sha256):
    grid=validate_record(record)
    first,last=record['first'],record['last']
    degrees=record['degrees']; high=record['storage']['highest_reference_order']
    lines=['#pragma once','#include "fast_boys/boys_types.h"',
           f'namespace fast_boys::models::m_{ident} {{','struct Model {',
           f'  static constexpr int first={first}, last={last}, highest_reference_order={high};',
           '  inline static constexpr int degrees[] = {'+','.join(map(str,degrees))+'};',
           f'  static constexpr unsigned retained_bits={grid.b}, discarded_bits={grid.shift};',
           f'  static constexpr double offset={grid.offset.hex()}, domain_end={grid.domain_end.hex()};',
           f'  static constexpr std::uint64_t key_min={grid.keys.start}ULL, key_max={grid.keys.stop-1}ULL;',
           f'  static constexpr std::size_t row_count={len(grid.keys)}, row_words={record["storage"]["row_bytes"]//8}, table_bytes={record["storage"]["table_bytes"]};',
           '  static constexpr std::size_t word_count=table_bytes/8;',
           f'  inline static constexpr char payload_layout[]="{MAIN_LAYOUT}";',
           f'  inline static constexpr char canonical_payload_sha256[]="{record["payload_sha256"]}";',
           f'  inline static constexpr char payload_sha256[]="{payload_sha256}";',
           f'  inline static constexpr char model_id[]="{ident}";',
           f'  static constexpr ErrorMetric error_metric=ErrorMetric::{error["metric"].capitalize()};',
           f'  static constexpr double error_limit={float(error["limit"]).hex()};',
           '  // Sampled qualification, not a continuous-domain error certificate.',
           '  FAST_BOYS_HD static constexpr int high_before(int begin,int end) {',
           '    int high=begin-1;',
           '    for(int n=begin;n<end;++n) if(n+degrees[n-first]>high) high=n+degrees[n-first];',
           '    return high;', '  }',
           '  FAST_BOYS_HD static constexpr int degree_before(int begin,int end) {',
           '    int degree=1;',
           '    for(int n=begin;n<end;++n) if(degrees[n-first]>degree) degree=degrees[n-first];',
           '    return degree;', '  }',
           '  template<class O,int First,int Limit>',
           '  FAST_BOYS_HD static FAST_BOYS_INLINE void evaluate(const std::uint64_t* FAST_BOYS_RESTRICT row,double h,int last_output,double* FAST_BOYS_RESTRICT out,std::size_t stride) {',
           '    static_assert(first<=First && First<=Limit && Limit<=last,"invalid subset");',
           '    // No dynamic coefficient array: every access below has a fixed index.',
           '    std::uint64_t minimum_up FAST_BOYS_INDETERMINATE;']
    lines += [f'    double c{j} FAST_BOYS_INDETERMINATE;' for j in range(first+1,high+1)]
    lines += [f'    double a{k} FAST_BOYS_INDETERMINATE;' for k in range(2,max(degrees)+1)]
    paired='tail' in record
    if paired:
        lines += [f'    std::uint64_t w{i} FAST_BOYS_INDETERMINATE;' for i in range((last-first+8)//8)]
    for n,p in zip(range(first,last+1),degrees):
        lines += [f'    if constexpr(First<={n} && {n}<=Limit) {{']
        for j in range(n,n+p+1):
            index=coefficient_word(record,j)
            load=f'minimum_up=row[{index}];' if j==first else f'c{j}=O::value(row[{index}]);'
            lines += [f'      if constexpr({j}>high_before(First,{n})) {load}']
        for k in range(2,p+1):
            lines += [f'      if constexpr({k}>degree_before(First,{n})) a{k}=O::mul(h,{inv(k)});']
        slot=(n-first)//8
        if paired:
            lines += [f'      if constexpr(First=={n} || {n}=={first+8*slot}) w{slot}=row[{correction_word(record,n)}];']
        lines += [f'      double q=c{n+p};']
        for k in range(p-1,0,-1):
            lines += [f'      q=O::fma(a{k+1},q,c{n+k});']
        hi='minimum_up-1' if n==first else f'O::bits(c{n})'
        up='minimum_up' if n==first else 'hi+1'
        offset=n-first
        correction=f'w{slot}' if paired else f'row[{correction_word(record,n)}]'
        lines += [f'      const auto hi={hi};',
                  f'      out[({n}-First)*stride]=O::add(O::value({up}),O::fma(h,q,-O::template correction_from_word<{offset%8}>(hi,{correction})));',
                  f'      if(last_output=={n}) return;', '    }']
    source='\n'.join(lines+['  }','};','}'])+'\n'
    if 'tail' in record:
        source=source.replace('std::size_t stride) {','std::size_t stride,unsigned scale_k=0) {')
        for n in range(first,last+1):
            prefix=f'      out[({n}-First)*stride]='
            start=source.index(prefix); end=source.index(';',start)
            expr=source[start+len(prefix):end]
            source=source[:start]+f'      const double result={expr};\n'+prefix+f'O::scale(result,unsigned({2*n+1}*scale_k))'+source[end:]
    return source


def tail_source(record,ident):
    m=record['metadata']; first,last,p,b=(m[k] for k in ('first','last','degree','retained_bits'))
    top=last+p; shift=52-b; stride=m['storage']['row_words']
    lines=['#pragma once','#include "fast_boys/boys_types.h"',
           f'namespace fast_boys::models::m_{ident} {{','struct Model {',
           f'  static constexpr int first={first},last={last},degree={p};',
           f'  static constexpr ErrorMetric error_metric=ErrorMetric::{m["accuracy_target"]["metric"].capitalize()};',
           f'  static constexpr double error_limit={float(m["accuracy_target"]["limit"]).hex()};',
           f'  static constexpr double minimum_x={float(m["minimum_x"]).hex()};',
           f'  static constexpr std::size_t table_bytes={m["storage"]["allocated_bytes"]},word_count=table_bytes/8;',
           '  template<class O,int First,int Limit>',
           '  FAST_BOYS_HD static inline void evaluate(const std::uint64_t* data,double u,int k,int last_output,double* out,std::size_t stride) {',
           f'    const auto key=(O::bits(u)+(1ULL<<{shift-1}))>>{shift};',
           f'    const auto* row=data+(key-{1023<<b}ULL)*{stride};',
           f'    const double r=O::value(key<<{shift}),h=O::sub(r,u),t=O::add(r,r);',
           f'    const double g{top}=O::value(row[0]);']
    for n in range(top-1,first-1,-1):
        i=top-1-n
        lines += [f'    const unsigned byte{n}=unsigned((row[{1+i//8}]>>{8*(i%8)}) & 255U);',
                  f'    const int patch{n}=int(byte{n})-int(byte{n} & 128U)*2;',
                  f'    const double raw{n}=O::mul(O::fma(t,g{n+1},0.0),{inv(2*n+1)});',
                  f'    const double g{n}=O::value(O::bits(raw{n})+std::uint64_t(patch{n}));']
    lines += [f'    const double a{j}=O::mul(h,{inv(j)});' for j in range(2,p+1)]
    for n in range(first,last+1):
        i=top-first+n-first
        lines += [f'    if constexpr(First<={n} && {n}<=Limit) {{', f'      double q=g{n+p};']
        lines += [f'      q=O::fma(a{j+1},q,g{n+j});' for j in range(p-1,0,-1)]
        lines += [f'      const auto hi=O::bits(g{n});',
                  f'      const double v=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<{i%8}>(hi,row[{1+i//8}])));',
                  f'      out[({n}-First)*stride]=O::scale(v,unsigned({2*n+1}*k));',
                  f'      if(last_output=={n}) return;', '    }']
    return '\n'.join(lines+['  }','};','}'])+'\n'


def write_model(root,ident,source,rows,expected):
    directory=root/'fast_boys/models'/ident
    directory.mkdir(parents=True,exist_ok=True)
    temporary=directory/'data.h.tmp'; sha=hashlib.sha256(); count=0
    try:
        with temporary.open('w') as stream:
            stream.write('#pragma once\n#include "model.h"\n#include "fast_boys/table.h"\nnamespace fast_boys {\n')
            stream.write(f'template<> struct BoysTable<models::m_{ident}::Model> {{\n  using Model=models::m_{ident}::Model;\n  alignas(8) const std::uint64_t words[Model::word_count]={{\n')
            for row in rows:
                sha.update(row); count+=len(row)
                words=struct.unpack('<'+'Q'*(len(row)//8),row)
                stream.write('    '+','.join(f'0x{v:016x}ULL' for v in words)+',\n')
            stream.write('  };\n  constexpr const std::uint64_t* data() const { return words; }\n  constexpr TableView<Model> view() const { return TableView<Model>::from_pointer(words); }\n};\n}\n')
        if expected is not None and sha.hexdigest()!=expected:
            raise ValueError('regenerated payload differs from frozen SHA-256')
        if callable(source):
            source=source(sha.hexdigest())
        (directory/'model.h.tmp').write_text(source)
        (directory/'model.h.tmp').replace(directory/'model.h')
        temporary.replace(directory/'data.h')
    finally:
        temporary.unlink(missing_ok=True)
    return count,sha.hexdigest()


def emit_main(task):
    output,key,record,error,emitter=task
    validate_record(record)
    ident=digest({'recipe':record,'error':error,'layout':MAIN_LAYOUT,'emitter':emitter})
    rows=interleaved_rows(record,payload_rows(record))
    count,sha=write_model(output,ident,lambda sha: main_source(record,ident,error,sha),rows,None)
    return key,{'id':ident,'cpp_model':f'fast_boys::models::m_{ident}::Model','table_bytes':count,
                'payload_layout':MAIN_LAYOUT,'payload_sha256':sha,'record':record}


def generate(summary,output,ranges=None,workers=1):
    if workers<1:
        raise ValueError('workers must be positive')
    if not summary.get('complete') or summary.get('unresolved',0):
        raise ValueError('a complete resolved selection is required')
    output=Path(output); records=summary['winners']
    chosen=sorted(records if ranges is None else ranges)
    if not chosen or any(key not in records for key in chosen):
        raise ValueError('requested range is missing')
    error=summary['config']['error']
    if any('tail' in records[key] for key in chosen):
        from .paired_headers import generate as generate_pairs
        return generate_pairs(summary,output,chosen,workers)
    if error['metric'] not in ('ulp','absolute','relative'):
        raise ValueError('unsupported error metric')
    manifest={'schema':1,'numerical_identity':summary['identity'],'models':{},'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'runtime_sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'include/fast_boys').rglob('*')) if p.is_file() and p.suffix in ('.h','.cuh') and 'models' not in p.relative_to(ROOT/'include/fast_boys').parts and p.name not in ('selected.h','selected_simd.h')}}
    tasks=[(output,key,records[key],error,manifest['generator_sha256']) for key in chosen]
    if workers==1:
        manifest['models']=dict(map(emit_main,tasks))
    else:
        with ProcessPoolExecutor(max_workers=min(workers,len(tasks))) as pool:
            manifest['models']=dict(pool.map(emit_main,tasks))
    tail=json.loads(TAIL.read_text()); meta=tail['metadata']
    raw=b''.join(int(w,16).to_bytes(8,'little') for w in tail['words'])
    if len(raw)!=meta['storage']['allocated_bytes'] or hashlib.sha256(raw).hexdigest()!=meta['storage']['sha256']:
        raise ValueError('archived tail payload is corrupt')
    ident=digest({'archive':tail,'consumer_layout':'compact-tail-v1','emitter':manifest['generator_sha256']})
    count,_=write_model(output,ident,tail_source(tail,ident),[raw],meta['storage']['sha256'])
    manifest['tail']={'id':ident,'cpp_model':f'fast_boys::models::m_{ident}::Model','table_bytes':count,'archive_commit':tail['archive_commit'],'archive_definition':meta['definition_id'],'accuracy_target':meta['accuracy_target'],'qualification':meta['qualification']}
    # Main and tail qualifications remain separate. A stricter/different target
    # cannot inherit this archived tail's 1-ULP qualification.
    manifest['tail']['matches_main_target']=(error==meta['accuracy_target'])
    # Lightweight catalog: payloads remain opt-in, one data header per range.
    catalog_id=digest({'models':{k:v['id'] for k,v in manifest['models'].items()},'tail':ident})
    namespace=f'fast_boys::models::catalog_{catalog_id}'
    lines=['#pragma once']
    for model in [*manifest['models'].values(),manifest['tail']]:
        lines.append(f'#include "fast_boys/models/{model["id"]}/model.h"')
    lines += [f'namespace {namespace} {{','template<int First,int Last> struct Selection;']
    for key,model in manifest['models'].items():
        record=model['record']; first,last=record['first'],record['last']
        lines.append(f'template<> struct Selection<{first},{last}> {{ using type={model["cpp_model"]}; }};')
        # A convenient opt-in payload header, without embedding other tables.
        path=output/f'fast_boys/models/data_{first}_{last}.h'
        path.write_text(f'#pragma once\n#include "fast_boys/models/{model["id"]}/data.h"\n')
    lines += ['template<int Last,int First=0> using Model=typename Selection<First,Last>::type;',
              f'using Tail={manifest["tail"]["cpp_model"]};','}']
    (output/'fast_boys/models'/f'catalog_{catalog_id}.h').write_text('\n'.join(lines)+'\n')
    (output/'fast_boys/selected.h').write_text(f'#pragma once\n#include "fast_boys/models/catalog_{catalog_id}.h"\nnamespace fast_boys {{ namespace selected=models::catalog_{catalog_id}; }}\n')
    (output/'fast_boys/models/tail_data.h').write_text(f'#pragma once\n#include "fast_boys/models/{ident}/data.h"\n')
    manifest['catalog']={'id':catalog_id,'cpp_namespace':namespace,'header':'fast_boys/selected.h'}
    path=output/'manifest.json'; path.with_suffix('.json.tmp').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n'); path.with_suffix('.json.tmp').replace(path)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--output',type=Path,required=True,help='generated include root')
    parser.add_argument('--ranges',nargs='+',help='selected keys, e.g. 0-4 0-8 0-12')
    parser.add_argument('--workers',type=int,default=1,help='parallel model regenerations (no numerical search)')
    args=parser.parse_args()
    generate(json.loads(args.summary.read_text()),args.output,args.ranges,args.workers)


if __name__=='__main__':
    main()

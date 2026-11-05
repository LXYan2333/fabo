"""Emit independent paired tables, preserving the common coefficient layout."""
import hashlib
import json
from pathlib import Path
from .headers import digest,emit_main,write_model,coefficient_word,correction_word
from .tail import payload_rows


def rows(record):
    first,last=record['first'],record['last']
    count=record['storage']['highest_reference_order']-first+1
    codes=(last-first+8)//8
    checksum=hashlib.sha256()
    for raw in payload_rows(record):
        checksum.update(raw)
        words=[raw[i:i+8] for i in range(0,len(raw),8)]
        result=[]
        for i in range(count):
            if i%8==0 and i//8<codes: result.append(words[count+i//8])
            result.append(words[i])
        yield b''.join(result)
    if record.get('payload_sha256',checksum.hexdigest())!=checksum.hexdigest():
        raise ValueError('tail payload differs from frozen recipe')


def generate(summary,output,chosen,workers=1):
    output=Path(output)
    emitter=hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('headers.py').read_bytes()).hexdigest()
    result=dict(schema=2,numerical_identity=summary['identity'],models={},tails={},generator_sha256=emitter)
    for key in chosen:
        record=summary['winners'][key]
        if 'tail' not in record: raise ValueError('mixed paired and legacy selections')
        _,main=emit_main((output,key,record,summary['config']['error'],emitter))
        tm=record['tail']; first,last=record['first'],record['last']
        if tm['degrees']!=record['degrees'] or tm['first']!=first or tm['last']!=last:
            raise ValueError('paired degrees/ranges disagree')
        if tm['storage']['row_bytes']!=record['storage']['row_bytes'] or tm['minimum_x']!=float.fromhex(record['grid']['domain_end']):
            raise ValueError('paired layout/seam mismatch')
        if tm['storage']['table_bytes']+record['storage']['table_bytes']>summary['config']['budget_bytes']:
            raise ValueError('paired table exceeds combined budget')
        ident=digest(dict(main=main['id'],tail=tm,emitter=emitter))
        source=f'''#pragma once
#include "fast_boys/models/{main['id']}/model.h"
namespace fast_boys::models::m_{ident} {{
struct Model : {main['cpp_model']} {{
  using MainModel={main['cpp_model']};
  static constexpr bool shared_arithmetic=true;
  static constexpr unsigned retained_bits={tm['retained_bits']}, discarded_bits={52-tm['retained_bits']};
  static constexpr double minimum_x={tm['minimum_x'].hex()};
  static constexpr std::size_t row_count={tm['storage']['row_count']}, row_words={tm['storage']['row_words']};
  static constexpr std::size_t table_bytes={tm['storage']['table_bytes']},word_count=table_bytes/8;
  inline static constexpr char model_id[]="{ident}";
  inline static constexpr char canonical_payload_sha256[]="{tm.get('payload_sha256','fixture')}";
  inline static constexpr char payload_sha256[]="PAYLOAD_SHA";
}};
}}
'''
        count,sha=write_model(output,ident,lambda sha:source.replace('PAYLOAD_SHA',sha),rows(tm),None)
        result['models'][key]=main
        result['tails'][key]=dict(id=ident,cpp_model=f'fast_boys::models::m_{ident}::Model',record=tm,
                                  table_bytes=count,payload_sha256=sha,qualification=record['tail_qualification'])
        for prefix,model in [('data',main),('tail_data',result['tails'][key])]:
            (output/f'fast_boys/models/{prefix}_{first}_{last}.h').write_text(f'#pragma once\n#include "fast_boys/models/{model["id"]}/data.h"\n')
    catalog=digest(result)
    ns=f'fast_boys::models::catalog_{catalog}'
    lines=['#pragma once','#define FAST_BOYS_RANGE_TAILS 1']
    for entry in [*result['models'].values(),*result['tails'].values()]:
        lines.append(f'#include "fast_boys/models/{entry["id"]}/model.h"')
    lines += [f'namespace {ns} {{','template<int First,int Last> struct Selection;']
    for key,main in result['models'].items():
        r=main['record']; tail=result['tails'][key]
        lines.append(f'template<> struct Selection<{r["first"]},{r["last"]}> {{ using type={main["cpp_model"]}; using tail={tail["cpp_model"]}; }};')
    lines += ['template<int Last,int First=0> using Model=typename Selection<First,Last>::type;',
              'template<int Last,int First=0> using Tail=typename Selection<First,Last>::tail;','}']
    (output/f'fast_boys/models/catalog_{catalog}.h').write_text('\n'.join(lines)+'\n')
    (output/'fast_boys/selected.h').write_text(f'#pragma once\n#include "fast_boys/models/catalog_{catalog}.h"\nnamespace fast_boys {{ namespace selected={ns}; }}\n')
    result['catalog']=dict(id=catalog,cpp_namespace=ns,header='fast_boys/selected.h')
    (output/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result

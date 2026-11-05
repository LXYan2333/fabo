"""Emit one contiguous main+tail array per numerical range."""
import hashlib
import json
from pathlib import Path
from .headers import digest, main_source, validate_record, write_model, interleaved_rows, MAIN_LAYOUT
from .search import payload_rows as main_rows
from .tail import payload_rows as tail_rows, storage as tail_storage

LAYOUT='materialized-nextup-main-tail-v3'


def rows(record):
    first,last=record['first'],record['last']
    count=record['storage']['highest_reference_order']-first+1
    codes=(last-first+8)//8
    checksum=hashlib.sha256()
    for raw in tail_rows(record):
        checksum.update(raw)
        words=[raw[i:i+8] for i in range(0,len(raw),8)]
        result=[]
        for i in range(count):
            if i%8==0 and i//8<codes: result.append(words[count+i//8])
            result.append(words[i])
        yield b''.join(result)
    if record.get('payload_sha256',checksum.hexdigest())!=checksum.hexdigest():
        raise ValueError('tail payload differs from frozen recipe')


def combined_source(record,ident,error,sha):
    source=main_source(record,ident,error,sha)
    source=source.replace(MAIN_LAYOUT,LAYOUT)
    main=record['storage']; tail=record['tail']; total=main['table_bytes']+tail['storage']['table_bytes']
    source=source.replace(f'table_bytes={main["table_bytes"]}',f'table_bytes={total}')
    constants=f'''  static constexpr bool combined_table=true;
  static constexpr std::size_t main_table_bytes={main['table_bytes']},tail_table_bytes={tail['storage']['table_bytes']};
  static constexpr std::size_t tail_row_offset=row_count,tail_row_count={tail['storage']['row_count']};
  static constexpr unsigned tail_retained_bits={tail['retained_bits']},tail_discarded_bits={52-tail['retained_bits']};
  static_assert(tail_row_offset*row_words*8==main_table_bytes,"tail offset mismatch");
  static_assert((row_count+tail_row_count)*row_words*8==table_bytes,"combined allocation mismatch");
'''
    return source.replace('  // Sampled qualification',constants+'  // Sampled qualification')


def generate(summary,output,chosen,workers=1):
    output=Path(output)
    emitter=hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('headers.py').read_bytes()).hexdigest()
    result=dict(schema=3,combined_table=True,numerical_identity=summary['identity'],models={},generator_sha256=emitter)
    for key in chosen:
        record=summary['winners'][key]; validate_record(record)
        tm=record['tail']; first,last=record['first'],record['last']
        if tm['degrees']!=record['degrees'] or tm['first']!=first or tm['last']!=last:
            raise ValueError('paired degrees/ranges disagree')
        if tm['storage']!=tail_storage(first,tm['degrees'],tm['retained_bits']):
            raise ValueError('tail storage does not match recipe')
        if tm['storage']['row_bytes']!=record['storage']['row_bytes'] or tm['minimum_x']!=float.fromhex(record['grid']['domain_end']):
            raise ValueError('paired layout/seam mismatch')
        total=tm['storage']['table_bytes']+record['storage']['table_bytes']
        if total>summary['config']['budget_bytes']:
            raise ValueError('paired table exceeds combined budget')
        ident=digest(dict(recipe=record,error=summary['config']['error'],layout=LAYOUT,emitter=emitter))
        checksums={}
        def data():
            for name,stream in [('main',interleaved_rows(record,main_rows(record))),('tail',rows(tm))]:
                checksum=hashlib.sha256()
                for raw in stream:
                    checksum.update(raw)
                    yield raw
                checksums[name]=checksum.hexdigest()
        count,sha=write_model(output,ident,lambda sha:combined_source(record,ident,summary['config']['error'],sha),data(),None)
        if count!=total: raise ValueError('combined payload size mismatch')
        result['models'][key]=dict(id=ident,cpp_model=f'fast_boys::models::m_{ident}::Model',record=record,
            table_bytes=count,payload_sha256=sha,payload_layout=LAYOUT,tail_row_offset=record['grid']['row_count'],
            section_sha256=checksums)
        (output/f'fast_boys/models/data_{first}_{last}.h').write_text(f'#pragma once\n#include "fast_boys/models/{ident}/data.h"\n')
    catalog=digest(result)
    ns=f'fast_boys::models::catalog_{catalog}'
    lines=['#pragma once','#define FAST_BOYS_COMBINED_TABLE 1']
    for entry in result['models'].values():
        lines.append(f'#include "fast_boys/models/{entry["id"]}/model.h"')
    lines += [f'namespace {ns} {{','template<int First,int Last> struct Selection;']
    for main in result['models'].values():
        r=main['record']
        lines.append(f'template<> struct Selection<{r["first"]},{r["last"]}> {{ using type={main["cpp_model"]}; }};')
    lines += ['template<int Last,int First=0> using Model=typename Selection<First,Last>::type;','}']
    (output/f'fast_boys/models/catalog_{catalog}.h').write_text('\n'.join(lines)+'\n')
    (output/'fast_boys/selected.h').write_text(f'#pragma once\n#include "fast_boys/models/catalog_{catalog}.h"\nnamespace fast_boys {{ namespace selected={ns}; }}\n')
    result['catalog']=dict(id=catalog,cpp_namespace=ns,header='fast_boys/selected.h')
    (output/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result

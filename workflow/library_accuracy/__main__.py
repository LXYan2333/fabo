"""Explicit stages; scan requires an already prepared immutable run."""
import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from .core import ROOT, sha, identity, save, partitions, merge, storage, csv_write

def run(a):
    root=a.run.resolve()
    if a.stage=='storage':
        root.mkdir(parents=True,exist_ok=True)
        rows=storage(ROOT/'data/numerical/paired-1ulp/summary.json',ROOT/'include')
        save(root/'storage.json',rows);csv_write(root/'storage.csv',rows)
        from .report import storage_plot
        storage_plot(root,rows)
        return
    if a.stage=='prepare':
        config=json.loads(a.config.read_text())
        if config.get('layout','adjacent') not in ('adjacent','mixed'):raise ValueError('invalid lane layout')
        if root.exists():raise ValueError('use a new run directory')
        total=config.get('total',1000000001)
        if not 0<total<=1000000001:raise ValueError('grid exceeds [0,1000]')
        records=[]
        for item in config['adapters']:
            if not 0<=item['N']<=12 or item['mode'] not in ('strict','fast'):raise ValueError('invalid adapter')
            path=Path(item['path']).resolve()
            records.append(dict(item,path=str(path),sha256=sha(path)))
        ids=[r['id'] for r in records]
        if not ids or len(ids)!=len(set(ids)):raise ValueError('empty/duplicate adapters')
        scanner=Path(config['scanner']).resolve();table=Path(config['reference_table']).resolve()
        resources={str(Path(p).resolve()):sha(p) for p in config.get('resources',[])}
        recipe=dict(config=config,adapters=records,resources=resources,scanner=str(scanner),scanner_sha256=sha(scanner),reference_table=str(table),reference_sha256=sha(table),
                    total=total,denominator=1000000,shards=partitions(total,config.get('shard_size',1000000)),
                    sources={str(p.relative_to(ROOT)):sha(p) for folder in ('workflow/library_accuracy','benchmark/library_accuracy') for p in (ROOT/folder).glob('*') if p.is_file()})
        root.mkdir(parents=True)
        save(root/'run.json',dict(identity=identity(recipe),recipe=recipe))
        (root/'adapters.txt').write_text(''.join(f'{json.dumps(r["id"])} {json.dumps(r["path"])} {r["N"]}\n' for r in records))
        return
    record=json.loads((root/'run.json').read_text());r=record['recipe']
    if identity(r)!=record['identity']:raise ValueError('modified run recipe')
    expected=''.join(f'{json.dumps(v["id"])} {json.dumps(v["path"])} {v["N"]}\n' for v in r['adapters'])
    if (root/'adapters.txt').read_text()!=expected:raise ValueError('modified adapter manifest')
    for path,digest in [(r['scanner'],r['scanner_sha256']),(r['reference_table'],r['reference_sha256'])]+[(v['path'],v['sha256']) for v in r['adapters']]+list(r.get('resources',{}).items()):
        if sha(path)!=digest:raise ValueError('artifact changed: '+path)
    if a.stage in ('scan','pilot'):
        import tempfile
        from .environment import bind
        execution=bind(root,r)
        if a.stage=='scan' and r['total']>100000 and not (root/'pilot-summary.json').exists():
            raise ValueError('a successful pilot is required before production scanning')
        if a.shard<0 or a.shard>=len(r['shards']):raise ValueError('invalid shard')
        pilot_count=min(1031,r['total']) # Includes a partial SIMD vector/CUDA block.
        spans=[r['shards'][a.shard]] if a.stage=='scan' else [(v,pilot_count) for v in sorted({0,(r['total']-pilot_count)//2,r['total']-pilot_count})]
        dest=root/a.stage;dest.mkdir(exist_ok=True)
        jobs=[(first,count,r['config'].get('layout','adjacent'),f'{first}.json') for first,count in spans]
        if a.stage=='pilot':jobs.append((0,pilot_count,'mixed','mixed.json'))
        for first,count,layout,filename in jobs:
            name=dest/filename
            if name.exists():
                old=json.loads(name.read_text())
                if old['identity']!=record['identity'] or old.get('execution')!=execution:raise ValueError('stale shard')
                continue
            with tempfile.TemporaryDirectory(prefix='fabo-accuracy-',dir=os.environ.get('SLURM_TMPDIR','/tmp')) as tmp:
                output=Path(tmp)/'result.json'
                env=dict(os.environ);env.pop('FABO_ACCURACY_MIXED',None)
                env['FABO_ACCURACY_GRID_TOTAL']=str(r['total'])
                if layout=='mixed':env['FABO_ACCURACY_MIXED']='1'
                subprocess.run([r['scanner'],'scan',r['reference_table'],str(root/'adapters.txt'),str(first),str(count),'1000000',str(r['config'].get('batch',1024)),str(output)],check=True,env=env)
                result=json.loads(output.read_text());result.update(identity=record['identity'],execution=execution,host=platform.node(),layout=layout)
                save(name,result)
        if a.stage=='pilot':
            samples=[json.loads((dest/f'{f}.json').read_text()) for f,c in spans]
            count=sum(s['count'] for s in samples);seconds=sum(s['seconds'] for s in samples)
            save(root/'pilot-summary.json',dict(identity=record['identity'],execution=execution,inputs=count,seconds=seconds,
                 estimated_serial_scan_seconds=seconds/count*r['total'],peak_rss_kib=max(s.get('peak_rss_kib',0) for s in samples),
                 note='Bounded pilot, not a timing benchmark; estimate excludes scheduling and shard startup.'))
        return
    if a.stage=='report':
        shards=[json.loads(p.read_text()) for p in (root/'scan').glob('*.json')]
        from .core import identity as digest
        execution=digest(json.loads((root/'execution.json').read_text()))
        if any(s['identity']!=record['identity'] or s.get('execution')!=execution for s in shards):raise ValueError('incompatible shards')
        rows=merge(shards,r['total'])
        by_id={v['id']:v for v in r['adapters']}
        expected={(v['id'],v['N'],n,m) for v in r['adapters'] for n in range(v['N']+1) for m in ('absolute','relative','ulp')}
        actual={(v['id'],v['N'],v['n'],v['metric']) for v in rows if v['n']!='all'}
        if expected!=actual:raise ValueError('missing or unexpected metric/order coverage')
        for row in rows:
            row.update({k:by_id[row['id']].get(k,'unspecified') for k in ('platform','backend','mode')})
        save(root/'accuracy.json',rows);csv_write(root/'accuracy.csv',rows)
        from .report import accuracy_plots
        accuracy_plots(root,rows)
        save(root/'complete.json',dict(identity=record['identity'],execution=execution,inputs=r['total'],denominator=r['denominator'],
             sampled_only=True,files={p.name:sha(p) for p in root.iterdir() if p.suffix in ('.pdf','.csv','.tex') or p.name=='accuracy.json'}))

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('stage',choices=['prepare','scan','pilot','report','storage']);p.add_argument('--run',type=Path,required=True);p.add_argument('--config',type=Path);p.add_argument('--shard',type=int,default=0)
    a=p.parse_args()
    if a.stage=='prepare' and not a.config:p.error('prepare requires --config')
    run(a)
if __name__=='__main__':main()

"""Reports from saved measurements only; never launches computation."""
LABELS={'fabo':'FABO (native gather)','fabo_software':'FABO (software gather)',
        'quick':'QUICK','simint':'Simint','libintx':'LibintX',
        'vsr':'Vikhamar–Sandberg–Repisky','laikov':'Laikov','gansu':'GANSU'}
def storage_plot(root, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots()
    n=[r['N'] for r in rows]
    ax.stackplot(n,[r['main_bytes']/1024 for r in rows],[r['tail_bytes']/1024 for r in rows],labels=['Main table','Tail table'])
    ax.axhline(1024,color='gray',linestyle='--',label='1 MiB budget')
    ax.set(xlabel='Requested maximum order N',ylabel='Reference storage (KiB)');ax.legend()
    fig.tight_layout();fig.savefig(root/'reference-storage.pdf');plt.close(fig)
    with (root/'storage.tex').open('w') as f:
        f.write('\\begin{tabular}{rrrr}\n$N$ & Main (bytes) & Tail (bytes) & Total (bytes) \\\\\n')
        for r in rows:f.write(f'{r["N"]} & {r["main_bytes"]} & {r["tail_bytes"]} & {r["total_bytes"]} \\\\\n')
        f.write('\\end{tabular}\n')

def accuracy_plots(root, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pooled=[r for r in rows if r['n']=='all' and r['status']=='complete']
    groups=sorted({(r['platform'],r['mode']) for r in rows})
    for platform,mode in groups:
        subset=[r for r in pooled if (r['platform'],r['mode'])==(platform,mode)]
        for metric in ('absolute','relative','ulp'):
            fig,axes=plt.subplots(1,2,figsize=(11,4))
            for backend in sorted({r['backend'] for r in subset}):
                data=sorted((r for r in subset if r['backend']==backend and r['metric']==metric),key=lambda r:r['N'])
                for ax,stat in zip(axes,('max','mean')):
                    label='FABO' if platform=='cuda' and backend=='fabo' else LABELS.get(backend,backend)
                    ax.plot([r['N'] for r in data],[float(r[stat+'_hi']) for r in data],'.',label=label)
                    ax.set(xlabel='Requested maximum order N',ylabel=f'{stat.capitalize()} {metric} error (upper bound)',yscale='log')
            fig.suptitle(f'{platform}: {mode}');axes[1].legend();fig.tight_layout()
            fig.savefig(root/f'accuracy-{platform}-{mode}-{metric}.pdf');plt.close(fig)
    def esc(value):return str(value).replace('_',r'\_')
    with (root/'accuracy.tex').open('w') as f:
        f.write('\\begin{longtable}{llrlrr}\nPlatform/mode & Backend & $N$ & Metric & Maximum (upper) & Mean (upper) \\\\\n\\endhead\n')
        for r in rows:
            if r['n']!='all':continue
            numbers=[r.get(k) for k in ('max_hi','mean_hi')]
            values=['---' if v is None else f'{float(v):.7g}' for v in numbers]
            f.write(f'{esc(r["platform"])}/{esc(r["mode"])} & {esc(r["backend"])} & {r["N"]} & {r["metric"]} & {values[0]} & {values[1]} \\\\\n')
        f.write('\\end{longtable}\n')

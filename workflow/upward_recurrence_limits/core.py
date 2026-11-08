GATES=(1,2,4,8,16)
DENOMINATOR=1_000_000
FINAL=1_000_000_000
WINDOW=1_000_000

def reduce_windows(shards, final=FINAL, window=WINDOW):
    """Exact from first/last failures only when each shard is shorter than window."""
    keys={(n,g) for n in range(1,13) for g in GATES}
    streak={key:0 for key in keys};found={};cursor=1
    for d in shards:
        a,b=d['begin'],d['end']
        if d['protocol']!='upward-window-v1' or a!=cursor or not 0<b-a<window:
            raise ValueError('missing/overlapping/oversized shard')
        rows={(r['N'],r['gate']):r for r in d['rows']}
        if set(rows)!=keys or len(d['rows'])!=len(keys):raise ValueError('incomplete/duplicate coverage')
        for key,r in rows.items():
            f,l=r['first_fail'],r['last_fail']
            if not ((f==l==-1) or a<=f<=l<b):raise ValueError('invalid failure indices')
            prefix=f-a if f>=0 else b-a
            if key not in found and streak[key]+prefix>=window:found[key]=a-streak[key]
            streak[key]=b-l-1 if l>=0 else streak[key]+b-a
        cursor=b
    if cursor!=final+1:raise ValueError('incomplete domain')
    return [dict(N=n,gate=g,status='found' if (n,g) in found else 'no_window_found',
        start_index=found.get((n,g)),end_index=found[n,g]+window-1 if (n,g) in found else None,
        start_x=found[n,g]/DENOMINATOR if (n,g) in found else None,
        end_x=(found[n,g]+window-1)/DENOMINATOR if (n,g) in found else None)
        for n,g in sorted(keys)]

def plot(rows,path):
    from pathlib import Path
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6.4,4.5))
    for j,g in enumerate(GATES):
        data=[r for r in rows if r['gate']==g]
        if not any(r['start_x'] is not None for r in data):continue
        ax.plot([r['start_x'] if r['start_x'] is not None else float('nan') for r in data],[r['N'] for r in data],'.-',color=f'C{j}',label=f'{g} ULP')
    ax.set(xlabel='First passing-window start x',ylabel='Requested maximum order N',yticks=range(1,13),xscale='log')
    ax.legend(ncol=2);fig.tight_layout();fig.savefig(path);plt.close(fig)

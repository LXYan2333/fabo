"""Regenerate selected payloads and figures without repeating the grid search."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from .search import payload_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tables',action='store_true')
    args=parser.parse_args()
    summary=json.loads(args.summary.read_text())
    args.output.mkdir(parents=True,exist_ok=True)
    if args.tables:
        for name,record in summary['winners'].items():
            temporary=args.output/(name+'.bin.tmp')
            checksum=hashlib.sha256()
            with temporary.open('wb') as stream:
                for row in payload_rows(record):
                    checksum.update(row)
                    stream.write(row)
            if checksum.hexdigest()!=record['payload_sha256']:
                temporary.unlink()
                raise ValueError('regenerated payload does not match frozen recipe: '+name)
            temporary.replace(args.output/(name+'.bin'))
    os.environ.setdefault('MPLCONFIGDIR',str(args.output/'.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    records=sorted(summary['winners'].values(),key=lambda r:(r['first'],r['last']))
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for record in records:
        n=record['last']
        axes[0].plot(range(record['first'],n+1),record['degrees'],'.-',label=f"[{record['first']},{n}]")
        axes[1].plot(n,record['storage']['table_bytes']/1024,'.')
        axes[2].plot(n,max(q['max_error_upper'] for q in record['qualification']),'.')
    axes[0].set(xlabel='Output order',ylabel='Selected Taylor degree')
    axes[1].set(xlabel='Highest requested order',ylabel='Table size (KiB)')
    axes[2].set(xlabel='Highest requested order',ylabel='Sampled error upper bound ('+summary['config']['error']['metric']+')')
    axes[2].axhline(summary['config']['error']['limit'],color='gray',linestyle='--')
    if len(records)<=8:
        axes[0].legend()
    fig.savefig(args.output/'selection.pdf')
    plt.close(fig)
    from .model import Grid
    for record in records:
        meta=record['grid']
        grid=Grid(meta['b'],meta['e'],meta['m'],float.fromhex(meta['domain_end']))
        fig,ax=plt.subplots(layout='constrained')
        # Plot ideal reference spacings, not claimed exact mapping-cell widths.
        nodes=[grid.node(k) for k in grid.keys]
        if len(nodes)>1:
            ax.plot(nodes[:-1],[b-a for a,b in zip(nodes,nodes[1:])],'.')
        ax.set(xscale='symlog',yscale='log',xlabel='Reference x',ylabel='Next reference spacing')
        fig.savefig(args.output/f"grid-{record['first']}-{record['last']}.pdf")
        plt.close(fig)


if __name__=='__main__':
    main()

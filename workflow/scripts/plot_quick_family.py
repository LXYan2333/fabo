#!/usr/bin/env python3
"""Plot archived family observations only; no GPU work or timing."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def finite(values):
    return [math.nan if v is None else v for v in values]


def plot(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.ticker import PercentFormatter
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    families=data['families'];settings=data['settings']
    mode=data.get('provenance',{}).get('mode','see source provenance')
    footer=f"{mode}; {data['weighting']}.\nInstrumented active cohorts, not necessarily full physical warps; no timing prediction."
    def save(fig, book=None):
        fig.text(.5,.015,footer,ha='center',fontsize=8,wrap=True)
        fig.tight_layout(rect=(0,.09,1,.94))
        if book is not None:book.savefig(fig)
    fig,axes=plt.subplots(len(families),4,figsize=(13,3*len(families)),squeeze=False)
    for row,f in zip(axes,families):
        for ax,key,title in zip(row,('maximum','active','span','distinct'),
                               ('Maximum requested order','Active lanes','Maximum − minimum order','Distinct requested orders')):
            values=f[key];start=1 if key in ('active','distinct') else 0
            ax.bar(range(start,len(values)),finite(values[start:]),color='#0072B2')
            ax.set(title=f"{f['name']}: {title}",xlabel=title,ylabel='Cohort probability',ylim=(0,1))
            if key=='active':ax.set_xlim(.5,32.5);ax.set_xticks([1,8,16,24,32])
            ax.yaxis.set_major_formatter(PercentFormatter(1));ax.grid(axis='y',alpha=.2)
            if all(v is None for v in values):ax.text(.5,.5,'No observations',ha='center',transform=ax.transAxes)
    fig.suptitle('Requests and active participation by QUICK family');save(fig)
    fig.savefig(output/'requests.pdf');plt.close(fig)
    fig,axes=plt.subplots(len(families),2,figsize=(10,3*len(families)),squeeze=False)
    edges=[0,*settings['histogram_edges']]
    for row,f in zip(axes,families):
        ax=row[0];mass=f['histogram']
        density=[v/(b-a) if v is not None and v>0 else math.nan for v,a,b in zip(mass[1:-2],edges,edges[1:])]
        ax.stairs(density,edges,color='#0072B2');ax.set_yscale('log')
        ax.set_xscale('symlog',base=10,linthresh=10)
        ax.set_xlim(0,edges[-1])
        ax.set(title=f['name']+' inputs',xlabel='Argument x',ylabel='Probability density / unit x')
        label=lambda v:'unobserved' if v is None else f'{v:.2%}'
        ax.text(.97,.96,'Zero: '+label(mass[0])+'\nOverflow: '+label(mass[-2])+'\nInvalid: '+label(mass[-1]),
                transform=ax.transAxes,ha='right',va='top',fontsize=8)
        ax=row[1];ax.bar(['All bounded','All tail','Mixed'],finite(f['split']),color='#0072B2')
        ax.set(title=f"{f['name']}: boundary {settings['domain_end']:g}",ylabel='Valid-cohort probability',ylim=(0,1))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    fig.suptitle('Argument distribution and bounded/tail split');save(fig)
    fig.savefig(output/'inputs.pdf');plt.close(fig)
    for kind,stem in (('all','alltrue'),('mixed','mixed')):
        with PdfPages(output/(stem+'.pdf')) as book:
            for f in families:
                maxima=[-1,*range(len(f['maximum']))]
                for begin in range(0,len(maxima),6):
                    chunk=maxima[begin:begin+6]
                    fig,axes=plt.subplots(math.ceil(len(chunk)/3),3,figsize=(12,3.3*math.ceil(len(chunk)/3)+1),squeeze=False)
                    for ax,n in zip(axes.flat,chunk):
                        observed=False
                        for activity,style in (('full','-'),('partial','--')):
                            b=next(b for b in f['branches'] if b['maximum']==n and b['activity']==activity)
                            for suffix,color in (('gt','#0072B2'),('lt','#D55E00')):
                                values=b[kind+'_'+suffix];observed|=any(v is not None for v in values)
                                ax.plot(settings['thresholds'],finite(values),color=color,linestyle=style,
                                        label=f"{'All' if kind=='all' else 'Mixed'} x {'>' if suffix=='gt' else '<'} t; {activity}")
                        ax.set(title='All maxima' if n==-1 else f'Cohort maximum = {n}',xlabel='Threshold t',ylabel='Valid-cohort probability',ylim=(-.02,1.02))
                        ax.set_xscale('symlog',base=10,linthresh=10);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.grid(alpha=.2)
                        ax.set_xlim(0,settings['thresholds'][-1] or 1)
                        ax.axvline(117,color='.65',linestyle=':',linewidth=1)
                        ax.axvline(settings['domain_end'],color='.35',linestyle='-.',linewidth=1)
                        if not observed:ax.text(.5,.5,'No observations',ha='center',transform=ax.transAxes)
                    for ax in list(axes.flat)[len(chunk):]:ax.set_visible(False)
                    fig.suptitle(f"{f['name']}: {'all-true' if kind=='all' else 'mixed'} strict predicates (dotted: 117; dash-dot: {settings['domain_end']:g})")
                    fig.legend(*axes.flat[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.055),ncol=4,fontsize=8)
                    save(fig,book);plt.close(fig)
    (output/'README.md').write_text('# QUICK family diagnostic plots\n\n'+footer+'\n\n[Requests and participation](requests.pdf) · [Inputs and domain split](inputs.pdf) · [All-true probabilities](alltrue.pdf) · [Mixed probabilities](mixed.pdf)\n\nFull curves use 32 participating lanes; partial curves use fewer. Empty conditions remain unobserved. The horizontal argument/threshold axes are linear through 10 and logarithmic afterward. Input density is normalized by actual bin width.\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records',type=Path,help='summary.json, views.json, equal-case.json, or report directory')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    paths=[args.records] if args.records.is_file() else sorted(args.records.rglob('views.json'))+sorted(args.records.rglob('equal-case.json'))
    if not paths and args.records.is_dir():paths=sorted(args.records.rglob('summary.json'))
    if not paths:parser.error('no family report views found')
    for path in paths:
        name=path.stem if args.records.is_file() else str(path.relative_to(args.records).with_suffix('')).replace('/','--')
        output=(args.output or (args.records.parent if args.records.is_file() else args.records)/'family-plots')/name
        data=json.loads(path.read_text())
        if data.get('schema')==2:
            from quick_family_probe import views
            data=dict(settings=data['settings'],families=views(data),provenance=data.get('provenance',{}),
                      weighting='pooled cohorts for requests/branches; pooled lanes for inputs')
        plot(data,output)
        (output/'provenance.json').write_text(json.dumps(dict(source=str(path.resolve()),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':main()

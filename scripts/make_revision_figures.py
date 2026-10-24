"""Render 16 scientific figures directly from frozen model outputs."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(k,'1')
import csv,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import joblib
import legacy_benchmark
from enhanced_mgre import SmoothMGRE

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures'
COLORS={'MGRE':'#126C8A','RBF_SVR_tuned':'#E48B37','LegacyMGRE':'#A763A6','PolynomialRidge':'#5A8C4B','MLP':'#C45C5A','HGB':'#71859D','Ridge':'#A9B3BD','RandomForest':'#65794B','Mean':'#C7C7C7'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.titlesize':13,'axes.labelsize':12,
    'xtick.labelsize':11,'ytick.labelsize':11,'legend.fontsize':10.5,'axes.spines.top':False,'axes.spines.right':False,
    'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white','svg.fonttype':'none','svg.hashsalt':'mgre-revision-20261024','axes.grid':True,'grid.alpha':.16})

def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def build():
    OUT.mkdir(exist_ok=True);r=load('analysis/revision_results.json');s=r['summary'];spec=load('analysis/development_frozen_spec.json');data=load('data/dataset.json');features=data['metadata']['features'];rows=data['rows'];label=r['model_labels'];manifest=[]
    pretty=['Width, b (mm)','Thickness, h (mm)','Span, L (mm)','Punch radius (mm)','Support radius (mm)','Pre-bend stroke (mm)']
    splits={sp:[v for v in rows if v['split']==sp] for sp in ['train','validation','calibration','test','ood']}
    x={sp:np.array([[v[f] for f in features] for v in vv]) for sp,vv in splits.items()}
    y={sp:np.array([v['reference_stroke_mm'] for v in vv]) for sp,vv in splits.items()}
    ids={sp:[v['sample_id'] for v in vv] for sp,vv in splits.items()}
    pred={}
    with (ROOT/'analysis'/'predictions.csv').open(newline='',encoding='utf-8') as stream:
        for v in csv.DictReader(stream):
            key=(v['model'],int(v['seed']),v['split']);pred.setdefault(key,{'id':[],'p':[],'lo':[],'hi':[]})
            pred[key]['id'].append(v['sample_id'])
            for dest,source in [('p','predicted_stroke_mm'),('lo','lower_90_mm'),('hi','upper_90_mm')]:pred[key][dest].append(float(v[source]))
    for key,v in pred.items():
        assert v['id']==ids[key[2]]
        for k in ['p','lo','hi']:v[k]=np.array(v[k])
    central=[n for n in r['names'] if not n.startswith('No') and n!='Mean']
    def panel(ax,letter):ax.text(-.13,1.05,letter,transform=ax.transAxes,fontweight='bold',fontsize=14)
    def save(fig,id,caption,section):
        png=OUT/f'{id}.png';svg=OUT/f'{id}.svg';fig.savefig(png,dpi=200,bbox_inches='tight');fig.savefig(svg,bbox_inches='tight',metadata={'Date':'2026-10-24'});plt.close(fig)
        manifest.append({'id':id,'filename':png.name,'path':'figures/'+png.name,'svg':'figures/'+svg.name,'section':section,'caption':caption,
            'sha256':hashlib.sha256(png.read_bytes()).hexdigest()})
    def box(ax,x0,y0,w,h,text,color='#EAF3F6'):
        ax.add_patch(FancyBboxPatch((x0,y0),w,h,boxstyle='round,pad=.012',fc=color,ec='#407088',lw=1))
        ax.text(x0+w/2,y0+h/2,text,ha='center',va='center',fontsize=11)
    def arrow(ax,a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#335568','lw':1.3})
    # 01 Process and study roles.
    fig,ax=plt.subplots(figsize=(10,4.4));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    for i,text in enumerate(['Six physical inputs\nand stroke response','Fixed split roles\n4,800 / 1,200 / 1,000\n/ 1,000 / 1,000','Train + validation\nmodel development','Freeze settings\nthen evaluate']):
        box(ax,.02+i*.25,.60,.20,.27,text)
        if i<3:arrow(ax,(.234+i*.25,.735),(.256+i*.25,.735))
    box(ax,.12,.12,.30,.24,'Calibrate 90% intervals\non 1,000 calibration rows','#FAEFDF');box(ax,.58,.12,.30,.24,'Report IID + thickness shift\naccuracy, intervals, ablations','#E9F1E5')
    arrow(ax,(.77,.59),(.77,.37));arrow(ax,(.52,.59),(.27,.37));arrow(ax,(.42,.24),(.57,.24))
    ax.text(.5,.01,'Training seeds 40, 41, 42  |  Fixed mean-prediction bootstrap seed 43',ha='center',fontsize=11)
    save(fig,'F01','Analysis workflow and the separate roles of training, validation, calibration and final evaluation partitions.','Methods')
    # 02 Distributions.
    fig,axes=plt.subplots(2,4,figsize=(12,6))
    for j,ax in enumerate(axes.flat):
        if j==7:ax.axis('off');continue
        for sp,col in [('train','#126C8A'),('test','#7CAE9C'),('ood','#E48B37')]:
            vals=x[sp][:,j] if j<6 else y[sp];ax.hist(vals,bins=25,density=True,histtype='step',lw=1.3,color=col,label={'train':'Training','test':'IID test','ood':'Thickness shift'}[sp])
        ax.set_xlabel(pretty[j] if j<6 else 'Reference stroke (mm)');ax.set_ylabel('Density');panel(ax,chr(97+j))
    axes.flat[0].legend();fig.tight_layout();save(fig,'F02','Distributions of six input variables and the response across training, IID test and thickness-shift partitions.','Methods')
    # 03 Input-response projections.
    fig,axes=plt.subplots(2,3,figsize=(11,6))
    for j,ax in enumerate(axes.flat):
        idx=np.arange(0,len(y['train']),4);ax.scatter(x['train'][idx,j],y['train'][idx],s=5,alpha=.3,color='#126C8A',rasterized=True)
        ax.set(xlabel=pretty[j],ylabel='Reference stroke (mm)');panel(ax,chr(97+j))
    fig.tight_layout();save(fig,'F03','Univariate projections of the response against the six training inputs. Each panel uses the same 1,200 rows, selected as every fourth row of the 4,800-row training partition.','Methods')
    # 04 Correlation.
    values=np.column_stack([x['train'],y['train']]);corr=np.corrcoef(values,rowvar=False)
    fig,ax=plt.subplots(figsize=(7.1,6));im=ax.imshow(corr,vmin=-1,vmax=1,cmap='RdBu_r');ax.grid(False)
    ticks=['b','h','L','Rp','Rs','u','Stroke'];ax.set_xticks(range(7),ticks);ax.set_yticks(range(7),ticks)
    for i in range(7):
        for j in range(7):ax.text(j,i,f'{corr[i,j]:.2f}',ha='center',va='center',color='white' if abs(corr[i,j])>.6 else '#222',fontsize=11)
    fig.colorbar(im,ax=ax,label='Pearson correlation',shrink=.8);save(fig,'F04','Pearson correlations among inputs and response for all 4,800 training rows. Correlation is descriptive, not a feature-selection criterion.','Methods')
    # 05 Exact architecture.
    fig,ax=plt.subplots(figsize=(11,5.3));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    box(ax,.02,.43,.14,.17,'Six inputs x');box(ax,.23,.72,.21,.18,'Positive mechanics\nreference m(x)')
    basis=spec['mgre_spec'].get('basis','polynomial')
    basis_label='Cubic splines +\npairwise tensor products' if basis=='tensor_spline' else 'Standardized inputs\npolynomial basis'
    box(ax,.23,.43,.21,.18,basis_label)
    box(ax,.23,.13,.21,.18,'Dimensionless\ngating coordinates')
    box(ax,.52,.60,.22,.18,'Regularized global\nlog-residual trend g(x)')
    n=spec['mgre_spec']['n_experts'];box(ax,.52,.20,.22,.20,f'{n} Gaussian-gated\nlocal residual experts\n+ support taper t(x)')
    box(ax,.81,.43,.17,.20,'Positive output\nm(x) exp[g(x)\n+ βt(x)c(x)]','#FAEFDF')
    for a,b in [((.16,.52),(.23,.81)),((.16,.52),(.23,.52)),((.16,.52),(.23,.22)),((.44,.52),(.52,.69)),((.44,.22),(.52,.3)),((.74,.69),(.81,.55)),((.74,.30),(.81,.48))]:arrow(ax,a,b)
    ax.plot([.445,.895],[.81,.81],color='#335568',lw=1.3);arrow(ax,(.895,.81),(.895,.645))
    arrow(ax,(.63,.585),(.63,.415));ax.text(.64,.49,'Training\nresidual',fontsize=10.5,va='center')
    ax.text(.5,.025,'The gate uses input features only; training residuals fit the local correction.',ha='center',fontsize=11)
    save(fig,'F05','MGRE architecture: a positive mechanics reference, a smooth global residual trend with pairwise spline interactions, probabilistically gated local residual correction and training-support taper.','Methods')
    # 06 IID metrics.
    fig,axes=plt.subplots(2,2,figsize=(11,7));metrics=['MAE_mm','RMSE_mm','MAPE_percent','R2'];titles=['MAE (mm)','RMSE (mm)','MAPE (%)','R²']
    for j,(ax,metric,title) in enumerate(zip(axes.flat,metrics,titles)):
        vals=[s[n]['test'][metric]['mean'] for n in central];errs=[s[n]['test'][metric]['std'] for n in central]
        ax.bar(range(len(central)),vals,yerr=errs,color=[COLORS.get(n,'#888') for n in central],capsize=2);ax.set_xticks(range(len(central)),[label[n] for n in central],rotation=60,ha='right');ax.set_ylabel(title);panel(ax,chr(97+j))
        if metric=='R2':ax.set_ylim(max(0,min(vals)-.015),1.002)
    fig.tight_layout();save(fig,'F06','IID performance of the nonconstant comparison methods. Bars show the mean and error bars the sample SD across three training seeds.','Results')
    # 07 Parity.
    fig,axes=plt.subplots(2,3,figsize=(11,7))
    for i,sp in enumerate(['test','ood']):
        for j,name in enumerate(['MGRE','RBF_SVR_tuned','LegacyMGRE']):
            ax=axes[i,j];p=np.mean([pred[(name,seed,sp)]['p'] for seed in [40,41,42]],axis=0);ax.scatter(y[sp],p,s=6,alpha=.3,color=COLORS[name],rasterized=True)
            mn=min(y[sp].min(),p.min());mx=max(y[sp].max(),p.max());ax.plot([mn,mx],[mn,mx],color='#555',lw=.8,ls='--')
            ax.set(xlabel='Observed stroke (mm)',ylabel='Predicted stroke (mm)',title=label[name]+(' — IID' if sp=='test' else ' — thickness shift'));panel(ax,chr(97+i*3+j))
    fig.tight_layout();save(fig,'F07','Observed-versus-predicted stroke for MGRE, tuned SVR and legacy MGRE. Points use fixed mean-across-seed predictions.','Results')
    # 08 Seeds.
    fig,axes=plt.subplots(1,3,figsize=(11,3.7))
    for j,(ax,sp,metric) in enumerate(zip(axes,['validation','test','ood'],['validation_MAE_mm','RMSE_mm','RMSE_mm'])):
        for name in ['MGRE','RBF_SVR_tuned','LegacyMGRE','MLP']:
            values=[v[metric] if sp=='validation' else v['metrics'][sp][metric] for v in r['runs'] if v['model']==name]
            ax.plot([40,41,42],values,'o-',color=COLORS[name],label=label[name],ms=4,lw=1)
        ax.set_xticks([40,41,42]);ax.set(xlabel='Training seed',ylabel='MAE (mm)' if j==0 else 'RMSE (mm)',title=['Validation','IID test','Thickness shift'][j]);panel(ax,chr(97+j))
    axes[0].legend();fig.tight_layout();save(fig,'F08','Seed-specific validation and evaluation errors; deterministic tuned SVR repeats exactly across the three seed labels.','Results')
    # 09 Paired bootstrap.
    fig,axes=plt.subplots(2,2,figsize=(10,6.5))
    for i,sp in enumerate(['test','ood']):
        for j,metric in enumerate(['MAE','RMSE']):
            ax=axes[i,j];cc=r['bootstrap'][sp];nn=list(cc);val=np.array([cc[n][f'delta_{metric}_mm'] for n in nn]);ci=np.array([cc[n][f'{metric}_CI95_mm'] for n in nn])
            ax.errorbar(val,np.arange(len(nn)),xerr=np.array([val-ci[:,0],ci[:,1]-val]),fmt='o',color='#126C8A',capsize=3);ax.axvline(0,color='#555',ls='--',lw=1)
            ax.set_yticks(range(len(nn)),[label[n] for n in nn]);ax.set(xlabel=f'MGRE − comparator Δ{metric} (mm)',title=('IID' if sp=='test' else 'Thickness shift'));panel(ax,chr(97+i*2+j))
    fig.tight_layout();save(fig,'F09','Paired differences with 95% bootstrap intervals from 1,000 row resamples using seed 43 and fixed mean-across-seed predictions. Negative differences favor MGRE.','Results')
    # 10 Learning.
    fig,axes=plt.subplots(1,2,figsize=(10,4));lc=r['learning_curves'];sizes=sorted({v['n_train'] for v in lc})
    for j,(ax,sp) in enumerate(zip(axes,['test','ood'])):
        for name in ['MGRE','RBF_SVR_tuned']:
            vv=np.array([[v[sp+'_RMSE_mm'] for v in lc if v['model']==name and v['n_train']==n] for n in sizes]);mean=vv.mean(axis=1);std=vv.std(axis=1,ddof=1)
            ax.plot(sizes,mean,'o-',label=label[name],color=COLORS[name],ms=4);ax.fill_between(sizes,mean-std,mean+std,color=COLORS[name],alpha=.15)
        ax.set(xscale='log',xlabel='Training sample count',ylabel='RMSE (mm)',title='IID test' if sp=='test' else 'Thickness shift');ax.set_xticks(sizes,[str(v) for v in sizes],rotation=35);panel(ax,chr(97+j))
    axes[0].legend();fig.tight_layout();save(fig,'F10','Learning curves on fixed nested subsets. Lines and bands show means and sample SDs over three seeds; all model settings remain frozen.','Results')
    # 11 Ablations.
    ab=['MGRE']+[n for n in r['names'] if n.startswith('No')];fig,axes=plt.subplots(1,2,figsize=(11,4.7))
    for j,(ax,sp) in enumerate(zip(axes,['test','ood'])):
        vals=[s[n][sp]['RMSE_mm']['mean'] for n in ab];err=[s[n][sp]['RMSE_mm']['std'] for n in ab]
        ax.barh(range(len(ab)),vals,xerr=err,color=['#126C8A']+['#91ABB5']*(len(ab)-1),capsize=2);ax.set_yticks(range(len(ab)),[label[n] for n in ab]);ax.invert_yaxis();ax.set(xlabel='RMSE (mm)',title='IID test' if sp=='test' else 'Thickness shift');panel(ax,chr(97+j))
    fig.tight_layout();save(fig,'F11','Removal experiments for the selected MGRE modules. Every variant retains the full-model hyperparameters; no ablation is retuned.','Results')
    # 12 Support.
    model=joblib.load(ROOT/'models'/'MGRE_seed40.joblib')['model'];fig,axes=plt.subplots(1,3,figsize=(11,3.7))
    for sp,col,name in [('test','#126C8A','IID'),('ood','#E48B37','Thickness shift')]:
        ref,trend,local,taper,probs=model.components(x[sp]);outside=np.maximum(model.bounds_min_-x[sp],0)+np.maximum(x[sp]-model.bounds_max_,0);distance=np.sqrt(np.sum((outside/model.bounds_range_)**2,axis=1))
        axes[0].scatter(distance,taper,s=5,alpha=.35,color=col,label=name);axes[1].scatter(x[sp][:,1],local,s=5,alpha=.3,color=col);axes[2].hist(probs.max(axis=1),bins=25,density=True,histtype='step',lw=1.3,color=col)
    axes[0].set(xlabel='Normalized distance beyond\ntraining bounds',ylabel='Local-correction taper');axes[1].set(xlabel='Thickness (mm)',ylabel='Gated local log-residual\ncorrection');axes[2].set(xlabel='Largest Gaussian\nresponsibility',ylabel='Density');axes[0].legend()
    for j,ax in enumerate(axes):panel(ax,chr(97+j))
    fig.tight_layout();save(fig,'F12','Seed40 support and gate diagnostics: attenuation beyond training bounds, local residual corrections and maximum Gaussian responsibilities.','Results')
    # 13 Derivatives.
    ss=load('analysis/sensitivities.json');fig,axes=plt.subplots(1,3,figsize=(11,4))
    for j,(ax,name) in enumerate(zip(axes,['MGRE','RBF_SVR_tuned','LegacyMGRE'])):
        vv=[v for v in ss if v['model']==name];median=np.array([v['median_derivative_mm_per_mm'] for v in vv]);lo=np.array([v['p10'] for v in vv]);hi=np.array([v['p90'] for v in vv]);ax.errorbar(median,range(6),xerr=np.array([median-lo,hi-median]),fmt='o',color=COLORS[name],capsize=3)
        ax.set_yticks(range(6),['b','h','L','Rp','Rs','u']);ax.axvline(0,color='#555',lw=.8,ls='--');ax.set(xlabel='Local derivative (mm/mm)',title=label[name]);panel(ax,chr(97+j))
    fig.tight_layout();save(fig,'F13','Median local prediction derivatives with 10th–90th percentile ranges at 300 fixed validation inputs. These responses are descriptive sensitivities, not causal effects.','Results')
    # 14 OOD and intervals.
    compare=['MGRE','RBF_SVR_tuned','LegacyMGRE','PolynomialRidge','MLP','HGB'];fig,axes=plt.subplots(2,2,figsize=(10.5,7));mm=['RMSE_mm','coverage_90','mean_interval_width_mm','interval_score_90_mm'];titles=['RMSE (mm)','Coverage (%)','Interval width (mm)','Interval score (mm)']
    for j,(ax,metric,title) in enumerate(zip(axes.flat,mm,titles)):
        for k,sp in enumerate(['test','ood']):
            v=np.array([s[n][sp][metric]['mean'] for n in compare])*(100 if metric=='coverage_90' else 1)
            ax.bar(np.arange(len(compare))+(k-.5)*.35,v,width=.35,color='#126C8A' if k==0 else '#E48B37',label='IID' if k==0 else 'Thickness shift')
        if metric=='coverage_90':ax.axhline(90,ls='--',lw=1,color='#555')
        ax.set_xticks(range(len(compare)),[label[n] for n in compare],rotation=60,ha='right');ax.set_ylabel(title);panel(ax,chr(97+j))
    axes[0,0].legend();fig.tight_layout();save(fig,'F14','Predictive error and interval behavior in IID and shifted evaluation. The dashed line marks nominal 90% coverage; lower interval score jointly rewards sharpness and penalizes misses.','Results')
    # 15 Concrete intervals.
    fig,axes=plt.subplots(2,2,figsize=(11,6.5))
    for i,sp in enumerate(['test','ood']):
        order=np.argsort(y[sp]);ii=order[np.linspace(0,len(order)-1,100).astype(int)]
        for j,name in enumerate(['MGRE','RBF_SVR_tuned']):
            ax=axes[i,j];v=pred[(name,40,sp)];ax.fill_between(range(100),v['lo'][ii],v['hi'][ii],color=COLORS[name],alpha=.25,label='90% interval');ax.scatter(range(100),y[sp][ii],s=7,color='#222',label='Observed');ax.plot(range(100),v['p'][ii],color=COLORS[name],lw=.8,label='Predicted')
            ax.set(xlabel='Fixed sample, ordered by observed stroke',ylabel='Stroke (mm)',title=label[name]+(' — IID' if sp=='test' else ' — thickness shift'));panel(ax,chr(97+i*2+j))
    axes[0,0].legend(loc='upper left');fig.tight_layout();save(fig,'F15','Seed40 prediction intervals for 100 evenly spaced order statistics from each final partition. Ordering is for visualization only.','Results')
    # 16 Binned coverage.
    fig,axes=plt.subplots(2,2,figsize=(10,6.5))
    for i,sp in enumerate(['test','ood']):
        h=x[sp][:,1];bounds=np.quantile(h,[0,.25,.5,.75,1]);centers=(bounds[:-1]+bounds[1:])/2
        for name in ['MGRE','RBF_SVR_tuned','LegacyMGRE']:
            cover=[];width=[]
            for k in range(4):
                mask=(h>=bounds[k]) & ((h<bounds[k+1]) if k<3 else (h<=bounds[k+1]));c=[];w=[]
                for seed in [40,41,42]:
                    v=pred[(name,seed,sp)];c.append(np.mean((y[sp][mask]>=v['lo'][mask])&(y[sp][mask]<=v['hi'][mask]))*100);w.append(np.mean(v['hi'][mask]-v['lo'][mask]))
                cover.append(np.mean(c));width.append(np.mean(w))
            axes[i,0].plot(centers,cover,'o-',color=COLORS[name],label=label[name],ms=4);axes[i,1].plot(centers,width,'o-',color=COLORS[name],ms=4)
        axes[i,0].axhline(90,color='#555',ls='--',lw=1);axes[i,0].set_ylabel('Coverage (%)');axes[i,1].set_ylabel('Mean interval width (mm)')
        for j in range(2):axes[i,j].set(xlabel='Thickness-bin midpoint (mm)',title='IID test' if sp=='test' else 'Thickness shift');panel(axes[i,j],chr(97+i*2+j))
    axes[0,0].legend();fig.tight_layout();save(fig,'F16','Thickness-stratified interval coverage and width, averaged across training seeds. Quartiles are descriptive and do not influence model selection.','Results')
    (OUT/'figure_manifest.json').write_text(json.dumps({'figures':manifest},indent=2),encoding='utf-8')
    print(json.dumps({'figures':len(manifest),'directory':str(OUT)}))

if __name__=='__main__':build()

"""Export manuscript-ready tables from the executed revision, never stored prose."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
R=load(ROOT/'analysis/results.json')
D=load(ROOT/'data/dataset.json')
S=R['model_summaries'];F=D['metadata']['features'];Y=D['metadata']['target']
BEST=R['metadata']['best_baseline_by_validation']
LABEL={'Mean':'Training mean','Ridge':'Ridge regression','RBF_SVR':'RBF SVR',
 'RandomForest':'Random forest','HGB':'Histogram gradient boosting','MLP':'Multilayer perceptron',
 'MGRE':'MGRE full','NoMechanics':'No mechanics representation','NoRatioPredictor':'No predictor ratios',
 'NoResidualPrior':'No residual prior','NoGate':'No GMM gate','NoGlobal':'No global branch',
 'NoLocal':'No local branch','ConstantInterval':'Constant interval scale'}
TABLES=[]
def ms(v,n=4,scale=1):
    m,s=v['mean']*scale,v['std']*scale
    return f'{m:.{n}f} ± {s:.{n}f}' if s>10**(-n)/2 else f'{m:.{n}f}'
def t(id,caption,headers,rows):
    TABLES.append(dict(id=id,caption=caption,headers=headers,rows=rows))
def values(split,key):return np.asarray([r[key] for r in D['rows'] if r['split']==split],float)
def first(name,split):
    return next(r for r in R['seed_results'] if r['model']==name and r['seed']==40)['predictions'][split]
def mean(name,key,split='iid'):return S[name][split][key]['mean']

rows=[]
for sym,name,k in zip(['b','h','L','Rp','Rs','u'],['Width','Thickness','Correction span','Punch radius','Support radius','Peak pre-bend stroke'],F):
    a,b=D['metadata']['in_domain_bounds'][k];c,e=D['metadata']['ood_bounds'][k]
    rows.append([sym,name,f'{a:g}–{b:g}',f'{c:g}–{e:g}','mm'])
t('Table 1','Declared six-input design supports.', ['Symbol','Input','Reference domain','Thickness-shift group','Unit'],rows)
rows=[]
for name in ['Mean','Ridge','RBF_SVR','RandomForest','HGB','MLP','MGRE']:
    s=S[name]['iid']
    rows.append([LABEL[name],ms(s['MAE_mm']),ms(s['RMSE_mm']),ms(s['R2'],5),ms(s['coverage_90'],2,100),ms(s['mean_interval_width_mm'])])
t('Table 2','Reference-domain performance: mean across training seeds 40, 41 and 42; ± denotes sample standard deviation.',
 ['Model','MAE mm','RMSE mm','R²','C90 %','W90 mm'],rows)
rows=[]
for split in ['train','validation','calibration','test','ood']:
    a=values(split,Y);h=values(split,'thickness_mm')
    rows.append([split,len(a),f'{h.min():.3f}–{h.max():.3f}',f'{a.mean():.4f} ± {a.std(ddof=1):.4f}',f'{a.min():.4f}–{a.max():.4f}'])
t('Supplementary Table S2','Partition counts and empirical ranges.', ['Partition','Rows','Thickness mm','Label mean ± SD mm','Label range mm'],rows)
rows=[]
for k,name in zip(F+[Y],['Width','Thickness','Span','Punch radius','Support radius','Prebend stroke','Reference label']):
    a=np.asarray([r[k] for r in D['rows']],float);q=np.quantile(a,[.05,.5,.95])
    rows.append([name,f'{a.mean():.4f}',f'{a.std(ddof=1):.4f}',f'{a.min():.4f}–{a.max():.4f}',f'{q[0]:.4f} / {q[1]:.4f} / {q[2]:.4f}'])
t('Supplementary Table S3','Descriptive statistics for all 9,000 supplied rows (mm).', ['Variable','Mean','SD','Min–max','P5 / P50 / P95'],rows)
rows=[]
for name in ['Mean','Ridge','RBF_SVR','RandomForest','HGB','MLP']:
    v=min(R['hyperparameter_selection'][name],key=lambda z:z['validation_MAE_mm'])
    cfg='Training target mean' if not v['parameters'] else '; '.join(str(k)+'='+str(v) for k,v in v['parameters'].items())
    rows.append([LABEL[name],cfg,f'{S[name]["validation_MAE_mm"]["mean"]:.6f}'])
rows.append(['MGRE','3 local HGB + global RBF SVR; validation blend',f'{S["MGRE"]["validation_MAE_mm"]["mean"]:.6f}'])
t('Supplementary Table S4','Seed-40 hyperparameter grid selections and three-seed mean validation error.', ['Family','Selected setting','Final mean VAL MAE mm'],rows)
components=['MGRE','NoRatioPredictor','NoResidualPrior','NoMechanics','NoGate','NoGlobal','NoLocal','ConstantInterval']
rows=[[LABEL[n],f'{S[n]["validation_MAE_mm"]["mean"]:.6f}',ms(S[n]['iid']['MAE_mm']),ms(S[n]['iid']['RMSE_mm']),f'{mean(n,"RMSE_mm")-mean("MGRE","RMSE_mm"):+.5f}'] for n in components]
t('Supplementary Table S5','Full ensemble and seven ablations; three-seed mean metrics.', ['Configuration','VAL MAE mm','Eval MAE mm','Eval RMSE mm','ΔRMSE mm'],rows)
rows=[[LABEL[n],f'{mean(n,"MAE_mm","ood"):.4f}',f'{mean(n,"RMSE_mm","ood"):.4f}',f'{mean(n,"R2","ood"):.5f}',f'{100*mean(n,"coverage_90","ood"):.2f}',f'{mean(n,"mean_interval_width_mm","ood"):.4f}'] for n in S]
t('Supplementary Table S6','All configurations on the fixed thickness-shift partition.', ['Configuration','MAE mm','RMSE mm','R²','C90 %','W90 mm'],rows)
rows=[]
for size in sorted({c['n_train'] for c in R['learning_curves']}):
    vals=[]
    for name in ['MGRE',BEST]:
        c=[x for x in R['learning_curves'] if x['model']==name and x['n_train']==size]
        vals += [f'{np.mean([x[k] for x in c]):.5f}' for k in ['test_MAE_mm','test_RMSE_mm']]
    rows.append([size,*vals])
t('Supplementary Table S7','Learning curves on nested training subsets, averaged across seeds 40, 41 and 42.', ['Training rows','MGRE MAE mm','MGRE RMSE mm',LABEL[BEST]+' MAE mm',LABEL[BEST]+' RMSE mm'],rows)
rows=[]
for split in ['test','ood']:
    for name in ['MGRE',BEST,'ConstantInterval']:
        p=first(name,split);y=np.asarray(p['y_true']);yp=np.asarray(p['y_pred']);e=yp-y
        lower=np.asarray(p['lower']);upper=np.asarray(p['upper'])
        rows.append([split,LABEL[name],f'{100*np.mean((y>=lower)&(y<=upper)):.2f}',f'{np.mean(upper-lower):.4f}',f'{e.mean():+.5f}',f'{np.quantile(abs(e),.95):.5f}'])
t('Supplementary Table S8','Seed-40 interval and tail-error diagnostics.', ['Subset','Predictor','C90 %','W90 mm','Bias mm','P95 |error| mm'],rows)
rows=[]
for split,b in R['paired_bootstrap'].items():
    for key in ['MAE','RMSE']:
        ci=b[key+'_delta_95CI_mm'];rows.append([split,key,f'{b[key+"_delta_mm"]:+.6f}',f'[{ci[0]:.6f}, {ci[1]:.6f}]'])
t('Supplementary Table S9','Paired row bootstrap of fixed mean-across-seed predictions; 1,000 resamples, seed 43.', ['Subset','Metric','MGRE minus baseline mm','Conditional 95% interval mm'],rows)
rows=[[k,str(v)] for k,v in R['metadata']['versions'].items()]
rows += [['Training seeds','40 / 41 / 42'],['CAL rank / bootstrap','901 / 1,000 resamples; seed 43'],['Saved model bundles',str(len(R['seed_results']))],['Runtime (seconds)',f'{R["runtime_seconds"]:.1f}'],['Replay','experiment_validation.json'],['NoRatio isolation','Same prior and gate; predictor dimension 12 → 6'],['Solver / physical validation','No solver invoked; native FE provenance pending']]
t('Supplementary Table S10','Computational environment and executed revision settings.', ['Component','Recorded version or check'],rows)
rows=[]
for split,edges in [('test',[7,7.5,8,8.5,9]),('ood',[9.25,9.625,10])]:
    h=values(split,'thickness_mm')
    for j,(lo,hi) in enumerate(zip(edges[:-1],edges[1:])):
        mask=(h>=lo)&(h<hi if j<len(edges)-2 else h<=hi);v=[]
        for name in ['MGRE',BEST]:
            p=first(name,split);err=np.asarray(p['y_pred'])-np.asarray(p['y_true']);v.append(f'{np.sqrt(np.mean(err[mask]**2)):.5f}')
        rows.append([split,f'{lo:g}–{hi:g}',int(mask.sum()),*v])
t('Supplementary Table S11','Seed-40 thickness-bin errors.', ['Subset','Thickness bin','Rows','MGRE RMSE mm',LABEL[BEST]+' RMSE mm'],rows)
y=values('train',Y)
rows=[[k,f'{np.corrcoef(values("train",k),y)[0,1]:+.5f}',f'{spearmanr(values("train",k),y).statistic:+.5f}'] for k in F]
t('Supplementary Table S12','Training-row linear and rank association with the supplied target.', ['Recorded input','Pearson r','Spearman ρ'],rows)

display={2:2,3:3,4:5,5:7,6:10,7:8,8:9,9:6,10:15,11:11,12:4}
for tab in TABLES:
    tab['source_stable_id']=tab['id']
    if tab['id'].startswith('Supplementary Table S'):
        number=int(tab['id'].split('S')[-1])
        tab['id']='Supplementary Table S'+str(display[number])
static=load(ROOT/'data/retained_protocol_tables.json')
TABLES.extend(static['tables'])
TABLES.sort(key=lambda z:(z['id'].startswith('Supplementary'),int(z['id'].split()[-1].replace('S',''))))
for tab in TABLES:
    tab['widths']=static['table_widths'][tab['id']]
out=ROOT/'tables';out.mkdir(exist_ok=True)
for tab in TABLES:
    with (out/(tab['id'].replace(' ','_')+'.csv')).open('w',encoding='utf-8-sig',newline='') as fh:
        w=csv.writer(fh);w.writerow(tab['headers']);w.writerows(tab['rows'])
payload=dict(training_seeds=R['metadata']['training_seeds'],bootstrap_seed=R['metadata']['paired_bootstrap_seed'],source_results_sha256=hashlib.sha256((ROOT/'analysis/results.json').read_bytes()).hexdigest(),tables=TABLES)
(ROOT/'analysis/revision_tables.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')

# Public CSV contains only declared source identifiers/assignments and six inputs + label.
with (ROOT/'data/straightening_dataset.csv').open('w',encoding='utf-8',newline='') as fh:
    fields=['sample_id','group_id','split']+F+[Y]
    w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in D['rows'])
dictionary=dict(features=F,target=Y,unit='mm',splits=R['metadata']['split_counts'],row_count=len(D['rows']),data_origin=D['metadata']['data_origin'],source_workbook_sha256=D['metadata']['source_workbook']['sha256'],source_sheet='dataset',source_excel_columns=dict(zip(F+ [Y],list('EFGHIJK'))),source_rows=[2,9001],excluded_diagnostic_columns=['L','M'],provenance='Native FE evidence pending. Numerical values coincide with the prior analytical development table to Excel precision; not independent verified FE measurements.',canonical_json_sha256=hashlib.sha256((ROOT/'data/dataset.json').read_bytes()).hexdigest())
(ROOT/'data/data_dictionary.json').write_text(json.dumps(dictionary,indent=2),encoding='utf-8')
with (ROOT/'analysis/evaluation_predictions.csv').open('w',encoding='utf-8',newline='') as fh:
    fields=['model','training_seed','split','sample_id','reference_stroke_mm','prediction_mm','lower_90_mm','upper_90_mm']
    w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
    for run in R['seed_results']:
        for split,p in run['predictions'].items():
            for i,sid in enumerate(p['sample_ids']):
                w.writerow(dict(model=run['model'],training_seed=run['seed'],split=split,sample_id=sid,reference_stroke_mm=p['y_true'][i],prediction_mm=p['y_pred'][i],lower_90_mm=p['lower'][i],upper_90_mm=p['upper'][i]))
with (ROOT/'analysis/model_metrics.csv').open('w',encoding='utf-8',newline='') as fh:
    metrics=['MAE_mm','RMSE_mm','R2','coverage_90','mean_interval_width_mm']
    fields=['model','split']+[k+'_'+v for k in metrics for v in ['mean','std']]
    w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
    for model,s in R['model_summaries'].items():
        for split in ['iid','ood']:
            row=dict(model=model,split=split)
            row.update({k+'_'+v:s[split][k][v] for k in metrics for v in ['mean','std']})
            w.writerow(row)
manuscript_metrics=dict(training_seeds=R['metadata']['training_seeds'],bootstrap_seed=R['metadata']['paired_bootstrap_seed'],family_selected=R['metadata']['family_selected_by_validation'],model_summaries=R['model_summaries'],paired_bootstrap=R['paired_bootstrap'],learning_curve_means=[])
for size in sorted({c['n_train'] for c in R['learning_curves']}):
    for model in ['MGRE',BEST]:
        c=[x for x in R['learning_curves'] if x['model']==model and x['n_train']==size]
        manuscript_metrics['learning_curve_means'].append(dict(n_train=size,model=model,MAE_mm=float(np.mean([x['test_MAE_mm'] for x in c])),RMSE_mm=float(np.mean([x['test_RMSE_mm'] for x in c]))))
(ROOT/'analysis/manuscript_metrics.json').write_text(json.dumps(manuscript_metrics,indent=2),encoding='utf-8')
print(json.dumps(dict(tables=len(TABLES),output=str(ROOT/'analysis/revision_tables.json'),csv_rows=len(D['rows']))))

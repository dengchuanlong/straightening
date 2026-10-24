"""Build editable manuscript tables from unrounded, frozen-revision results."""
import csv,json,hashlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def display(x,d=4):
    if isinstance(x,(float,np.floating)):return f'{x:.{d}f}'
    return str(x)
def pm(v,d=4):return f'{v["mean"]:.{d}f} ± {v["std"]:.{d}f}'

def build():
    r=load('analysis/revision_results.json');spec=load('analysis/development_frozen_spec.json');protocol=load('analysis/evaluation_frozen_protocol.json')
    data=load('data/dataset.json'); md=data['metadata'];rows=data['rows'];fs=md['features'];target=md['target'];names=r['names'];labels=r['model_labels'];s=r['summary']
    tables=[]
    def add(id,title,section,columns,rows,note=''):
        tables.append({'id':id,'title':title,'section':section,'columns':columns,'rows':rows,'note':note})
    add('T01','Input variables and response in the supplied workbook','Methods',
        ['Variable','Role','Unit','Minimum','Maximum','Mean ± SD'],
        [[f,'Input' if f in fs else 'Response','mm',display(min(v[f] for v in rows)),display(max(v[f] for v in rows)),
          pm({'mean':np.mean([v[f] for v in rows]),'std':np.std([v[f] for v in rows],ddof=1)})] for f in fs+[target]],
        'Only the six declared inputs enter prediction. Diagnostic columns are excluded.')
    splitrows=[]
    for split in ['train','validation','calibration','test','ood']:
        rr=[v for v in rows if v['split']==split];h=[v['thickness_mm'] for v in rr];y=[v[target] for v in rr]
        splitrows.append([split,len(rr),f'{min(h):.3f}–{max(h):.3f}',f'{min(y):.3f}–{max(y):.3f}',
            {'train':'Coefficient fitting','validation':'Selection and interval-scale fitting','calibration':'Conformal quantile','test':'IID evaluation','ood':'Thickness-shift evaluation'}[split]])
    add('T02','Fixed data partitions and their roles','Methods',['Partition','n','Thickness (mm)','Stroke (mm)','Role'],splitrows,
        'These inherited partitions were inspected in preceding work; the present revision is exploratory.')
    add('T03','Normalization and evaluation configuration','Methods',['Item','Value'],[
        ['Elastic reference (MPa)',spec['material'][0]],['Yield reference (MPa)',spec['material'][1]],
        ['Training seeds','40, 41, 42'],['Bootstrap seed','43'],['Bootstrap replicates','1,000'],
        ['Conformal nominal coverage','90%'],['Calibration rank','901 of 1,000'],['Scale floor (mm)','0.015'],
        ['Features','Six geometric/loading variables'],['Target','Straightening stroke (mm)'],
        ['Learning-curve sizes',', '.join(map(str,protocol['learning_curve_sizes']))]],
        'The fixed material constants set the mechanics reference scale; they are not tuned by evaluation outcomes.')
    add('T04','Frozen MGRE settings','Methods',['Setting','Value'],[[k,str(v)] for k,v in spec['mgre_spec'].items()]+[
        ['Ablation policy',spec['ablation_policy']],['Primary selection','Validation MAE'],['Tie-break','Validation RMSE']],
        'All selections are frozen before this revision\'s final evaluation.')
    search=load('analysis/development_search.json')
    candidates=[]
    for key,val in search.items():
        if isinstance(val,list) and val and isinstance(val[0],dict) and 'validation_MAE_mm' in val[0]:
            best=min(val,key=lambda x:x['validation_MAE_mm'])
            candidates.append([key.replace('_',' '),len(val),display(best['validation_MAE_mm'],6),display(best['validation_RMSE_mm'],6)])
    candidates.extend([[name,len([x for x in protocol['baseline_validation_search'] if x['model']==name]),
        display(min(x['validation_MAE_mm'] for x in protocol['baseline_validation_search'] if x['model']==name),6),
        display(min([x for x in protocol['baseline_validation_search'] if x['model']==name],key=lambda x:x['validation_MAE_mm'])['validation_RMSE_mm'],6)] for name in protocol['baseline_specs']])
    add('T05','Declared validation searches','Methods',['Candidate family','Validation scores','Best MAE (mm)','Corresponding RMSE (mm)'],candidates,
        'Shared-fit shrinkage choices count as separate validation scores. Search budgets are reported rather than assumed equal.')
    descriptions={
        'Mean':'Training-response mean',
        'Ridge':'Standardized six inputs; '+json.dumps(protocol['baseline_specs']['Ridge']),
        'PolynomialRidge':'Direct target; '+json.dumps(protocol['baseline_specs']['PolynomialRidge'],sort_keys=True),
        'RandomForest':'160 trees; all input features; '+json.dumps(protocol['baseline_specs']['RandomForest']),
        'HGB':'260 iterations; learning rate 0.06; min leaf 20; L2=1; '+json.dumps(protocol['baseline_specs']['HGB']),
        'MLP':'64–32 tanh units; learning rate 0.003; max 350 iterations; internal early stopping; '+json.dumps(protocol['baseline_specs']['MLP'])}
    configs=[[labels.get(name,name),descriptions[name],pm(s[name]['validation_MAE_mm'],6)] for name,params in protocol['baseline_specs'].items()]
    mg=spec['mgre_spec']
    mg_description=f"Pairwise cubic splines: {mg.get('knots',4)} knots, ridge {mg['ridge']}; {mg['n_experts']} Gaussian-gated degree-{mg['local_degree']} ridge-{mg['local_ridge']} residual experts; beta={mg['correction_weight']}; exp(-4d) support taper"
    configs += [['Tuned RBF-SVR',json.dumps(spec['tuned_svr_spec'],sort_keys=True),pm(s['RBF_SVR_tuned']['validation_MAE_mm'],6)],
                ['Legacy MGRE','Three full-covariance Gaussian components; HGB local experts; global SVR; validation blend per seed',pm(s['LegacyMGRE']['validation_MAE_mm'],6)],
                ['MGRE',mg_description,pm(s['MGRE']['validation_MAE_mm'],6)],
                ['Common interval estimator',protocol['interval_method']['scale_model'],'—']]
    add('T06','Comparison methods and selected settings','Methods',['Method','Configuration','Validation MAE (mm)'],configs,
        'Validation MAE is mean ± sample SD across seeds. All models share the same input columns, train/validation/calibration partitions and normalized split-conformal construction.')
    full=[n for n in names if not n.startswith('No')]
    for split,id,title in [('test','T07','IID predictive accuracy'),('ood','T08','Predictive accuracy under thickness shift')]:
        add(id,title,'Results',['Model','MAE (mm)','RMSE (mm)','MAPE (%)','R²','P95 error (mm)','Max. error (mm)'],
            [[labels.get(n,n)]+[pm(s[n][split][metric],4 if metric!='MAPE_percent' else 3) for metric in ['MAE_mm','RMSE_mm','MAPE_percent','R2','P95_absolute_error_mm','max_absolute_error_mm']] for n in full],
            'Mean ± sample SD across training seeds 40, 41 and 42; deterministic methods repeat exactly.')
    ab=['MGRE']+[n for n in names if n.startswith('No')]
    add('T09','Module removal experiments','Results',['Variant','IID MAE (mm)','IID RMSE (mm)','OOD MAE (mm)','OOD RMSE (mm)'],
        [[labels.get(n,n)]+[pm(s[n][sp][m]) for sp,m in [('test','MAE_mm'),('test','RMSE_mm'),('ood','MAE_mm'),('ood','RMSE_mm')]] for n in ab],
        'Ablations retain the full-model selected hyperparameters and remove their named component without retuning.')
    add('T10','Prediction-interval calibration and efficiency','Results',['Model','Split','Coverage (%)','Width (mm)','Interval score (mm)'],
        [[labels.get(n,n),'IID' if sp=='test' else 'OOD',pm({'mean':100*s[n][sp]['coverage_90']['mean'],'std':100*s[n][sp]['coverage_90']['std']},2),
          pm(s[n][sp]['mean_interval_width_mm']),pm(s[n][sp]['interval_score_90_mm'])] for sp in ['test','ood'] for n in ['MGRE','LegacyMGRE','RBF_SVR_tuned','PolynomialRidge','MLP','HGB']],
        'Nominal coverage is 90%; coverage closer to the target, narrower intervals at comparable coverage, and lower interval score are preferable. OOD exchangeability is not assumed.')
    add('T11','Seed-level outcomes for the central comparison','Results',['Model','Seed','Validation MAE','IID RMSE','OOD RMSE','Calibration q'],
        [[labels.get(v['model'],v['model']),v['seed'],display(v['validation_MAE_mm'],6),display(v['metrics']['test']['RMSE_mm'],6),
          display(v['metrics']['ood']['RMSE_mm'],6),display(v['conformal_q'],6)] for v in r['runs'] if v['model'] in ['MGRE','LegacyMGRE','RBF_SVR_tuned']],
        'Error columns are in mm. q is the normalized finite-sample conformal quantile.')
    add('T12','Paired bootstrap comparison of fixed mean predictions','Results',['Split','Comparator','ΔMAE (mm)','95% CI','ΔRMSE (mm)','95% CI'],
        [['IID' if sp=='test' else 'OOD',labels.get(n,n),display(v['delta_MAE_mm'],6),f"[{v['MAE_CI95_mm'][0]:.6f}, {v['MAE_CI95_mm'][1]:.6f}]",
          display(v['delta_RMSE_mm'],6),f"[{v['RMSE_CI95_mm'][0]:.6f}, {v['RMSE_CI95_mm'][1]:.6f}]"] for sp,comparators in r['bootstrap'].items() for n,v in comparators.items()],
        'Differences are MGRE minus comparator; negative values favor MGRE. Row resampling uses seed 43 and 1,000 replicates; intervals are conditional on fitted models.')
    curve=[]
    for n in ['MGRE','RBF_SVR_tuned']:
        for size in protocol['learning_curve_sizes']:
            vv=[v for v in r['learning_curves'] if v['model']==n and v['n_train']==size]
            curve.append([labels[n],size]+[pm({'mean':np.mean([v[m] for v in vv]),'std':np.std([v[m] for v in vv],ddof=1)}) for m in ['test_MAE_mm','test_RMSE_mm','ood_RMSE_mm']])
    add('T13','Fixed-setting learning curves','Results',['Model','Training n','IID MAE (mm)','IID RMSE (mm)','OOD RMSE (mm)'],curve,
        'Nested subset-order seeds are 740, 741 and 742, corresponding to training seeds 40, 41 and 42. Full-data selected settings remain fixed; no learning-curve outcome selects a model.')
    with (ROOT/'analysis'/'predictions.csv').open(newline='',encoding='utf-8') as f:preds=list(csv.DictReader(f))
    indexes={v['sample_id']:v for v in rows};groups=[]
    for sp in ['test','ood']:
        current=[v for v in rows if v['split']==sp];hs=np.array([v['thickness_mm'] for v in current]);bounds=np.quantile(hs,[0,.25,.5,.75,1])
        for k in range(4):
            ids={v['sample_id'] for v in current if bounds[k]<=v['thickness_mm'] and (v['thickness_mm']<bounds[k+1] or k==3)}
            rec=['IID' if sp=='test' else 'OOD',f'{bounds[k]:.3f}–{bounds[k+1]:.3f}',len(ids)]
            for name in ['MGRE','RBF_SVR_tuned','LegacyMGRE']:
                mm=[]
                for seed in [40,41,42]:
                    pp=[v for v in preds if v['model']==name and int(v['seed'])==seed and v['sample_id'] in ids]
                    mm.append(np.mean([abs(float(v['observed_stroke_mm'])-float(v['predicted_stroke_mm'])) for v in pp]))
                rec.append(pm({'mean':np.mean(mm),'std':np.std(mm,ddof=1)}))
            groups.append(rec)
    add('T14','Thickness-stratified absolute errors','Results',['Split','Thickness (mm)','n','MGRE MAE','SVR MAE','Legacy MAE'],groups,
        'Quartile boundaries are descriptive only and do not tune any model; MAE is in mm.')
    sens=load('analysis/sensitivities.json')
    add('T15','Local sensitivity of predicted stroke','Results',['Model','Input','Median derivative','10th percentile','90th percentile'],
        [[labels[v['model']],v['feature'],display(v['median_derivative_mm_per_mm']),display(v['p10']),display(v['p90'])] for v in sens],
        'Central differences at 300 fixed validation inputs, seed40 model; step is 0.1% of training feature range. Derivative unit is mm/mm. These are model responses, not causal effects.')
    add('T16','Computational cost on the recorded environment','Results',['Method','Fit time (s)','IID inference /1,000 (s)','OOD inference /1,000 (s)'],
        [[labels.get(n,n),pm(s[n]['training_seconds'],3),pm(s[n]['test']['inference_seconds_1000'],5),pm(s[n]['ood']['inference_seconds_1000'],5)] for n in full],
        'Single-thread wall time is environment-dependent. Fit time excludes prior validation search and conformal-scale fitting.')
    add('T17','Reproduction record','Methods',['Item','Recorded value'],[
        ['Dataset SHA-256',r['data_sha256']],['Development specification SHA-256',r['development_sha256']],
        ['Evaluation protocol SHA-256',r['protocol_sha256']],['Model-seed bundles',len(r['runs'])],
        ['Learning-curve fits',len(r['learning_curves'])],['Evaluation rows per split','1,000'],
        ['Run elapsed seconds',display(r['elapsed_seconds'],2)],
        ['Numerical threads',r['hardware']['numerical_threads']],['Logical CPUs',r['hardware']['logical_cpus']],
        *[[k,v] for k,v in r['versions'].items()]],'Full precision predictions and executable analysis scripts accompany the manuscript.')
    path=ROOT/'tables';path.mkdir(exist_ok=True)
    for table in tables:
        with (path/f"{table['id']}.csv").open('w',newline='',encoding='utf-8-sig') as stream:
            w=csv.writer(stream);w.writerow(table['columns']);w.writerows(table['rows'])
    (ROOT/'analysis'/'revision_tables.json').write_text(json.dumps({'tables':tables},indent=2,allow_nan=False),encoding='utf-8')
    (ROOT/'analysis'/'manuscript_metrics.json').write_text(json.dumps({k:r[k] for k in ['summary','bootstrap','names','model_labels','seeds','bootstrap_seed','versions','elapsed_seconds']},indent=2),encoding='utf-8')
    print(json.dumps({'tables':len(tables),'path':str(path)}))

if __name__=='__main__':build()

"""Reproduce the frozen MGRE revision without fitting on calibration/test/OOD labels.

Use the bundled final development freeze, or rerun enhanced_mgre.py followed by
development_splines.py, development_svr_extension.py and development_finalize.py.
Prior partition outcomes were already examined: this is exploratory replication.
"""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(_key,'1')
import argparse, hashlib, json, platform, time, warnings
from pathlib import Path
import numpy as np
import scipy, sklearn, joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, FunctionTransformer
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
import legacy_benchmark as old
from enhanced_mgre import SmoothMGRE, load_development_data

SEEDS=[40,41,42]
BOOTSTRAP_SEED=43
SIZES=[100,250,500,1000,2000,4800]
BASELINES=['Mean','Ridge','PolynomialRidge','RandomForest','HGB','MLP']
LABELS={'MGRE':'MGRE','LegacyMGRE':'Legacy MGRE','RBF_SVR_tuned':'Tuned RBF-SVR',
        'NoMechanics':'Without mechanics','NoRatioPredictor':'Raw predictors',
        'NoResidualPrior':'Without residual prior','NoGate':'Single local expert',
        'NoLocal':'Global trend only','NoSupportTaper':'Without support taper','NoSplineInteractions':'Additive spline trend',
        'RandomForest':'Random forest','HGB':'Gradient boosting','MLP':'MLP',
        'Ridge':'Ridge','PolynomialRidge':'Polynomial ridge','Mean':'Mean'}
GRIDS={**old.GRIDS,'PolynomialRidge':[{'degree':d,'alpha':a} for d in (2,3) for a in (.0001,.01,1.)]}

def baseline(name,params,seed):
    if name=='PolynomialRidge':
        transformer=FunctionTransformer(np.log if params.get('representation')=='log_raw' else None)
        return make_pipeline(transformer,StandardScaler(),PolynomialFeatures(degree=params['degree'],include_bias=False),Ridge(alpha=params['alpha']))
    return old.baseline(name,params,seed)

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def evaluate(y,pred,lo,hi):
    ae=np.abs(y-pred); alpha=.1
    score=hi-lo+2/alpha*(lo-y)*(y<lo)+2/alpha*(y-hi)*(y>hi)
    return {'MAE_mm':float(ae.mean()),'RMSE_mm':float(np.sqrt(np.mean((y-pred)**2))),
            'MAPE_percent':float(np.mean(ae/y)*100),'R2':float(r2_score(y,pred)),
            'max_absolute_error_mm':float(ae.max()),'P95_absolute_error_mm':float(np.quantile(ae,.95)),
            'coverage_90':float(np.mean((y>=lo)&(y<=hi))),
            'mean_interval_width_mm':float(np.mean(hi-lo)),
            'interval_score_90_mm':float(score.mean())}

def avg_std(values):
    return {'mean':float(np.mean(values)),'std':float(np.std(values,ddof=1)) if len(values)>1 else 0.}

def create_model(name,seed,frozen,baseline_specs):
    if name=='RBF_SVR_tuned': return make_pipeline(StandardScaler(),SVR(**frozen['tuned_svr_spec']))
    if name=='LegacyMGRE': return old.MGRE(seed=seed,material=tuple(frozen['material']))
    if name in BASELINES: return baseline(name,baseline_specs[name],seed)
    return SmoothMGRE(seed=seed,material=tuple(frozen['material']),variant=name,**frozen['mgre_spec'])

def freeze_remaining(data_path,out,development):
    """Only train/validation labels are converted before this full protocol freeze."""
    parts,material=load_development_data(data_path)
    xt,yt=parts['train']['x'],parts['train']['y']; xv,yv=parts['validation']['x'],parts['validation']['y']
    choices={}; search=[]
    for name in BASELINES:
        if name=='PolynomialRidge' and 'polynomial_baseline_spec' in development:
            choices[name]=development['polynomial_baseline_spec']
            development_search=json.loads((out/'analysis'/'development_search.json').read_text(encoding='utf-8'))
            for record in development_search['polynomial_candidates']:
                search.append({'model':name,'params':record['spec'],'validation_MAE_mm':record['validation_MAE_mm'],
                    'validation_RMSE_mm':record['validation_RMSE_mm'],'seconds':record.get('fit_seconds',0.)})
            continue
        for params in GRIDS[name]:
            tick=time.perf_counter()
            m=baseline(name,params,40)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',ConvergenceWarning);m.fit(xt,yt)
            p=m.predict(xv)
            rec={'model':name,'params':params,'validation_MAE_mm':float(mean_absolute_error(yv,p)),
                 'validation_RMSE_mm':float(np.sqrt(mean_squared_error(yv,p))), 'seconds':time.perf_counter()-tick}
            search.append(rec)
        choices[name]=min([r for r in search if r['model']==name],key=lambda r:(r['validation_MAE_mm'],r['validation_RMSE_mm']))['params']
    legacy_alphas={}
    for seed in SEEDS:
        m=old.MGRE(seed=seed,material=material).fit(xt,yt).select_alpha(xv,yv)
        legacy_alphas[str(seed)]={'alpha':m.alpha_,'validation_scores':m.alpha_scores_}
    protocol={'frozen':True,'frozen_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'development_spec_sha256':sha(out/'analysis'/'development_frozen_spec.json'),
              'implementation_sha256':{name:sha(Path(__file__).parent/name) for name in ['enhanced_mgre.py','legacy_benchmark.py','run_revision.py']},
              'data_sha256':sha(data_path),'baseline_specs':choices,'baseline_validation_search':search,
              'legacy_blend_by_seed':legacy_alphas,'seeds':SEEDS,'bootstrap_seed':BOOTSTRAP_SEED,
              'bootstrap_replicates':1000,'bootstrap_comparators':['RBF_SVR_tuned','LegacyMGRE','PolynomialRidge','NoLocal','MLP','HGB'],
              'nominal_coverage':.9,'learning_curve_sizes':SIZES,'learning_subset_seed_offset':700,
              'learning_curve_selection':'Same full-data validation selections, with no retuning.',
              'evaluation_models':['Mean','Ridge','PolynomialRidge','RBF_SVR_tuned','RandomForest','HGB','MLP','LegacyMGRE','MGRE']+development['ablation_variants'],
              'interval_method':{'name':'Normalized split conformal','scale_fit_split':'validation',
                  'scale_model':'HGB absolute error, 80 iterations, 7 leaves, min_leaf45, l2=2, learning_rate=.06',
                  'scale_floor_mm':.015,'calibration_quantile_rank':901,'calibration_n':1000},
              'interval_lower_bound_mm':0.0,
              'diagnostic_columns_used':False,'final_test_or_ood_labels_accessed':False,
              'interpretation':'Previously examined partitions; exploratory revision, not independent confirmation.'}
    write_json(out/'analysis'/'evaluation_frozen_protocol.json',protocol)
    return protocol

def run(data_path,out):
    started=time.perf_counter(); analysis=out/'analysis'; models=out/'models'
    analysis.mkdir(parents=True,exist_ok=True);models.mkdir(parents=True,exist_ok=True)
    spec_path=analysis/'development_frozen_spec.json'
    if not spec_path.exists(): raise RuntimeError('Freeze development choices before evaluation.')
    frozen=json.loads(spec_path.read_text(encoding='utf-8'))
    assert frozen['test_or_calibration_used_for_selection'] is False and frozen['seeds']==SEEDS
    assert frozen.get('final_freeze_ready') is True, 'Preliminary development output cannot authorize final evaluation.'
    assert sha(Path(__file__).parent/'enhanced_mgre.py')==frozen['source_code_sha256'], 'Implementation changed after development freeze.'
    assert frozen['data_sha256']==sha(data_path), 'Development freeze belongs to a different dataset.'
    protocol=freeze_remaining(data_path,out,frozen)
    protocol_hash=sha(analysis/'evaluation_frozen_protocol.json')
    # The first full-data conversion occurs only after both freeze records exist.
    data,parts,material,checks,origin=old.validated_data(data_path)
    checks['diagnostic_columns_used']=False
    for p in parts.values():
        p.pop('clean',None);p.pop('noise_std',None)
    assert protocol['data_sha256']==sha(data_path)
    write_json(analysis/'dataset_checks.json',checks)
    names=protocol['evaluation_models']; runs=[]; predictions={}; fit_warning=[]
    xt,yt=parts['train']['x'],parts['train']['y'];xv,yv=parts['validation']['x'],parts['validation']['y']
    xc,yc=parts['calibration']['x'],parts['calibration']['y']
    for name in names:
        for seed in SEEDS:
            if name=='LegacyMGRE':old.GLOBAL_SVR_CACHE.clear()
            tick=time.perf_counter();m=create_model(name,seed,frozen,protocol['baseline_specs'])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always',ConvergenceWarning);m.fit(xt,yt)
            for w in caught: fit_warning.append({'model':name,'seed':seed,'warning':str(w.message)})
            if name=='LegacyMGRE': m.alpha_=protocol['legacy_blend_by_seed'][str(seed)]['alpha']
            training_seconds=time.perf_counter()-tick
            pv=m.predict(xv);err=np.abs(yv-pv)
            scale,floor=old.fit_scale(xv,err,seed)
            cal_scale=np.maximum(scale.predict(xc),floor)
            q,rank=old.qfinite(np.abs(yc-m.predict(xc))/cal_scale,.9)
            run={'model':name,'seed':seed,'training_seconds':training_seconds,'validation_MAE_mm':float(err.mean()),
                 'conformal_q':q,'conformal_rank':rank,'metrics':{}}
            for split in ('test','ood'):
                x,y=parts[split]['x'],parts[split]['y']; t=time.perf_counter();p=m.predict(x)
                inference=time.perf_counter()-t; radius=q*np.maximum(scale.predict(x),floor)
                lo,hi=np.maximum(0.,p-radius),p+radius
                run['metrics'][split]=evaluate(y,p,lo,hi)
                run['metrics'][split]['inference_seconds_1000']=inference*1000/len(y)
                predictions[(name,seed,split)]={'pred':p,'lower':lo,'upper':hi}
            joblib.dump({'model':m,'scale_model':scale,'scale_floor_mm':floor,'conformal_q':q,
                         'features':old.FEATURES,'seed':seed,'protocol_sha256':protocol_hash},models/f'{name}_seed{seed}.joblib',compress=3)
            runs.append(run)
            print(json.dumps({'phase':'evaluation','model':name,'seed':seed,'iid_RMSE':run['metrics']['test']['RMSE_mm'],'ood_RMSE':run['metrics']['ood']['RMSE_mm']}),flush=True)
    summaries={}
    for name in names:
        rr=[r for r in runs if r['model']==name]
        summaries[name]={'label':LABELS.get(name,name),'training_seconds':avg_std([r['training_seconds'] for r in rr]),
            'validation_MAE_mm':avg_std([r['validation_MAE_mm'] for r in rr])}
        for split in ('test','ood'):
            summaries[name][split]={k:avg_std([r['metrics'][split][k] for r in rr]) for k in rr[0]['metrics'][split]}
    write_json(analysis/'evaluation_metrics.json',{'summary':summaries,'runs':runs,'data_sha256':sha(data_path),
        'protocol_sha256':protocol_hash,'point_and_interval_evaluation_complete':True,'learning_curves_complete':False})
    # Persist every final row prediction; no rounded display value drives analysis.
    import csv
    with (analysis/'predictions.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['model','seed','split','sample_id','observed_stroke_mm','predicted_stroke_mm','lower_90_mm','upper_90_mm'])
        for (name,seed,split),p in predictions.items():
            for i,sid in enumerate(parts[split]['ids']): writer.writerow([name,seed,split,sid,parts[split]['y'][i],p['pred'][i],p['lower'][i],p['upper'][i]])
    bootstrap={}
    rng=np.random.default_rng(BOOTSTRAP_SEED)
    for split in ('test','ood'):
        y=parts[split]['y']; indexes=rng.integers(0,len(y),(1000,len(y)))
        mg=np.mean([predictions[('MGRE',seed,split)]['pred'] for seed in SEEDS],axis=0)
        bootstrap[split]={}
        for name in protocol['bootstrap_comparators']:
            comparison=np.mean([predictions[(name,seed,split)]['pred'] for seed in SEEDS],axis=0)
            ae=np.abs(y-mg);be=np.abs(y-comparison);a2=(y-mg)**2;b2=(y-comparison)**2
            dd=(ae[indexes]-be[indexes]).mean(axis=1)
            rd=np.sqrt(a2[indexes].mean(axis=1))-np.sqrt(b2[indexes].mean(axis=1))
            bootstrap[split][name]={'delta_MAE_mm':float(ae.mean()-be.mean()),'MAE_CI95_mm':np.quantile(dd,[.025,.975]).tolist(),
                'delta_RMSE_mm':float(np.sqrt(a2.mean())-np.sqrt(b2.mean())),'RMSE_CI95_mm':np.quantile(rd,[.025,.975]).tolist()}
    write_json(analysis/'bootstrap.json',{'seed':43,'replicates':1000,'fixed_mean_across_training_seed_predictions':True,'comparisons':bootstrap})
    # Fixed nested training subsets. No selection from learning-curve outcomes.
    learning=[]
    for seed in SEEDS:
        order=np.random.default_rng(seed+700).permutation(len(yt))
        for size in SIZES:
            ii=order[:size]
            for name in ('MGRE','RBF_SVR_tuned'):
                tick=time.perf_counter();m=create_model(name,seed,frozen,protocol['baseline_specs']).fit(xt[ii],yt[ii])
                row={'model':name,'seed':seed,'n_train':size,'training_seconds':time.perf_counter()-tick}
                for split in ('test','ood'):
                    p=m.predict(parts[split]['x']);y=parts[split]['y']
                    row[split+'_MAE_mm']=float(mean_absolute_error(y,p));row[split+'_RMSE_mm']=float(np.sqrt(mean_squared_error(y,p)))
                learning.append(row)
    write_json(analysis/'learning_curves.json',learning)
    # Sensitivity evaluates model derivatives at fixed validation inputs, not labels.
    sensitivities=[]
    for name in ('MGRE','RBF_SVR_tuned','LegacyMGRE'):
        m=joblib.load(models/f'{name}_seed40.joblib')['model'];x=xv[:300].copy()
        for j,feat in enumerate(old.FEATURES):
            step=(xt[:,j].max()-xt[:,j].min())*.001
            a=x.copy();b=x.copy();a[:,j]-=step;b[:,j]+=step
            derivative=(m.predict(b)-m.predict(a))/(2*step)
            sensitivities.append({'model':name,'feature':feat,'median_derivative_mm_per_mm':float(np.median(derivative)),
                                  'p10':float(np.quantile(derivative,.1)),'p90':float(np.quantile(derivative,.9))})
    write_json(analysis/'sensitivities.json',sensitivities)
    frozen_after=sha(spec_path)
    result={'protocol_sha256':protocol_hash,'development_sha256':frozen_after,'data_sha256':sha(data_path),
            'data_origin':origin,'seeds':SEEDS,'bootstrap_seed':43,'names':names,'model_labels':LABELS,
            'runs':runs,'summary':summaries,'bootstrap':bootstrap,'learning_curves':learning,
            'warnings':fit_warning,'versions':{'python':platform.python_version(),'numpy':np.__version__,
            'scipy':scipy.__version__,'scikit_learn':sklearn.__version__,'joblib':joblib.__version__},
            'hardware':{'processor':platform.processor(),'logical_cpus':os.cpu_count(),'numerical_threads':1,'platform':platform.platform()},
            'elapsed_seconds':time.perf_counter()-started,'complete':True}
    write_json(analysis/'revision_results.json',result)
    print(json.dumps({'phase':'complete','seconds':result['elapsed_seconds'],'MGRE':summaries['MGRE'],'SVR':summaries['RBF_SVR_tuned']}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,default=Path(__file__).resolve().parents[1]/'data'/'dataset.json')
    ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args()
    with threadpool_limits(limits=1): run(args.data,args.output)

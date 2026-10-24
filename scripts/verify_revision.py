"""Independent arithmetic and artifact checks for the frozen MGRE revision."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'1')
import csv,hashlib,json
from pathlib import Path
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from PIL import Image
import legacy_benchmark
from enhanced_mgre import SmoothMGRE

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    r=load('analysis/revision_results.json');protocol=load('analysis/evaluation_frozen_protocol.json');spec=load('analysis/development_frozen_spec.json');data=load('data/dataset.json')
    assert r['complete'] and protocol['frozen']
    assert r['data_sha256']==sha(ROOT/'data'/'dataset.json')==protocol['data_sha256']
    assert r['development_sha256']==sha(ROOT/'analysis'/'development_frozen_spec.json')==protocol['development_spec_sha256']
    assert r['protocol_sha256']==sha(ROOT/'analysis'/'evaluation_frozen_protocol.json')
    assert spec['test_or_calibration_used_for_selection'] is False
    assert protocol['final_test_or_ood_labels_accessed'] is False
    assert spec['seeds']==[40,41,42] and protocol['bootstrap_seed']==43
    rows={v['sample_id']:v for v in data['rows']};arrays={}
    with (ROOT/'analysis'/'predictions.csv').open(newline='',encoding='utf-8') as stream:
        for v in csv.DictReader(stream):
            source=rows[v['sample_id']];assert source['split']==v['split'];assert source['reference_stroke_mm']==float(v['observed_stroke_mm'])
            arrays.setdefault((v['model'],int(v['seed']),v['split']),[]).append([float(v[k]) for k in ['observed_stroke_mm','predicted_stroke_mm','lower_90_mm','upper_90_mm']])
    maxdiff=0.;count=0;prediction_diff=0.;interval_diff=0.;quantile_diff=0.
    xx={sp:np.array([[v[f] for f in data['metadata']['features']] for v in data['rows'] if v['split']==sp]) for sp in ['test','ood']}
    calrows=[v for v in data['rows'] if v['split']=='calibration']
    calx=np.array([[v[f] for f in data['metadata']['features']] for v in calrows]);caly=np.array([v['reference_stroke_mm'] for v in calrows])
    for run in r['runs']:
        bundle=joblib.load(ROOT/'models'/f"{run['model']}_seed{run['seed']}.joblib")
        assert bundle['seed']==run['seed'] and run['conformal_rank']==901 and len(caly)==1000
        scores=np.abs(caly-bundle['model'].predict(calx))/np.maximum(bundle['scale_model'].predict(calx),bundle['scale_floor_mm'])
        independent_q=float(np.sort(scores)[900]);quantile_diff=max(quantile_diff,abs(independent_q-bundle['conformal_q']),abs(independent_q-run['conformal_q']))
        assert quantile_diff<1e-10
        for split,metrics in run['metrics'].items():
            y,p,lo,hi=np.asarray(arrays[(run['model'],run['seed'],split)]).T
            assert len(y)==1000 and np.isfinite([y,p,lo,hi]).all() and np.all(lo<=p) and np.all(p<=hi)
            replay=bundle['model'].predict(xx[split]);radius=bundle['conformal_q']*np.maximum(bundle['scale_model'].predict(xx[split]),bundle['scale_floor_mm'])
            prediction_diff=max(prediction_diff,float(np.max(np.abs(replay-p))))
            interval_diff=max(interval_diff,float(np.max(np.abs(np.maximum(0.,replay-radius)-lo))),float(np.max(np.abs(replay+radius-hi))))
            assert prediction_diff<1e-10 and interval_diff<1e-10
            error=y-p;ae=np.abs(error);score=(hi-lo)+20*np.maximum(lo-y,0)+20*np.maximum(y-hi,0)
            independent={'MAE_mm':ae.mean(),'RMSE_mm':np.sqrt(np.mean(error**2)),'MAPE_percent':np.mean(ae/y)*100,
                'R2':1-np.sum(error**2)/np.sum((y-y.mean())**2),'max_absolute_error_mm':ae.max(),
                'P95_absolute_error_mm':np.quantile(ae,.95),'coverage_90':np.mean((y>=lo)&(y<=hi)),
                'mean_interval_width_mm':np.mean(hi-lo),'interval_score_90_mm':score.mean()}
            for name,value in independent.items():
                diff=abs(value-metrics[name]);maxdiff=max(maxdiff,diff);assert diff<1e-12,(run['model'],split,name,diff)
            count+=len(y)
    assert count==len(r['runs'])*2000 and len(r['runs'])==len(r['names'])*3
    assert len(r['learning_curves'])==36
    rng=np.random.default_rng(43);bootstrap_diff=0.
    for split in ['test','ood']:
        yy=np.array([v['reference_stroke_mm'] for v in data['rows'] if v['split']==split]);ii=rng.integers(0,len(yy),(1000,len(yy)))
        mm=np.mean([np.asarray(arrays[('MGRE',seed,split)])[:,1] for seed in [40,41,42]],axis=0)
        for name in protocol['bootstrap_comparators']:
            pp=np.mean([np.asarray(arrays[(name,seed,split)])[:,1] for seed in [40,41,42]],axis=0)
            a=np.abs(yy-mm);b=np.abs(yy-pp);a2=(yy-mm)**2;b2=(yy-pp)**2
            expected={'delta_MAE_mm':float(a.mean()-b.mean()),'MAE_CI95_mm':np.quantile((a[ii]-b[ii]).mean(axis=1),[.025,.975]),
                'delta_RMSE_mm':float(np.sqrt(a2.mean())-np.sqrt(b2.mean())),
                'RMSE_CI95_mm':np.quantile(np.sqrt(a2[ii].mean(axis=1))-np.sqrt(b2[ii].mean(axis=1)),[.025,.975])}
            for k,v in expected.items():
                dd=float(np.max(np.abs(np.asarray(v)-np.asarray(r['bootstrap'][split][name][k]))));bootstrap_diff=max(bootstrap_diff,dd);assert dd<1e-12
    fm=load('figures/figure_manifest.json')['figures'];tm=load('analysis/revision_tables.json')['tables']
    assert len(fm)==16 and len(tm)==17
    for f in fm:
        p=ROOT/'figures'/f['filename'];assert p.exists() and sha(p)==f['sha256']
        with Image.open(p) as im:assert im.width>=1000 and im.height>=500
    assert all(len(row)==len(t['columns']) for t in tm for row in t['rows'])
    result={'passed':True,'model_seed_bundles':len(r['runs']),'final_predictions_verified':count,
            'max_absolute_metric_recomputation_difference':maxdiff,'figures':len(fm),'tables':len(tm),
            'max_absolute_saved_model_prediction_difference':prediction_diff,'max_absolute_interval_replay_difference':interval_diff,
            'calibration_quantiles_recomputed':len(r['runs']),'max_absolute_conformal_quantile_difference':quantile_diff,
            'paired_bootstrap_comparators_verified':len(protocol['bootstrap_comparators']),
            'max_absolute_bootstrap_recomputation_difference':bootstrap_diff,
            'learning_fits':36,'seeds':[40,41,42],'bootstrap_seed':43,'frozen_specs_unchanged':True,
            'data_sha256':r['data_sha256'],'protocol_sha256':r['protocol_sha256'],
            'diagnostic_columns_used':False,'physical_provenance_validation':'Outside the scope of this numerical audit.'}
    (ROOT/'analysis'/'revision_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    with threadpool_limits(limits=1):verify()

"""Freeze all development choices before final benchmark label access."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,datetime,hashlib,json
from pathlib import Path
from threadpoolctl import threadpool_limits
from enhanced_mgre import SmoothMGRE,load_development_data,score,write_json

def main(data,out):
    original=json.loads((out/'development_search.json').read_text())
    spline=json.loads((out/'development_spline_search.json').read_text())
    extension=json.loads((out/'development_svr_extension.json').read_text())
    assert len(original['svr_candidates'])==36 and extension['complete'] and len(extension['candidates'])==36
    assert len(spline['spline_candidates'])==27 and len(spline['gated_candidates'])==48
    mgre_candidates=original['global_candidates']+original['gated_candidates']+spline['spline_candidates']+spline['gated_candidates']
    select=lambda rows:min(rows,key=lambda r:(r['validation_MAE_mm'],r['validation_RMSE_mm']))
    selected=select(mgre_candidates);svr=select(original['svr_candidates']+extension['candidates'])
    poly=select(spline['polynomial_baselines'])
    p,material=load_development_data(data);train=p['train'];val=p['validation']
    seed_results=[]
    for seed in (40,41,42):
        m=SmoothMGRE(seed=seed,material=material,**selected['spec']).fit(train['x'],train['y'])
        seed_results.append({'seed':seed,**score(val['y'],m.predict(val['x']))})
    assert selected['spec']['representation']=='raw'
    variants=['NoMechanics','NoResidualPrior','NoSplineInteractions','NoGate','NoLocal','NoSupportTaper']
    features=m._features(train['x']);z=m.scaler_.transform(features[1])
    descriptors={'global_basis_columns':int(m._global_basis(z).shape[1]),
        'global_ridge_coefficients_including_intercept':int(m.global_.coef_.size+1),
        'local_basis_columns':int(m.local_poly_.transform(z).shape[1]),
        'local_ridge_coefficients_including_intercepts':int(sum(e.coef_.size+1 for e in m.experts_)),
        'gate_components':len(m.experts_),'gate_dimensions':4,
        'gate_covariance_type':'full','gate_fitted_scalar_parameters':4*4+4*10+(4-1),
        'note':'Basis dimensions apply to selected six-coordinate4knotcubic tensor spline and cubic residual experts; scalers/envelope summaries are additional preprocessing statistics.'}
    unique_fit_records=(original['global_candidates']+
        [r for r in original['gated_candidates'] if r['spec']['correction_weight']==.25]+
        spline['spline_candidates']+
        [r for r in spline['gated_candidates'] if r['spec']['correction_weight']==.25]+
        original['svr_candidates']+extension['candidates']+spline['polynomial_baselines'])
    original.update({'spline_candidates':spline['spline_candidates'],'spline_gated_candidates':spline['gated_candidates'],
        'additional_svr_candidates':extension['candidates'],'polynomial_candidates':spline['polynomial_baselines'],
        'selected_mgre':selected,'selected_svr':svr,'selected_polynomial_baseline':poly,
        'fit_budget':{'MGRE_fits':75,'MGRE_validation_comparisons':138,'SVR_fits':72,'SVR_validation_comparisons':72,
                     'polynomial_baseline_fits':18,'post_selection_seed_repeats':3,
                     'adaptive_extension_reason':spline['phase_reason'],
                     'note':'The27polynomial+9gated initial fits preceded27spline+12gated refinement fits. Each gated fit has4validation correction-weight choices.'},
        'initial_search_elapsed_seconds':original['elapsed_seconds'],
        'sum_unique_candidate_fit_seconds':sum(r['fit_seconds'] for r in unique_fit_records),
        'runtime_note':'Initial and extension SVR searches ran concurrently; the fit-time sum is not wall-clock duration. The original elapsed_seconds field describes only initial development.',
        'post_selection_validation_seeds':seed_results,'final_freeze_ready':True})
    write_json(out/'development_search.json',original)
    frozen={'model_class':'enhanced_mgre.SmoothMGRE','material':material,'seeds':[40,41,42],
        'data_sha256':hashlib.sha256(Path(data).read_bytes()).hexdigest(),
        'bootstrap_seed':43,'mgre_spec':selected['spec'],'tuned_svr_spec':svr['spec'],
        'polynomial_baseline_spec':poly['spec'],'ablation_variants':variants,
        'ablation_policy':'Selected full-model parameters retained; remove only the named component without ablation-specific retuning.',
        'validation_selection':{'MGRE':selected,'RBF_SVR_tuned':svr,'PolynomialRidge':poly},
        'validation_seed_results':seed_results,'model_descriptors':descriptors,
        'fit_budget':original['fit_budget'],'consumed_development_splits':['train','validation'],
        'test_or_calibration_used_for_selection':False,
        'interpretation':'Exploratory revision of previously examined partitions, not an untouched confirmatory test.',
        'final_freeze_ready':True,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_code_sha256':hashlib.sha256((Path(__file__).parent/'enhanced_mgre.py').read_bytes()).hexdigest()}
    write_json(out/'development_frozen_spec.json',frozen)
    print(json.dumps(frozen,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    with threadpool_limits(limits=1):main(a.data,a.output)

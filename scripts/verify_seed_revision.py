"""Independently verify the requested training and fixed-prediction bootstrap seeds."""
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
R=json.loads((ROOT/'analysis/results.json').read_text(encoding='utf-8'))
assert R['metadata']['training_seeds']==[40,41,42]
assert R['metadata']['paired_bootstrap_seed']==43
assert {r['seed'] for r in R['seed_results']}=={40,41,42}
assert len(R['seed_results'])==42
assert len(R['learning_curves'])==36
assert {r['seed'] for r in R['learning_curves']}=={40,41,42}
assert R['metadata']['script_sha256']==hashlib.sha256((ROOT/'scripts/run_experiments.py').read_bytes()).hexdigest()
assert R['metadata']['data_sha256']==hashlib.sha256((ROOT/'data/dataset.json').read_bytes()).hexdigest()
best=R['metadata']['best_baseline_by_validation']
rng=np.random.default_rng(43)
checks=[]
for split in ['test','ood']:
    records={name:[r for r in R['seed_results'] if r['model']==name] for name in ['MGRE',best]}
    truth=np.asarray(records['MGRE'][0]['predictions'][split]['y_true'])
    pm={name:np.mean([r['predictions'][split]['y_pred'] for r in rs],axis=0) for name,rs in records.items()}
    em=truth-pm['MGRE'];eb=truth-pm[best]
    actual=np.array([np.abs(em).mean()-np.abs(eb).mean(),np.sqrt(np.mean(em**2))-np.sqrt(np.mean(eb**2))])
    draws=[]
    for _ in range(1000):
        ii=rng.integers(0,len(truth),len(truth))
        draws.append([np.abs(em[ii]).mean()-np.abs(eb[ii]).mean(),np.sqrt(np.mean(em[ii]**2))-np.sqrt(np.mean(eb[ii]**2))])
    ci=np.quantile(draws,[.025,.975],axis=0)
    saved=R['paired_bootstrap'][split]
    assert saved['seed']==43 and saved['n_bootstrap']==1000
    for j,metric in enumerate(['MAE','RMSE']):
        np.testing.assert_allclose(actual[j],saved[metric+'_delta_mm'],rtol=0,atol=1e-14)
        np.testing.assert_allclose(ci[:,j],saved[metric+'_delta_95CI_mm'],rtol=0,atol=1e-14)
    checks.append(dict(split=split,seed=43,bootstrap_resamples=1000,fixed_mean_across_seed_predictions=True,maximum_CI_difference=float(max(abs(ci[0,0]-saved['MAE_delta_95CI_mm'][0]),abs(ci[1,1]-saved['RMSE_delta_95CI_mm'][1])))))
out=dict(passed=True,training_seeds=[40,41,42],bootstrap_seed=43,model_seed_records=42,learning_curve_records=36,
         source_script_and_data_hashes_match=True,checks=checks,claims_scope='Reproduction of the recorded numerical benchmark, not verification of FE provenance.')
(ROOT/'analysis/seed_revision_validation.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))

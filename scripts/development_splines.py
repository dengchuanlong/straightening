"""Validation-only spline refinement after documented polynomial inadequacy."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import argparse,itertools,json,time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from sklearn.preprocessing import StandardScaler,PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from enhanced_mgre import SmoothMGRE,load_development_data,score,write_json

def main(data,out):
    parts,material=load_development_data(data)
    xt,yt=parts['train']['x'],parts['train']['y']; xv,yv=parts['validation']['x'],parts['validation']['y']
    log={'phase_reason':'Polynomial mechanics residual trends failed validation versus previously established SVR; add prespecified tensor-spline family before any final test evaluation.',
         'used_splits':['train','validation'],'spline_candidates':[],'gated_candidates':[],'polynomial_baselines':[]}
    for representation,knots,ridge in itertools.product(('raw','ratios','log_ratios'),(4,6,8),(0.0001,0.01,1.)):
        spec=dict(representation=representation,degree=3,ridge=ridge,n_experts=0,local_degree=2,
                  local_ridge=1.,correction_weight=0.,taper=True,basis='tensor_spline',knots=knots)
        tick=time.perf_counter(); m=SmoothMGRE(material=material,**spec).fit(xt,yt)
        rec={'spec':spec,**score(yv,m.predict(xv)),'fit_seconds':time.perf_counter()-tick}
        log['spline_candidates'].append(rec)
        print(json.dumps({'phase':'spline',**rec}),flush=True)
        write_json(out/'development_spline_search.json',log)
    best=min(log['spline_candidates'],key=lambda a:(a['validation_MAE_mm'],a['validation_RMSE_mm']))
    for k,d,lr in itertools.product((2,3,4),(2,3),(0.1,1.)):
        spec={**best['spec'],'n_experts':k,'local_degree':d,'local_ridge':lr,'correction_weight':1.}
        tick=time.perf_counter(); m=SmoothMGRE(material=material,**spec).fit(xt,yt)
        ref,tr,lo,taper,_=m.components(xv); elapsed=time.perf_counter()-tick
        for beta in (.25,.5,.75,1.):
            s={**spec,'correction_weight':beta}
            rec={'spec':s,**score(yv,ref*np.exp(tr+beta*taper*lo)),'fit_seconds':elapsed}
            log['gated_candidates'].append(rec); print(json.dumps({'phase':'spline_gate',**rec}),flush=True)
        write_json(out/'development_spline_search.json',log)
    for representation,degree,alpha in itertools.product(('raw','log_raw'),(2,3,4),(0.0001,0.01,1.)):
        a,b=(np.log(xt),np.log(xv)) if representation=='log_raw' else (xt,xv)
        tick=time.perf_counter(); m=make_pipeline(StandardScaler(),PolynomialFeatures(degree,include_bias=False),Ridge(alpha=alpha)).fit(a,yt)
        rec={'spec':{'representation':representation,'degree':degree,'alpha':alpha},
             **score(yv,m.predict(b)),'fit_seconds':time.perf_counter()-tick}
        log['polynomial_baselines'].append(rec); print(json.dumps({'phase':'poly_baseline',**rec}),flush=True)
    log['selected_spline']=min(log['spline_candidates']+log['gated_candidates'],key=lambda a:(a['validation_MAE_mm'],a['validation_RMSE_mm']))
    log['selected_polynomial_baseline']=min(log['polynomial_baselines'],key=lambda a:(a['validation_MAE_mm'],a['validation_RMSE_mm']))
    write_json(out/'development_spline_search.json',log)
    print(json.dumps({'phase':'spline_complete','selected':log['selected_spline'],'polybaseline':log['selected_polynomial_baseline']}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    with threadpool_limits(limits=1):main(a.data,a.output)

"""Validation-only additional SVR budget following smooth-MGRE family extension."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,itertools,json,time
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVR
from threadpoolctl import threadpool_limits
from enhanced_mgre import load_development_data,score,write_json

def main(data,out):
    p,_=load_development_data(data);xt,yt=p['train']['x'],p['train']['y'];xv,yv=p['validation']['x'],p['validation']['y']
    log={'reason':'The smooth MGRE family extension brings its fit budget to75;36 additional SVR fits bring the SVR budget to72. All alternatives are validation-only.',
         'consumed_splits':['train','validation'],'candidates':[]}
    for C,gamma,epsilon in itertools.product((16.,64.,256.),(.01,.04,.16),(.015,.025,.05,.1)):
        spec={'C':C,'gamma':gamma,'epsilon':epsilon};tick=time.perf_counter()
        model=make_pipeline(StandardScaler(),SVR(**spec)).fit(xt,yt)
        rec={'spec':spec,**score(yv,model.predict(xv)),'fit_seconds':time.perf_counter()-tick}
        log['candidates'].append(rec);write_json(out/'development_svr_extension.json',log)
        print(json.dumps(rec),flush=True)
    log['selected']=min(log['candidates'],key=lambda r:(r['validation_MAE_mm'],r['validation_RMSE_mm']))
    log['complete']=True;write_json(out/'development_svr_extension.json',log)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    with threadpool_limits(limits=1):main(a.data,a.output)

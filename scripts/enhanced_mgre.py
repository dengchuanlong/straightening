"""Smooth mechanics-guided residual experts, development strictly train/validation.

No solver or analytical label generator is called. Only six physical inputs and
the declared response are consumed. Original benchmark partitions have already
been examined in earlier research; this revision remains exploratory.
"""
from __future__ import annotations
import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_name, '1')
import argparse, hashlib, itertools, json, time
from pathlib import Path
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, SplineTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.mixture import GaussianMixture
from sklearn.svm import SVR
from sklearn.metrics import mean_absolute_error, mean_squared_error
from threadpoolctl import threadpool_limits

FEATURES = ['width_mm','thickness_mm','span_mm','punch_radius_mm','support_radius_mm','prebend_stroke_mm']
TARGET = 'reference_stroke_mm'
SEEDS = [40,41,42]

def write_json(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def load_development_data(path):
    """Explicit allowlist: discard all rows/columns outside train/validation x/y.

    JSON is decoded to locate declared splits; excluded split labels and diagnostic
    columns are never converted, returned, summarized, fitted or scored.
    """
    obj=json.loads(Path(path).read_text(encoding='utf-8'))
    md=obj['metadata']
    assert md['features']==FEATURES and md['target']==TARGET
    material=tuple(float(md['fixed_material'][key]) for key in ('elastic_modulus_MPa','yield_stress_MPa'))
    out={}
    for split in ('train','validation'):
        selected=[row for row in obj['rows'] if row['split']==split]
        out[split]={'x':np.asarray([[float(row[k]) for k in FEATURES] for row in selected]),
                    'y':np.asarray([float(row[TARGET]) for row in selected])}
    del obj
    return out,material

def engineering_features(x,material,representation='log_ratios'):
    b,h,L,Rp,Rs,u=np.asarray(x,float).T
    E,sy=material
    dy=sy*L**2/(6*E*h)
    ref=u*(L/260.)**2+dy
    ratios=np.column_stack((b/h,L/h,Rp/h,Rs/h,u/dy,h))
    if representation=='log_ratios': z=np.log(ratios)
    elif representation=='ratios': z=ratios
    elif representation=='raw': z=np.asarray(x,float)
    else: raise ValueError(representation)
    gate=np.column_stack((np.log(u/dy),np.log(L/h),np.log(Rp/h),np.log(Rs/h)))
    return ref,z,gate

class SmoothMGRE(BaseEstimator,RegressorMixin):
    """Positive smooth global trend plus Gaussian-gated polynomial corrections.

    A train-support taper attenuates only the local correction outside the
    coordinate-wise training envelope. No OOD points determine that envelope.
    """
    def __init__(self,seed=40,material=(204401.,1000.121),representation='log_ratios',
                 degree=3,ridge=0.01,n_experts=3,local_degree=2,local_ridge=1.,
                 correction_weight=1.,taper=True,variant='MGRE',basis='polynomial',knots=5):
        self.seed=seed; self.material=material; self.representation=representation
        self.degree=degree; self.ridge=ridge; self.n_experts=n_experts
        self.local_degree=local_degree; self.local_ridge=local_ridge
        self.correction_weight=correction_weight; self.taper=taper; self.variant=variant
        self.basis=basis; self.knots=knots

    def _global_basis(self,zz,fit=False):
        if self.basis=='polynomial':
            if fit: self.poly_=PolynomialFeatures(self.degree,include_bias=False).fit(zz)
            return self.poly_.transform(zz)
        if fit:
            self.poly_=SplineTransformer(n_knots=self.knots,degree=3,knots='uniform',
                extrapolation='linear',include_bias=False).fit(zz)
        additive=self.poly_.transform(zz)
        if self.variant=='NoSplineInteractions': return additive
        ns=additive.shape[1]//zz.shape[1]
        blocks=[additive]
        for j,k in itertools.combinations(range(zz.shape[1]),2):
            blocks.append((additive[:,j*ns:(j+1)*ns,None]*additive[:,None,k*ns:(k+1)*ns]).reshape(len(zz),-1))
        return np.column_stack(blocks)

    def _features(self,x):
        ref,z,gate=engineering_features(x,self.material,self.representation)
        if self.variant=='NoMechanics':
            ref=np.full(len(x),self.reference_constant_); z=np.asarray(x,float); gate=z[:,[1,2,3,4]]
        elif self.variant=='NoResidualPrior': ref=np.ones(len(x))
        elif self.variant=='NoRatioPredictor': z=np.asarray(x,float)
        return ref,z,gate

    def fit(self,x,y):
        x=np.asarray(x,float); y=np.asarray(y,float)
        assert x.shape[1]==6 and np.isfinite(x).all() and (x>0).all()
        assert np.isfinite(y).all() and (y>0).all()
        self.reference_constant_=float(np.median(y))
        ref,z,gate=self._features(x)
        target=np.log(y/ref)
        self.scaler_=StandardScaler().fit(z); zz=self.scaler_.transform(z)
        pp=self._global_basis(zz,fit=True)
        self.global_=Ridge(alpha=self.ridge).fit(pp,target)
        residual=target-self.global_.predict(pp)
        self.gate_scaler_=StandardScaler().fit(gate)
        gg=self.gate_scaler_.transform(gate)
        self.gmm_=None; self.experts_=[]
        self.local_poly_=PolynomialFeatures(self.local_degree,include_bias=False).fit(zz)
        local_basis=self.local_poly_.transform(zz)
        if self.n_experts and self.variant!='NoLocal':
            if self.variant=='NoGate': probabilities=np.ones((len(x),1))
            else:
                self.gmm_=GaussianMixture(n_components=self.n_experts,covariance_type='full',
                    reg_covar=1e-4,n_init=2,max_iter=200,random_state=self.seed).fit(gg)
                probabilities=self.gmm_.predict_proba(gg)
            for k in range(probabilities.shape[1]):
                expert=Ridge(alpha=self.local_ridge).fit(local_basis,residual,
                    sample_weight=np.maximum(probabilities[:,k],0.02))
                self.experts_.append(expert)
        self.bounds_min_=x.min(axis=0); self.bounds_max_=x.max(axis=0)
        self.bounds_range_=np.maximum(self.bounds_max_-self.bounds_min_,1e-12)
        return self

    def components(self,x):
        x=np.asarray(x,float); ref,z,gate=self._features(x)
        zz=self.scaler_.transform(z)
        global_log=self.global_.predict(self._global_basis(zz))
        probs=self.gmm_.predict_proba(self.gate_scaler_.transform(gate)) if self.gmm_ is not None else np.ones((len(x),1))
        local_basis=self.local_poly_.transform(zz)
        correction=sum(probs[:,k]*expert.predict(local_basis) for k,expert in enumerate(self.experts_)) if self.experts_ else np.zeros(len(x))
        outside=np.maximum(self.bounds_min_-x,0)+np.maximum(x-self.bounds_max_,0)
        distance=np.sqrt(np.sum((outside/self.bounds_range_)**2,axis=1))
        taper=np.exp(-4.*distance) if self.taper and self.variant!='NoSupportTaper' else np.ones(len(x))
        return ref,global_log,correction,taper,probs

    def predict(self,x):
        ref,trend,correction,taper,_=self.components(x)
        return ref*np.exp(trend+self.correction_weight*taper*correction)

def score(y,pred):
    return {'validation_MAE_mm':float(mean_absolute_error(y,pred)),
            'validation_RMSE_mm':float(np.sqrt(mean_squared_error(y,pred)))}

def develop(data_path,out):
    started=time.perf_counter()
    parts,material=load_development_data(data_path)
    xt,yt=parts['train']['x'],parts['train']['y']; xv,yv=parts['validation']['x'],parts['validation']['y']
    log={'protocol':'Only train/validation labels and six raw feature columns. Primary selection: validation MAE; RMSE tie-break.',
         'data_sha256':hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
         'seeds':SEEDS,'selection_seed':40,'fixed_bootstrap_seed':43,
         'consumed_columns':FEATURES+[TARGET],'consumed_splits':['train','validation'],
         'train_n':len(yt),'validation_n':len(yv),'material':material,
         'global_candidates':[],'gated_candidates':[],'svr_candidates':[]}
    cache={}
    # Twenty-seven global trend alternatives. All are declared before evaluation.
    for representation,degree,ridge in itertools.product(('log_ratios','ratios','raw'),(2,3,4),(0.0001,0.01,1.)):
        spec=dict(representation=representation,degree=degree,ridge=ridge,n_experts=0,local_degree=2,local_ridge=1.,correction_weight=0.,taper=True)
        tick=time.perf_counter(); model=SmoothMGRE(material=material,**spec).fit(xt,yt)
        rec={'spec':spec,**score(yv,model.predict(xv)),'fit_seconds':time.perf_counter()-tick}
        log['global_candidates'].append(rec)
        cache[json.dumps(spec,sort_keys=True)]=model
        print(json.dumps({'phase':'global',**rec}),flush=True)
    best_global=min(log['global_candidates'],key=lambda r:(r['validation_MAE_mm'],r['validation_RMSE_mm']))
    base=dict(best_global['spec'])
    # Nine local structures and four shrinkage choices, all selected by validation.
    for experts,local_degree in itertools.product((2,3,4),(1,2,3)):
        spec={**base,'n_experts':experts,'local_degree':local_degree,'local_ridge':1.,'correction_weight':1.}
        tick=time.perf_counter(); model=SmoothMGRE(material=material,**spec).fit(xt,yt)
        ref,trend,local,taper,_=model.components(xv)
        duration=time.perf_counter()-tick
        for weight in (0.25,0.5,0.75,1.):
            s={**spec,'correction_weight':weight}
            rec={'spec':s,**score(yv,ref*np.exp(trend+weight*taper*local)),'fit_seconds':duration}
            log['gated_candidates'].append(rec)
            print(json.dumps({'phase':'gated',**rec}),flush=True)
    all_mgre=log['global_candidates']+log['gated_candidates']
    selected=min(all_mgre,key=lambda r:(r['validation_MAE_mm'],r['validation_RMSE_mm']))
    # Thirty-six baseline fits, equal to MGRE's 27 global + 9 gated fits.
    for C,gamma,epsilon in itertools.product((8.,32.,128.),(0.02,0.08,0.25),(0.01,0.035,0.07,0.12)):
        spec={'C':C,'gamma':gamma,'epsilon':epsilon}
        tick=time.perf_counter(); model=make_pipeline(StandardScaler(),SVR(**spec)).fit(xt,yt)
        rec={'spec':spec,**score(yv,model.predict(xv)),'fit_seconds':time.perf_counter()-tick}
        log['svr_candidates'].append(rec)
        print(json.dumps({'phase':'svr',**rec}),flush=True)
    svr=min(log['svr_candidates'],key=lambda r:(r['validation_MAE_mm'],r['validation_RMSE_mm']))
    log['selected_mgre']=selected; log['selected_svr']=svr
    log['fit_budget']={'MGRE_fits':36,'MGRE_validation_scores':63,'SVR_fits':36,'SVR_validation_scores':36,
        'note':'MGRE four correction weights share each gated fit; all validation comparisons are disclosed.'}
    log['elapsed_seconds']=time.perf_counter()-started
    log['frozen_before_final_test']=True
    write_json(out/'development_search.json',log)
    frozen={'model_class':'enhanced_mgre.SmoothMGRE','material':material,'seeds':SEEDS,
            'bootstrap_seed':43,'mgre_spec':selected['spec'],'tuned_svr_spec':svr['spec'],
            'ablation_variants':['NoMechanics','NoRatioPredictor','NoResidualPrior','NoGate','NoLocal','NoSupportTaper'],
            'ablation_policy':'Use selected full-model parameters; remove exactly stated component. No ablation-specific tuning.',
            'validation_selection':{'MGRE':selected,'RBF_SVR_tuned':svr},
            'allowed_development_splits':['train','validation'],'test_or_calibration_used_for_selection':False,
            'interpretation':'This is an exploratory revision of previously examined partitions, not a new untouched confirmation test.'}
    # This first-stage receipt is not the final architecture freeze. Adaptive
    # spline/SVR extensions and development_finalize.py complete that protocol.
    frozen['final_freeze_ready']=False
    write_json(out/'development_initial_spec.json',frozen)
    print(json.dumps({'phase':'frozen','mgre':selected,'svr':svr,'elapsed_seconds':log['elapsed_seconds']}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    with threadpool_limits(limits=1): develop(args.data,args.output)

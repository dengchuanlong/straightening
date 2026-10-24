"""Portable, provenance-explicit regression benchmark; never invokes a FE solver.

Run with --data your_dataset.json --output an_empty_result_directory.
Only declared six physical inputs enter the models. Calibration labels are used
only for the finite-sample conformal quantile. Within this rerun, test/OOD labels never tune models. The inherited partitions
and their outcomes were already inspected on 2026-10-16; this is an exploratory
replication, not an untouched confirmatory test or verified FE experiment.
"""
from __future__ import annotations
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
import warnings
import numpy as np
import scipy
import sklearn
import joblib
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.mixture import GaussianMixture
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

FEATURES = ["width_mm", "thickness_mm", "span_mm", "punch_radius_mm", "support_radius_mm", "prebend_stroke_mm"]
TARGET = "reference_stroke_mm"
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
SEEDS = [40, 41, 42]
BOOTSTRAP_SEED = 43
MODEL_NAMES = ["Mean", "Ridge", "RBF_SVR", "RandomForest", "HGB", "MLP", "MGRE", "NoMechanics", "NoRatioPredictor", "NoResidualPrior", "NoGate", "NoGlobal", "NoLocal", "ConstantInterval"]
ABLATIONS = ["NoMechanics", "NoRatioPredictor", "NoResidualPrior", "NoGate", "NoGlobal", "NoLocal", "ConstantInterval"]
BASELINES = MODEL_NAMES[:6]
DETERMINISTIC_BASELINES = ["Mean", "Ridge", "RBF_SVR", "HGB"]
GLOBAL_SVR_CACHE = {}
sys.modules.setdefault("run_experiments", sys.modules[__name__])

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validated_data(path, requested_origin=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    md, rows = data["metadata"], data["rows"]
    assert md["features"] == FEATURES, "Six feature names/order must match the published schema"
    assert md["target"] == TARGET
    assert all(md["units"].get(k) == "mm" for k in FEATURES+[TARGET]), "All six inputs and target must have explicit mm units"
    origin = requested_origin or md.get("data_origin")
    assert origin and md.get("data_origin") == origin, "Explicit origin must match dataset metadata"
    assert all(row.get("data_origin") == origin for row in rows), "Mixed/missing row origins prohibited"
    ids, geometries, group_splits = set(), set(), {}
    for row in rows:
        vals = np.asarray([row[k] for k in FEATURES]+[row[TARGET]], float)
        assert np.isfinite(vals).all() and (vals>0).all(), "Declared input values and response must be positive finite numbers"
        assert row["span_mm"] < md.get("bar_length_mm", 270), "Support span must be shorter than the declared bar"
        assert row["sample_id"] not in ids, "Duplicate sample_id"
        ids.add(row["sample_id"])
        geom = tuple(float(row[k]) for k in FEATURES)
        assert geom not in geometries, "Duplicate six-input tuple"
        geometries.add(geom)
        group = row["group_id"]
        assert group not in group_splits or group_splits[group] == row["split"], "Declared group occurs across splits"
        group_splits[group] = row["split"]
        assert row["split"] in ["train", "validation", "calibration", "test", "ood"]
    parts = {}
    for split in ["train", "validation", "calibration", "test", "ood"]:
        subset = [r for r in rows if r["split"] == split]
        if not subset:
            assert split == "ood", f"Missing {split} split"
            continue
        parts[split] = {"x": np.array([[r[k] for k in FEATURES] for r in subset], float),
                        "y": np.array([r[TARGET] for r in subset], float),
                        "ids": [r["sample_id"] for r in subset]}
        if all("clean_reference_stroke_mm" in r for r in subset):
            parts[split]["clean"] = np.array([r["clean_reference_stroke_mm"] for r in subset], float)
        if all("noise_std_mm" in r for r in subset):
            parts[split]["noise_std"] = np.array([r["noise_std_mm"] for r in subset], float)
    mat = md["fixed_material"]
    material = (float(mat["elastic_modulus_MPa"]), float(mat["yield_stress_MPa"]))
    assert all(np.isfinite(v) and v>0 for v in material)
    checks = {"passed": True, "rows": len(rows), "unique_ids": len(ids), "unique_geometries": len(geometries),
              "group_split_leakage": False, "split_counts": {k: len(v["y"]) for k,v in parts.items()},
              "inputs_positive_finite": True, "labels_positive_finite": True, "units_checked": "mm",
              "oracle_fields_excluded_from_training_selection_calibration": True,
              "data_origin": origin, "physical_correctness_verified": False,
              "provenance_scope": "Checks verify declared schema, units, row-origin consistency and split integrity only. The workbook reproduces the previous synthetic numerical benchmark; author-supplied FE provenance is pending native-solver evidence. No material, FE, or experimental truth is established."}
    return data, parts, material, checks, origin

def mechanics(x, material):
    b,h,L,Rp,Rs,u = x.T
    E, sy = material
    dy = sy*L**2/(6*E*h)
    ref = u*(L/260)**2+dy
    ratios = np.column_stack([b/h, L/h, Rp/h, Rs/h, u/dy, dy/u])
    gate = np.column_stack([u/dy, L/h, Rp/h, Rs/h])
    return ref, np.column_stack([x, ratios]), gate

class MGRE(BaseEstimator, RegressorMixin):
    def __init__(self, seed=40, material=(204401.,1000.121), variant="MGRE", max_iter=180):
        self.seed=seed; self.material=material; self.variant=variant; self.max_iter=max_iter

    def features(self, x):
        if self.variant == "NoMechanics":
            return np.full(len(x), self.reference_constant_), x, x[:,[1,2,3,4]]
        if self.variant == "NoResidualPrior":
            _,z,gate=mechanics(x,self.material)
            return np.ones(len(x)),z,gate
        if self.variant == "NoRatioPredictor":
            ref, _, gate = mechanics(x, self.material)
            return ref, x, gate
        return mechanics(x, self.material)

    def fit(self, x, y):
        self.reference_constant_ = float(np.median(y))
        ref, z, gate = self.features(x)
        residual = np.log(y/ref)
        self.z_scaler_ = StandardScaler().fit(z)
        zz = self.z_scaler_.transform(z)
        self.gate_scaler_ = StandardScaler().fit(gate)
        gg = self.gate_scaler_.transform(gate)
        self.global_ = None; self.experts_=[]; self.gmm_=None
        if self.variant != "NoGlobal":
            # Identical deterministic global branches are shared, never across
            # different features/labels. This changes computation, not fitting.
            cache_key=hashlib.sha256(zz.tobytes()+residual.tobytes()).hexdigest()
            if cache_key not in GLOBAL_SVR_CACHE:
                GLOBAL_SVR_CACHE[cache_key]=SVR(C=3.0, epsilon=0.003, gamma="scale").fit(zz, residual)
            self.global_=GLOBAL_SVR_CACHE[cache_key]
        if self.variant != "NoLocal":
            if self.variant == "NoGate":
                probs = np.ones((len(x),1))
            else:
                self.gmm_ = GaussianMixture(n_components=3,covariance_type="full",reg_covar=1e-4,
                                           n_init=2,max_iter=150,random_state=self.seed).fit(gg)
                probs = self.gmm_.predict_proba(gg)
            for k in range(probs.shape[1]):
                expert = HistGradientBoostingRegressor(max_iter=self.max_iter,max_leaf_nodes=15,
                    min_samples_leaf=25,l2_regularization=1.,learning_rate=.055,
                    early_stopping=False,random_state=self.seed+k)
                expert.fit(zz,residual,sample_weight=np.maximum(probs[:,k],.02))
                self.experts_.append(expert)
        self.alpha_=1.0 if self.variant == "NoLocal" else 0.0 if self.variant == "NoGlobal" else .5
        return self

    def components(self, x):
        ref,z,gate=self.features(x); zz=self.z_scaler_.transform(z)
        gp=self.gmm_.predict_proba(self.gate_scaler_.transform(gate)) if self.gmm_ is not None else np.ones((len(x),1))
        global_res=self.global_.predict(zz) if self.global_ is not None else np.zeros(len(x))
        local_res=sum(gp[:,k]*m.predict(zz) for k,m in enumerate(self.experts_)) if self.experts_ else np.zeros(len(x))
        return ref,global_res,local_res,gp

    def select_alpha(self, x, y):
        ref,gl,lo,_=self.components(x)
        candidates=ALPHAS if self.variant not in ["NoGlobal","NoLocal"] else [self.alpha_]
        self.alpha_scores_=[{"alpha":float(a),"validation_MAE_mm":float(mean_absolute_error(y,ref*np.exp(a*gl+(1-a)*lo)))} for a in candidates]
        self.alpha_=min(self.alpha_scores_,key=lambda v:v["validation_MAE_mm"])["alpha"]
        return self

    def predict(self, x):
        ref,gl,lo,_=self.components(x)
        return ref*np.exp(self.alpha_*gl+(1-self.alpha_)*lo)

MGRE.__module__="run_experiments"

def baseline(name, params, seed):
    if name == "Mean": return DummyRegressor(strategy="mean")
    if name == "Ridge": return make_pipeline(StandardScaler(),Ridge(alpha=params["alpha"]))
    if name == "RBF_SVR": return make_pipeline(StandardScaler(),SVR(C=params["C"],gamma=params["gamma"],epsilon=.035))
    if name == "RandomForest": return RandomForestRegressor(n_estimators=160,max_features=1.,min_samples_leaf=params["min_samples_leaf"],n_jobs=1,random_state=seed)
    if name == "HGB": return HistGradientBoostingRegressor(max_iter=260,max_leaf_nodes=params["max_leaf_nodes"],learning_rate=.06,min_samples_leaf=20,l2_regularization=1.,early_stopping=False,random_state=seed)
    if name == "MLP": return make_pipeline(StandardScaler(),MLPRegressor(hidden_layer_sizes=(64,32),activation="tanh",alpha=params["alpha"],learning_rate_init=.003,max_iter=350,early_stopping=True,validation_fraction=.12,n_iter_no_change=25,random_state=seed))
    raise ValueError(name)

GRIDS={"Mean":[{}],"Ridge":[{"alpha":.01},{"alpha":1.},{"alpha":100.}],
       "RBF_SVR":[{"C":32.,"gamma":.08},{"C":128.,"gamma":.12}],
       "RandomForest":[{"min_samples_leaf":1},{"min_samples_leaf":3}],
       "HGB":[{"max_leaf_nodes":15},{"max_leaf_nodes":31}],
       "MLP":[{"alpha":.001},{"alpha":.05}]}

def fit_scale(xv, errors, seed):
    floor=.015
    model=HistGradientBoostingRegressor(loss="absolute_error",max_iter=80,max_leaf_nodes=7,
        min_samples_leaf=45,l2_regularization=2.,learning_rate=.06,early_stopping=False,random_state=seed)
    model.fit(xv,errors)
    return model,floor

def qfinite(scores, coverage):
    n=len(scores)
    rank=min(n,int(np.ceil((n+1)*coverage)))
    return float(np.sort(scores)[rank-1]),rank

def metrics(y, pred, lower, upper, clean=None):
    ae=np.abs(y-pred)
    out={"MAE_mm":float(np.mean(ae)),"RMSE_mm":float(np.sqrt(mean_squared_error(y,pred))),
        "MAPE_percent":float(np.mean(ae/y)*100),"R2":float(r2_score(y,pred)),
        "max_absolute_error_mm":float(ae.max()),"coverage_90":float(np.mean((y>=lower)&(y<=upper))),
        "mean_interval_width_mm":float(np.mean(upper-lower))}
    if clean is not None:
        out["oracle_clean_MAE_mm"]=float(mean_absolute_error(clean,pred))
        out["oracle_clean_RMSE_mm"]=float(np.sqrt(mean_squared_error(clean,pred)))
    return out

def summarize(runs):
    out={}
    for name in MODEL_NAMES:
        rs=[r for r in runs if r["model"]==name]
        if not rs: continue
        item={"n_training_seeds":len(rs),"training_time_seconds":{"mean":float(np.mean([r["training_seconds"] for r in rs])),"std":float(np.std([r["training_seconds"] for r in rs],ddof=1)) if len(rs)>1 else 0.},
              "validation_MAE_mm":{"mean":float(np.mean([r["validation_MAE_mm"] for r in rs])),"std":float(np.std([r["validation_MAE_mm"] for r in rs],ddof=1)) if len(rs)>1 else 0.}}
        for split in ["test","ood"]:
            if split not in rs[0]["metrics"]: continue
            item["iid" if split=="test" else "ood"]={k:{"mean":float(np.mean([r["metrics"][split][k] for r in rs])),"std":float(np.std([r["metrics"][split][k] for r in rs],ddof=1)) if len(rs)>1 else 0.} for k in rs[0]["metrics"][split]}
        out[name]=item
    return out

def main():
    started=time.perf_counter()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data",type=Path,default=Path(__file__).resolve().parents[1]/"data"/"dataset.json")
    ap.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--data-origin",default=None,help="Must exactly match metadata and every row; never auto-label real data as FE")
    ap.add_argument("--seeds",nargs="+",type=int,default=SEEDS)
    ap.add_argument("--bootstrap-seed",type=int,default=BOOTSTRAP_SEED,
                    help="Paired row-resampling seed for fixed mean-across-training-seed predictions.")
    ap.add_argument("--skip-learning-curves",action="store_true")
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    analysis=args.output/"analysis"; models=args.output/"models"
    analysis.mkdir(exist_ok=True); models.mkdir(exist_ok=True)
    data,parts,material,checks,origin=validated_data(args.data,args.data_origin)
    train,val,cal=parts["train"],parts["validation"],parts["calibration"]
    versions={"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"sklearn":sklearn.__version__,"joblib":joblib.__version__,"platform":platform.platform()}
    dump(analysis/"software_checks.json",{"versions":versions,"schema_checks":checks,"solver_started":False,"real_label_generator_fit":False,"data_sha256":sha(args.data),"script_sha256":sha(Path(__file__)),"material_role":"Assigned illustrative constants for positive engineering normalization; these are not calibrated material properties and do not verify the author-supplied FE provenance."})
    print(json.dumps({"phase":"validated","checks":checks}),flush=True)
    chosen={}; selection={}; cache={}
    with threadpool_limits(limits=1):
        # Every baseline hyperparameter decision occurs before any test evaluation.
        for name in BASELINES:
            candidates=[]; best=None
            for params in GRIDS[name]:
                m=baseline(name,params,args.seeds[0]); t=time.perf_counter()
                with warnings.catch_warnings(record=True) as ws:
                    warnings.simplefilter("always",ConvergenceWarning); m.fit(train["x"],train["y"])
                duration=time.perf_counter()-t
                score=float(mean_absolute_error(val["y"],m.predict(val["x"])))
                record={"parameters":params,"validation_MAE_mm":score,"fit_seconds":duration,"warnings":[str(w.message) for w in ws]}
                candidates.append(record)
                if best is None or score<best[0]: best=(score,m,params,duration,record["warnings"])
            chosen[name]=best[2];cache[(name,args.seeds[0])]=(best[1],best[3],best[4]); selection[name]=candidates
            print(json.dumps({"phase":"baseline_selected","model":name,"best_validation_MAE_mm":best[0],"parameters":best[2]}),flush=True)
        best_baseline=min(BASELINES,key=lambda name:min(v["validation_MAE_mm"] for v in selection[name]))
        # Freeze all point predictors using training and validation only.
        fitted={}; train_records=[]
        for seed in args.seeds:
            for name in MODEL_NAMES:
                if name=="ConstantInterval":
                    fitted[(name,seed)]=fitted[("MGRE",seed)]
                    continue
                if name in BASELINES:
                    reused=False
                    if name in DETERMINISTIC_BASELINES and seed!=args.seeds[0]:
                        cache[(name,seed)]=cache[(name,args.seeds[0])];reused=True
                    if (name,seed) in cache: m,duration,ws=cache[(name,seed)]
                    else:
                        m=baseline(name,chosen[name],seed); t=time.perf_counter()
                        with warnings.catch_warnings(record=True) as got:
                            warnings.simplefilter("always",ConvergenceWarning);m.fit(train["x"],train["y"])
                        duration=time.perf_counter()-t;ws=[str(w.message) for w in got]
                    details={"parameters":chosen[name],"deterministic_fit_reused":reused,
                             "timing_scope":"Reference duration of identical first-seed deterministic fit" if reused else "Actual fit duration"}
                else:
                    t=time.perf_counter();m=MGRE(seed=seed,material=material,variant=name).fit(train["x"],train["y"])
                    m.select_alpha(val["x"],val["y"]);duration=time.perf_counter()-t;ws=[]
                    details={"alpha":m.alpha_,"alpha_validation_candidates":m.alpha_scores_,"degenerate_branch": "global_only" if m.alpha_==1 else "local_only" if m.alpha_==0 else "both", "n_experts":len(m.experts_),"max_iter":m.max_iter}
                fitted[(name,seed)]={"model":m,"training_seconds":duration,"warnings":ws,"details":details,
                    "validation_MAE_mm":float(mean_absolute_error(val["y"],m.predict(val["x"]))) }
            print(json.dumps({"phase":"point_models_frozen","seed":seed,"MGRE":fitted[("MGRE",seed)]["details"],"elapsed_seconds":time.perf_counter()-started}),flush=True)
        winner=min(MODEL_NAMES[:-1],key=lambda name:float(np.mean([fitted[(name,s)]["validation_MAE_mm"] for s in args.seeds])))
        dump(analysis/"selection_frozen.json",{"data_origin":origin,"best_baseline_by_first_seed_validation":best_baseline,"selected_family_by_mean_validation_MAE":winner,"baseline_search":selection,"frozen_model_details":[{"model":n,"seed":s,**{k:v for k,v in fitted[(n,s)].items() if k!="model"}} for s in args.seeds for n in MODEL_NAMES],"test_used_for_selection_in_this_rerun":False,"historical_test_inspection":True,"study_status":"exploratory replication using previously examined partitions; provenance pending"})
        # Validation-trained error scales are frozen before calibration quantiles.
        calibrated={}
        for seed in args.seeds:
            for name in MODEL_NAMES:
                rec=fitted[(name,seed)];m=rec["model"];t=time.perf_counter()
                if name=="ConstantInterval":
                    scale_model=None;floor=1.;sc=np.ones(len(cal["y"]))
                else:
                    scale_model,floor=fit_scale(val["x"],np.abs(val["y"]-m.predict(val["x"])),seed)
                    sc=np.maximum(scale_model.predict(cal["x"]),floor)
                q,rank=qfinite(np.abs(cal["y"]-m.predict(cal["x"]))/sc,.90)
                calibrated[(name,seed)]={"scale_model":scale_model,"floor":floor,"q":q,"rank":rank,"scale_and_calibration_seconds":time.perf_counter()-t}
        print(json.dumps({"phase":"calibration_frozen","selected_family":winner,"best_baseline":best_baseline,"elapsed_seconds":time.perf_counter()-started}),flush=True)
        # Only now evaluate reserved labels in this rerun; no adaptive decisions use these metrics. These partitions were already inspected in the earlier synthetic study.
        runs=[]
        for seed in args.seeds:
            for name in MODEL_NAMES:
                rec=fitted[(name,seed)];m=rec["model"];ci=calibrated[(name,seed)]
                run={"model":name,"seed":seed,"data_origin":origin,**{k:v for k,v in rec.items() if k!="model"},
                     "conformal":{"nominal_coverage":.90,"n_calibration":len(cal["y"]),"rank":ci["rank"],"q":ci["q"],"scale_floor_mm":ci["floor"] if ci["scale_model"] else None,"scale_and_calibration_seconds":ci["scale_and_calibration_seconds"]},"metrics":{},"predictions":{}}
                for split in ["test","ood"]:
                    if split not in parts:continue
                    part=parts[split];pred=m.predict(part["x"])
                    scale=np.maximum(ci["scale_model"].predict(part["x"]),ci["floor"]) if ci["scale_model"] else np.ones(len(pred))
                    low=np.maximum(0.,pred-ci["q"]*scale);up=pred+ci["q"]*scale
                    run["metrics"][split]=metrics(part["y"],pred,low,up,part.get("clean"))
                    pr={"sample_ids":part["ids"],"y_true":part["y"].tolist(),"y_pred":pred.tolist(),"lower":low.tolist(),"upper":up.tolist(),"scale_mm":scale.tolist()}
                    if name=="MGRE":
                        gate=m.components(part["x"])[3];pr["gate_probabilities"]=gate.tolist();pr["regime_argmax"]=gate.argmax(axis=1).tolist()
                    run["predictions"][split]=pr
                runs.append(run)
                joblib.dump({"point_model":m,"scale_model":ci["scale_model"],"scale_floor_mm":ci["floor"],"conformal_q":ci["q"],"feature_names":FEATURES,"data_origin":origin,"data_sha256":sha(args.data),"training_seed":seed,"model_name":name,"physical_correctness_verified":False},models/f"{name}_seed{seed}.joblib",compress=3)
        curves=[]
        if not args.skip_learning_curves:
            for seed in args.seeds:
                order=np.random.default_rng(seed+700).permutation(len(train["y"]))
                for size in [100,250,500,1000,2000,4800]:
                    if size>len(order):continue
                    idx=order[:size]
                    for name in ["MGRE",best_baseline]:
                        t=time.perf_counter()
                        if size==len(order):m=fitted[(name,seed)]["model"]
                        elif name=="MGRE":m=MGRE(seed=seed,material=material).fit(train["x"][idx],train["y"][idx]).select_alpha(val["x"],val["y"])
                        else:m=baseline(name,chosen[name],seed).fit(train["x"][idx],train["y"][idx])
                        pp=m.predict(parts["test"]["x"])
                        curves.append({"model":name,"seed":seed,"n_train":size,"data_origin":origin,"test_RMSE_mm":float(np.sqrt(mean_squared_error(parts["test"]["y"],pp))),"test_MAE_mm":float(mean_absolute_error(parts["test"]["y"],pp)),"validation_MAE_mm":float(mean_absolute_error(val["y"],m.predict(val["x"]))),"training_seconds":time.perf_counter()-t,"alpha":m.alpha_ if name=="MGRE" else None})
                print(json.dumps({"phase":"learning_curve_complete","seed":seed,"elapsed_seconds":time.perf_counter()-started}),flush=True)
        # Paired row bootstrap is conditional on this fixed test set and trained models.
        boot={}
        rng=np.random.default_rng(args.bootstrap_seed)
        for split in ["test","ood"]:
            if split not in parts:continue
            y=parts[split]["y"]
            pm=np.mean([r["predictions"][split]["y_pred"] for r in runs if r["model"]=="MGRE"],axis=0)
            pb=np.mean([r["predictions"][split]["y_pred"] for r in runs if r["model"]==best_baseline],axis=0)
            deltas=[]
            for _ in range(1000):
                ii=rng.integers(0,len(y),len(y));em=y[ii]-pm[ii];eb=y[ii]-pb[ii]
                deltas.append([np.mean(np.abs(em))-np.mean(np.abs(eb)),np.sqrt(np.mean(em**2))-np.sqrt(np.mean(eb**2))])
            ar=np.array(deltas)
            boot[split]={"comparison":f"MGRE minus {best_baseline}","predictor":"Mean prediction across training seeds, fixed before bootstrap","MAE_delta_mm":float(np.mean(np.abs(y-pm))-np.mean(np.abs(y-pb))),"MAE_delta_95CI_mm":np.quantile(ar[:,0],[.025,.975]).tolist(),"RMSE_delta_mm":float(np.sqrt(np.mean((y-pm)**2))-np.sqrt(np.mean((y-pb)**2))),"RMSE_delta_95CI_mm":np.quantile(ar[:,1],[.025,.975]).tolist(),"n_bootstrap":1000,"seed":args.bootstrap_seed,"interpretation":"Conditional test-row resampling; not independent physical experiments or evidence of FE validity. Negative favors MGRE."}
        oracle={}
        for split,part in parts.items():
            if "clean" in part:
                oracle[split]={"noise_realized_RMSE_mm":float(np.sqrt(np.mean((part["y"]-part["clean"])**2))),"noise_std_mean_mm":float(part["noise_std"].mean()) if "noise_std" in part else None}
        result={"schema_version":"provenance-pending-replication-results-v1","data_origin":origin,
            "metadata":{"features":FEATURES,"target":TARGET,"units":data["metadata"]["units"],"data_file":str(args.data.resolve()),"data_sha256":sha(args.data),"script_sha256":sha(Path(__file__)),"generator_formula":data["metadata"].get("generator_formula"),"versions":versions,"split_counts":checks["split_counts"],"training_seeds":args.seeds,"paired_bootstrap_seed":args.bootstrap_seed,"family_selected_by_validation":winner,"best_baseline_by_validation":best_baseline,
              "selection_protocol":"Within this rerun baseline grids and MGRE alpha use validation only; point predictors and validation-trained scales are frozen before calibration; calibration supplies only the finite-sample conformal quantile. Test and thickness-shift partitions are evaluated after the rerun freeze, but the inherited partitions and their outcomes were inspected on 2026-10-16. Results are exploratory replication, not an untouched confirmatory evaluation or verified FE generalization. Learning curves reuse fixed baseline hyperparameters, their own training subset and validation-only alpha.",
              "seed_interpretation":"Training seeds are 40, 41 and 42 by default; paired bootstrap uses seed 43 on fixed mean-across-seed predictions. Same fixed train/validation/calibration/test groups; seeds measure algorithm sensitivity, not independent experiments. Mean/Ridge/RBF_SVR/HGB are deterministic here, fit once and reused across seeds with identical predictions and zero SD; their reported training duration is the original reference fit. Identical deterministic MGRE global SVR branches are cached by exact training features+labels hash; stochastic gates/experts and MLP/RandomForest are actually fitted for each seed.",
              "material_role":"Assigned illustrative normalization constants only; no material calibration performed.","study_status":"AUTHOR_SUPPLIED_PROVENANCE_PENDING","historical_test_inspection":True,"native_solver_evidence_verified":False,"retained_auxiliary_fields_role":"The workbook clean-reference and noise-scale columns coincide with the prior synthetic benchmark. They are diagnostic-only, not verified physical truth, never model inputs, tuning criteria, or calibration inputs.","physical_correctness_verified":False,"solver_started":False,"source_evidence":data["metadata"].get("source_evidence",[]),
              "model_architecture":{"name":"Mechanics-normalized gated residual ensemble (MGRE)","engineering_scale":"d_y=sigma_y*L^2/(6*E*h); m=u*(L/260)^2+d_y >0","residual_target":"r=log(reference_stroke_mm/m)","z_order":FEATURES+["b_over_h","L_over_h","Rp_over_h","Rs_over_h","u_over_dy","dy_over_u"],"gate_features_order":["u_over_dy","L_over_h","Rp_over_h","Rs_over_h"],"normalization":"StandardScaler fitted on train only, separately for z and gate","gate":"3-component full-covariance GaussianMixture, 2 initializations, reg_covar=1e-4, train features only","expert_objective":"HGB squared residual loss with weights max(g_k,0.02), 180 iterations,15 leaves, minleaf25,lr0.055,l2=1","global_objective":"RBF-SVR residual epsilon-insensitive loss, C3,epsilon0.003,gamma=scale","fusion":"rhat=alpha*f_global+(1-alpha)*sum_k(g_k*f_k); alpha grid [0,.25,.5,.75,1] minimizes validation MAE in mm; yhat=m*exp(rhat)","uncertainty":"For every baseline and point-model ablation, absolute validation errors train HGB(loss=absolute_error,80iter,7leaves,minleaf45,lr.06,l2=2); positive scale=max(predicted_error,.015mm). Calibration q is sorted normalized error at ceil((n_cal+1)*.9), capped at n_cal. Interval=[max(0,yhat-q*scale),yhat+q*scale]. ConstantInterval reuses MGRE point predictions and q from unnormalized errors, scale=1.","NoMechanics":"Raw six features, median-training-label constant positive scale; gate uses [h,L,Rp,Rs]. Jointly removes engineered descriptors and mechanics prior; not a single-component descriptor-only test.","NoRatioPredictor":"Isolated predictor-descriptor ablation: retains exactly the same mechanics prior and four gate inputs, but changes the global and local predictor input z from 12 descriptors to the raw six inputs. The gate remains normalized and mechanics-informed; own validation alpha is allowed.","NoResidualPrior":"Retains all 12 descriptors and the same four dimensionless gate inputs; learns log(y) with m=1, removing only the mechanics residual prior.","NoGate":"One globally trained HGB local branch, global SVR branch; own validation-selected alpha.","NoGlobal":"Softly gated local experts only, alpha=0.","NoLocal":"Global residual SVR only, alpha=1.","ConstantInterval":"MGRE points unchanged; replaces adaptive error scale by a constant. This tests interval adaptation only, not point performance."}},
            "hyperparameter_selection":selection,"model_summaries":summarize(runs),"seed_results":runs,
            "learning_curves":curves,"paired_bootstrap":boot,"oracle_noise_diagnostics":oracle,
            "runtime_seconds":time.perf_counter()-started,"claims_boundary":"All conclusions are conditional on this author-supplied, provenance-pending workbook. Its numerical values coincide with the prior synthetic benchmark; native FE origin is unverified. This exploratory replication cannot establish real FE/experimental accuracy, unique optimal stroke, final residual shape, or physical qualification. Auxiliary clean/noise columns are unverified diagnostics only. No superiority is assumed and all negative results are retained."}
        dump(analysis/"results.json",result)
        print(json.dumps({"phase":"finished","results":str(analysis/"results.json"),"runtime_seconds":result["runtime_seconds"],"selected_family":winner,"best_baseline":best_baseline,"summaries":{k:v["iid"]["RMSE_mm"] for k,v in result["model_summaries"].items()}}),flush=True)

if __name__=="__main__":main()

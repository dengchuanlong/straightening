"""Independently recompute stored metrics and reload each trained weight bundle.

This checks software/data consistency only and cannot establish physical truth.
"""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from run_experiments import validated_data, metrics, qfinite, dump, sha

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args();root=args.root
    result=json.loads((root/"analysis"/"results.json").read_text(encoding="utf-8"))
    recorded_path=Path(result["metadata"]["data_file"])
    data_path=recorded_path if recorded_path.exists() else root/"data"/"dataset.json"
    assert sha(data_path)==result["metadata"]["data_sha256"], "Dataset hash differs from the executed run"
    _,parts,_,checks,origin=validated_data(data_path)
    max_prediction_difference=0.;max_metric_difference=0.;max_quantile_difference=0.
    with threadpool_limits(limits=1):
        for run in result["seed_results"]:
            bundle=joblib.load(root/"models"/f'{run["model"]}_seed{run["seed"]}.joblib')
            assert bundle["data_origin"]==origin
            assert bundle["data_sha256"]==sha(data_path)
            assert bundle["feature_names"]==result["metadata"]["features"]
            for split,p in run["predictions"].items():
                part=parts[split]
                assert p["sample_ids"]==part["ids"]
                assert np.array_equal(p["y_true"],part["y"])
                pred=bundle["point_model"].predict(part["x"])
                max_prediction_difference=max(max_prediction_difference,float(np.max(np.abs(pred-np.array(p["y_pred"])))))
                mm=metrics(part["y"],np.array(p["y_pred"]),np.array(p["lower"]),np.array(p["upper"]),part.get("clean"))
                max_metric_difference=max(max_metric_difference,max(abs(mm[k]-run["metrics"][split][k]) for k in mm))
            cp=bundle["point_model"].predict(parts["calibration"]["x"])
            sm=bundle["scale_model"]
            sc=np.maximum(sm.predict(parts["calibration"]["x"]),bundle["scale_floor_mm"]) if sm else np.ones(len(cp))
            qq,rank=qfinite(np.abs(parts["calibration"]["y"]-cp)/sc,.90)
            max_quantile_difference=max(max_quantile_difference,abs(qq-run["conformal"]["q"]))
            assert rank==run["conformal"]["rank"]
    assert max_prediction_difference<1e-12
    assert max_metric_difference<1e-12
    assert max_quantile_difference<1e-12
    for seed in result["metadata"]["training_seeds"]:
        r={r["model"]:r for r in result["seed_results"] if r["seed"]==seed}
        for split in ["test","ood"]:
            if split in r["MGRE"]["predictions"]:
                assert r["MGRE"]["predictions"][split]["y_pred"]==r["ConstantInterval"]["predictions"][split]["y_pred"]
        full=joblib.load(root/"models"/f"MGRE_seed{seed}.joblib")["point_model"]
        isolated=joblib.load(root/"models"/f"NoRatioPredictor_seed{seed}.joblib")["point_model"]
        ref_full,z_full,g_full=full.features(parts["test"]["x"])
        ref_iso,z_iso,g_iso=isolated.features(parts["test"]["x"])
        assert np.array_equal(ref_full,ref_iso),"Descriptor ablation changed prior"
        assert np.array_equal(g_full,g_iso),"Descriptor ablation changed gate inputs"
        assert np.array_equal(full.components(parts["test"]["x"])[3],isolated.components(parts["test"]["x"])[3]),"Descriptor ablation changed fitted gate"
        assert z_full.shape[1]==12 and z_iso.shape[1]==6
        assert np.array_equal(z_iso,parts["test"]["x"])
        assert full.z_scaler_.n_features_in_==12 and isolated.z_scaler_.n_features_in_==6
    selected=min([n for n in result["model_summaries"] if n!="ConstantInterval"],key=lambda n:result["model_summaries"][n]["validation_MAE_mm"]["mean"])
    assert selected==result["metadata"]["family_selected_by_validation"]
    report={"passed":True,"data_origin":origin,"n_weight_bundles_verified":len(result["seed_results"]),
        "max_reloaded_prediction_difference_mm":max_prediction_difference,"max_recomputed_metric_difference":max_metric_difference,
        "max_recomputed_conformal_quantile_difference":max_quantile_difference,"constant_interval_points_identical":True,
        "family_winner_validation_consistent":True,"schema_checks":checks,
        "isolated_NoRatioPredictor_prior_and_gate_unchanged":True,
        "isolated_NoRatioPredictor_fitted_gate_probabilities_identical":True,
        "isolated_NoRatioPredictor_predictor_dimension_change":"12 to raw 6 only",
        "historical_test_inspection":True,
        "physical_correctness_verified":False,"solver_invocation_performed":False,
        "scope":"Software replay and provenance/schema consistency only; no FE, native result, experiment, or physical qualification verified."}
    dump(root/"analysis"/"experiment_validation.json",report)
    files=list((root/"scripts").glob("*.py"))+list((root/"data").glob("*.json"))+list((root/"analysis").glob("*.json"))+list((root/"models").glob("*.joblib"))
    dump(root/"analysis"/"manifest.json",{"data_origin":origin,"files":[{"path":str(p.relative_to(root)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(files) if p.name!="manifest.json"],"physical_correctness_verified":False})
    print(json.dumps(report))
if __name__=="__main__":main()

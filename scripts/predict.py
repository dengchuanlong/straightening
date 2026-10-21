"""Predict with saved portable bundles; requires the benchmark sklearn version.

python scripts/predict.py --model models/MGRE_seed40.joblib --data data/dataset.json --output analysis/prediction_replay.json
Input schema and origin are checked; output makes no physical qualification claim.
"""
import argparse
from pathlib import Path
import joblib
import numpy as np
from run_experiments import validated_data, dump, FEATURES

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model",type=Path,required=True)
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    bundle=joblib.load(args.model)
    _,parts,_,_,origin=validated_data(args.data)
    rows=[]
    for split,part in parts.items():
        p=bundle["point_model"].predict(part["x"])
        sm=bundle["scale_model"]
        scale=np.maximum(sm.predict(part["x"]),bundle["scale_floor_mm"]) if sm else np.ones(len(p))
        for i,sid in enumerate(part["ids"]):
            rows.append({"sample_id":sid,"split":split,"prediction_mm":float(p[i]),"lower_mm":float(max(0,p[i]-bundle["conformal_q"]*scale[i])),"upper_mm":float(p[i]+bundle["conformal_q"]*scale[i]),"data_origin":origin})
    dump(args.output,{"model_training_data_origin":bundle["data_origin"],"prediction_input_data_origin":origin,"physical_correctness_verified":False,"rows":rows})
if __name__=="__main__":main()

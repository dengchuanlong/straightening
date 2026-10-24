"""Predict strokes and calibrated intervals from a recreated fitted model."""
from pathlib import Path
import argparse,csv
import numpy as np
import joblib
import legacy_benchmark  # Registers the legacy run_experiments pickle alias.
import enhanced_mgre

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model',type=Path,required=True)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    bundle=joblib.load(args.model)
    with args.input.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    x=np.asarray([[float(row[k]) for k in bundle['features']] for row in rows])
    assert x.ndim==2 and x.shape[1]==6 and np.isfinite(x).all() and (x>0).all()
    pred=bundle['model'].predict(x)
    scale=np.maximum(bundle['scale_model'].predict(x),bundle['scale_floor_mm'])
    radius=bundle['conformal_q']*scale
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['sample_id','predicted_stroke_mm','lower_90_mm','upper_90_mm'])
        for i,row in enumerate(rows):w.writerow([row.get('sample_id',str(i+1)),pred[i],max(0,pred[i]-radius[i]),pred[i]+radius[i]])
    print(f'Wrote {len(rows)} predictions to {args.output}')

if __name__=='__main__':main()

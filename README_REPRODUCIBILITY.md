# Straightening stroke prediction: reproducible numerical benchmark

This release contains the six-input regression benchmark, baseline comparisons,
component ablations, learning curves and calibrated interval analysis accompanying
the manuscript revision. **Training seeds are 40, 41 and 42. The paired bootstrap
uses seed 43 and fixed predictions averaged across those three fitted seeds.**
Seed 43 does not produce a fourth trained point predictor.

## Data and scope

`data/straightening_dataset.csv` contains 9,000 records with source identifiers,
the inherited partition assignment, six inputs and the reference stroke label.
All physical input and target columns are in millimetres:

| Role | Column |
| --- | --- |
| Input | `width_mm` |
| Input | `thickness_mm` |
| Input | `span_mm` |
| Input | `punch_radius_mm` |
| Input | `support_radius_mm` |
| Input | `prebend_stroke_mm` |
| Target | `reference_stroke_mm` |

The fixed partition sizes are 4,800 training, 1,200 validation, 1,000 calibration,
1,000 reference-domain test and 1,000 thickness-shift rows. No row is split again
using a training seed. Thickness is 7–9 mm in the reference domain and 9.25–10 mm
in the shifted partition. The other five declared ranges are unchanged.

`data/dataset.json` is the canonical analysis input. It also retains original
source metadata and two diagnostic columns, which are excluded from all model
fitting, selection and interval calibration. `data/data_dictionary.json` gives
the workbook sheet, rows, column map and checksum. Absolute historical paths in
source metadata document the original import; the code uses paths relative to
this repository and does not require those historical folders.

**The source is author supplied and its native finite-element provenance remains
pending. Its 9,000 × 9 numerical fields agree with the earlier analytical
development table within Excel precision (maximum absolute difference
9.947598300641403e-13). These are not established independent native FE results.**
The labels are analysed as supplied stroke references. The repository contains
no solver run claiming to establish the physical optimum, final unloaded shape,
or accuracy on a straightening machine. Previously inspected partitions are
reused, so this is an exploratory replication. A separate historical
circular-beam report must not be treated as the source of these 9,000 rows.

## Reproduce

The executed environment used Python 3.12.14 and the exact package versions in
`requirements.txt`. Create a Python 3.12 environment, then run:

```sh
python -m pip install -r requirements.txt
python reproduce.py
```

Or run the explicit steps:

```sh
python scripts/run_experiments.py --seeds 40 41 42 --bootstrap-seed 43
python scripts/verify_experiment.py
python scripts/export_revision_tables.py
python scripts/make_paper_figures.py
```

The training script uses one numerical thread, deterministic parameter grids and
fixed subsets. It trains six baseline families, full MGRE and seven ablations,
and writes 42 local fitted bundles, prediction arrays and metrics. Four
deterministic baseline fits are reused across seeds; this does not create new
fits or physical repetitions. For learning curves, nested training subsets are
defined by `default_rng(training_seed + 700)` and use 100, 250, 500, 1,000, 2,000
and 4,800 rows. Thus the three subset-order seeds are 740, 741 and 742.

Baseline grids are selected on validation data using training seed 40. The final
family comparison uses validation MAE averaged across the three seeds. MGRE's
blend weight is selected separately on validation data for each fit. Calibration
uses only the 901st sorted score out of 1,000 for nominal 90% coverage. The paired
bootstrap resamples the fixed evaluation rows 1,000 times; no model is refit
during resampling. Results on shifted data are retained without recalibration.

After a complete local rerun, `analysis/results.json` contains all fitted-model outcomes and saved evaluation
predictions, including negative comparisons. `analysis/experiment_validation.json`
records independent bundle reload, prediction, metric and conformal-quantile
checks. `analysis/revision_tables.json` and `tables/*.csv` provide manuscript
tables directly from the executed outcomes. `figures/figure_manifest.json` binds
each figure to its data/results and rendering script checksums. The figure IDs
retain stable source identifiers; the manifest's `display_id` gives the
continuous Figure 1–16 numbering used in the merged manuscript. Table CSV
filenames likewise retain source identifiers, independent of their final
placement and numbering in the Word manuscript.

Fitted `.joblib` bundles are recreated locally and excluded from version control.
No large binary checkpoint is needed to rerun the study. `scripts/predict.py`
can evaluate a locally recreated bundle, for example:

```sh
python scripts/predict.py --model models/MGRE_seed40.joblib --data data/dataset.json --output analysis/prediction_replay.json
```

MGRE combines a positive mechanics-like scale, logarithmic residual targets,
three Gaussian-mixture-gated histogram-gradient-boosting experts and a global
residual RBF support-vector regressor. The fixed elastic modulus and yield
stress are illustrative normalization constants, not a material calibration.
`NoRatioPredictor` changes only predictor descriptors, preserving the prior and
gate; `NoResidualPrior` preserves descriptors and gate but removes the prior;
`NoMechanics` is a joint intervention; `NoGate` uses one globally trained local
HGB branch; `NoGlobal` and `NoLocal` remove their corresponding branches;
`ConstantInterval` preserves point predictions and changes only interval scaling.

Software replay verifies numerical consistency, not the physical truth of the
source labels. Native solver input/output links will be needed before the data
can be described as a verified finite-element study.

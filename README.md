# Straightening stroke prediction: reproducible numerical benchmark

Code and tabular data for *Mechanics guided residual ensembles for straightening
stroke prediction*. This release contains the executed training-seed revision:
**training seeds 40, 41 and 42; paired-bootstrap seed 43**. The bootstrap uses
fixed predictions averaged across those three fits; seed 43 is not a fourth
training seed.

## Data and interpretation

There are 9,000 supplied records, six input features and one stroke-reference
target. Their native finite-element provenance remains pending. All nine
numeric fields, including two excluded diagnostics, agree with the earlier
disclosed analytical development table within Excel serialization precision.
These records must not be described as independently verified FE calculations
or physical experiments. See [DATA_PROVENANCE.md](DATA_PROVENANCE.md) for the
audit and its independently executable comparison.

| Role | Field | Unit |
| --- | --- | --- |
| Input | `width_mm` | mm |
| Input | `thickness_mm` | mm |
| Input | `span_mm` | mm |
| Input | `punch_radius_mm` | mm |
| Input | `support_radius_mm` | mm |
| Input | `prebend_stroke_mm` | mm |
| Target | `reference_stroke_mm` | mm |

The inherited partitions contain 4,800 training, 1,200 validation, 1,000
calibration, 1,000 reference-domain test and 1,000 thickness-shift records.
Thickness is 7–9 mm in the reference domain and 9.25–10 mm in the shifted set.
The partitions were examined during earlier development; this analysis is an
exploratory replication on those fixed partitions.

- `data/dataset.json`: canonical model input, complete source-row metadata,
  explicit pending-provenance status and two excluded diagnostic columns.
- `data/straightening_dataset.csv`: convenient export of IDs, partition, six
  predictors and the target.
- `data/source_numeric_records.csv`: source-row export of all nine numeric
  fields, original group/origin cells and the analysis provenance status.
- `data/data_dictionary.json`: units, worksheet coordinates and source hashes.
- `analysis/results_summary.json`: all fitted seed-level metrics, settings,
  conformal quantiles, aggregate results, learning curves and paired comparisons;
  per-row prediction arrays are omitted from this compact published file.
- `analysis/manuscript_metrics.json`, `analysis/model_metrics.csv` and
  `tables/*.csv`: executed numerical results for inspection and manuscript reuse.
- `analysis/*validation.json`: the recorded software replay, seed and lineage
  checks. These checks do not establish physical correctness.

## Reproduce the complete model analysis

The reference execution used Python 3.12.14 and the versions pinned in
`requirements.txt`. From a Python 3.12 environment:

```sh
python -m pip install -r requirements.txt
python reproduce.py
```

The runner trains six baseline families, full MGRE and seven ablations; writes
42 local fitted model bundles; performs 36 learning-curve fits; recalculates the
90% intervals and paired row bootstrap; reloads the models to verify predictions;
exports tables; and generates 16 figures with PNG/SVG versions. The recorded
model-analysis run took approximately 205 seconds on its reference computer.
Runtime and font rendering depend on the environment.

The large `analysis/results.json`, per-row prediction CSV, model bundles and
rendered figures are generated locally instead of being stored in this minimal
release. The complete run uses only the canonical supplied table, not values
reconstructed by the separate lineage audit. No Ansys or other FE solver is
invoked, and no new physical or FE records are produced.

The reference script is also available directly:

```sh
python scripts/run_experiments.py --seeds 40 41 42 --bootstrap-seed 43
python scripts/verify_experiment.py
python scripts/verify_seed_revision.py
python scripts/export_revision_tables.py
python scripts/make_paper_figures.py
```

After the full run, predict with a locally recreated bundle:

```sh
python scripts/predict.py --model models/MGRE_seed40.joblib --data data/dataset.json --output analysis/prediction_replay.json
```

The tree of script/data paths is relative to this repository. Historical paths
inside the unchanged canonical JSON are descriptive import metadata only;
access to those folders is not required.

## Selection and model definition

Baseline grids are selected on validation data using seed 40; model-family
selection uses validation MAE averaged over seeds 40–42. Each applicable MGRE
fit selects its global/local blend on validation data. A validation-trained
error scale is fixed before the separate 1,000-record calibration set supplies
the 901st ranked score. The paired bootstrap uses 1,000 row resamples without
refitting a model. Thickness-shift evaluation retains the fitted predictors and
calibration quantiles.

MGRE learns a logarithmic residual around a positive mechanics-like scale. A
global RBF support-vector regressor is blended with three local histogram
gradient-boosting experts weighted by a Gaussian-mixture gate. The reference
elastic modulus and yield stress are assigned normalization constants, not a
verified calibration of material properties for these rows.

`NoRatioPredictor` removes only the derived predictor descriptors;
`NoResidualPrior` removes the target prior while retaining descriptors/gate;
`NoMechanics` changes all three together; `NoGate` uses one globally trained
HGB branch; `NoGlobal` and `NoLocal` remove their respective prediction branches;
`ConstantInterval` preserves point predictions and changes interval scaling.
All comparisons, including results favoring a baseline, are retained.

## Historical process context and rights

The separately reported circular-beam pilot in the manuscript is not the source
of these 9,000 records and is not reconstructed by this code. Its raw case files
and third-party material datasets or publisher PDFs are not redistributed here.
The numeric model benchmark, its source-field map and reproducible analyses are
the scope of this release.

No new license grant is asserted by this staging release. Any repository license
must be supplied or confirmed by the rights holder. Third-party packages retain
their own licenses. To identify this release, cite the exact Git commit together
with the repository URL and the canonical dataset hash recorded in
`DATA_PROVENANCE.md`.

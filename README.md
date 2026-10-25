# Mechanics guided residual experts for straightening stroke prediction

This repository contains the executable 24 October 2026 revision of MGRE,
validation-selected comparisons, component ablations, prediction intervals,
learning curves and the numerical source data. The previous implementation is
retained as `LegacyMGRE` in the comparison and in `scripts/legacy_benchmark.py`.

## Open FE reference materials added 26 October 2026

The existing 9,000-row learning table, fixed splits, prediction targets and
reported ML results are unchanged. The separately traceable rectangular-bar FE
reference project is now documented in [engineering/README.md](engineering/README.md).

- [FE methods and numerical evidence](engineering/FE_REFERENCE_METHODS.md):
  material parameters, geometry, contact, mesh, eleven load steps, extraction,
  sampled-search and feasible-action definitions, and their limitations.
- [Supplementary Software 1](engineering/Supplementary_Software_1.zip): original
  source/material snapshots, three complete sampled-search records, selected
  native inputs and receipts, benchmark comparisons, and a prepare-only wrapper.
- [Case summary](engineering/reference_cases.csv),
  [package instructions](engineering/PACKAGE_README.md), and
  [archive checksum](engineering/Supplementary_Software_1.zip.sha256).

The compact package supports source review and portable cold-core input
preparation. It omits large native result/restart files and full field exports;
it cannot independently replay the archived warm branches. Existing raw text
exports were re-parsed locally and all 15 checked metrics matched their stored
values. No new FE solve or ML refit was performed for this addition.

These local cases do not establish a native FE origin for each of the current
9,000 learning labels. The full numerical correspondence with the earlier
explicitly synthetic analytical benchmark remains documented in
[DATA_PROVENANCE.md](DATA_PROVENANCE.md). Neither historical provenance artifacts
nor the mechanical scale used by MGRE have been deleted.

## Reproduce the paper analysis

Use Python 3.12 and the pinned dependencies. The repository `.gitattributes`
preserves exact line endings so recorded source hashes also work on Windows:

```sh
python -m pip install -r requirements.txt
python reproduce.py
```

The command fits the frozen configurations, recomputes calibration, all evaluation
predictions, paired bootstrap statistics, learning curves, tables and figures,
then independently checks the saved fitted models. No finite-element solver is
invoked by this code. Local model bundles and PNG figures are generated, rather
than required downloads. Published SVGs provide directly inspectable figure data.

The individual steps are:

```sh
python scripts/run_revision.py
python scripts/build_revision_tables.py
python scripts/make_revision_figures.py
python scripts/verify_revision.py
```

After reproduction, a six-input CSV can be evaluated using a local model bundle:

```sh
python scripts/predict.py --model models/MGRE_seed40.joblib --input data/straightening_dataset.csv --output analysis/prediction_replay.csv
```

## Data and splits

The six inputs are `width_mm`, `thickness_mm`, `span_mm`, `punch_radius_mm`,
`support_radius_mm`, and `prebend_stroke_mm`. The target is
`reference_stroke_mm`. All seven quantities use millimetres. The stroke origin is
defined as first punch contact, excluding free travel and machine compliance.
The numerical data are unchanged from the previous release: 4,800 training,
1,200 validation, 1,000 calibration, 1,000 reference-domain test and 1,000
thickness-shift rows. The thickness shift is 9.25–10 mm, compared with 7–9 mm
in the reference domain. Exact source worksheet coordinates and hashes are in
`data/data_dictionary.json` and the source-row CSV exports.

The author declares the source to be independently completed FE data. The
recorded numerical comparison with an earlier analytical development table is
retained.
`DATA_PROVENANCE.md` gives the evidence and scope. Auxiliary clean-response and
noise columns are excluded from fitting, model selection and calibration. No
new labels or extra synthetic samples were generated in this revision.

## Model and selection protocol

MGRE learns a logarithmic residual relative to a positive beam-inspired scale.
The revised global trend uses cubic univariate splines and all pairwise spline
products. Gaussian responsibilities weight local polynomial residual regressors.
A fixed taper based only on the training envelope attenuates the local correction
outside that envelope. Predictions are reconstructed by the positive scale times
the exponential of the corrected residual. The reference elastic modulus and
yield stress are normalization constants, not material calibration evidence.

The complete selected configuration is:

```json
{
  "representation": "raw",
  "degree": 3,
  "ridge": 0.01,
  "n_experts": 4,
  "local_degree": 3,
  "local_ridge": 1.0,
  "correction_weight": 1.0,
  "taper": true,
  "basis": "tensor_spline",
  "knots": 4
}
```

All hyperparameters were chosen using training and validation only, before this
revision's final evaluation. `analysis/development_search.json` retains every
candidate score, including unsuccessful polynomial alternatives. The frozen
architecture, tuned SVR settings and ablation policy are in
`analysis/development_frozen_spec.json`; `analysis/evaluation_frozen_protocol.json`
records the remaining baseline choices and statistical plan. The previously
examined test partitions make this an exploratory revision, not a newly untouched
confirmation study. No evaluation labels are used to select a revised winner.

Training seeds are 40, 41 and 42. Paired bootstrap seed 43 resamples fixed
mean-across-seed predictions 1,000 times and is not a fourth trained predictor.
Learning curves use nested subsets of 100, 250, 500, 1,000, 2,000 and 4,800 rows,
with subset-order seeds 740, 741 and 742 and fixed full-data hyperparameters.

All compared point models use the same normalized split-conformal procedure.
Validation absolute errors fit a scale predictor; calibration supplies the 901st
of 1,000 normalized residuals for nominal 90% coverage. The same frozen quantile
is used for reference and shifted evaluation. Interval score combines interval
width with a penalty for missed observations; smaller is better. Higher coverage
alone is not interpreted as better, and no coverage guarantee under thickness
shift is claimed.

## Executed results

Values below are averages over training seeds, conditional on the supplied table.
All errors and interval scores are in millimetres.

| Predictor | Test MAE | Test RMSE | Shift RMSE | Test interval score | Shift interval score |
| --- | ---: | ---: | ---: | ---: | ---: |
| MGRE | 0.052198 | 0.067134 | 0.161889 | 0.276774 | 0.885036 |
| Legacy MGRE | 0.055000 | 0.071396 | 0.397500 | 0.295558 | 3.840732 |
| Tuned RBF-SVR | 0.055538 | 0.071780 | 0.266663 | 0.295705 | 1.908940 |
| Polynomial ridge | 0.066623 | 0.085282 | 0.162134 | 0.342553 | 0.830662 |
| MLP | 0.069532 | 0.088649 | 0.229685 | 0.367738 | 1.496674 |
| Gradient boosting | 0.081868 | 0.102957 | 0.513836 | 0.420343 | 5.192735 |
| Random forest | 0.132128 | 0.164639 | 0.615422 | 0.639906 | 5.105442 |
| Ridge | 0.188296 | 0.242604 | 0.457884 | 0.803162 | 2.114077 |
| Mean | 1.653434 | 1.968337 | 2.398396 | 4.842779 | 9.051189 |

The frozen primary model is not the best in every component comparison. Removing
support attenuation improves the observed thickness-shift RMSE, while removal of
the mechanical response prior slightly improves reference-domain RMSE but worsens
shifted RMSE. These outcomes are retained rather than used to reselect a new
primary model after evaluation. The ablation table reports the full tradeoff.

`analysis/revision_results.json` contains the complete unrounded metrics,
including negative results, all ablations and seed variation. The independently
recomputed verification is in `analysis/revision_verification.json`.
`tables/` contains editable CSV tables; `figures/figure_manifest.json` maps the
figures to their generating code. A fresh run writes every prediction to
`analysis/predictions.csv` and fitted models to `models/`.

## Source and rights

`RELEASE_MANIFEST.json` records hashes of the published files, including the
new engineering archive. OPARA-derived comparison records retain their original
CC BY-NC 4.0 attribution and conditions; see
[engineering/THIRD_PARTY_DATA_NOTICE.txt](engineering/THIRD_PARTY_DATA_NOTICE.txt). The separate historical circular-beam study provides
context.

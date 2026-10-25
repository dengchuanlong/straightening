# Data provenance and reproducibility scope

The author reaffirmed on 24 and 26 October 2026 that the current 9,000-row table
was completed by FE work on an institutional laboratory server. This remains an
author declaration about that table. On 26 October the author permitted disclosure
of the supplied local reference project's methods and data. Selected native
inputs, solver receipts and search records for three local rectangular-bar cases
are now supplied in `engineering/Supplementary_Software_1.zip`. These establish
traceable local calculations; they do not provide the missing per-row native
execution mapping for the 9,000 learning labels. The analytical numerical
correspondence and its audit status are retained.

The supplied source file was `fea_dataset.xlsx`, worksheet `dataset`, header
row 1 and observation rows 2–9001. Columns E–J are the six predictors, K is the
reference stroke, and L–M are two diagnostic columns. The workbook SHA-256 is:

```text
171aee2faac094fb6b0ffd912c7c881ab458a8bea03a16ce21168a3a79595274
```

The unmodified imported canonical `data/dataset.json` SHA-256 is:

```text
cb0bb4d147649378d5282b611e133f75df48e40f5e5f30af70f6813e13ff287b
```

## What the source comparison established

The workbook numeric values reproduce the earlier disclosed analytical
development dataset. The audit compared 9,000 rows × 9 numeric fields = 81,000
values: the six inputs, `reference_stroke_mm`,
`clean_reference_stroke_mm` and `noise_std_mm`. Every row matched at relative
tolerance 1e-12 and absolute tolerance 1e-10. The maximum absolute difference
was 9.947598300641403e-13, consistent with Excel serialization rounding.
Source IDs/origin text differ; changing those cells does not establish new
solver-generated records. See `data/source_comparison.json` for field-level
differences, representative rows and the original source hashes.

The original workbook contains the text `FINITE_ELEMENT_ANALYSIS`. That text is
preserved as `source_declared_origin`; the analysis uses
`AUTHOR_SUPPLIED_PROVENANCE_PENDING` instead. Native solver inputs, completion
records and outputs have not been linked case by case to these rows. The release
does not assert 9,000 independent FE solves, validated optimum strokes, final
unloaded geometry or physical machine accuracy.

## Independently check the analytical numerical lineage

```sh
python scripts/verify_source_lineage.py
```

This separate audit reconstructs the disclosed historical analytical response
and random design **in memory**, compares all nine numeric fields and the fixed
partition assignments, and writes `analysis/source_lineage_validation.json`.
It neither changes the canonical dataset nor supplies reconstructed records to
the model-training pipeline. The artificial response coefficients and noise
are numerical development choices, not material laws or calibrated FE error.

Historical analytical-generation seeds were design 2026101601, shifted design
2026101602, noise 2026101604 and partition 2026101603. These are lineage-audit
settings and are distinct from the requested current training seeds 40, 41 and
42 and paired-bootstrap seed 43.

The known analytical `clean_reference_stroke_mm` and `noise_std_mm` fields are
diagnostic only. They are excluded from predictor inputs, model fitting,
hyperparameter selection, scale fitting, calibration targets and partitioning.

## Row tracing and group identifiers

`source_excel_row` identifies the original worksheet row. The original group
cells are retained in `source_group_id`. Excel converted group identifiers at
rows 1410 and 5947 to numbers; the import therefore assigns a deterministic hash
of the six imported inputs as the computational `group_id`. This supplies exact
numeric-row grouping and prevents tuple duplication across partitions; it does
not prove independence of physical specimens or simulations.

`data/source_numeric_records.csv` exposes the nine numeric fields and source
cells; `data/straightening_dataset.csv` gives the smaller model-facing export.
All distances in the predictors and reference target are in millimetres.

## Scope of the recorded verification

The current analysis reruns the improved MGRE, the legacy model, tuned baselines, and ablations using training seeds 40, 41 and 42. The verification receipt recalculates saved predictions, metrics, interval quantiles and paired bootstrap results. Model selection uses the training and validation partitions; the calibration partition supplies only the conformal quantile. Previously inspected evaluation partitions remain exploratory. See README.md and analysis/revision_verification.json for the current executed counts and checks.

The historical three-diameter circular-beam report is a distinct four-input
pilot. Its reported endpoints provide process context; they do not supply a
row-level origin or native FE validation for the present six-input benchmark.

The 26 October addition includes selected OPARA-derived benchmark comparison
records with their original attribution and CC BY-NC 4.0 conditions. The raw
material-specimen archive, large FE result/restart files, complete copied-field
text exports, publisher PDFs and manuscript drafts are not included. The source
workbook remains represented by its numeric export, source coordinates and
checksum. A verified FE replacement would require its own traceable export and
a fresh run rather than relabeling the current records.

## Why the earlier analytical artifacts are retained

The original generator explicitly describes a synthetic analytical toy, using a
designed nonlinear mean and artificial heteroscedastic Gaussian noise; it does
not invoke an FE solver. The original table and an in-memory reconstruction both
match the current nine numerical columns and all partition assignments. They
therefore retain provenance value even though the current training entry point
does not call the old generator. Deleting that evidence would neither change the
current targets nor resolve their origin.

The current MGRE positive mechanical scale is a separate, active part of the
prediction model. It is not the full historical label generator and remains in
use. The latest disclosure does not change either algorithm or any data value.

## Scope of the newly disclosed FE evidence

The reference framework uses RECT3D004, the v002 CHAB3–Voce material card and
the B mesh. The three historical best-sampled local strokes are 14.641792,
8.103878 and 15.238613 mm; their final unloaded deviations are approximately
0.119915, 0.115181 and 0.140392 mm. They are executed reference actions, not
forward evaluations of MGRE predictions, and are not asserted to be rows of the
current learning table. Best-sampled search, later policy-conditioned feasible
action and the existing reference_stroke_mm target remain distinct definitions.
Formal dataset qualification remains false in the supplied local records.

The 15/15 matching extraction checks used large raw text files retained locally.
The compact public package omits those large fields and native restart binaries,
so it does not offer a standalone replay of that check or the warm calculations.
Its portable wrapper only prepares a cold-core input and does not launch MAPDL.
See engineering/FE_REFERENCE_METHODS.md and engineering/PACKAGE_README.md for
the exact reproduction levels, public benchmark scope and remaining dependencies.


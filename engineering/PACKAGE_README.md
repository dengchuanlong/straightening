# Supplementary Software 1 — RECT3D004 reference FE review package

This local package contains original model/search/postprocessing source, frozen V002
material files, three complete historical sampled-search records, their original best
warm inputs and text receipts, selected-B public four-point-bending comparisons, and
method-review JSON. Original copied files are byte-for-byte unchanged. MANIFEST.json
records the SHA-256, byte size and original absolute source path of every payload file;
generated files are marked explicitly. Historical absolute paths inside copied records
are evidence, not portable run commands. No new FE simulation or ML training was run
to construct this package. No formal qualification has been granted.

## Three distinct levels of reproducibility

1. **Source-record review.** Read the original source and complete search/result/status/
   command JSON, original input.inp, solver text logs, and comparison CSV/JSON. The three
   selected strokes are 14.641792, 8.103878 and 15.238613 mm (B0001/P0008/R0004).
   Their saved final chord errors are 0.11991514155457911, 0.11518078590588862 and
   0.14039192416958007 mm. These are historical warm V003 results, not new computations.
   The saved qualified_for_formal_dataset and formal_generation_unlocked flags remain
   false. A completed best-sampled local search is not proof of a global optimum.

2. **Portable preparation only.** With Python 3.11+ (tested with 3.12.14) and NumPy, the wrapper below loads
   only the original rect_model.py and binds its MATERIAL path in memory to the bundled
   V002 card. It reads an exact extracted historical config and its selected stroke,
   then writes a complete cold-core input.inp, model_metadata.json, config.json and
   preparation_receipt.json to a new or empty external directory. It has no solve option
   and never imports trial.py or solver_runner.py. Source files are not modified.
   The model's cold history includes A/B/C0/C/D through load step 11. This cold-core
   preparation does not apply the historical V003 warm continuation transformer,
   does not replay its native restart state and must not be presented as reproducing
   the historical warm result or as proving convergence or label accuracy.

   ```text
   python -B /path/to/Supplementary_Software_1/verify_package.py
   python -B /path/to/Supplementary_Software_1/prepare_case.py --case B0001 --output /new/empty/output
   ```

   On Windows, quote paths containing spaces. Other case choices are P0008 and R0004.
   Invocation is independent of the working directory. Any existing nonempty output
   directory is refused. The package directory itself cannot be an output target.
   Original preparation used NumPy 2.3.5; the included validation record reports the
   actually tested bundled Python/NumPy versions, without claiming all versions tested.

3. **Full FE recomputation.** Requires a separate licensed ANSYS/MAPDL environment,
   Windows-specific runner dependencies, validated solver path/resource adaptation,
   and independent execution and numerical review. Original records used ANSYS 2026 R1
   Windows x64, four cores. solver_runner.py retains its historical absolute EXE path.
   No solver/license, native restart state, or full field archive is included. Full
   native warm replay is impossible from this light package alone: .rst/.rdb/.r006 and
   other restart binaries are omitted. Full standalone re-parsing of all fields is
   also not available because large copied integration-point listings are omitted.
   Historical reparse verification is supplied as evidence of that earlier read-only
   check, not as a test readers can repeat with omitted fields. Complete cold FE solves
   can be designed from prepared inputs, but were not executed here; they need new
   completion records and a separate cold/warm comparison before equivalence is claimed.
   The search libraries are auditable source, not a portable one-command production
   pipeline. No cleanup, recovery-kill or large-batch launch script is bundled.

## Layout and interpretation

- straightening_study/full3d_rect_20261007: original relative source/evidence layout.
- straightening_study/auto_run_20261001: frozen material card and shared source dependencies.
- review_cases: exact config values extracted from each complete search_result.config,
  plus a derived human-readable reference summary; JSON pointers are in the manifest.
- cases_index.json: portable config/stroke index, not new physical labels.
- verification: prior read-only source-field reparse evidence and package preparation checks.
- provenance_9000: numerical-lineage evidence only, not training data or an FE row mapping.

The selected-B benchmark supplies force/DIC comparisons from one public four-point
bending specimen. Its 696 time points are not 696 independent experiments. It does not
directly validate reverse-straightening machine accuracy, every optimized stroke or
the current 9000 ML labels. Fixed-stroke time/contact checks with inconclusive overall
status remain inconclusive; software checks are not new physical experiments.

All OPARA-derived files retain the original attribution and CC BY-NC 4.0 conditions
in THIRD_PARTY_DATA_NOTICE.txt. No blanket new licence or re-licensing is asserted for
original source, data, ANSYS software or third-party material. Consult original rights
holders for uses beyond the applicable permissions. The four raw public specimen CSVs
and the complete material-identification raw archive are not bundled; raw-source hashes
and roles are retained in provenance. Their acquisition is separate from prepare-only.

The three local FE records and public bending comparisons must not be substituted for
the 9000-row reference_stroke_mm provenance. The authors report a server FE origin;
the disclosed full numerical match to the earlier synthetic benchmark is retained.
This package does not independently trace 9000 native FE labels. The old generator is
not used as training input and the old synthetic table has not been deleted.

"""Compare the supplied table with its disclosed analytical development lineage.

This audit reconstructs the historical analytical response in memory. It does
not invoke a finite-element solver, modify dataset.json, create new training
records, or feed its reconstructed values to the prediction experiments.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["width_mm", "thickness_mm", "span_mm", "punch_radius_mm", "support_radius_mm", "prebend_stroke_mm"]
NUMERIC_FIELDS = FEATURES + ["reference_stroke_mm", "clean_reference_stroke_mm", "noise_std_mm"]
HISTORICAL_SEEDS = {"design": 2026101601, "ood_design": 2026101602, "noise": 2026101604, "split": 2026101603}


def reconstruct():
    bounds = np.array([[30, 40], [7, 9], [180, 260], [10, 25], [10, 25], [12, 16]], dtype=float)
    x = np.random.default_rng(HISTORICAL_SEEDS["design"]).uniform(bounds[:, 0], bounds[:, 1], size=(8000, 6))
    shifted = bounds.copy()
    shifted[1] = [9.25, 10]
    xo = np.random.default_rng(HISTORICAL_SEEDS["ood_design"]).uniform(shifted[:, 0], shifted[:, 1], size=(1000, 6))
    x = np.vstack([x, xo])
    b, h, length, rp, rs, u = x.T
    a, t, ell = (b - 35) / 5, h - 8, (length - 220) / 40
    p, r = (rp - 17.5) / 7.5, (rs - 17.5) / 7.5
    dy = 1000.121 * length**2 / (6 * 204401.0 * h)
    q = u / dy
    clean = ((0.76 * u * (length / 260)**2 + 0.36 * dy)
             * (1 + 0.022 * a + 0.055 * t + 0.018 * (h / rp - h / rs))
             + 0.42 * np.tanh((q - 2.7) / 0.50)
             + 0.20 * np.sin(0.8 * np.pi * ell) * t
             + 0.10 * a * p + 0.16 * np.sin(np.pi * p) * np.cos(np.pi * r)
             + 0.22 * expit((q - 3.1) / 0.18) * (t + 0.35 * ell)
             + 0.12 * (h / rp)**1.4)
    scale = 0.025 + 0.035 * ((q - 2) / 2)**2 + 0.025 * np.abs(t) + 0.015 * (p - r)**2
    reference = clean + scale * np.random.default_rng(HISTORICAL_SEEDS["noise"]).normal(size=len(x))
    expected = np.column_stack([x, reference, clean, scale])
    permutation = np.random.default_rng(HISTORICAL_SEEDS["split"]).permutation(8000)
    splits = np.full(9000, "ood", dtype=object)
    cursor = 0
    for name, count in [("train", 4800), ("validation", 1200), ("calibration", 1000), ("test", 1000)]:
        splits[permutation[cursor:cursor + count]] = name
        cursor += count
    return expected, splits


def main():
    source = ROOT / "data/dataset.json"
    digest_before = hashlib.sha256(source.read_bytes()).hexdigest()
    dataset = json.loads(source.read_text(encoding="utf-8"))
    observed = np.array([[row[key] for key in NUMERIC_FIELDS] for row in dataset["rows"]], dtype=float)
    expected, splits = reconstruct()
    assert observed.shape == expected.shape == (9000, 9)
    tolerance = {"relative": 1e-12, "absolute": 1e-10}
    matching = np.isclose(observed, expected, rtol=tolerance["relative"], atol=tolerance["absolute"])
    split_matching = [row["split"] == str(split) for row, split in zip(dataset["rows"], splits)]
    difference = np.abs(observed - expected)
    report = {
        "passed": bool(matching.all() and all(split_matching)),
        "audit_scope": "Analytical numerical-lineage comparison; not a finite-element validation.",
        "historical_analytical_seeds": HISTORICAL_SEEDS,
        "training_seeds_are_separate": [40, 41, 42],
        "paired_bootstrap_seed_is_separate": 43,
        "rows_compared": 9000,
        "numeric_fields_compared": NUMERIC_FIELDS,
        "numeric_values_compared": int(observed.size),
        "matching_numeric_values": int(matching.sum()),
        "matching_rows_all_nine_fields": int(matching.all(axis=1).sum()),
        "matching_partition_assignments": int(sum(split_matching)),
        "maximum_absolute_difference": float(difference.max()),
        "maximum_absolute_difference_by_field": dict(zip(NUMERIC_FIELDS, difference.max(axis=0).tolist())),
        "tolerance": tolerance,
        "canonical_dataset_sha256": digest_before,
        "canonical_dataset_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == digest_before,
        "native_solver_invoked": False,
        "reconstructed_values_used_for_model_fitting": False,
        "interpretation": "The supplied numeric table reproduces the disclosed analytical development design/response within Excel precision; this comparison does not establish independent FE records."
    }
    assert report["passed"] and report["canonical_dataset_unchanged"]
    output = ROOT / "analysis/source_lineage_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()

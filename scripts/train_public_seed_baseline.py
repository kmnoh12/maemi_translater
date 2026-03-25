from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from baseline_audio_utils import extract_features


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "windows_csv",
        type=Path,
        nargs="?",
        default=ROOT / "ml-workspace" / "reports" / "public_seed_windows.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "public_seed_baseline_report.json",
    )
    parser.add_argument(
        "--model-out",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "public_seed_baseline.joblib",
    )
    args = parser.parse_args()

    windows_csv = args.windows_csv.resolve()
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with windows_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)

    X = []
    y = []
    groups = []
    meta = []
    for row in rows:
        audio_path = ROOT / row["audio_path"]
        features = extract_features(audio_path, float(row["start_sec"]), float(row["window_sec"]))
        X.append(features)
        y.append(row["species_code"])
        groups.append(row["observation_id"])
        meta.append({"window_id": row["window_id"], "sound_id": row["sound_id"]})

    X = np.stack(X)
    y = np.asarray(y)
    groups = np.asarray(groups)

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)
    logo = LeaveOneGroupOut()

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=5000)),
        ]
    )

    all_true = []
    all_pred = []
    fold_details = []

    for fold_idx, (train_idx, test_idx) in enumerate(logo.split(X, y_encoded, groups), start=1):
        pipeline.fit(X[train_idx], y_encoded[train_idx])
        preds = pipeline.predict(X[test_idx])
        all_true.extend(y_encoded[test_idx].tolist())
        all_pred.extend(preds.tolist())
        fold_details.append(
            {
                "fold": fold_idx,
                "held_out_observation_ids": sorted(set(groups[test_idx].tolist())),
                "test_size": int(len(test_idx)),
            }
        )

    labels = list(range(len(encoder.classes_)))
    cm = confusion_matrix(all_true, all_pred, labels=labels)
    report = classification_report(
        all_true,
        all_pred,
        labels=labels,
        target_names=encoder.classes_.tolist(),
        output_dict=True,
        zero_division=0,
    )

    confusion_pairs = []
    for i, true_name in enumerate(encoder.classes_):
        for j, pred_name in enumerate(encoder.classes_):
            if i != j and cm[i, j] > 0:
                confusion_pairs.append(
                    {"true": true_name, "pred": pred_name, "count": int(cm[i, j])}
                )

    by_class_counts = Counter(y.tolist())
    by_group_counts = defaultdict(int)
    for group in groups.tolist():
        by_group_counts[group] += 1

    result = {
        "dataset_summary": {
            "num_windows": int(len(rows)),
            "num_observations": int(len(set(groups.tolist()))),
            "classes": encoder.classes_.tolist(),
            "windows_per_class": dict(by_class_counts),
        },
        "cross_validation": {
            "strategy": "LeaveOneGroupOut(observation_id)",
            "num_folds": len(fold_details),
            "folds": fold_details,
        },
        "metrics": report,
        "confusion_matrix": {
            "labels": encoder.classes_.tolist(),
            "matrix": cm.tolist(),
            "off_diagonal": sorted(confusion_pairs, key=lambda x: x["count"], reverse=True),
        },
        "notes": [
            "This report is built from public seed audio only.",
            "There is no no_cicada class in this run.",
            "This is a pipeline check, not a deployment-grade validation.",
        ],
        "group_window_counts": dict(by_group_counts),
    }

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    args.model_out = args.model_out.resolve()
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    pipeline.fit(X, y_encoded)
    joblib.dump(
        {
            "pipeline": pipeline,
            "classes": encoder.classes_.tolist(),
            "window_sec": float(rows[0]["window_sec"]) if rows else 3.0,
            "hop_sec": 1.5,
            "feature_version": "mfcc20_plus_spectral_stats_v1",
        },
        args.model_out,
    )
    print(f"Wrote baseline report to {out}")
    print(f"Wrote model artifact to {args.model_out}")


if __name__ == "__main__":
    main()

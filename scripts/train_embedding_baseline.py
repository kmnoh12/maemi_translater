from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import SGDClassifier


ROOT = Path(__file__).resolve().parent.parent


def load_metadata(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("features_npz", type=Path)
    parser.add_argument("metadata_csv", type=Path)
    parser.add_argument("--group-column", default="observation_id")
    parser.add_argument("--num-splits", type=int, default=8)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_logmel_svm_report.json",
    )
    parser.add_argument(
        "--model-out",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "inat_full_logmel_svm_model.joblib",
    )
    args = parser.parse_args()

    features_blob = np.load(args.features_npz.resolve(), allow_pickle=True)
    X = features_blob["X"]
    metadata_rows = load_metadata(args.metadata_csv.resolve())

    y = np.asarray([row["species_code"] for row in metadata_rows])
    groups = np.asarray([row[args.group_column] for row in metadata_rows])

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                SGDClassifier(
                    loss="log_loss",
                    penalty="l2",
                    alpha=1e-4,
                    class_weight="balanced",
                    max_iter=2000,
                    tol=1e-3,
                    random_state=42,
                ),
            ),
        ]
    )
    splitter = GroupShuffleSplit(n_splits=args.num_splits, test_size=args.test_size, random_state=42)

    all_true: list[int] = []
    all_pred: list[int] = []
    folds: list[dict[str, object]] = []
    for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(X, y_encoded, groups), start=1):
        pipeline.fit(X[train_idx], y_encoded[train_idx])
        preds = pipeline.predict(X[test_idx])
        all_true.extend(y_encoded[test_idx].tolist())
        all_pred.extend(preds.tolist())
        folds.append(
            {
                "fold": fold_idx,
                "held_out_group_values": sorted(set(groups[test_idx].tolist())),
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

    off_diagonal = []
    for i, true_label in enumerate(encoder.classes_):
        for j, pred_label in enumerate(encoder.classes_):
            if i != j and cm[i, j] > 0:
                off_diagonal.append({"true": true_label, "pred": pred_label, "count": int(cm[i, j])})

    result = {
        "dataset_summary": {
            "num_feature_rows": int(len(metadata_rows)),
            "num_groups": int(len(set(groups.tolist()))),
            "group_column": args.group_column,
            "classes": encoder.classes_.tolist(),
            "feature_version": str(features_blob["feature_version"]),
            "window_sec": float(features_blob["window_sec"]),
            "hop_sec": float(features_blob["hop_sec"]),
            "rows_per_class": dict(Counter(y.tolist())),
        },
        "cross_validation": {
            "strategy": f"GroupShuffleSplit({args.group_column}, n_splits={args.num_splits}, test_size={args.test_size})",
            "num_folds": len(folds),
            "folds": folds,
        },
        "metrics": report,
        "confusion_matrix": {
            "labels": encoder.classes_.tolist(),
            "matrix": cm.tolist(),
            "off_diagonal": sorted(off_diagonal, key=lambda x: x["count"], reverse=True),
        },
    }

    args.report_out = args.report_out.resolve()
    args.model_out = args.model_out.resolve()
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    pipeline.fit(X, y_encoded)
    joblib.dump(
        {
            "pipeline": pipeline,
            "classes": encoder.classes_.tolist(),
            "feature_version": str(features_blob["feature_version"]),
            "window_sec": float(features_blob["window_sec"]),
            "hop_sec": float(features_blob["hop_sec"]),
            "model_type": "SGDClassifier(log_loss)",
        },
        args.model_out,
    )
    print(f"Wrote report to {args.report_out}")
    print(f"Wrote model to {args.model_out}")


if __name__ == "__main__":
    main()

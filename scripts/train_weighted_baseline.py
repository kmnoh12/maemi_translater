from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent.parent


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_inventory_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row.get("observation_id", ""), row.get("sound_id", ""))
        lookup[key] = row
    return lookup


def truth_pred_pairs(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]) -> list[dict[str, object]]:
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(classes))))
    pairs: list[dict[str, object]] = []
    for i, true_label in enumerate(classes):
        for j, pred_label in enumerate(classes):
            if i != j and cm[i, j] > 0:
                pairs.append({"true": true_label, "pred": pred_label, "count": int(cm[i, j])})
    return sorted(pairs, key=lambda item: item["count"], reverse=True)


def metrics_payload(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]) -> dict[str, object]:
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "per_class": {
            label: {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": int(report[label]["support"]),
            }
            for label in classes
        },
        "top_confusions": truth_pred_pairs(y_true, y_pred, classes)[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("features_npz", type=Path)
    parser.add_argument("metadata_csv", type=Path)
    parser.add_argument("inventory_csv", type=Path)
    parser.add_argument("--group-column", default="observation_id")
    parser.add_argument("--korea-weight", type=float, default=3.0)
    parser.add_argument("--pair-weight", type=float, default=1.75)
    parser.add_argument("--focus-pair", default="aemaemi,chammaemi")
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_weighted_feature_report.json",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_weighted_feature_summary.md",
    )
    parser.add_argument(
        "--model-out",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "inat_full_weighted_feature_model.joblib",
    )
    args = parser.parse_args()

    focus_pair = tuple(part.strip() for part in args.focus_pair.split(",") if part.strip())
    if len(focus_pair) != 2:
        raise SystemExit("--focus-pair must contain exactly two comma-separated species codes")

    features_blob = np.load(args.features_npz.resolve(), allow_pickle=True)
    X = features_blob["X"]
    metadata_rows = load_csv(args.metadata_csv.resolve())
    inventory_lookup = build_inventory_lookup(load_csv(args.inventory_csv.resolve()))

    y = np.asarray([row["species_code"] for row in metadata_rows])
    groups = np.asarray([row[args.group_column] for row in metadata_rows])

    is_korea: list[bool] = []
    sample_weights: list[float] = []
    for row in metadata_rows:
        key = (row.get("observation_id", ""), row.get("sound_id", ""))
        inv = inventory_lookup.get(key, {})
        korea_flag = str(inv.get("is_korea", "")).lower() == "true"
        is_korea.append(korea_flag)
        weight = 1.0
        if korea_flag:
            weight *= args.korea_weight
        if row["species_code"] in focus_pair:
            weight *= args.pair_weight
        sample_weights.append(weight)

    is_korea_arr = np.asarray(is_korea, dtype=bool)
    sample_weights_arr = np.asarray(sample_weights, dtype=float)
    focus_mask = np.asarray([label in focus_pair for label in y], dtype=bool)

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)
    classes = encoder.classes_.tolist()

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=5000)),
        ]
    )
    logo = LeaveOneGroupOut()

    all_true: list[int] = []
    all_pred: list[int] = []
    fold_summaries: list[dict[str, object]] = []
    for fold_idx, (train_idx, test_idx) in enumerate(logo.split(X, y_encoded, groups), start=1):
        pipeline.fit(
            X[train_idx],
            y_encoded[train_idx],
            clf__sample_weight=sample_weights_arr[train_idx],
        )
        preds = pipeline.predict(X[test_idx])
        all_true.extend(y_encoded[test_idx].tolist())
        all_pred.extend(preds.tolist())
        fold_summaries.append(
            {
                "fold": fold_idx,
                "held_out_group_values": sorted(set(groups[test_idx].tolist())),
                "test_size": int(len(test_idx)),
                "korea_rows": int(is_korea_arr[test_idx].sum()),
            }
        )

    y_true = np.asarray(all_true, dtype=int)
    y_pred = np.asarray(all_pred, dtype=int)

    overall = metrics_payload(y_true, y_pred, classes)
    korea_idx = np.where(is_korea_arr)[0]
    focus_idx = np.where(focus_mask)[0]
    korea_focus_idx = np.where(is_korea_arr & focus_mask)[0]

    result = {
        "dataset_summary": {
            "num_feature_rows": int(len(metadata_rows)),
            "num_groups": int(len(set(groups.tolist()))),
            "group_column": args.group_column,
            "classes": classes,
            "feature_version": str(features_blob["feature_version"]),
            "window_sec": float(features_blob["window_sec"]),
            "hop_sec": float(features_blob["hop_sec"]),
            "rows_per_class": dict(Counter(y.tolist())),
            "korea_rows": int(is_korea_arr.sum()),
            "korea_weight": args.korea_weight,
            "pair_weight": args.pair_weight,
            "focus_pair": list(focus_pair),
        },
        "cross_validation": {
            "strategy": f"LeaveOneGroupOut({args.group_column})",
            "num_folds": len(fold_summaries),
            "folds": fold_summaries,
        },
        "metrics": {
            "overall": overall,
            "korea_only": metrics_payload(y_true[korea_idx], y_pred[korea_idx], classes) if len(korea_idx) else {},
            "focus_pair_only": metrics_payload(y_true[focus_idx], y_pred[focus_idx], classes) if len(focus_idx) else {},
            "korea_focus_pair_only": metrics_payload(y_true[korea_focus_idx], y_pred[korea_focus_idx], classes) if len(korea_focus_idx) else {},
        },
    }

    args.report_out = args.report_out.resolve()
    args.summary_out = args.summary_out.resolve()
    args.model_out = args.model_out.resolve()
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    pipeline.fit(X, y_encoded, clf__sample_weight=sample_weights_arr)
    joblib.dump(
        {
            "pipeline": pipeline,
            "classes": classes,
            "feature_version": str(features_blob["feature_version"]),
            "window_sec": float(features_blob["window_sec"]),
            "hop_sec": float(features_blob["hop_sec"]),
            "weighting": {
                "korea_weight": args.korea_weight,
                "pair_weight": args.pair_weight,
                "focus_pair": list(focus_pair),
            },
        },
        args.model_out,
    )

    summary_lines = [
        "# Weighted Baseline Summary",
        "",
        f"- Korea weight: {args.korea_weight}",
        f"- Pair weight: {args.pair_weight}",
        f"- Focus pair: {focus_pair[0]} / {focus_pair[1]}",
        f"- Overall accuracy: {overall['accuracy']:.4f}",
        f"- Overall macro F1: {overall['macro_f1']:.4f}",
    ]
    korea_metrics = result["metrics"]["korea_only"]
    if korea_metrics:
        summary_lines.append(f"- Korea-only accuracy: {korea_metrics['accuracy']:.4f}")
        summary_lines.append(f"- Korea-only macro F1: {korea_metrics['macro_f1']:.4f}")
    focus_metrics = result["metrics"]["korea_focus_pair_only"]
    if focus_metrics:
        summary_lines.append(f"- Korea focus-pair accuracy: {focus_metrics['accuracy']:.4f}")
        summary_lines.append(f"- Korea focus-pair macro F1: {focus_metrics['macro_f1']:.4f}")
    summary_lines.extend(["", "## Top confusions"])
    for row in overall["top_confusions"][:10]:
        summary_lines.append(f"- {row['true']} -> {row['pred']}: {row['count']}")
    args.summary_out.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Wrote report to {args.report_out}")
    print(f"Wrote summary to {args.summary_out}")
    print(f"Wrote model to {args.model_out}")


if __name__ == "__main__":
    main()

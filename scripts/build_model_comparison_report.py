from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_accuracy(report: dict) -> tuple[float, float]:
    metrics = report["metrics"]
    if "accuracy" in metrics:
        return float(metrics["accuracy"]), float(metrics["macro avg"]["f1-score"])
    return float(metrics["overall"]["accuracy"]), float(metrics["overall"]["macro_f1"])


def top_pair(report: dict, true_label: str, pred_label: str) -> int:
    if "confusion_matrix" in report:
        rows = report["confusion_matrix"]["off_diagonal"]
    else:
        rows = report["metrics"]["overall"]["top_confusions"]
    for row in rows:
        if row["true"] == true_label and row["pred"] == pred_label:
            return int(row["count"])
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=ROOT / "ml-workspace" / "reports" / "inat_full_feature_report.json")
    parser.add_argument("--weighted", type=Path, default=ROOT / "ml-workspace" / "reports" / "inat_full_weighted_feature_report.json")
    parser.add_argument("--embedding", type=Path, default=ROOT / "ml-workspace" / "reports" / "inat_full_logmel_svm_report.json")
    parser.add_argument("--out-json", type=Path, default=ROOT / "ml-workspace" / "reports" / "model_comparison_report.json")
    parser.add_argument("--out-md", type=Path, default=ROOT / "ml-workspace" / "reports" / "model_comparison_report.md")
    args = parser.parse_args()

    base = load_json(args.baseline)
    weighted = load_json(args.weighted)
    embedding = load_json(args.embedding)

    payload = {
        "baseline": {
            "accuracy": extract_accuracy(base)[0],
            "macro_f1": extract_accuracy(base)[1],
            "aemaemi_to_chammaemi": top_pair(base, "aemaemi", "chammaemi"),
            "chammaemi_to_aemaemi": top_pair(base, "chammaemi", "aemaemi"),
        },
        "weighted": {
            "accuracy": extract_accuracy(weighted)[0],
            "macro_f1": extract_accuracy(weighted)[1],
            "aemaemi_to_chammaemi": top_pair(weighted, "aemaemi", "chammaemi"),
            "chammaemi_to_aemaemi": top_pair(weighted, "chammaemi", "aemaemi"),
        },
        "embedding": {
            "accuracy": extract_accuracy(embedding)[0],
            "macro_f1": extract_accuracy(embedding)[1],
            "aemaemi_to_chammaemi": top_pair(embedding, "aemaemi", "chammaemi"),
            "chammaemi_to_aemaemi": top_pair(embedding, "chammaemi", "aemaemi"),
        },
    }

    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Model Comparison Report",
        "",
        "| model | accuracy | macro_f1 | aemaemi->chammaemi | chammaemi->aemaemi |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("baseline", "weighted", "embedding"):
        row = payload[name]
        lines.append(
            f"| {name} | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | {row['aemaemi_to_chammaemi']} | {row['chammaemi_to_aemaemi']} |"
        )
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")


if __name__ == "__main__":
    main()

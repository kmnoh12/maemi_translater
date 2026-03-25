from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    reports = {
        "focus_4species": ROOT / "ml-workspace" / "reports" / "focus_species_cnn_report.json",
        "cnn_6species_augmented": ROOT / "ml-workspace" / "reports" / "cnn_balanced_stratified_augmented_report.json",
        "baseline_full": ROOT / "ml-workspace" / "reports" / "inat_full_feature_report.json",
    }
    out_json = ROOT / "ml-workspace" / "reports" / "confusion_experiment_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "confusion_experiment_report.md"

    payload: dict[str, object] = {}
    for key, path in reports.items():
        if not path.exists():
            continue
        report = load_json(path)
        if "test_metrics" in report:
            accuracy = report["test_metrics"]["accuracy"]
            macro_f1 = report["test_metrics"]["macro avg"]["f1-score"]
            off_diag = report["confusion_matrix"]["off_diagonal"][:10]
        else:
            accuracy = report["metrics"]["accuracy"]
            macro_f1 = report["metrics"]["macro avg"]["f1-score"]
            off_diag = report["confusion_matrix"]["off_diagonal"][:10]
        payload[key] = {
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "top_confusions": off_diag,
        }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Confusion Experiment Report", ""]
    for key, row in payload.items():
        lines.append(f"## {key}")
        lines.append(f"- accuracy: {row['accuracy']:.4f}")
        lines.append(f"- macro_f1: {row['macro_f1']:.4f}")
        for confusion in row["top_confusions"]:
            lines.append(f"- {confusion['true']} -> {confusion['pred']}: {confusion['count']}")
        lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

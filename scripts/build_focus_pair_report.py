from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline-report",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_feature_report.json",
    )
    parser.add_argument(
        "--weighted-report",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_weighted_feature_report.json",
    )
    parser.add_argument("--pair", default="aemaemi,chammaemi")
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "focus_pair_report.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "focus_pair_report.md",
    )
    args = parser.parse_args()

    pair = tuple(part.strip() for part in args.pair.split(",") if part.strip())
    if len(pair) != 2:
        raise SystemExit("--pair must contain exactly two comma-separated species codes")

    baseline = json.loads(args.baseline_report.read_text(encoding="utf-8"))
    weighted = json.loads(args.weighted_report.read_text(encoding="utf-8"))

    def extract_pair_confusions(report: dict) -> list[dict[str, object]]:
        rows = report["confusion_matrix"]["off_diagonal"] if "confusion_matrix" in report else report["metrics"]["overall"]["top_confusions"]
        return [
            row for row in rows
            if row["true"] in pair and row["pred"] in pair
        ]

    payload = {
        "pair": list(pair),
        "baseline": {
            "overall_accuracy": baseline["metrics"]["accuracy"] if "accuracy" in baseline["metrics"] else baseline["metrics"]["overall"]["accuracy"],
            "overall_macro_f1": baseline["metrics"]["macro avg"]["f1-score"] if "macro avg" in baseline["metrics"] else baseline["metrics"]["overall"]["macro_f1"],
            "pair_confusions": extract_pair_confusions(baseline),
        },
        "weighted": {
            "overall_accuracy": weighted["metrics"]["overall"]["accuracy"],
            "overall_macro_f1": weighted["metrics"]["overall"]["macro_f1"],
            "korea_only_accuracy": weighted["metrics"]["korea_only"].get("accuracy", 0.0),
            "korea_only_macro_f1": weighted["metrics"]["korea_only"].get("macro_f1", 0.0),
            "korea_pair_accuracy": weighted["metrics"]["korea_focus_pair_only"].get("accuracy", 0.0),
            "korea_pair_macro_f1": weighted["metrics"]["korea_focus_pair_only"].get("macro_f1", 0.0),
            "pair_confusions": extract_pair_confusions(weighted),
        },
    }

    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Focus Pair Report",
        "",
        f"- Pair: {pair[0]} / {pair[1]}",
        "",
        "## Baseline",
        f"- Overall accuracy: {payload['baseline']['overall_accuracy']:.4f}",
        f"- Overall macro F1: {payload['baseline']['overall_macro_f1']:.4f}",
    ]
    for row in payload["baseline"]["pair_confusions"]:
        lines.append(f"- {row['true']} -> {row['pred']}: {row['count']}")
    lines.extend([
        "",
        "## Weighted",
        f"- Overall accuracy: {payload['weighted']['overall_accuracy']:.4f}",
        f"- Overall macro F1: {payload['weighted']['overall_macro_f1']:.4f}",
        f"- Korea-only accuracy: {payload['weighted']['korea_only_accuracy']:.4f}",
        f"- Korea-only macro F1: {payload['weighted']['korea_only_macro_f1']:.4f}",
        f"- Korea pair accuracy: {payload['weighted']['korea_pair_accuracy']:.4f}",
        f"- Korea pair macro F1: {payload['weighted']['korea_pair_macro_f1']:.4f}",
    ])
    for row in payload["weighted"]["pair_confusions"]:
        lines.append(f"- {row['true']} -> {row['pred']}: {row['count']}")
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")


if __name__ == "__main__":
    main()

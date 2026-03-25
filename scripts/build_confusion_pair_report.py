from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    report_path = ROOT / "ml-workspace" / "reports" / "inat_full_feature_report.json"
    out_json = ROOT / "ml-workspace" / "reports" / "confusion_pair_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "confusion_pair_report.md"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    off_diag = report["confusion_matrix"]["off_diagonal"][:20]
    payload = {
        "top_confusion_pairs": off_diag,
        "accuracy": report["metrics"]["accuracy"],
        "macro_f1": report["metrics"]["macro avg"]["f1-score"],
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Confusion Pair Report",
        "",
        f"- Accuracy: {payload['accuracy']:.4f}",
        f"- Macro F1: {payload['macro_f1']:.4f}",
        "",
        "## Top confusion pairs",
    ]
    for row in payload["top_confusion_pairs"]:
        lines.append(f"- {row['true']} -> {row['pred']}: {row['count']}")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    source_path = ROOT / "ml-workspace" / "reports" / "two_stage_metrics_report.json"
    out_json = ROOT / "ml-workspace" / "reports" / "final_operating_rule_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "final_operating_rule_report.md"

    report = json.loads(source_path.read_text(encoding="utf-8"))
    payload = {
        "rule_summary": {
            "stage_1": "baseline accepts only when top1-top2 gap >= 0.08 and votes gap > 2",
            "stage_2": "if stage 1 is low_confidence, promote only when focus-species CNN also passes strict thresholds (prob >= 0.8, gap >= 0.15, votes >= 8)",
            "fallback": "otherwise abstain",
        },
        "operating_metrics": {
            "baseline_accepted_accuracy": report["baseline"]["accepted_accuracy"],
            "baseline_abstain_rate": report["baseline"]["abstain_rate"],
            "final_accepted_accuracy": report["final"]["accepted_accuracy"],
            "final_abstain_rate": report["final"]["abstain_rate"],
            "promotion_count": report["second_stage"]["promotion_count"],
            "promotion_fix_count": report["second_stage"]["fixed_count"],
            "promotion_hurt_count": report["second_stage"]["hurt_count"],
        },
        "korea_only": report["korea_only"],
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Final Operating Rule Report",
        "",
        "## Rule",
        f"- Stage 1: {payload['rule_summary']['stage_1']}",
        f"- Stage 2: {payload['rule_summary']['stage_2']}",
        f"- Fallback: {payload['rule_summary']['fallback']}",
        "",
        "## Metrics",
        f"- Baseline accepted accuracy: {payload['operating_metrics']['baseline_accepted_accuracy']}",
        f"- Baseline abstain rate: {payload['operating_metrics']['baseline_abstain_rate']}",
        f"- Final accepted accuracy: {payload['operating_metrics']['final_accepted_accuracy']}",
        f"- Final abstain rate: {payload['operating_metrics']['final_abstain_rate']}",
        f"- Second-stage promotions: {payload['operating_metrics']['promotion_count']}",
        f"- Promotions that fixed baseline errors: {payload['operating_metrics']['promotion_fix_count']}",
        f"- Promotions that hurt baseline-correct cases: {payload['operating_metrics']['promotion_hurt_count']}",
        "",
        "## Korea only",
        f"- Baseline accepted accuracy: {payload['korea_only']['baseline_accepted_accuracy']}",
        f"- Final accepted accuracy: {payload['korea_only']['final_accepted_accuracy']}",
        f"- Promotions: {payload['korea_only']['promotion_count']}",
    ]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

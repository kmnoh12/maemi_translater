from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cache_path = ROOT / "dashboard" / "prediction_cache.json"
    out_json = ROOT / "ml-workspace" / "reports" / "two_stage_metrics_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "two_stage_metrics_report.md"

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    items: list[dict[str, object]] = cache.get("items", [])

    baseline_total = baseline_correct = 0
    final_total = final_correct = 0
    second_stage_promotions = second_stage_fixed = second_stage_hurt = 0
    transition_counter: Counter[tuple[str, str]] = Counter()

    korea_total = 0
    korea_baseline_total = korea_baseline_correct = 0
    korea_final_total = korea_final_correct = 0
    korea_promotions = 0

    for item in items:
        truth = str(item.get("species_code", ""))
        is_korea = str(item.get("is_korea", "")).lower() == "true"
        baseline = dict(item.get("recommendation") or {})
        final = dict(item.get("final_recommendation") or baseline)

        baseline_status = str(baseline.get("status", "no_result"))
        baseline_label = baseline.get("display_label")
        final_status = str(final.get("status", "no_result"))
        final_label = final.get("display_label")
        transition_counter[(baseline_status, final_status)] += 1

        if baseline_status == "accepted":
            baseline_total += 1
            if baseline_label == truth:
                baseline_correct += 1

        if final_status == "accepted":
            final_total += 1
            if final_label == truth:
                final_correct += 1

        if is_korea:
            korea_total += 1
            if baseline_status == "accepted":
                korea_baseline_total += 1
                if baseline_label == truth:
                    korea_baseline_correct += 1
            if final_status == "accepted":
                korea_final_total += 1
                if final_label == truth:
                    korea_final_correct += 1

        if final.get("source_model") == "focus_species_cnn":
            second_stage_promotions += 1
            if is_korea:
                korea_promotions += 1
            if baseline_label != truth and final_label == truth:
                second_stage_fixed += 1
            elif baseline_label == truth and final_label != truth:
                second_stage_hurt += 1

    payload = {
        "cache_size": len(items),
        "baseline": {
            "accepted_count": baseline_total,
            "accepted_accuracy": round(baseline_correct / baseline_total, 4) if baseline_total else 0.0,
            "abstained_count": len(items) - baseline_total,
            "abstain_rate": round((len(items) - baseline_total) / len(items), 4) if items else 0.0,
        },
        "final": {
            "accepted_count": final_total,
            "accepted_accuracy": round(final_correct / final_total, 4) if final_total else 0.0,
            "abstained_count": len(items) - final_total,
            "abstain_rate": round((len(items) - final_total) / len(items), 4) if items else 0.0,
        },
        "second_stage": {
            "promotion_count": second_stage_promotions,
            "promotion_rate": round(second_stage_promotions / len(items), 4) if items else 0.0,
            "fixed_count": second_stage_fixed,
            "hurt_count": second_stage_hurt,
        },
        "korea_only": {
            "baseline_accepted_count": korea_baseline_total,
            "baseline_accepted_accuracy": round(korea_baseline_correct / korea_baseline_total, 4) if korea_baseline_total else 0.0,
            "baseline_abstained_count": korea_total - korea_baseline_total,
            "final_accepted_count": korea_final_total,
            "final_accepted_accuracy": round(korea_final_correct / korea_final_total, 4) if korea_final_total else 0.0,
            "final_abstained_count": korea_total - korea_final_total,
            "promotion_count": korea_promotions,
        },
        "status_transitions": [
            {"from": src, "to": dst, "count": count}
            for (src, dst), count in sorted(transition_counter.items(), key=lambda x: x[1], reverse=True)
        ],
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Two-Stage Metrics Report",
        "",
        f"- Cache size: {payload['cache_size']}",
        f"- Baseline accepted accuracy: {payload['baseline']['accepted_accuracy']}",
        f"- Baseline abstain rate: {payload['baseline']['abstain_rate']}",
        f"- Final accepted accuracy: {payload['final']['accepted_accuracy']}",
        f"- Final abstain rate: {payload['final']['abstain_rate']}",
        f"- Second-stage promotions: {payload['second_stage']['promotion_count']}",
        f"- Promotions that fixed baseline errors: {payload['second_stage']['fixed_count']}",
        f"- Promotions that hurt baseline-correct cases: {payload['second_stage']['hurt_count']}",
        "",
        "## Korea only",
        f"- Baseline accepted accuracy: {payload['korea_only']['baseline_accepted_accuracy']}",
        f"- Final accepted accuracy: {payload['korea_only']['final_accepted_accuracy']}",
        f"- Promotions: {payload['korea_only']['promotion_count']}",
        "",
        "## Status transitions",
    ]
    for row in payload["status_transitions"]:
        lines.append(f"- {row['from']} -> {row['to']}: {row['count']}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

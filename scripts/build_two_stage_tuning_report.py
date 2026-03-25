from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def accepted_accuracy(items: list[dict]) -> dict[str, float | int]:
    accepted = [item for item in items if item["status"] == "accepted"]
    correct = sum(1 for item in accepted if item["display_label"] == item["truth"])
    return {
        "accepted_count": len(accepted),
        "accepted_accuracy": round(correct / len(accepted), 4) if accepted else 0.0,
        "abstained_count": sum(1 for item in items if item["status"] != "accepted"),
        "abstain_rate": round(sum(1 for item in items if item["status"] != "accepted") / len(items), 4) if items else 0.0,
    }


def main() -> None:
    cache_path = ROOT / "dashboard" / "prediction_cache.json"
    out_json = ROOT / "ml-workspace" / "reports" / "two_stage_tuning_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "two_stage_tuning_report.md"

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    items = cache.get("items", [])

    configs = [
        {"label": "current", "min_prob": 0.0, "min_gap": 0.0, "min_votes": 0},
        {"label": "strict_a", "min_prob": 0.80, "min_gap": 0.15, "min_votes": 8},
        {"label": "strict_b", "min_prob": 0.90, "min_gap": 0.25, "min_votes": 12},
        {"label": "strict_c", "min_prob": 0.95, "min_gap": 0.40, "min_votes": 18},
    ]

    rows = []
    for cfg in configs:
        final_rows = []
        promotions = 0
        for item in items:
            truth = item["species_code"]
            baseline = item.get("recommendation", {}) or {}
            baseline_status = baseline.get("status", "no_result")
            baseline_label = baseline.get("display_label")
            second = item.get("second_stage", {}) or {}
            second_rec = second.get("recommendation", {}) or {}

            result = {
                "truth": truth,
                "status": baseline_status,
                "display_label": baseline_label,
            }
            if baseline_status == "low_confidence" and second_rec.get("status") == "accepted":
                if (
                    float(second_rec.get("prob_gap", 0.0)) >= cfg["min_gap"]
                    and int(second_rec.get("vote_gap", 0)) >= cfg["min_votes"]
                    and float((second.get("aggregate_ranking") or [{}])[0].get("mean_probability", 0.0)) >= cfg["min_prob"]
                ):
                    result = {
                        "truth": truth,
                        "status": "accepted",
                        "display_label": second_rec.get("display_label"),
                    }
                    promotions += 1
            final_rows.append(result)

        summary = accepted_accuracy(final_rows)
        summary["label"] = cfg["label"]
        summary["promotion_count"] = promotions
        summary["min_prob"] = cfg["min_prob"]
        summary["min_gap"] = cfg["min_gap"]
        summary["min_votes"] = cfg["min_votes"]
        rows.append(summary)

    payload = {"rows": rows}
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Two-Stage Tuning Report",
        "",
        "| label | min_prob | min_gap | min_votes | accepted_count | accepted_accuracy | abstain_rate | promotions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['min_prob']:.2f} | {row['min_gap']:.2f} | {row['min_votes']} | "
            f"{row['accepted_count']} | {row['accepted_accuracy']:.4f} | {row['abstain_rate']:.4f} | {row['promotion_count']} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def summarize(items: list[dict], prob_gap_threshold: float, vote_gap_threshold: int) -> dict[str, float | int]:
    total = len(items)
    abstained = 0
    decided = 0
    correct = 0
    wrong = 0
    for item in items:
        ranking = item.get("aggregate_ranking", [])
        if not ranking:
            abstained += 1
            continue
        top1 = ranking[0]
        top2 = ranking[1] if len(ranking) > 1 else {"mean_probability": 0.0, "vote_count": 0}
        prob_gap = float(top1.get("mean_probability", 0.0)) - float(top2.get("mean_probability", 0.0))
        vote_gap = int(top1.get("vote_count", 0)) - int(top2.get("vote_count", 0))
        if prob_gap < prob_gap_threshold or vote_gap <= vote_gap_threshold:
            abstained += 1
            continue
        decided += 1
        if top1.get("label") == item.get("species_code"):
            correct += 1
        else:
            wrong += 1
    return {
        "total_items": total,
        "abstained": abstained,
        "abstain_rate": round(abstained / total, 4) if total else 0.0,
        "decided": decided,
        "decided_accuracy": round(correct / decided, 4) if decided else 0.0,
        "correct": correct,
        "wrong": wrong,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache-path",
        type=Path,
        default=ROOT / "dashboard" / "prediction_cache.json",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "abstain_rule_report.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "abstain_rule_report.md",
    )
    args = parser.parse_args()

    cache = json.loads(args.cache_path.read_text(encoding="utf-8"))
    items = cache.get("items", [])
    korea_items = [item for item in items if str(item.get("is_korea", "")).lower() == "true"]

    configs = [
        {"prob_gap_threshold": 0.03, "vote_gap_threshold": 1},
        {"prob_gap_threshold": 0.05, "vote_gap_threshold": 2},
        {"prob_gap_threshold": 0.08, "vote_gap_threshold": 2},
        {"prob_gap_threshold": 0.10, "vote_gap_threshold": 3},
    ]

    payload = {
        "all_items": [],
        "korea_items": [],
    }
    for cfg in configs:
        payload["all_items"].append({
            **cfg,
            **summarize(items, cfg["prob_gap_threshold"], cfg["vote_gap_threshold"]),
        })
        payload["korea_items"].append({
            **cfg,
            **summarize(korea_items, cfg["prob_gap_threshold"], cfg["vote_gap_threshold"]),
        })

    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Abstain Rule Report", "", "## All cached items"]
    for row in payload["all_items"]:
        lines.append(
            f"- prob_gap<{row['prob_gap_threshold']}, vote_gap<={row['vote_gap_threshold']}: "
            f"abstain_rate={row['abstain_rate']}, decided_accuracy={row['decided_accuracy']}"
        )
    lines.extend(["", "## Korea cached items"])
    for row in payload["korea_items"]:
        lines.append(
            f"- prob_gap<{row['prob_gap_threshold']}, vote_gap<={row['vote_gap_threshold']}: "
            f"abstain_rate={row['abstain_rate']}, decided_accuracy={row['decided_accuracy']}"
        )
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")


if __name__ == "__main__":
    main()

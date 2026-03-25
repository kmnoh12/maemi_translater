from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cache_path = ROOT / "dashboard" / "prediction_cache.json"
    out_json = ROOT / "ml-workspace" / "reports" / "korea_prediction_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "korea_prediction_report.md"

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    korea_items = [item for item in cache.get("items", []) if str(item.get("is_korea", "")).lower() == "true"]

    total = len(korea_items)
    correct = 0
    confusion_counter = Counter()
    per_species_total = Counter()
    per_species_correct = Counter()

    for item in korea_items:
        truth = item["species_code"]
        pred = item["aggregate_ranking"][0]["label"] if item.get("aggregate_ranking") else "unknown"
        per_species_total[truth] += 1
        if pred == truth:
            correct += 1
            per_species_correct[truth] += 1
        else:
            confusion_counter[(truth, pred)] += 1

    payload = {
        "korea_items": total,
        "top1_accuracy_over_cached_korea_items": round(correct / total, 4) if total else 0.0,
        "per_species_accuracy": {
            species: round(per_species_correct[species] / count, 4) if count else 0.0
            for species, count in sorted(per_species_total.items())
        },
        "top_confusions": [
            {"true": truth, "pred": pred, "count": count}
            for (truth, pred), count in confusion_counter.most_common(15)
        ],
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Korea Prediction Report",
        "",
        f"- Korea cached items: {payload['korea_items']}",
        f"- Cached top1 accuracy: {payload['top1_accuracy_over_cached_korea_items']}",
        "",
        "## Per-species accuracy",
    ]
    for species, acc in payload["per_species_accuracy"].items():
        lines.append(f"- {species}: {acc}")
    lines.extend(["", "## Top confusions"])
    for row in payload["top_confusions"]:
        lines.append(f"- {row['true']} -> {row['pred']}: {row['count']}")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

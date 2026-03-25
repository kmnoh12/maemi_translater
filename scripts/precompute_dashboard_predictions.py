from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from predict_audio_with_baseline import predict_audio


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    inventory_path = ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv"
    model_path = ROOT / "ml-workspace" / "artifacts" / "inat_full_feature_model.joblib"
    out_path = ROOT / "dashboard" / "prediction_cache.json"

    rows = load_csv(inventory_path)
    rows.sort(
        key=lambda row: (
            row["species_code"],
            row.get("is_korea", "").lower() != "true",
            -float(row["duration_sec"]),
            row["sound_id"],
        )
    )

    cache: list[dict[str, object]] = []
    selected_keys: set[tuple[str, str]] = set()
    selected: list[dict[str, str]] = []

    # Include every Korea row first so local validation stays visible in the dashboard.
    for row in rows:
        if row.get("is_korea", "").lower() == "true":
            key = (row["species_code"], row["sound_id"])
            if key not in selected_keys:
                selected_keys.add(key)
                selected.append(row)

    # Then add extra long-duration worldwide rows per species.
    by_species: dict[str, int] = {}
    for row in rows:
        key = (row["species_code"], row["sound_id"])
        if key in selected_keys:
            continue
        count = by_species.get(row["species_code"], 0)
        if count >= 12:
            continue
        by_species[row["species_code"]] = count + 1
        selected_keys.add(key)
        selected.append(row)

    for row in selected:
        result = predict_audio(ROOT / row["derived_path"], model_path)
        cache.append(
            {
                "species_code": row["species_code"],
                "common_name_ko": row.get("common_name_ko", ""),
                "sound_id": row["sound_id"],
                "observation_id": row["observation_id"],
                "audio_path": str(row["derived_path"]).replace("\\", "/"),
                "is_korea": row.get("is_korea", ""),
                "license_code": row.get("license_code", ""),
                "place_guess": row.get("place_guess", ""),
                "duration_sec": result["duration_sec"],
                "num_windows": result["num_windows"],
                "aggregate_ranking": result["aggregate_ranking"],
                "window_predictions_preview": result["window_predictions"][:10],
                "recommendation": result.get("recommendation", {}),
                "risky_accepted_trigger": result.get("risky_accepted_trigger"),
                "second_stage": result.get("second_stage"),
                "final_recommendation": result.get("final_recommendation", {}),
            }
        )

    payload = {
        "model_path": str(model_path.relative_to(ROOT)).replace("\\", "/"),
        "cache_size": len(cache),
        "selection_policy": {
            "all_korea_rows": True,
            "extra_world_rows_per_species": 12,
        },
        "items": cache,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cache)} cached predictions to {out_path}")


if __name__ == "__main__":
    main()

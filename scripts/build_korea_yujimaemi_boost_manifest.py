from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split_manifest_csv", type=Path)
    parser.add_argument(
        "--inventory-csv",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=ROOT / "ml-workspace" / "experiments" / "focus_species" / "focus_manifest_with_split_yuji_boost.csv",
    )
    parser.add_argument("--boost-factor", type=int, default=4)
    args = parser.parse_args()

    rows = load_rows(args.split_manifest_csv.resolve())
    inventory_rows = load_rows(args.inventory_csv.resolve())
    inventory_index = {
        (row["observation_id"], row["sound_id"]): row
        for row in inventory_rows
    }

    boosted_rows: list[dict[str, str]] = []
    extra_count = 0
    for row in rows:
        boosted_rows.append({**row, "boost_copy_index": "0", "boost_reason": ""})
        meta = inventory_index.get((row["observation_id"], row["sound_id"]), {})
        is_korea = str(meta.get("is_korea", "")).lower() == "true"
        if row["split"] != "train":
            continue
        if row["species_code"] != "yujimaemi":
            continue
        if not is_korea:
            continue
        for copy_idx in range(1, args.boost_factor + 1):
            boosted_rows.append(
                {
                    **row,
                    "window_id": f"{row['window_id']}__boost{copy_idx}",
                    "boost_copy_index": str(copy_idx),
                    "boost_reason": "korea_yujimaemi_train_priority",
                }
            )
            extra_count += 1

    fieldnames = list(boosted_rows[0].keys())
    args.out_csv = args.out_csv.resolve()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(boosted_rows)

    print(f"Wrote boosted manifest to {args.out_csv}")
    print(f"Original rows: {len(rows)}")
    print(f"Extra boosted rows: {extra_count}")
    print(f"Total rows: {len(boosted_rows)}")


if __name__ == "__main__":
    main()

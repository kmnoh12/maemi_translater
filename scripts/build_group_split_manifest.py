from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_csv", type=Path)
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=ROOT / "ml-workspace" / "experiments" / "cnn_dataset" / "cnn_manifest_with_split.csv",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    args = parser.parse_args()

    rows = load_rows(args.manifest_csv.resolve())
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["observation_id"]].append(row)

    by_species: dict[str, list[str]] = defaultdict(list)
    for obs_id, obs_rows in grouped.items():
        species = obs_rows[0]["species_code"]
        by_species[species].append(obs_id)

    rng = random.Random(args.seed)
    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()
    per_species_counts: dict[str, dict[str, int]] = {}

    for species, observation_ids in sorted(by_species.items()):
        observation_ids = observation_ids[:]
        rng.shuffle(observation_ids)
        total = len(observation_ids)
        train_cut = max(1, int(total * args.train_ratio))
        val_count = max(1, int(total * args.val_ratio))
        if train_cut + val_count >= total:
            val_count = 1 if total >= 3 else max(0, total - train_cut - 1)
        val_cut = train_cut + val_count
        species_train = set(observation_ids[:train_cut])
        species_val = set(observation_ids[train_cut:val_cut])
        species_test = set(observation_ids[val_cut:])
        if not species_test and total >= 3:
            moved = next(iter(species_val or species_train))
            if moved in species_val:
                species_val.remove(moved)
            else:
                species_train.remove(moved)
            species_test.add(moved)

        train_ids.update(species_train)
        val_ids.update(species_val)
        test_ids.update(species_test)
        per_species_counts[species] = {
            "train_obs": len(species_train),
            "val_obs": len(species_val),
            "test_obs": len(species_test),
        }

    args.out_csv = args.out_csv.resolve()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) + ["split"]
    with args.out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            obs_id = row["observation_id"]
            split = "train" if obs_id in train_ids else "val" if obs_id in val_ids else "test"
            writer.writerow({**row, "split": split})

    print(f"Wrote split manifest to {args.out_csv}")
    print(f"Observation groups: train={len(train_ids)}, val={len(val_ids)}, test={len(test_ids)}")
    for species, counts in per_species_counts.items():
        print(
            f"{species}: train_obs={counts['train_obs']}, "
            f"val_obs={counts['val_obs']}, test_obs={counts['test_obs']}"
        )


if __name__ == "__main__":
    main()

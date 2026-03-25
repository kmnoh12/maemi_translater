from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "hash_duplicates.csv",
    )
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    args.report_out = args.report_out.resolve()
    args.report_out.parent.mkdir(parents=True, exist_ok=True)

    hash_map: dict[str, list[dict[str, str]]] = defaultdict(list)
    rows = list(csv.DictReader(manifest.open("r", encoding="utf-8-sig", newline="")))
    for row in rows:
        raw_path = ROOT / row["local_raw_path"]
        if not raw_path.exists():
            continue
        digest = sha256_file(raw_path)
        hash_map[digest].append(row)

    duplicate_groups = [items for items in hash_map.values() if len(items) > 1]

    with args.report_out.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "sha256",
            "duplicate_count",
            "species_code",
            "observation_id",
            "sound_id",
            "license_code",
            "raw_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for digest, items in hash_map.items():
            if len(items) < 2:
                continue
            for row in items:
                writer.writerow(
                    {
                        "sha256": digest,
                        "duplicate_count": len(items),
                        "species_code": row["species_code"],
                        "observation_id": row["observation_id"],
                        "sound_id": row["sound_id"],
                        "license_code": row["license_code"],
                        "raw_path": row["local_raw_path"],
                    }
                )

    print(f"Rows in manifest: {len(rows)}")
    print(f"Duplicate groups: {len(duplicate_groups)}")
    print(f"Wrote duplicate report to {args.report_out}")


if __name__ == "__main__":
    main()

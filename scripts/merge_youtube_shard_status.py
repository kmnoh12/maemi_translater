from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_SHARD_DIR = ROOT / "data-workspace" / "metadata" / "youtube_shards"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge shard manifest statuses back into youtube_manifest.csv")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--shard-dir", type=Path, default=DEFAULT_SHARD_DIR)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    shard_dir = args.shard_dir.resolve()
    rows = load_rows(manifest_path)
    if not rows:
        print("Manifest is empty.")
        return

    by_video_id = {row.get("video_id", ""): row for row in rows}
    merged = 0
    for shard_path in sorted(shard_dir.glob("*.csv")):
        for shard_row in load_rows(shard_path):
            video_id = shard_row.get("video_id", "")
            if not video_id or video_id not in by_video_id:
                continue
            target = by_video_id[video_id]
            old_status = target.get("status", "")
            new_status = shard_row.get("status", old_status)
            target["status"] = new_status
            target["download_date"] = shard_row.get("download_date", target.get("download_date", ""))
            if old_status != new_status:
                merged += 1

    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Merged {merged} status updates from {shard_dir}")


if __name__ == "__main__":
    main()

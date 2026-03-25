from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "maemi-translater-manifest-downloader/0.1"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    downloaded = 0
    skipped = 0

    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            license_code = (row.get("license_code") or "").strip().lower()
            if not license_code:
                skipped += 1
                continue
            destination = ROOT / row["local_raw_path"]
            if destination.exists():
                skipped += 1
                continue

            ensure_parent(destination)
            req = Request(row["file_url"], headers={"User-Agent": USER_AGENT})
            with urlopen(req) as response, destination.open("wb") as out:
                out.write(response.read())
            sidecar = destination.with_suffix(destination.suffix + ".json")
            sidecar.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            downloaded += 1
            print(f"Downloaded {row['sound_id']} -> {destination}")

            if args.limit and downloaded >= args.limit:
                break

    print(f"Downloaded: {downloaded}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()

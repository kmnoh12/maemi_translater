from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data-workspace" / "metadata" / "public_seed_manifest.csv"
USER_AGENT = "maemi-translater-seed-downloader/0.1"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def download_file(url: str, destination: Path) -> None:
    ensure_parent(destination)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response, destination.open("wb") as handle:
        handle.write(response.read())


def write_sidecar(destination: Path, row: dict[str, str]) -> None:
    sidecar = destination.with_suffix(destination.suffix + ".json")
    with sidecar.open("w", encoding="utf-8") as handle:
        json.dump(row, handle, ensure_ascii=False, indent=2)


def main() -> None:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}")

    downloaded = 0
    skipped = 0

    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            license_code = (row.get("license_code") or "").strip().lower()
            if not license_code:
                skipped += 1
                continue

            relative_path = row["local_raw_path"].strip()
            destination = ROOT / relative_path
            if destination.exists():
                skipped += 1
                continue

            print(f"Downloading {row['sound_id']} -> {relative_path}")
            download_file(row["file_url"], destination)
            write_sidecar(destination, row)
            downloaded += 1

    print(f"Downloaded: {downloaded}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()

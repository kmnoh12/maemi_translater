from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INAT = ROOT / "data-workspace" / "metadata" / "inat_full_manifest.csv"
DEFAULT_YOUTUBE = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_SPECIES = ROOT / "data-workspace" / "metadata" / "species_catalog.json"
DEFAULT_OUT = ROOT / "data-workspace" / "metadata" / "combined_training_manifest.csv"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_species_lookup(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {row["species_code"]: row for row in data}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a unified training manifest from iNat and YouTube audio.")
    parser.add_argument("--inat-manifest", type=Path, default=DEFAULT_INAT)
    parser.add_argument("--youtube-manifest", type=Path, default=DEFAULT_YOUTUBE)
    parser.add_argument("--species-catalog", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    inat_rows = load_rows(args.inat_manifest.resolve())
    youtube_rows = load_rows(args.youtube_manifest.resolve())
    species_lookup = load_species_lookup(args.species_catalog.resolve())

    fieldnames = [
        "source",
        "species_code",
        "common_name_ko",
        "scientific_name",
        "observation_id",
        "sound_id",
        "quality_grade",
        "license_code",
        "region_scope",
        "observed_on",
        "source_url",
        "local_raw_path",
        "local_derived_path",
    ]

    combined: list[dict[str, str]] = []

    for row in inat_rows:
        derived = (row.get("local_derived_path") or "").strip()
        if not derived or not (ROOT / derived).exists():
            continue
        combined.append(
            {
                "source": "inat",
                "species_code": row["species_code"],
                "common_name_ko": row.get("common_name_ko", ""),
                "scientific_name": row.get("scientific_name", ""),
                "observation_id": row.get("observation_id", ""),
                "sound_id": row.get("sound_id", ""),
                "quality_grade": row.get("quality_grade", ""),
                "license_code": row.get("license_code", ""),
                "region_scope": "korea" if row.get("is_korea") == "true" else "global",
                "observed_on": row.get("observed_on", ""),
                "source_url": row.get("source_url", ""),
                "local_raw_path": row.get("local_raw_path", ""),
                "local_derived_path": derived,
            }
        )

    for row in youtube_rows:
        if (row.get("status") or "").strip().lower() != "downloaded":
            continue
        derived = (row.get("local_derived_path") or "").strip()
        if not derived or not (ROOT / derived).exists():
            continue

        species_code = row["species_code"]
        species_meta = species_lookup.get(species_code, {})
        video_id = row.get("video_id", "")
        combined.append(
            {
                "source": "youtube",
                "species_code": species_code,
                "common_name_ko": species_meta.get("common_name_ko", ""),
                "scientific_name": species_meta.get("scientific_name", ""),
                "observation_id": f"yt_{video_id}",
                "sound_id": f"yt_{video_id}",
                "quality_grade": row.get("label_confidence", ""),
                "license_code": row.get("license_note", ""),
                "region_scope": "global",
                "observed_on": row.get("upload_date", ""),
                "source_url": row.get("video_url", ""),
                "local_raw_path": row.get("local_raw_path", ""),
                "local_derived_path": derived,
            }
        )

    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined)

    print(f"Wrote {len(combined)} rows to {args.out}")


if __name__ == "__main__":
    main()

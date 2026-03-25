from __future__ import annotations

import argparse
import csv
from pathlib import Path

import soundfile as sf


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    rows_out: list[dict[str, str | int | float]] = []
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            derived_path = ROOT / row["local_derived_path"]
            raw_path = ROOT / row["local_raw_path"]
            if not derived_path.exists():
                continue

            info = sf.info(str(derived_path))
            rows_out.append(
                {
                    "species_code": row["species_code"],
                    "common_name_ko": row.get("common_name_ko", ""),
                    "scientific_name": row.get("scientific_name", ""),
                    "observation_id": row["observation_id"],
                    "sound_id": row["sound_id"],
                    "region_scope": row.get("region_scope", ""),
                    "is_korea": row.get("is_korea", ""),
                    "place_guess": row.get("place_guess", ""),
                    "license_code": row["license_code"],
                    "quality_grade": row.get("quality_grade", ""),
                    "raw_path": str(raw_path.relative_to(ROOT)),
                    "derived_path": str(derived_path.relative_to(ROOT)),
                    "samplerate": info.samplerate,
                    "channels": info.channels,
                    "frames": info.frames,
                    "duration_sec": round(info.duration, 3),
                    "subtype": info.subtype,
                }
            )

    with out.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "species_code",
            "common_name_ko",
            "scientific_name",
            "observation_id",
            "sound_id",
            "region_scope",
            "is_korea",
            "place_guess",
            "license_code",
            "quality_grade",
            "raw_path",
            "derived_path",
            "samplerate",
            "channels",
            "frames",
            "duration_sec",
            "subtype",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows to {out}")


if __name__ == "__main__":
    main()

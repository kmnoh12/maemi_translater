from __future__ import annotations

import argparse
import csv
from pathlib import Path

import soundfile as sf


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--window-sec", type=float, default=3.0)
    parser.add_argument("--hop-sec", type=float, default=1.5)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "public_seed_windows.csv",
    )
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    rows_out: list[dict[str, str | int | float]] = []
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            audio_path = ROOT / row["local_derived_path"]
            if not audio_path.exists():
                continue
            info = sf.info(str(audio_path))
            sr = info.samplerate
            total_sec = info.duration
            window_sec = args.window_sec
            hop_sec = args.hop_sec

            if total_sec < window_sec:
                continue

            start_sec = 0.0
            index = 0
            while start_sec + window_sec <= total_sec + 1e-9:
                rows_out.append(
                    {
                        "window_id": f"{row['species_code']}_{row['sound_id']}_{index:03d}",
                        "species_code": row["species_code"],
                        "observation_id": row["observation_id"],
                        "sound_id": row["sound_id"],
                        "license_code": row["license_code"],
                        "quality_grade": row.get("quality_grade", ""),
                        "audio_path": str(audio_path.relative_to(ROOT)),
                        "sample_rate": sr,
                        "start_sec": round(start_sec, 3),
                        "end_sec": round(start_sec + window_sec, 3),
                        "window_sec": window_sec,
                    }
                )
                start_sec += hop_sec
                index += 1

    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "window_id",
                "species_code",
                "observation_id",
                "sound_id",
                "license_code",
                "quality_grade",
                "audio_path",
                "sample_rate",
                "start_sec",
                "end_sec",
                "window_sec",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} windows to {out}")


if __name__ == "__main__":
    main()

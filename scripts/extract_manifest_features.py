from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import soundfile as sf

from baseline_audio_utils import extract_features, iter_windows


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--features-out",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "features" / "baseline_features.npz",
    )
    parser.add_argument(
        "--metadata-out",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "features" / "baseline_features_metadata.csv",
    )
    parser.add_argument("--window-sec", type=float, default=3.0)
    parser.add_argument("--hop-sec", type=float, default=1.5)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    args.features_out = args.features_out.resolve()
    args.metadata_out = args.metadata_out.resolve()
    args.features_out.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_out.parent.mkdir(parents=True, exist_ok=True)

    feature_rows: list[np.ndarray] = []
    metadata_rows: list[dict[str, str | int | float]] = []

    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            audio_path = ROOT / row["local_derived_path"]
            if not audio_path.exists():
                continue

            info = sf.info(str(audio_path))
            window_index = 0
            for start_sec, end_sec in iter_windows(
                info.duration,
                window_sec=args.window_sec,
                hop_sec=args.hop_sec,
            ):
                feature_rows.append(extract_features(audio_path, start_sec, args.window_sec))
                metadata_rows.append(
                    {
                        "feature_index": len(feature_rows) - 1,
                        "window_id": f"{row['species_code']}_{row['sound_id']}_{window_index:03d}",
                        "species_code": row["species_code"],
                        "common_name_ko": row.get("common_name_ko", ""),
                        "scientific_name": row.get("scientific_name", ""),
                        "observation_id": row["observation_id"],
                        "sound_id": row["sound_id"],
                        "license_code": row["license_code"],
                        "quality_grade": row.get("quality_grade", ""),
                        "region_scope": row.get("region_scope", ""),
                        "audio_path": str(audio_path.relative_to(ROOT)),
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "window_sec": args.window_sec,
                        "hop_sec": args.hop_sec,
                    }
                )
                window_index += 1

    if not feature_rows:
        raise RuntimeError("No features were extracted.")

    np.savez_compressed(
        args.features_out,
        X=np.stack(feature_rows),
        feature_version="mfcc20_plus_spectral_stats_v1",
        window_sec=args.window_sec,
        hop_sec=args.hop_sec,
    )

    with args.metadata_out.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(metadata_rows[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"Wrote features to {args.features_out}")
    print(f"Wrote metadata to {args.metadata_out}")
    print(f"Num windows: {len(metadata_rows)}")


if __name__ == "__main__":
    main()

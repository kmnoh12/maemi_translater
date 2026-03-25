from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import librosa
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def render_logmel_image(audio_path: Path, start_sec: float, end_sec: float, image_size: int = 128) -> Image.Image:
    duration = max(0.0, end_sec - start_sec)
    y, sr = librosa.load(audio_path, sr=None, mono=True, offset=start_sec, duration=duration)
    if len(y) == 0:
        raise ValueError(f"Empty audio window: {audio_path} @ {start_sec}")

    mel = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=1024,
        hop_length=256,
        n_mels=128,
        fmin=150,
        fmax=min(8000, sr // 2),
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    normalized = (log_mel - log_mel.min()) / max(1e-6, (log_mel.max() - log_mel.min()))
    array = np.uint8(np.clip(normalized * 255.0, 0, 255))
    image = Image.fromarray(array).convert("L").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return image.resize((image_size, image_size), Image.Resampling.BILINEAR)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_csv", type=Path)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "ml-workspace" / "experiments" / "cnn_dataset" / "images",
    )
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=ROOT / "ml-workspace" / "experiments" / "cnn_dataset" / "cnn_manifest.csv",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for quick experiments")
    parser.add_argument("--balanced-per-species", type=int, default=0, help="Export up to N rows per species for quick balanced experiments")
    args = parser.parse_args()

    rows = load_rows(args.metadata_csv.resolve())
    if args.balanced_per_species > 0:
        selected: list[dict[str, str]] = []
        counts: dict[str, int] = defaultdict(int)
        for row in rows:
            species = row["species_code"]
            if counts[species] >= args.balanced_per_species:
                continue
            counts[species] += 1
            selected.append(row)
        rows = selected
    elif args.limit > 0:
        rows = rows[: args.limit]

    args.out_dir = args.out_dir.resolve()
    args.manifest_out = args.manifest_out.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "feature_index",
        "window_id",
        "species_code",
        "common_name_ko",
        "scientific_name",
        "observation_id",
        "sound_id",
        "license_code",
        "quality_grade",
        "audio_path",
        "start_sec",
        "end_sec",
        "image_path",
    ]

    with args.manifest_out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(rows, start=1):
            audio_path = (ROOT / row["audio_path"]).resolve()
            image_name = f"{row['window_id']}.png"
            image_path = args.out_dir / row["species_code"] / image_name
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image = render_logmel_image(audio_path, float(row["start_sec"]), float(row["end_sec"]))
            image.save(image_path)

            writer.writerow(
                {
                    "feature_index": row.get("feature_index", str(idx - 1)),
                    "window_id": row["window_id"],
                    "species_code": row["species_code"],
                    "common_name_ko": row.get("common_name_ko", ""),
                    "scientific_name": row.get("scientific_name", ""),
                    "observation_id": row["observation_id"],
                    "sound_id": row["sound_id"],
                    "license_code": row.get("license_code", ""),
                    "quality_grade": row.get("quality_grade", ""),
                    "audio_path": row["audio_path"],
                    "start_sec": row["start_sec"],
                    "end_sec": row["end_sec"],
                    "image_path": str(image_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
            if idx % 500 == 0:
                print(f"exported {idx}/{len(rows)} images")

    print(f"Wrote CNN manifest to {args.manifest_out}")


if __name__ == "__main__":
    main()

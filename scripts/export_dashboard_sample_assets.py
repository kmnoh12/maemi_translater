from __future__ import annotations

import argparse
import csv
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent


def choose_samples(rows: list[dict[str, str]], per_species: int) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["species_code"], []).append(row)

    selected = []
    for species_code, items in grouped.items():
        items.sort(
            key=lambda row: (
                row.get("is_korea", "").lower() != "true",
                -float(row["duration_sec"]),
                row["sound_id"],
            )
        )
        selected.extend(items[:per_species])
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inventory",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv",
    )
    parser.add_argument("--per-species", type=int, default=3)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "dashboard" / "assets" / "samples",
    )
    args = parser.parse_args()

    rows = list(csv.DictReader(args.inventory.resolve().open("r", encoding="utf-8-sig", newline="")))
    selected = choose_samples(rows, args.per_species)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for row in selected:
        audio_path = ROOT / row["derived_path"]
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        spec = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=1024, hop_length=256)), ref=np.max)

        fig, ax = plt.subplots(figsize=(8, 3))
        librosa.display.specshow(spec, sr=sr, x_axis="time", y_axis="hz", hop_length=256, ax=ax)
        ax.set_title(f"{row['species_code']} / {row['sound_id']}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Hz")
        plt.tight_layout()

        out_path = args.out_dir / f"{row['species_code']}_sound{row['sound_id']}.png"
        fig.savefig(out_path, dpi=160)
        plt.close(fig)
        print(f"Saved {out_path}")


if __name__ == "__main__":
    main()

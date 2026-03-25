from __future__ import annotations

import csv
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data-workspace" / "metadata" / "public_seed_manifest.csv"
OUT_DIR = ROOT / "ml-workspace" / "reports" / "spectrograms"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            audio_path = ROOT / row["local_derived_path"]
            if not audio_path.exists():
                continue

            y, sr = librosa.load(audio_path, sr=None, mono=True)
            spec = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=1024, hop_length=256)), ref=np.max)

            fig, ax = plt.subplots(figsize=(10, 4))
            librosa.display.specshow(spec, sr=sr, x_axis="time", y_axis="hz", hop_length=256, ax=ax)
            ax.set_title(f"{row['species_code']} ({row['sound_id']})")
            ax.set_xlabel("Time")
            ax.set_ylabel("Frequency")
            plt.tight_layout()

            out_path = OUT_DIR / f"{row['species_code']}_sound{row['sound_id']}.png"
            fig.savefig(out_path, dpi=160)
            plt.close(fig)

            print(f"Saved {out_path}")


if __name__ == "__main__":
    main()

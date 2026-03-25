from __future__ import annotations

import argparse
import csv
from pathlib import Path

import librosa
import numpy as np


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def window_embedding(audio_path: Path, start_sec: float, end_sec: float) -> np.ndarray:
    duration = max(0.0, end_sec - start_sec)
    y, sr = librosa.load(audio_path, sr=None, mono=True, offset=start_sec, duration=duration)
    if len(y) == 0:
        raise ValueError(f"Empty audio window: {audio_path} @ {start_sec}")

    mel = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=1024,
        hop_length=256,
        n_mels=64,
        fmin=150,
        fmax=min(8000, sr // 2),
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    delta = librosa.feature.delta(log_mel)
    delta2 = librosa.feature.delta(log_mel, order=2)

    features: list[float] = []
    for feat in (log_mel, delta, delta2):
        features.extend(np.mean(feat, axis=1).tolist())
        features.extend(np.std(feat, axis=1).tolist())
    return np.asarray(features, dtype=np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_csv", type=Path)
    parser.add_argument(
        "--out-npz",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "features" / "inat_full_logmel_features.npz",
    )
    parser.add_argument(
        "--feature-version",
        default="logmel64_delta_stats_v1",
    )
    args = parser.parse_args()

    rows = load_rows(args.metadata_csv.resolve())
    X: list[np.ndarray] = []
    for idx, row in enumerate(rows, start=1):
        audio_path = (ROOT / row["audio_path"]).resolve()
        start_sec = float(row["start_sec"])
        end_sec = float(row["end_sec"])
        X.append(window_embedding(audio_path, start_sec, end_sec))
        if idx % 500 == 0:
            print(f"processed {idx}/{len(rows)} windows")

    X_np = np.vstack(X)
    args.out_npz = args.out_npz.resolve()
    args.out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out_npz,
        X=X_np,
        feature_version=args.feature_version,
        window_sec=float(rows[0]["window_sec"]) if rows else 3.0,
        hop_sec=float(rows[0]["hop_sec"]) if rows else 1.5,
    )
    print(f"Wrote features to {args.out_npz}")
    print(f"Shape: {X_np.shape}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


def extract_features(audio_path: Path, start_sec: float, duration: float) -> np.ndarray:
    y, sr = librosa.load(audio_path, sr=None, mono=True, offset=start_sec, duration=duration)
    if len(y) == 0:
        raise ValueError(f"Empty audio window: {audio_path} @ {start_sec}")

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spec_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
    flatness = librosa.feature.spectral_flatness(y=y)
    zcr = librosa.feature.zero_crossing_rate(y)
    rms = librosa.feature.rms(y=y)

    features = []
    for feature in [mfcc, spec_centroid, spec_bandwidth, rolloff, flatness, zcr, rms]:
        features.extend(np.mean(feature, axis=1).tolist())
        features.extend(np.std(feature, axis=1).tolist())
    return np.asarray(features, dtype=np.float32)


def iter_windows(duration_sec: float, window_sec: float = 3.0, hop_sec: float = 1.5):
    start_sec = 0.0
    while start_sec + window_sec <= duration_sec + 1e-9:
        yield round(start_sec, 3), round(start_sec + window_sec, 3)
        start_sec += hop_sec

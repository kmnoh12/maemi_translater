from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data-workspace" / "metadata" / "combined_training_manifest_top200.csv"
DEFAULT_OUT_CSV = ROOT / "ml-workspace" / "reports" / "audio_quality_scores.csv"
DEFAULT_OUT_JSON = ROOT / "ml-workspace" / "reports" / "audio_quality_summary.json"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def score_one(audio_path: Path) -> dict[str, float | str]:
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    if y.size == 0:
        return {
            "status": "error",
            "quality_score": 0.0,
            "quality_bucket": "error",
            "error": "empty_audio",
        }

    duration_sec = float(y.size / sr)
    abs_y = np.abs(y)
    peak = float(abs_y.max())
    rms = float(np.sqrt(np.mean(np.square(y))))
    rms_db = float(20.0 * np.log10(max(rms, 1e-8)))

    # Treat very low-energy frames as effectively silent.
    frame = 2048
    hop = 512
    rms_frames = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop)[0]
    active_threshold = max(float(np.percentile(rms_frames, 75) * 0.15), 0.003)
    silence_ratio = float(np.mean(rms_frames < active_threshold))

    clipped_ratio = float(np.mean(abs_y >= 0.99))
    zero_crossing = float(np.mean(librosa.feature.zero_crossing_rate(y=y, frame_length=frame, hop_length=hop)[0]))
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=frame, hop_length=hop)[0]
    centroid_mean = float(np.mean(spectral_centroid))
    centroid_std = float(np.std(spectral_centroid))

    stft = np.abs(librosa.stft(y, n_fft=1024, hop_length=256))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
    total_energy = float(np.sum(stft))
    cicada_band = (freqs >= 1800) & (freqs <= min(9000, sr // 2))
    low_band = (freqs >= 0) & (freqs < 1200)
    cicada_energy_ratio = safe_div(float(np.sum(stft[cicada_band])), total_energy)
    low_band_ratio = safe_div(float(np.sum(stft[low_band])), total_energy)

    # Simple stability measure: strong energy swings often indicate handling noise or inconsistent recording.
    frame_energy = np.sum(stft, axis=0)
    energy_cv = safe_div(float(np.std(frame_energy)), float(np.mean(frame_energy)))

    score = 100.0
    reasons: list[str] = []

    if duration_sec < 4.0:
        score -= 8.0
        reasons.append("short_duration")
    if rms_db < -32:
        score -= 25.0
        reasons.append("very_low_volume")
    elif rms_db < -26:
        score -= 14.0
        reasons.append("low_volume")

    if silence_ratio > 0.65:
        score -= 24.0
        reasons.append("mostly_silent")
    elif silence_ratio > 0.45:
        score -= 12.0
        reasons.append("high_silence")

    if clipped_ratio > 0.01:
        score -= 20.0
        reasons.append("clipping_risk")
    elif clipped_ratio > 0.001:
        score -= 8.0
        reasons.append("minor_clipping")

    if cicada_energy_ratio < 0.30:
        score -= 22.0
        reasons.append("weak_cicada_band")
    elif cicada_energy_ratio < 0.42:
        score -= 10.0
        reasons.append("soft_cicada_band")

    if low_band_ratio > 0.45:
        score -= 16.0
        reasons.append("heavy_low_noise")
    elif low_band_ratio > 0.32:
        score -= 8.0
        reasons.append("moderate_low_noise")

    if energy_cv > 1.2:
        score -= 12.0
        reasons.append("unstable_energy")
    elif energy_cv > 0.9:
        score -= 6.0
        reasons.append("variable_energy")

    if zero_crossing < 0.015:
        score -= 6.0
        reasons.append("weak_texture")

    score = max(0.0, min(100.0, score))
    if score >= 78:
        bucket = "clean"
    elif score >= 58:
        bucket = "borderline"
    else:
        bucket = "noisy"

    return {
        "status": "ok",
        "quality_score": round(score, 2),
        "quality_bucket": bucket,
        "duration_sec": round(duration_sec, 3),
        "peak": round(peak, 5),
        "rms": round(rms, 6),
        "rms_db": round(rms_db, 3),
        "silence_ratio": round(silence_ratio, 4),
        "clipped_ratio": round(clipped_ratio, 6),
        "zero_crossing_rate": round(zero_crossing, 5),
        "spectral_centroid_mean": round(centroid_mean, 2),
        "spectral_centroid_std": round(centroid_std, 2),
        "cicada_band_ratio": round(cicada_energy_ratio, 4),
        "low_band_ratio": round(low_band_ratio, 4),
        "energy_cv": round(energy_cv, 4),
        "reasons": ",".join(reasons),
        "error": "",
    }


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    by_bucket = Counter(row["quality_bucket"] for row in rows)
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    by_species: dict[str, Counter[str]] = defaultdict(Counter)
    scores_by_bucket: dict[str, list[float]] = defaultdict(list)

    for row in rows:
        bucket = row["quality_bucket"]
        by_source[row.get("source", "")][bucket] += 1
        by_species[row.get("species_code", "")][bucket] += 1
        try:
            scores_by_bucket[bucket].append(float(row["quality_score"]))
        except ValueError:
            pass

    return {
        "total_rows": len(rows),
        "bucket_counts": dict(by_bucket),
        "mean_score_by_bucket": {
            bucket: round(float(np.mean(scores)), 2)
            for bucket, scores in scores_by_bucket.items()
            if scores
        },
        "by_source": {key: dict(value) for key, value in sorted(by_source.items())},
        "by_species": {key: dict(value) for key, value in sorted(by_species.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score audio quality for cicada training audio.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    args = parser.parse_args()

    rows = load_rows(args.manifest.resolve())
    scored_rows: list[dict[str, str]] = []

    for idx, row in enumerate(rows, start=1):
        audio_path = (ROOT / row["local_derived_path"]).resolve()
        if not audio_path.exists():
            quality = {
                "status": "error",
                "quality_score": 0.0,
                "quality_bucket": "missing",
                "duration_sec": "",
                "peak": "",
                "rms": "",
                "rms_db": "",
                "silence_ratio": "",
                "clipped_ratio": "",
                "zero_crossing_rate": "",
                "spectral_centroid_mean": "",
                "spectral_centroid_std": "",
                "cicada_band_ratio": "",
                "low_band_ratio": "",
                "energy_cv": "",
                "reasons": "missing_file",
                "error": "missing_file",
            }
        else:
            quality = score_one(audio_path)

        scored_rows.append(
            {
                **row,
                **{key: str(value) for key, value in quality.items()},
            }
        )
        if idx % 200 == 0:
            print(f"scored {idx}/{len(rows)} files")

    args.out_csv = args.out_csv.resolve()
    args.out_json = args.out_json.resolve()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(scored_rows[0].keys()) if scored_rows else []
    with args.out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored_rows)

    summary = summarize_rows(scored_rows)
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote quality scores to {args.out_csv}")
    print(f"Wrote quality summary to {args.out_json}")
    print(json.dumps(summary["bucket_counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()

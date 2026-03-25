from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
import soundfile as sf

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from baseline_audio_utils import extract_features, iter_windows


ROOT = SCRIPT_DIR.parent


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json_if_exists(path: Path, default: dict | None = None) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {} if default is None else default


def file_info(path: Path) -> dict[str, object]:
    stat = path.stat()
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return {
        "path": rel(path),
        "size_bytes": stat.st_size,
        "mtime_epoch": stat.st_mtime,
        "sha256": hasher.hexdigest(),
    }


def build_sample_predictions(
    inventory_rows: list[dict[str, str]],
    model_path: Path,
    per_species: int = 1,
) -> list[dict[str, object]]:
    model_blob = joblib.load(model_path)
    pipeline = model_blob["pipeline"]
    classes = model_blob["classes"]
    window_sec = float(model_blob["window_sec"])
    hop_sec = float(model_blob["hop_sec"])

    first_by_species: dict[str, dict[str, str]] = {}
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in inventory_rows:
        grouped.setdefault(row["species_code"], []).append(row)

    for species_code, items in grouped.items():
        items.sort(
            key=lambda row: (
                row.get("is_korea", "").lower() != "true",
                -float(row["duration_sec"]),
                row["sound_id"],
            )
        )
        first_by_species[species_code] = items[:per_species]

    samples = []
    for species_code, rows in sorted(first_by_species.items()):
        for row in rows:
            audio_path = ROOT / row["derived_path"]
            info = sf.info(str(audio_path))
            mean_probs = defaultdict(list)
            votes = Counter()

            for start_sec, _ in iter_windows(info.duration, window_sec=window_sec, hop_sec=hop_sec):
                features = extract_features(audio_path, start_sec, window_sec).reshape(1, -1)
                probs = pipeline.predict_proba(features)[0]
                top_idx = int(np.argmax(probs))
                votes[classes[top_idx]] += 1
                for idx, label in enumerate(classes):
                    mean_probs[label].append(float(probs[idx]))

            ranking = [
                {
                    "label": label,
                    "mean_probability": float(np.mean(mean_probs[label])) if mean_probs[label] else 0.0,
                    "vote_count": int(votes[label]),
                }
                for label in classes
            ]
            ranking.sort(key=lambda item: item["mean_probability"], reverse=True)

            samples.append(
                {
                    "species_code": species_code,
                    "common_name_ko": row.get("common_name_ko", ""),
                    "audio_path": rel(audio_path),
                    "preview_audio_path": f"dashboard/assets/preview_clips/{species_code}_sound{row['sound_id']}_preview.mp3",
                    "raw_audio_path": rel(ROOT / row["raw_path"]),
                    "sound_id": row["sound_id"],
                    "observation_id": row["observation_id"],
                    "duration_sec": float(row["duration_sec"]),
                    "license_code": row["license_code"],
                    "quality_grade": row.get("quality_grade", ""),
                    "place_guess": row.get("place_guess", ""),
                    "is_korea": row.get("is_korea", ""),
                    "spectrogram_path": f"dashboard/assets/samples/{species_code}_sound{row['sound_id']}.png",
                    "top_prediction": ranking[0] if ranking else None,
                    "top3": ranking[:3],
                }
            )

    return samples


def main() -> None:
    inventory_path = ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv"
    report_path = ROOT / "ml-workspace" / "reports" / "inat_full_feature_report.json"
    duplicates_path = ROOT / "ml-workspace" / "reports" / "inat_full_hash_duplicates.csv"
    screen_spec_path = ROOT / "design-workspace" / "specs" / "android_screen_spec.json"
    model_path = ROOT / "ml-workspace" / "artifacts" / "inat_full_feature_model.joblib"
    prediction_cache_path = ROOT / "dashboard" / "prediction_cache.json"
    health_report_path = ROOT / "ml-workspace" / "reports" / "dataset_health_report.json"
    korea_subset_path = ROOT / "ml-workspace" / "reports" / "korea_subset_report.json"
    korea_prediction_path = ROOT / "ml-workspace" / "reports" / "korea_prediction_report.json"
    confusion_pair_path = ROOT / "ml-workspace" / "reports" / "confusion_pair_report.json"
    two_stage_metrics_path = ROOT / "ml-workspace" / "reports" / "two_stage_metrics_report.json"
    final_operating_rule_path = ROOT / "ml-workspace" / "reports" / "final_operating_rule_report.json"
    two_stage_tuning_path = ROOT / "ml-workspace" / "reports" / "two_stage_tuning_report.json"
    confusion_experiment_path = ROOT / "ml-workspace" / "reports" / "confusion_experiment_report.json"
    cnn_report_path = ROOT / "ml-workspace" / "reports" / "cnn_balanced_stratified_augmented_report.json"
    top200_cnn_report_path = ROOT / "ml-workspace" / "reports" / "cnn_experiment_top200_gpu_report.json"
    top200_cnn_model_path = ROOT / "ml-workspace" / "artifacts" / "cnn_experiment_top200_gpu_model.pt"
    top200_features_path = ROOT / "ml-workspace" / "artifacts" / "features" / "combined_top200_features.npz"
    top200_features_metadata_path = ROOT / "ml-workspace" / "artifacts" / "features" / "combined_top200_features_metadata.csv"
    top200_combined_manifest_path = ROOT / "data-workspace" / "metadata" / "combined_training_manifest_top200.csv"
    inat_approved_manifest_path = ROOT / "data-workspace" / "metadata" / "inat_approved_manifest.csv"
    youtube_top200_manifest_path = ROOT / "data-workspace" / "metadata" / "youtube_manifest_top200.csv"
    focus_species_report_path = ROOT / "ml-workspace" / "reports" / "focus_species_cnn_report.json"
    focus_pair_ac_report_path = ROOT / "ml-workspace" / "reports" / "focus_pair_ac_cnn_report.json"
    focus_pair_ty_report_path = ROOT / "ml-workspace" / "reports" / "focus_pair_ty_cnn_report.json"
    features_path = ROOT / "ml-workspace" / "artifacts" / "features" / "inat_full_features.npz"
    features_metadata_path = ROOT / "ml-workspace" / "artifacts" / "features" / "inat_full_features_metadata.csv"
    ops_queue_path = ROOT / "design-workspace" / "specs" / "ops_queue.json"
    ops_log_dir = ROOT / "ml-workspace" / "reports" / "ops_logs"
    out_js = ROOT / "dashboard" / "data.js"

    inventory_rows = load_csv(inventory_path)
    duplicate_rows = load_csv(duplicates_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    screen_spec = json.loads(screen_spec_path.read_text(encoding="utf-8"))
    prediction_cache = (
        json.loads(prediction_cache_path.read_text(encoding="utf-8"))
        if prediction_cache_path.exists()
        else {"cache_size": 0, "items": []}
    )
    health_report = (
        json.loads(health_report_path.read_text(encoding="utf-8"))
        if health_report_path.exists()
        else {"duration_buckets": {}, "quality": {}}
    )
    korea_subset = (
        json.loads(korea_subset_path.read_text(encoding="utf-8"))
        if korea_subset_path.exists()
        else {"row_count": 0, "species_counts": {}, "duration_by_species": {}}
    )
    korea_prediction = (
        json.loads(korea_prediction_path.read_text(encoding="utf-8"))
        if korea_prediction_path.exists()
        else {"korea_items": 0, "top1_accuracy_over_cached_korea_items": 0.0, "top_confusions": []}
    )
    confusion_pair = (
        json.loads(confusion_pair_path.read_text(encoding="utf-8"))
        if confusion_pair_path.exists()
        else {"top_confusion_pairs": []}
    )
    two_stage_metrics = (
        json.loads(two_stage_metrics_path.read_text(encoding="utf-8"))
        if two_stage_metrics_path.exists()
        else {}
    )
    final_operating_rule = (
        json.loads(final_operating_rule_path.read_text(encoding="utf-8"))
        if final_operating_rule_path.exists()
        else {}
    )
    two_stage_tuning = (
        json.loads(two_stage_tuning_path.read_text(encoding="utf-8"))
        if two_stage_tuning_path.exists()
        else {"rows": []}
    )
    confusion_experiment = (
        json.loads(confusion_experiment_path.read_text(encoding="utf-8"))
        if confusion_experiment_path.exists()
        else {}
    )
    cnn_report = json.loads(cnn_report_path.read_text(encoding="utf-8")) if cnn_report_path.exists() else {}
    top200_cnn_report = load_json_if_exists(top200_cnn_report_path)
    focus_species_report = (
        json.loads(focus_species_report_path.read_text(encoding="utf-8")) if focus_species_report_path.exists() else {}
    )
    focus_pair_ac_report = (
        json.loads(focus_pair_ac_report_path.read_text(encoding="utf-8")) if focus_pair_ac_report_path.exists() else {}
    )
    focus_pair_ty_report = (
        json.loads(focus_pair_ty_report_path.read_text(encoding="utf-8")) if focus_pair_ty_report_path.exists() else {}
    )
    ops_queue = json.loads(ops_queue_path.read_text(encoding="utf-8")) if ops_queue_path.exists() else {"queues": []}
    latest_log = None
    if ops_log_dir.exists():
        logs = sorted(ops_log_dir.glob("long_pipeline_*.log"))
        if logs:
            latest_log = logs[-1]

    species_stats = []
    counts = Counter(row["species_code"] for row in inventory_rows)
    durations = defaultdict(float)
    korea_counts = Counter()
    license_counts = Counter()
    species_names: dict[str, dict[str, str]] = {}
    for row in inventory_rows:
        durations[row["species_code"]] += float(row["duration_sec"])
        if row.get("is_korea", "").lower() == "true":
            korea_counts[row["species_code"]] += 1
        license_counts[row["license_code"]] += 1
        species_names.setdefault(
            row["species_code"],
            {
                "common_name_ko": row.get("common_name_ko", ""),
                "scientific_name": row.get("scientific_name", ""),
            },
        )

    for species_code in sorted(counts):
        species_stats.append(
            {
                "species_code": species_code,
                "common_name_ko": species_names[species_code]["common_name_ko"],
                "scientific_name": species_names[species_code]["scientific_name"],
                "file_count": counts[species_code],
                "duration_sec": round(durations[species_code], 2),
                "korea_count": korea_counts[species_code],
                "world_only_count": counts[species_code] - korea_counts[species_code],
                "f1_score": round(report["metrics"][species_code]["f1-score"], 4),
            }
        )

    dashboard_collection_rows = inventory_rows
    dashboard_counts = counts
    dashboard_durations = durations
    dashboard_korea_counts = korea_counts
    dashboard_license_counts = license_counts
    dashboard_species_names = species_names
    current_training_accuracy = round(report["metrics"]["accuracy"], 4)
    current_training_macro_f1 = round(report["metrics"]["macro avg"]["f1-score"], 4)
    current_top_confusions = report["confusion_matrix"]["off_diagonal"][:10]
    current_feature_version = report["dataset_summary"]["feature_version"]
    current_window_sec = report["dataset_summary"]["window_sec"]
    current_hop_sec = report["dataset_summary"]["hop_sec"]
    current_model_path = model_path
    current_report_path = report_path
    current_features_path = features_path
    current_features_metadata_path = features_metadata_path
    current_dataset_summary = report["dataset_summary"]
    current_cv_strategy = report["cross_validation"]["strategy"]
    current_cv_folds = report["cross_validation"]["num_folds"]

    if top200_cnn_report_path.exists() and top200_cnn_model_path.exists():
        current_training_accuracy = round(top200_cnn_report.get("test_metrics", {}).get("accuracy", 0.0), 4)
        current_training_macro_f1 = round(top200_cnn_report.get("test_metrics", {}).get("macro avg", {}).get("f1-score", 0.0), 4)
        current_top_confusions = top200_cnn_report.get("confusion_matrix", {}).get("off_diagonal", [])[:10]
        current_feature_version = "logmel_cnn_top200_gpu_v1"
        current_window_sec = 3.0
        current_hop_sec = 1.5
        current_model_path = top200_cnn_model_path
        current_report_path = top200_cnn_report_path
        if top200_features_path.exists():
            current_features_path = top200_features_path
        if top200_features_metadata_path.exists():
            current_features_metadata_path = top200_features_metadata_path
        current_dataset_summary = {
            "feature_version": current_feature_version,
            "window_sec": current_window_sec,
            "hop_sec": current_hop_sec,
            "num_feature_rows": top200_cnn_report.get("dataset", {}).get("rows", 0),
            "experiment": "inat_approved_plus_youtube_top200_gpu",
            "source_manifest": rel(top200_combined_manifest_path) if top200_combined_manifest_path.exists() else None,
        }
        current_cv_strategy = "group split by observation_id"
        current_cv_folds = 1
        if top200_combined_manifest_path.exists():
            dashboard_collection_rows = load_csv(top200_combined_manifest_path)
            dashboard_counts = Counter(row["species_code"] for row in dashboard_collection_rows)
            dashboard_durations = defaultdict(float)
            dashboard_korea_counts = Counter()
            dashboard_license_counts = Counter()
            dashboard_species_names = {}
            for row in dashboard_collection_rows:
                derived_path = ROOT / row["local_derived_path"]
                try:
                    dashboard_durations[row["species_code"]] += float(sf.info(str(derived_path)).duration)
                except Exception:
                    pass
                if row.get("region_scope", "") == "korea":
                    dashboard_korea_counts[row["species_code"]] += 1
                dashboard_license_counts[row["license_code"]] += 1
                dashboard_species_names.setdefault(
                    row["species_code"],
                    {
                        "common_name_ko": row.get("common_name_ko", ""),
                        "scientific_name": row.get("scientific_name", ""),
                    },
                )

    species_stats = []
    current_per_class_metrics = top200_cnn_report.get("test_metrics", {}) if top200_cnn_report_path.exists() else report.get("metrics", {})
    for species_code in sorted(dashboard_counts):
        species_metric = current_per_class_metrics.get(species_code, {})
        species_stats.append(
            {
                "species_code": species_code,
                "common_name_ko": dashboard_species_names[species_code]["common_name_ko"],
                "scientific_name": dashboard_species_names[species_code]["scientific_name"],
                "file_count": dashboard_counts[species_code],
                "duration_sec": round(dashboard_durations[species_code], 2),
                "korea_count": dashboard_korea_counts[species_code],
                "world_only_count": dashboard_counts[species_code] - dashboard_korea_counts[species_code],
                "f1_score": round(float(species_metric.get("f1-score", 0.0)), 4),
            }
        )

    duplicate_groups = Counter(row["sha256"] for row in duplicate_rows)
    sample_predictions = build_sample_predictions(inventory_rows, model_path, per_species=3)
    cache_by_sound_id = {
        str(item.get("sound_id")): item
        for item in prediction_cache.get("items", [])
    }
    merged_samples = []
    for sample in sample_predictions:
        cached = cache_by_sound_id.get(str(sample["sound_id"]))
        if cached:
            merged_samples.append({**sample, **cached})
        else:
            merged_samples.append(sample)
    sample_predictions = merged_samples
    sample_spectrograms = {
        (sample["species_code"], sample["sound_id"]): sample["spectrogram_path"]
        for sample in sample_predictions
    }

    library_rows = []
    for row in sorted(
        inventory_rows,
        key=lambda item: (
            item["species_code"],
            item.get("is_korea", "").lower() != "true",
            -float(item["duration_sec"]),
            item["sound_id"],
        ),
    ):
        spectrogram_path = sample_spectrograms.get((row["species_code"], row["sound_id"]))
        library_rows.append(
            {
                "species_code": row["species_code"],
                "common_name_ko": row.get("common_name_ko", ""),
                "scientific_name": row.get("scientific_name", ""),
                "observation_id": row["observation_id"],
                "sound_id": row["sound_id"],
                "duration_sec": round(float(row["duration_sec"]), 2),
                "license_code": row.get("license_code", ""),
                "quality_grade": row.get("quality_grade", ""),
                "place_guess": row.get("place_guess", ""),
                "is_korea": row.get("is_korea", ""),
                "raw_audio_path": rel(ROOT / row["raw_path"]),
                "audio_path": rel(ROOT / row["derived_path"]),
                "preview_audio_path": f"dashboard/assets/preview_clips/{row['species_code']}_sound{row['sound_id']}_preview.mp3",
                "spectrogram_path": spectrogram_path,
            }
        )

    payload = {
        "project": {
            "title": "Maemi Translating Dashboard",
            "subtitle": "Worldwide same-species cicada audio collection and on-device baseline tracking",
        },
        "collection": {
            "inventory_rows": len(dashboard_collection_rows),
            "duplicate_groups": len(duplicate_groups),
            "total_duration_sec": round(sum(float(value) for value in dashboard_durations.values()), 2),
            "korea_rows": sum(dashboard_korea_counts.values()),
            "licenses": dict(dashboard_license_counts),
            "species_stats": species_stats,
            "library_rows": library_rows,
        },
        "training": {
            "feature_version": current_feature_version,
            "window_sec": current_window_sec,
            "hop_sec": current_hop_sec,
            "accuracy": current_training_accuracy,
            "macro_f1": current_training_macro_f1,
            "top_confusions": current_top_confusions,
            "model_status": {
                "baseline_ready": True,
                "app_integrated": False,
                "on_device_ready": False,
                "notes": [
                    "전통 특징 기반 baseline 학습과 예측은 현재 로컬에서 동작한다.",
                    "매미 없음 분류와 한국 현장 데이터 중심 재학습은 아직 필요하다.",
                    "안드로이드 앱과 바로 연결된 on-device 추론 파이프라인은 아직 없다.",
                ],
            },
            "proof": {
                "dataset_summary": current_dataset_summary,
                "cross_validation": {
                    "strategy": current_cv_strategy,
                    "num_folds": current_cv_folds,
                },
                "artifacts": {
                    "model": file_info(current_model_path),
                    "report": file_info(current_report_path),
                    "features": file_info(current_features_path),
                    "feature_metadata": file_info(current_features_metadata_path),
                },
            },
        },
        "assets": {
            "confusion_matrix": rel(ROOT / "ml-workspace" / "reports" / "inat_full_assets" / "confusion_matrix.png"),
            "per_class_f1": rel(ROOT / "ml-workspace" / "reports" / "inat_full_assets" / "per_class_f1.png"),
        },
        "prediction_cache": {
            "cache_size": prediction_cache.get("cache_size", 0),
            "path": rel(prediction_cache_path) if prediction_cache_path.exists() else None,
            "selection_policy": prediction_cache.get("selection_policy", {}),
        },
        "prediction_cache_items": prediction_cache.get("items", []),
        "dataset_health": {
            "duration_buckets": health_report.get("duration_buckets", {}),
            "quality": health_report.get("quality", {}),
            "path": rel(health_report_path) if health_report_path.exists() else None,
        },
        "korea_subset": {
            "row_count": korea_subset.get("row_count", 0),
            "species_counts": korea_subset.get("species_counts", {}),
            "duration_by_species": korea_subset.get("duration_by_species", {}),
            "path": rel(korea_subset_path) if korea_subset_path.exists() else None,
        },
        "korea_prediction": {
            "korea_items": korea_prediction.get("korea_items", 0),
            "top1_accuracy_over_cached_korea_items": korea_prediction.get("top1_accuracy_over_cached_korea_items", 0.0),
            "per_species_accuracy": korea_prediction.get("per_species_accuracy", {}),
            "top_confusions": korea_prediction.get("top_confusions", []),
            "path": rel(korea_prediction_path) if korea_prediction_path.exists() else None,
        },
        "confusion_pair_report": {
            "top_confusion_pairs": confusion_pair.get("top_confusion_pairs", []),
            "path": rel(confusion_pair_path) if confusion_pair_path.exists() else None,
        },
        "two_stage_metrics": two_stage_metrics,
        "final_operating_rule": final_operating_rule,
        "two_stage_tuning": two_stage_tuning,
        "model_comparison": {
            "baseline": {
                "label": "Baseline",
                "accuracy": round(report["metrics"]["accuracy"], 4),
                "macro_f1": round(report["metrics"]["macro avg"]["f1-score"], 4),
                "note": "full LOGO baseline",
            },
            "two_stage_strict": {
                "label": "2단계 운영",
                "accuracy": round(final_operating_rule.get("operating_metrics", {}).get("final_accepted_accuracy", 0.0), 4),
                "macro_f1": None,
                "note": "strict 승격 후 accepted 정확도",
                "abstain_rate": round(final_operating_rule.get("operating_metrics", {}).get("final_abstain_rate", 0.0), 4),
            },
            "cnn_6species": {
                "label": "6종 CNN",
                "accuracy": round(top200_cnn_report.get("test_metrics", {}).get("accuracy", 0.0), 4),
                "macro_f1": round(top200_cnn_report.get("test_metrics", {}).get("macro avg", {}).get("f1-score", 0.0), 4),
                "note": "iNat approved + YouTube top200",
            },
            "focus_4species": {
                "label": "4종 confusion CNN",
                "accuracy": round(focus_species_report.get("test_metrics", {}).get("accuracy", 0.0), 4),
                "macro_f1": round(focus_species_report.get("test_metrics", {}).get("macro avg", {}).get("f1-score", 0.0), 4),
                "note": "애매미/참매미/털매미/유지매미",
            },
        },
        "confusion_experiments": {
            "summary": confusion_experiment,
            "pair_ac": {
                "label": "애매미/참매미",
                "accuracy": round(focus_pair_ac_report.get("test_metrics", {}).get("accuracy", 0.0), 4),
                "macro_f1": round(focus_pair_ac_report.get("test_metrics", {}).get("macro avg", {}).get("f1-score", 0.0), 4),
                "top_confusions": focus_pair_ac_report.get("confusion_matrix", {}).get("off_diagonal", []),
            },
            "pair_ty": {
                "label": "털매미/유지매미",
                "accuracy": round(focus_pair_ty_report.get("test_metrics", {}).get("accuracy", 0.0), 4),
                "macro_f1": round(focus_pair_ty_report.get("test_metrics", {}).get("macro avg", {}).get("f1-score", 0.0), 4),
                "top_confusions": focus_pair_ty_report.get("confusion_matrix", {}).get("off_diagonal", []),
            },
        },
        "ops_queue": {
            "queues": ops_queue.get("queues", []),
            "latest_log_path": rel(latest_log) if latest_log else None,
        },
        "android": {
            "screen_count": len(screen_spec["screens"]),
            "screens": screen_spec["screens"],
            "spec_path": rel(screen_spec_path),
            "brief_path": rel(ROOT / "docs" / "10-android-screen-spec.md"),
        },
        "samples": sample_predictions,
        "paths": {
            "inventory": rel(top200_combined_manifest_path) if top200_combined_manifest_path.exists() else rel(inventory_path),
            "report": rel(current_report_path),
            "duplicates": rel(duplicates_path),
            "model": rel(current_model_path),
        },
    }

    out_js.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote dashboard payload to {out_js}")


if __name__ == "__main__":
    main()

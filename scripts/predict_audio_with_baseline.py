from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from baseline_audio_utils import iter_windows
from focus_cnn_utils import SmallCicadaCNN, render_logmel_tensor


ROOT = Path(__file__).resolve().parent.parent
LATEST_CNN_MODEL_PATH = ROOT / "ml-workspace" / "artifacts" / "cnn_experiment_top200_gpu_model.pt"
WINDOW_SEC = 3.0
HOP_SEC = 1.5


def build_recommendation(aggregate: list[dict[str, object]]) -> dict[str, object]:
    top1 = aggregate[0] if aggregate else None
    top2 = aggregate[1] if len(aggregate) > 1 else {"label": None, "mean_probability": 0.0, "vote_count": 0}
    if not top1:
        return {
            "status": "no_result",
            "display_label": None,
            "reason": "no_prediction",
            "prob_gap": 0.0,
            "vote_gap": 0,
        }

    prob_gap = float(top1["mean_probability"]) - float(top2["mean_probability"])
    vote_gap = int(top1["vote_count"]) - int(top2["vote_count"])
    if prob_gap < 0.08 or vote_gap <= 2:
        return {
            "status": "low_confidence",
            "display_label": None,
            "reason": "small_top1_top2_gap",
            "prob_gap": prob_gap,
            "vote_gap": vote_gap,
            "candidate_labels": [item["label"] for item in aggregate[:3]],
        }

    return {
        "status": "accepted",
        "display_label": top1["label"],
        "reason": "clear_margin",
        "prob_gap": prob_gap,
        "vote_gap": vote_gap,
        "candidate_labels": [item["label"] for item in aggregate[:3]],
    }


def load_cnn(model_path: Path) -> tuple[SmallCicadaCNN, list[str], int, torch.device]:
    blob = torch.load(model_path.resolve(), map_location="cpu")
    classes = list(blob["classes"])
    image_size = int(blob.get("image_size", 128))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SmallCicadaCNN(num_classes=len(classes))
    model.load_state_dict(blob["state_dict"])
    model.to(device)
    model.eval()
    return model, classes, image_size, device


def predict_audio(audio_path: Path, model_path: Path) -> dict[str, object]:
    audio_path = audio_path.resolve()
    model, classes, image_size, device = load_cnn(model_path)
    info = sf.info(str(audio_path))

    window_rows = []
    mean_probs = defaultdict(list)
    votes = Counter()

    with torch.no_grad():
        for start_sec, end_sec in iter_windows(info.duration, window_sec=WINDOW_SEC, hop_sec=HOP_SEC):
            tensor = render_logmel_tensor(audio_path, start_sec, WINDOW_SEC, image_size=image_size).to(device)
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()
            top_idx = int(np.argmax(probs))
            top_label = classes[top_idx]
            votes[top_label] += 1
            for idx, label in enumerate(classes):
                mean_probs[label].append(float(probs[idx]))
            window_rows.append(
                {
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "top_label": top_label,
                    "top_probability": float(probs[top_idx]),
                    "probabilities": {label: float(probs[i]) for i, label in enumerate(classes)},
                }
            )

    aggregate = [
        {
            "label": label,
            "mean_probability": float(np.mean(mean_probs[label])) if mean_probs[label] else 0.0,
            "vote_count": int(votes[label]),
        }
        for label in classes
    ]
    aggregate.sort(key=lambda item: item["mean_probability"], reverse=True)
    recommendation = build_recommendation(aggregate)

    return {
        "audio_path": str(audio_path),
        "duration_sec": info.duration,
        "num_windows": len(window_rows),
        "window_sec": WINDOW_SEC,
        "hop_sec": HOP_SEC,
        "aggregate_ranking": aggregate,
        "window_predictions": window_rows,
        "recommendation": recommendation,
        "risky_accepted_trigger": {
            "triggered": False,
            "min_top1_prob": None,
            "max_duration_sec": None,
            "focus_overlap_top3": 0,
            "top1_probability": float(aggregate[0]["mean_probability"]) if aggregate else 0.0,
        },
        "second_stage": None,
        "final_recommendation": {
            **recommendation,
            "source_model": "top200_gpu_cnn",
            "model_path": str(model_path.resolve().relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", type=Path)
    parser.add_argument("--model", type=Path, default=LATEST_CNN_MODEL_PATH)
    parser.add_argument("--out", type=Path, default=ROOT / "ml-workspace" / "reports" / "latest_prediction.json")
    args = parser.parse_args()

    result = predict_audio(args.audio_path, args.model)

    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote prediction report to {args.out}")
    if result["aggregate_ranking"]:
        top = result["aggregate_ranking"][0]
        print("Top label:", top["label"])
        print("Top mean probability:", round(float(top["mean_probability"]), 4))


if __name__ == "__main__":
    main()

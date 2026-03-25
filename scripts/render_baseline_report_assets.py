from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_json", type=Path)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "assets",
    )
    args = parser.parse_args()

    report = json.loads(args.report_json.resolve().read_text(encoding="utf-8"))
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = report["confusion_matrix"]["labels"]
    matrix = np.array(report["confusion_matrix"]["matrix"])
    f1_scores = [report["metrics"][label]["f1-score"] for label in labels]

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="YlGnBu")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion Matrix")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, int(matrix[i, j]), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    confusion_path = out_dir / "confusion_matrix.png"
    fig.savefig(confusion_path, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, f1_scores, color="#3b82f6")
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1 score")
    ax.set_title("Per-class F1")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    f1_path = out_dir / "per_class_f1.png"
    fig.savefig(f1_path, dpi=180)
    plt.close(fig)

    print(f"Saved {confusion_path}")
    print(f"Saved {f1_path}")


if __name__ == "__main__":
    main()

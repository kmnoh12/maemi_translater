from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class RGBSpectrogramDataset(Dataset):
    def __init__(self, rows: list[dict[str, str]], label_to_idx: dict[str, int], augment: bool = False) -> None:
        self.rows = rows
        self.label_to_idx = label_to_idx
        self.augment = augment

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        row = self.rows[index]
        image_path = (ROOT / row["image_path"]).resolve()
        image = Image.open(image_path).convert("L")
        arr = np.asarray(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0).repeat(3, 1, 1)
        if self.augment:
            if torch.rand(1).item() < 0.5:
                tensor = torch.clamp(tensor + 0.025 * torch.randn_like(tensor), 0.0, 1.0)
            if torch.rand(1).item() < 0.5:
                tensor = torch.flip(tensor, dims=[2])
            if torch.rand(1).item() < 0.3:
                width = tensor.shape[-1]
                start = int(torch.randint(0, max(1, width - 12), (1,)).item())
                tensor[:, :, start:start + 12] = 0.0
        label = self.label_to_idx[row["species_code"]]
        return tensor, label


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, object]:
    model.eval()
    all_true: list[int] = []
    all_pred: list[int] = []
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            logits = model(inputs)
            loss = criterion(logits, labels)
            total_loss += loss.item() * labels.size(0)
            preds = torch.argmax(logits, dim=1)
            all_true.extend(labels.cpu().tolist())
            all_pred.extend(preds.cpu().tolist())
    accuracy = float(np.mean(np.asarray(all_true) == np.asarray(all_pred))) if all_true else 0.0
    avg_loss = total_loss / len(all_true) if all_true else 0.0
    return {"loss": avg_loss, "accuracy": accuracy, "y_true": all_true, "y_pred": all_pred}


def build_model(num_classes: int, freeze_backbone: bool = True) -> nn.Module:
    weights = models.ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights)
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, num_classes),
    )
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split_manifest_csv", type=Path)
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "ml-workspace" / "reports" / "transfer_resnet_report.json",
    )
    parser.add_argument(
        "--model-out",
        type=Path,
        default=ROOT / "ml-workspace" / "artifacts" / "transfer_resnet_model.pt",
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--use-weighted-sampler", action="store_true")
    parser.add_argument("--unfreeze-backbone", action="store_true")
    args = parser.parse_args()

    rows = load_rows(args.split_manifest_csv.resolve())
    train_rows = [row for row in rows if row["split"] == "train"]
    val_rows = [row for row in rows if row["split"] == "val"]
    test_rows = [row for row in rows if row["split"] == "test"]
    classes = sorted({row["species_code"] for row in rows})
    label_to_idx = {label: idx for idx, label in enumerate(classes)}

    train_ds = RGBSpectrogramDataset(train_rows, label_to_idx, augment=True)
    val_ds = RGBSpectrogramDataset(val_rows, label_to_idx)
    test_ds = RGBSpectrogramDataset(test_rows, label_to_idx)

    if args.use_weighted_sampler:
        class_counts = Counter(row["species_code"] for row in train_rows)
        sample_weights = [1.0 / class_counts[row["species_code"]] for row in train_rows]
        sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
        train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler, num_workers=0)
    else:
        train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("cpu")
    model = build_model(len(classes), freeze_backbone=not args.unfreeze_backbone).to(device)
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=args.learning_rate)
    criterion = nn.CrossEntropyLoss()

    history: list[dict[str, float]] = []
    best_state = None
    best_val_acc = -1.0
    epochs_without_improvement = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        running_correct = 0
        running_total = 0
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * labels.size(0)
            preds = torch.argmax(logits, dim=1)
            running_correct += int((preds == labels).sum().item())
            running_total += int(labels.size(0))

        train_loss = running_loss / max(1, running_total)
        train_acc = running_correct / max(1, running_total)
        val_metrics = evaluate(model, val_loader, device)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_accuracy": train_acc,
                "val_loss": val_metrics["loss"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        print(
            f"epoch {epoch}/{args.epochs} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_metrics['loss']:.4f} val_acc={val_metrics['accuracy']:.4f}"
        )
        if val_metrics["accuracy"] > best_val_acc:
            best_val_acc = float(val_metrics["accuracy"])
            best_state = {key: value.cpu().clone() for key, value in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.patience:
                print(f"early stopping at epoch {epoch} (patience={args.patience})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    test_metrics = evaluate(model, test_loader, device)
    y_true = test_metrics["y_true"]
    y_pred = test_metrics["y_pred"]
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(classes))))
    off_diagonal = []
    for i, true_label in enumerate(classes):
        for j, pred_label in enumerate(classes):
            if i != j and cm[i, j] > 0:
                off_diagonal.append({"true": true_label, "pred": pred_label, "count": int(cm[i, j])})

    payload = {
        "dataset": {
            "split_manifest": str(args.split_manifest_csv.resolve()),
            "rows": len(rows),
            "train_rows": len(train_rows),
            "val_rows": len(val_rows),
            "test_rows": len(test_rows),
            "rows_per_class": dict(Counter(row["species_code"] for row in rows)),
            "classes": classes,
        },
        "training": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "patience": args.patience,
            "use_weighted_sampler": args.use_weighted_sampler,
            "unfreeze_backbone": args.unfreeze_backbone,
            "device": str(device),
            "history": history,
            "best_val_accuracy": best_val_acc,
        },
        "test_metrics": report,
        "confusion_matrix": {
            "labels": classes,
            "matrix": cm.tolist(),
            "off_diagonal": sorted(off_diagonal, key=lambda item: item["count"], reverse=True),
        },
    }

    args.report_out = args.report_out.resolve()
    args.model_out = args.model_out.resolve()
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    torch.save({"state_dict": model.state_dict(), "classes": classes, "image_size": 128}, args.model_out)
    print(f"Wrote report to {args.report_out}")
    print(f"Wrote model to {args.model_out}")
    print(f"Test accuracy: {report['accuracy']:.4f}")
    print(f"Test macro F1: {report['macro avg']['f1-score']:.4f}")


if __name__ == "__main__":
    main()

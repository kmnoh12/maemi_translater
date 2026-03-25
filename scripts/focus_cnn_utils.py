from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import torch
from torch import nn


class SmallCicadaCNN(nn.Module):
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 16 * 16, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def render_logmel_tensor(audio_path: Path, start_sec: float, duration: float, image_size: int = 128) -> torch.Tensor:
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
    arr = np.uint8(np.clip(normalized * 255.0, 0, 255))
    image = arr[::-1, :]
    image = torch.from_numpy(image.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0)
    image = torch.nn.functional.interpolate(image, size=(image_size, image_size), mode="bilinear", align_corners=False)
    return image

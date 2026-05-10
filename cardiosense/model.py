"""Compact 1D CNN for binary ECG classification."""
from __future__ import annotations

import torch
import torch.nn as nn

from .config import NUM_CLASSES, WINDOW_SAMPLES


class ECGCNN(nn.Module):
    """Small 1D CNN. Input: (B, 1, WINDOW_SAMPLES). Output: (B, NUM_CLASSES)."""

    def __init__(self, num_classes: int = NUM_CLASSES, in_samples: int = WINDOW_SAMPLES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=15, stride=2, padding=7),
            nn.BatchNorm1d(16), nn.ReLU(inplace=True),
            nn.MaxPool1d(2),

            nn.Conv1d(16, 32, kernel_size=11, stride=1, padding=5),
            nn.BatchNorm1d(32), nn.ReLU(inplace=True),
            nn.MaxPool1d(2),

            nn.Conv1d(32, 64, kernel_size=7, stride=1, padding=3),
            nn.BatchNorm1d(64), nn.ReLU(inplace=True),
            nn.MaxPool1d(2),

            nn.Conv1d(64, 64, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm1d(64), nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(64, 32), nn.ReLU(inplace=True),
            nn.Linear(32, num_classes),
        )
        self.in_samples = in_samples

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:
            x = x.unsqueeze(1)
        return self.head(self.features(x))


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

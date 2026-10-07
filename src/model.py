"""모델 정의 — project.md §16 baseline 구조.

Vision Encoder (initially frozen) → MLP Head → Sigmoid.
P00 skeleton 은 stub encoder 만 제공하며, 실제 SigLIP/DINO encoder 연결은
P02(§27 Phase 2 'Vision Encoder 연결')에서 추가한다.
"""
from __future__ import annotations

import torch
from torch import nn


class StubEncoder(nn.Module):
    """스모크·초기 파이프라인 검증용 경량 encoder (출력 차원 = embedding_dim)."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(16 * 4 * 4, embedding_dim),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.net(images)


def build_encoder(name: str, embedding_dim: int) -> nn.Module:
    """config 의 model.encoder 값을 encoder 인스턴스로 만든다."""
    if name == "stub":
        return StubEncoder(embedding_dim)
    raise ValueError(
        f"unknown encoder {name!r}: P00 은 'stub' 만 지원 (siglip/dino 는 P02 에서 추가)"
    )


class RealismScorer(nn.Module):
    """§16: Embedding → Linear → GELU → Dropout → Linear(1) → Sigmoid."""

    def __init__(self, encoder: nn.Module, embedding_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, 1),
            nn.Sigmoid(),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """이미지 배치 [B,3,H,W] → realism 확률 [B] (0.0 ~ 1.0, §16 inference 정의)."""
        return self.head(self.encoder(images)).squeeze(-1)


def set_encoder_frozen(model: RealismScorer, frozen: bool) -> None:
    """§16/§17: encoder 는 freeze 하고 학습 대상은 head (+이후 LoRA)."""
    for param in model.encoder.parameters():
        param.requires_grad_(not frozen)

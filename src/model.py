"""모델 정의 — project.md §16 baseline 구조.

Vision Encoder (initially frozen) → MLP Head → Sigmoid.
SigLIP vision adapter와 다운로드 없는 smoke용 stub을 제공한다.
"""
from __future__ import annotations

import torch
from torch import nn


class StubEncoder(nn.Module):
    """스모크·초기 파이프라인 검증용 경량 encoder (출력 차원 = embedding_dim)."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.embedding_dim = embedding_dim
        self.net = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(16 * 4 * 4, embedding_dim),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.net(images)


class SiglipEncoder(nn.Module):
    """Hugging Face vision-only 모델의 pretrained pooled feature를 반환한다."""

    def __init__(self, model_id: str, revision: str | None = None) -> None:
        super().__init__()
        from transformers import SiglipVisionModel

        self.vision = SiglipVisionModel.from_pretrained(model_id, revision=revision)
        self.embedding_dim = self.vision.config.hidden_size

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.vision(pixel_values=images).pooler_output


def build_encoder(name: str, embedding_dim: int = 64, model_id: str | None = None,
                  revision: str | None = None) -> nn.Module:
    """차원은 pretrained config에서 유도한다. stub만 명시 차원을 사용한다."""
    if name == "stub":
        return StubEncoder(embedding_dim)
    if name == "siglip":
        if model_id is None:
            raise ValueError("siglip requires model.model_id")
        return SiglipEncoder(model_id, revision)
    raise ValueError(f"unknown encoder {name!r}")


class RealismScorer(nn.Module):
    """§16: Embedding → Linear → GELU → Dropout → Linear(1) → Sigmoid."""

    def __init__(self, encoder: nn.Module, embedding_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.encoder = encoder
        self.encoder_frozen = False
        self.head = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, 1),
            nn.Sigmoid(),
        )

    def train(self, mode: bool = True) -> RealismScorer:
        super().train(mode)
        if self.encoder_frozen:
            self.encoder.eval()
        return self

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """이미지 배치 [B,3,H,W] → realism 확률 [B] (0.0 ~ 1.0, §16 inference 정의)."""
        if self.encoder_frozen:
            with torch.no_grad():
                features = self.encoder(images)
        else:
            features = self.encoder(images)
        return self.head(features).squeeze(-1)


def set_encoder_frozen(model: RealismScorer, frozen: bool) -> None:
    """§16/§17: encoder 는 freeze 하고 학습 대상은 head (+이후 LoRA)."""
    model.encoder_frozen = frozen
    model.encoder.train(model.training and not frozen)
    for param in model.encoder.parameters():
        param.requires_grad_(not frozen)

"""메타데이터 기반 Dataset — project.md §12 스키마(v1.2), §15 전처리.

CSV 컬럼(§12 v1.2): image_id, path, label, category, parts, source_type,
source_domain, generator, style, look_group, prompt_id, split. path 는 CSV 파일이
있는 디렉터리 기준 상대 경로로 해석한다.
"""
from __future__ import annotations

import csv
import io
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms


@dataclass(frozen=True)
class MetadataRow:
    image_id: str
    path: str
    label: int
    category: str
    source_type: str
    split: str = ""
    generator: str = ""
    source_domain: str = ""


def read_metadata(csv_path: str | Path) -> list[MetadataRow]:
    """metadata.csv 를 읽어 §12 스키마 행으로 변환한다."""
    rows: list[MetadataRow] = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            rows.append(
                MetadataRow(
                    image_id=record["image_id"],
                    path=record["path"],
                    label=int(record["label"]),
                    category=record["category"],
                    source_type=record["source_type"],
                    split=record.get("split", ""),
                    generator=record.get("generator", ""),
                    source_domain=record.get("source_domain", ""),
                )
            )
    return rows


class RandomJPEG:
    """§15: JPEG compression augmentation — 확률 p 로 무작위 품질 재압축."""

    def __init__(self, p: float = 0.5, quality_range: tuple[int, int] = (60, 95)) -> None:
        self.p = p
        self.quality_range = quality_range

    def __call__(self, image: Image.Image) -> Image.Image:
        if random.random() < self.p:
            buffer = io.BytesIO()
            quality = random.randint(*self.quality_range)
            image.save(buffer, format="JPEG", quality=quality)
            buffer.seek(0)
            return Image.open(buffer).convert("RGB")
        return image


def build_transform(image_size: int, horizontal_flip: bool, jpeg_aug: bool,
                    minor_crop: bool = False, color_jitter: bool = False,
                    normalization: dict | None = None) -> transforms.Compose:
    """§15: 약한 train augmentation, 평가에는 결정적 resize/정규화만 적용."""
    if normalization is None:
        normalization = dict(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
    layers: list = [transforms.Resize((image_size, image_size),
                    interpolation=transforms.InterpolationMode.BICUBIC)]
    if minor_crop:
        layers.append(transforms.RandomResizedCrop(
            image_size, scale=(0.95, 1.0), ratio=(0.95, 1.05),
            interpolation=transforms.InterpolationMode.BICUBIC,
        ))
    if color_jitter:
        layers.append(transforms.ColorJitter(brightness=0.05, contrast=0.05))
    if horizontal_flip:
        layers.append(transforms.RandomHorizontalFlip())
    if jpeg_aug:
        layers.append(RandomJPEG())
    layers += [
        transforms.ToTensor(),
        transforms.Normalize(mean=normalization["mean"], std=normalization["std"]),
    ]
    return transforms.Compose(layers)


class MetadataDataset(Dataset):
    """metadata.csv 기반 (image, label) Dataset. label: REAL=1, GENERATED=0 (§16)."""

    def __init__(
        self,
        csv_path: str | Path,
        image_size: int,
        horizontal_flip: bool,
        jpeg_aug: bool,
        split: str | None = None,
        minor_crop: bool = False,
        color_jitter: bool = False,
        image_root: str | Path | None = None,
        normalization: dict | None = None,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.image_root = Path(image_root) if image_root is not None else None
        self.rows = read_metadata(self.csv_path)
        if split is not None:
            self.rows = [row for row in self.rows if row.split == split]
        self.transform = build_transform(image_size, horizontal_flip, jpeg_aug, minor_crop, color_jitter, normalization)

    def __len__(self) -> int:
        return len(self.rows)

    def image_path(self, index: int) -> Path:
        row = self.rows[index]
        return (self.image_root / Path(row.path).relative_to("images")
                if self.image_root is not None else self.csv_path.parent / row.path)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, float]:
        row = self.rows[index]
        with Image.open(self.image_path(index)) as handle:
            image = handle.convert("RGB")
        return self.transform(image), float(row.label)

"""학습 entrypoint — project.md §25 config 구동.

사용:
    python -m src.train --config configs/baseline.yaml          # 실데이터 학습 (P01 이후)
    python -m src.train --config configs/baseline.yaml --smoke  # 실데이터 없이 skeleton 검증
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import torch
import yaml
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader

from src.dataset import MetadataDataset
from src.model import RealismScorer, build_encoder, set_encoder_frozen

SEED = 42
SMOKE_NUM_IMAGES = 8


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_smoke_dataset(directory: Path) -> Path:
    """tiny synthetic dataset — 실데이터 없이 전체 파이프라인을 관통시킨다(§35 thin-slice 원칙)."""
    images_dir = directory / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "metadata.csv"
    records = []
    for i in range(SMOKE_NUM_IMAGES):
        name = f"img_{i:06d}.png"
        Image.new("RGB", (32, 32), color=(i * 28 % 256, 64, 128)).save(images_dir / name)
        records.append(f"img_{i:06d},images/{name},{i % 2},smoke,{'real' if i % 2 else 'generated'}")
    csv_path.write_text(
        "image_id,path,label,category,source_type\n" + "\n".join(records) + "\n",
        encoding="utf-8",
    )
    return csv_path


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description="Tracepecter 학습 (§25 config 구동)")
    parser.add_argument("--config", required=True, help="YAML config 경로 (예: configs/baseline.yaml)")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="tiny synthetic 데이터로 1 epoch 실행 — 실데이터 없이 skeleton 검증",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    torch.manual_seed(SEED)

    checkpoint_dir = Path(config["output"]["checkpoint_dir"])
    epochs: int = config["training"]["epochs"]
    train_csv: str = config["data"]["train_csv"]
    # data.val_csv 를 사용한 validation 루프·metric 출력은 P02(§27 Phase 2)에서 구현한다.

    if args.smoke:
        smoke_root = Path(tempfile.mkdtemp(prefix="tracepecter_smoke_"))
        train_csv = str(build_smoke_dataset(smoke_root / "train"))
        epochs = 1
        checkpoint_dir = smoke_root / "checkpoints"

    train_dataset = MetadataDataset(
        train_csv,
        image_size=config["model"]["image_size"],
        horizontal_flip=config["augmentation"]["horizontal_flip"],
        jpeg_aug=config["augmentation"]["jpeg_aug"],
    )
    train_loader = DataLoader(
        train_dataset, batch_size=config["training"]["batch_size"], shuffle=True
    )

    model = RealismScorer(
        encoder=build_encoder(config["model"]["encoder"], config["model"]["embedding_dim"]),
        embedding_dim=config["model"]["embedding_dim"],
    )
    set_encoder_frozen(model, frozen=config["model"]["freeze_encoder"])

    optimizer = torch.optim.Adam(
        (param for param in model.parameters() if param.requires_grad),
        lr=config["training"]["learning_rate"],
    )
    loss_fn = nn.BCELoss()

    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            probabilities = model(images)
            # DataLoader 가 python float label 을 float64 로 collate 하므로 맞춘다.
            loss = loss_fn(probabilities, labels.to(probabilities.dtype))
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"epoch {epoch}/{epochs} train_loss={total_loss / len(train_loader):.6f}")

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "baseline.pt"
    torch.save(
        {"model_state": model.state_dict(), "config": config, "epochs_done": epochs},
        checkpoint_path,
    )
    print(f"checkpoint saved: {checkpoint_path}")
    if args.smoke:
        print("smoke ok")
    return checkpoint_path


if __name__ == "__main__":
    main()

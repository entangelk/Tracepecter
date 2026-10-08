"""학습 entrypoint — project.md §25 config 구동.

사용:
    python -m src.train --config configs/baseline.yaml          # 실데이터 학습 (P01 이후)
    python -m src.train --config configs/baseline.yaml --smoke  # 실데이터 없이 skeleton 검증
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import subprocess
import shutil
import tempfile
from pathlib import Path

import torch
import yaml
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader

from src.dataset import MetadataDataset
from src.evaluate import binary_metrics, predict
from src.model import RealismScorer, build_encoder, set_encoder_frozen

SEED = 42
SMOKE_NUM_IMAGES = 8


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_loss() -> nn.Module:
    """§16: Loss = Binary Cross Entropy."""
    return nn.BCELoss()


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


def run_training(config: dict, train_csv: str, epochs: int, checkpoint_dir: Path,
                 resume: bool = False) -> Path:
    """config 대로 dataset·model·optimizer 를 구성해 학습하고 checkpoint 를 저장한다."""
    device = config["training"].get("device", "cpu")
    mc = config["model"]
    augmentation = config["augmentation"]
    split = "train" if "metadata_csv" in config["data"] else None
    train_dataset = MetadataDataset(
        train_csv, image_size=mc["image_size"],
        horizontal_flip=augmentation["horizontal_flip"], jpeg_aug=augmentation["jpeg_aug"],
        split=split, minor_crop=augmentation.get("minor_crop", False),
        color_jitter=augmentation.get("color_jitter", False),
        image_root=config["data"].get("image_root"),
    )
    val_csv = config["data"].get("metadata_csv", config["data"].get("val_csv", train_csv))
    val_dataset = MetadataDataset(val_csv, mc["image_size"], False, False,
                                  split="val" if split else None, image_root=config["data"].get("image_root"))
    if not train_dataset or not val_dataset:
        raise ValueError("train and validation datasets must be nonempty")
    loader_options = dict(batch_size=config["training"]["batch_size"],
                          num_workers=config["training"].get("num_workers", 0),
                          pin_memory=device.startswith("cuda"))
    train_loader = DataLoader(train_dataset, shuffle=True, **loader_options)
    val_loader = DataLoader(val_dataset, **loader_options)
    encoder = build_encoder(mc["encoder"], mc.get("embedding_dim", 64), mc.get("model_id"), mc.get("revision"))
    model = RealismScorer(encoder, encoder.embedding_dim)
    set_encoder_frozen(model, frozen=mc["freeze_encoder"])
    model.to(device)
    optimizer = torch.optim.Adam(
        (param for param in model.parameters() if param.requires_grad),
        lr=config["training"]["learning_rate"],
    )
    loss_fn = build_loss()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "best.pt"
    best_loss = float("inf")
    history = []
    start_epoch = 1
    if resume:
        previous = torch.load(checkpoint_dir / "last.pt", map_location="cpu", weights_only=True)
        if previous["config"] != config:
            raise ValueError("resume requires the same config")
        model.load_state_dict(previous["model_state"])
        optimizer.load_state_dict(previous["optimizer_state"])
        torch.set_rng_state(previous["torch_rng"])
        random.setstate(previous["random_rng"])
        if device.startswith("cuda"):
            torch.cuda.set_rng_state_all(previous["cuda_rng"])
        best_loss = previous["best_loss"]
        history = previous["history"]
        start_epoch = previous["epochs_done"] + 1
    for epoch in range(start_epoch, epochs + 1):
        model.train()
        total_loss = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            probabilities = model(images.to(device))
            loss = loss_fn(probabilities, labels.to(device=device, dtype=probabilities.dtype))
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(labels)
        labels, probabilities = predict(model, val_loader, device)
        val_loss = loss_fn(torch.tensor(probabilities), torch.tensor(labels, dtype=torch.float32)).item()
        metrics = binary_metrics(labels, probabilities)
        history.append(dict(epoch=epoch, train_loss=total_loss / len(train_dataset),
                            val_loss=val_loss, validation_metrics=metrics))
        print(f"epoch {epoch}/{epochs} train_loss={history[-1]['train_loss']:.6f} "
              f"val_loss={val_loss:.6f} val_roc_auc={metrics['roc_auc']}")
        if val_loss < best_loss:
            best_loss = val_loss
            temporary = checkpoint_path.with_suffix(".tmp")
            torch.save(dict(model_state=model.state_dict(), config=config, epochs_done=epoch,
                            validation_metrics=metrics, val_loss=val_loss), temporary)
            temporary.replace(checkpoint_path)
        last_path = checkpoint_dir / "last.tmp"
        torch.save(dict(model_state=model.state_dict(), optimizer_state=optimizer.state_dict(),
                        config=config, epochs_done=epoch, best_loss=best_loss, history=history,
                        torch_rng=torch.get_rng_state(), random_rng=random.getstate(),
                        cuda_rng=torch.cuda.get_rng_state_all() if device.startswith("cuda") else []),
                   last_path)
        last_path.replace(checkpoint_dir / "last.pt")
        # 매 epoch 기록: 전원 단절 시 마지막 best checkpoint와 진행 기록이 남는다.
        commit = os.environ.get("GIT_COMMIT")
        if not commit and shutil.which("git"):
            commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        record = dict(experiment_name=checkpoint_dir.name, git_commit=commit,
                      dataset_version=hashlib.sha256(Path(train_csv).read_bytes()).hexdigest(),
                      model=mc, train_sample_count=len(train_dataset),
                      validation_sample_count=len(val_dataset), config=config,
                      checkpoint=str(checkpoint_path), history=history)
        temporary_record = checkpoint_dir / "experiment.tmp"
        temporary_record.write_text(json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        temporary_record.replace(checkpoint_dir / "experiment.json")
    print(f"checkpoint saved: {checkpoint_path}")
    return checkpoint_path


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description="Tracepecter 학습 (§25 config 구동)")
    parser.add_argument("--config", required=True, help="YAML config 경로 (예: configs/baseline.yaml)")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="tiny synthetic 데이터로 1 epoch 실행 — 실데이터 없이 skeleton 검증",
    )
    parser.add_argument("--resume", action="store_true", help="last.pt에서 동일 config로 epoch 재개")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    seed = config["training"].get("seed", SEED)
    torch.manual_seed(seed)
    random.seed(seed)

    checkpoint_dir = Path(config["output"]["checkpoint_dir"])
    epochs: int = config["training"]["epochs"]
    train_csv: str = config["data"].get("metadata_csv", config["data"].get("train_csv", ""))

    if args.smoke:
        smoke_root = Path(tempfile.mkdtemp(prefix="tracepecter_smoke_"))
        config = copy.deepcopy(config)
        config["model"].update(encoder="stub", embedding_dim=64)
        config["training"]["device"] = "cpu"
        smoke_csv = str(build_smoke_dataset(smoke_root / "train"))
        config["data"] = {"train_csv": smoke_csv, "val_csv": smoke_csv}
        try:
            checkpoint_path = run_training(
                config,
                train_csv=smoke_csv,
                epochs=1,
                checkpoint_dir=smoke_root / "checkpoints",
            )
        except BaseException:
            # 학습 실패 시 임시디렉터리가 남지 않도록 정리 후 재발생(검증 H7).
            shutil.rmtree(smoke_root, ignore_errors=True)
            raise
        print("smoke ok")
        return checkpoint_path
    return run_training(config, train_csv, epochs, checkpoint_dir, resume=args.resume)


if __name__ == "__main__":
    main()

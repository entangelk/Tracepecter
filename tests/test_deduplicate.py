"""P01-05 deduplicate 회귀 가드 — pHash 근사중복 클러스터링·look_group 채움.

가드 방향:
- under-strict: 동일/근사 이미지가 같은 클러스터로 묶이지 않거나 빈 look_group이
  채워지지 않으면 재실패.
- over-strict: 서로 다른 이미지가 병합되거나 파일명 유래 기존 그룹이 덮어
  써지면 재실패.
"""
import csv
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from deduplicate import (  # noqa: E402
    compute_phash,
    fill_look_groups,
    hamming,
)

SCHEMA_V1_2_COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]


def _noise_image(seed: int, scale: float = 1.0) -> Image.Image:
    """구조가 있는 결정적 이미지(노이즈) — pHash 가 이미지별로 구분되게."""
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, size=(64, 64)).astype(np.float64)
    return Image.fromarray((pixels * scale).clip(0, 255).astype(np.uint8), "L")


def _row(image_id, look_group):
    return {col: "" for col in SCHEMA_V1_2_COLUMNS} | {
        "image_id": image_id, "label": "1", "source_type": "real",
        "source_domain": "kfashion", "look_group": look_group,
    }


def test_phash_identical_and_near_identical_cluster(tmp_path):
    """under-strict: 동일·밝기 변형 근사 이미지는 거리 0/유사, 다른 이미지는 멀다."""
    base = compute_phash(_noise_image(1))
    identical = compute_phash(_noise_image(1))
    brightened = compute_phash(_noise_image(1, scale=1.08))
    different = compute_phash(_noise_image(2))

    assert hamming(base, identical) == 0
    assert hamming(base, brightened) <= 10  # 근사중복 임계 이내
    assert hamming(base, different) > 10  # 서로 다른 이미지는 임계 밖
    # 해시는 결정적 — 같은 입력에 같은 값
    assert compute_phash(_noise_image(3)) == compute_phash(_noise_image(3))


def test_fill_look_groups_fills_empty_and_adopts_existing(tmp_path):
    """빈 look_group 채움 + 클러스터 내 기존 그룹 채택 + 기존 값 보존."""
    # a1/a2: 동일 룩(근사중복), a1 은 파일명 유래 그룹 보유 → a2 가 채택.
    # b: 단독(다른 이미지) → 신규 phash_ 그룹. c: 파일명 그룹 보유 단독(유지).
    rows = [
        _row("a1", "LIME_001"),
        _row("a2", ""),
        _row("b", ""),
        _row("c", "MUN_811"),
    ]
    hashes = [
        compute_phash(_noise_image(1)),
        compute_phash(_noise_image(1, scale=1.05)),  # a2 ≈ a1
        compute_phash(_noise_image(2)),              # b 는 별개
        compute_phash(_noise_image(3)),              # c 는 별개
    ]
    out, stats = fill_look_groups(rows, hashes, threshold=10)

    by_id = {r["image_id"]: r["look_group"] for r in out}
    assert by_id["a2"] == "LIME_001"  # 기존 그룹 채택
    assert by_id["a1"] == "LIME_001"  # 기존 값 보존(덮어쓰지 않음)
    assert by_id["c"] == "MUN_811"
    assert by_id["b"].startswith("phash_")  # 신규 발급
    assert stats["filled"] == 2
    assert stats["covered_after"] == 4
    assert stats["multi_clusters"] == 1


def test_different_images_not_merged(tmp_path):
    """over-strict: 임계 밖 서로 다른 이미지는 별개 그룹(병합 금지)."""
    rows = [_row("x", ""), _row("y", "")]
    hashes = [compute_phash(_noise_image(10)), compute_phash(_noise_image(11))]
    out, stats = fill_look_groups(rows, hashes, threshold=10)
    groups = {r["look_group"] for r in out}
    assert len(groups) == 2  # 병합 없음
    assert stats["multi_clusters"] == 0

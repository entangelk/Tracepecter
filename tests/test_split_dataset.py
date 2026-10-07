"""P01-06 split_dataset 회귀 가드 — 그룹 split·unseen 분리·누출 검사.

가드 방향:
- under-strict: 같은 look_group 이 서로 다른 split 에 흩어지면 재실패.
- over-strict: unseen 생성기가 standard split 에 들어가거나 층화 비율이 크게
  무너지면 재실패.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from split_dataset import (  # noqa: E402
    check_leakage,
    group_key,
    stratified_group_split,
)

COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]


def _real_row(image_id, look_group, category="상의"):
    return dict(zip(COLUMNS, [
        image_id, f"images/real/x/{image_id}.jpg", "1", category, "상의|하의",
        "real", "kfashion", "", "스트리트", look_group, "", "",
    ]))


def _gen_row(image_id, generator="qwen_image_21", category="상의"):
    return dict(zip(COLUMNS, [
        image_id, f"images/generated/{generator}/{image_id}.png", "0", category,
        category, "generated", "", generator, "", "", "f1b1v1", "",
    ]))


def test_group_split_no_leakage_and_ratios():
    """같은 그룹 동일 split + 근사 70/15/15 + 결정성."""
    rows = []
    for g in range(40):  # REAL: 그룹당 3장(룩 시리즈) — 120장
        for k in range(3):
            rows.append(_real_row(f"r{g:03d}_{k}", f"look_{g:03d}"))
    for i in range(80):  # GEN 80장(개별 그룹)
        rows.append(_gen_row(f"g{i:03d}"))

    split_rows, stats = stratified_group_split(rows, seed=42)
    again, _ = stratified_group_split(rows, seed=42)
    assert [r["split"] for r in split_rows] == [r["split"] for r in again]

    # 그룹 누출 없음
    assert check_leakage(split_rows) == []

    # 비율 근사(소규모 허용 오차 ±5%p)
    total = len(split_rows)
    train = sum(1 for r in split_rows if r["split"] == "train") / total
    val = sum(1 for r in split_rows if r["split"] == "val") / total
    test = sum(1 for r in split_rows if r["split"] == "test") / total
    assert abs(train - 0.70) < 0.05, train
    assert abs(val - 0.15) < 0.05, val
    assert abs(test - 0.15) < 0.05, test


def test_unseen_generator_separated():
    """unseen(sd35_medium)은 test_unseen — standard split 혼입 시 검사 재실패."""
    rows = [
        _real_row("r001", "look_001"),
        _gen_row("g001"),
        dict(zip(COLUMNS, [
            "u001", "images/generated/sd35_medium/u001.png", "0", "상의", "상의",
            "generated", "", "sd35_medium", "", "", "f1b1v1", "test_unseen",
        ])),
    ]
    assert check_leakage(rows) == []
    # unseen 을 standard split 에 섞으면(under-strict 방향) 검사가 잡는다
    rows[1]["generator"] = "sd35_medium"
    rows[1]["split"] = "train"
    problems = check_leakage(rows)
    assert problems, "unseen 혼입을 검사가 못 잡음"


def test_same_look_group_stays_together():
    """under-strict: 동일 look_group 이 train/test 에 갈라지면 check_leakage 재실패."""
    rows = [
        _real_row("a", "look_9"),
        _real_row("b", "look_9"),
    ]
    rows[0]["split"] = "train"
    rows[1]["split"] = "test"
    problems = check_leakage(rows)
    assert problems and "look_9" in problems[0]

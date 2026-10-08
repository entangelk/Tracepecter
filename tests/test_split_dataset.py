"""P01-06 split_dataset 회귀 가드 — 그룹 split·unseen 분리·누출 검사.

가드 방향:
- under-strict: 같은 look_group 이 서로 다른 split 에 흩어지면 재실패.
- over-strict: unseen 생성기가 standard split 에 들어가거나 층화 비율이 크게
  무너지면 재실패.

2026-10-08 독립검증 hardening 반영:
- H2: unseen↔test_unseen 양방향 혼입 + REAL의 test_unseen 그룹 분산 가드.
- H4: source_type×category 셀별 비율 가드.
- H6: main() 오케스트레이션 스모크(unseen 파티션·출력·종료 0).
- H7: 누출 어설션을 group_key 없이 look_group 직접 재그룹화해 독립화.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from split_dataset import (  # noqa: E402
    check_leakage,
    group_key,
    main,
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


def _unseen_row(image_id, split="test_unseen"):
    row = _gen_row(image_id, generator="sd35_medium")
    row["split"] = split
    return row


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_group_split_no_leakage_and_ratios():
    """같은 그룹 동일 split + 근사 70/15/15(셀별 포함) + 결정성."""
    rows = []
    for g in range(40):  # REAL: 그룹당 3장(룩 시리즈) — 상의 20·하의 20그룹 = 120장
        category = "상의" if g < 20 else "하의"
        for k in range(3):
            rows.append(_real_row(f"r{g:03d}_{k}", f"look_{g:03d}", category=category))
    for i in range(80):  # GEN 80장(개별 그룹) — 카테고리 교대
        rows.append(_gen_row(f"g{i:03d}", category="상의" if i % 2 == 0 else "하의"))

    split_rows, stats = stratified_group_split(rows, seed=42)
    again, _ = stratified_group_split(rows, seed=42)
    assert [r["split"] for r in split_rows] == [r["split"] for r in again]

    # 그룹 누출 없음 — 구현의 group_key 를 쓰지 않고 look_group 직접 재그룹화(H7:
    # group_key 변이가 이 어설션을 우회할 수 없게 한다)
    assert check_leakage(split_rows) == []
    lg_splits = defaultdict(set)
    for r in split_rows:
        if r["look_group"]:
            lg_splits[r["look_group"]].add(r["split"])
    scattered = {lg: sorted(s) for lg, s in lg_splits.items() if len(s) > 1}
    assert not scattered, scattered

    # 비율 근사 — 전체(소규모 허용 오차 ±5%p)
    total = len(split_rows)
    train = sum(1 for r in split_rows if r["split"] == "train") / total
    val = sum(1 for r in split_rows if r["split"] == "val") / total
    test = sum(1 for r in split_rows if r["split"] == "test") / total
    assert abs(train - 0.70) < 0.05, train
    assert abs(val - 0.15) < 0.05, val
    assert abs(test - 0.15) < 0.05, test

    # 셀별(source_type × category) 비율 근사(H4 — 층화가 셀 단위로 유지되는가)
    cells = defaultdict(lambda: defaultdict(int))
    for r in split_rows:
        cells[(r["source_type"], r["category"])][r["split"]] += 1
    assert set(cells) == {("real", "상의"), ("real", "하의"), ("generated", "상의"), ("generated", "하의")}
    for cell, by_split in cells.items():
        n = sum(by_split.values())
        for split_name, ratio in (("train", 0.70), ("val", 0.15), ("test", 0.15)):
            got = by_split[split_name] / n
            assert abs(got - ratio) < 0.05, (cell, split_name, got)


def test_unseen_generator_separated():
    """unseen(sd35_medium)은 test_unseen — standard split 혼입 시 검사 재실패."""
    rows = [
        _real_row("r001", "look_001"),
        _gen_row("g001"),
        _unseen_row("u001"),
    ]
    assert check_leakage(rows) == []
    # unseen 을 standard split 에 섞으면(under-strict 방향) 검사가 잡는다
    rows[1]["generator"] = "sd35_medium"
    rows[1]["split"] = "train"
    problems = check_leakage(rows)
    assert problems, "unseen 혼입을 검사가 못 잡음"


def test_unseen_scope_guards():
    """H2: unseen↔test_unseen 양방향 — REAL test_unseen 혼입·비-unseen의 test_unseen."""
    rows = [
        _real_row("r001", "look_001"),
        _real_row("r002", "look_001"),
        _unseen_row("u001"),
    ]
    rows[0]["split"] = "train"
    rows[1]["split"] = "test_unseen"  # REAL이 test_unseen에 — 그룹 분산 + 역방향 혼입
    problems = check_leakage(rows)
    assert any("look_001" in p for p in problems), "REAL test_unseen 그룹 분산 미검사"
    assert any("r002" in p for p in problems), "test_unseen에 비-unseen 혼입 미검사"

    clean = [_real_row("r003", "look_003"), _unseen_row("u002")]
    clean[0]["split"] = "train"
    assert check_leakage(clean) == []


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


def test_main_smoke_unseen_partition_and_output(tmp_path, monkeypatch):
    """H6: main 오케스트레이션 — unseen 전량 test_unseen 파티션 + 출력 기록 + 0 반환."""
    real_csv = tmp_path / "real.csv"
    gen_csv = tmp_path / "gen.csv"
    out_csv = tmp_path / "metadata.csv"
    _write_csv(real_csv, [_real_row("r001", "look_001"), _real_row("r002", "look_002")])
    _write_csv(gen_csv, [_gen_row("g001"), _unseen_row("u001")])
    monkeypatch.setattr(
        sys, "argv",
        ["split_dataset.py", "--inputs", str(real_csv), str(gen_csv), "--out", str(out_csv)],
    )
    assert main() == 0

    with open(out_csv, encoding="utf-8", newline="") as handle:
        produced = list(csv.DictReader(handle))
    by_id = {r["image_id"]: r["split"] for r in produced}
    assert len(produced) == 4
    assert by_id["u001"] == "test_unseen"
    assert by_id["r001"] in ("train", "val", "test") and by_id["r002"] in ("train", "val", "test")
    assert check_leakage(produced) == []

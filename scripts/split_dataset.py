"""Dataset group split — P01-06 (docs/plan/phase_1_data_pipeline.md, §14·§10).

REAL(metadata_real.csv)·Generated(metadata_gen_*.csv) metadata를 병합해
그룹 누출 없는 train/val/test 70/15/15 split을 배정하고, unseen generator
(Test B, §10) 구성을 별도 split 값(test_unseen)으로 배정한다. 결과는
data/metadata.csv(§12 v1.2, split 열 채움)에 기록한다.

그룹 키(§14): REAL → real:<source_domain>:<look_group>(동일 인물·룩/근사중복
클러스터 — 도메인 접두어로 미래 다중 출처 병합 시 그룹명 충돌을 방지,
독립검증 H5 반영), Generated → gen:<generator>:<image_id>(합성 이미지는 개별
그룹 — 시드 충돌에 의한 근사중복은 P01-05 pHash가 대규모 실행 시 점검).
unseen generator(sd35_medium)의 행은 전량 test_unseen — train/val/test 에서
제외(§10). stratification: source_type × category × generator 셀별 70/15/15
(독립검증 P01-07 H1 — generator 축이 없으면 결정적 배정의 사전순 소진으로
특정 생성기가 train에만 몰려 §19 generator별 평가가 불가능해진다. REAL은
generator 공백이라 셀 구조 불변).

배정은 알고리즘 자체가 결정적이다(그룹 크기 내림차순 + 키 사전순 tie-break)
— 시드 무관, 동일 입력은 항상 동일 split(독립검증 H1 반영).

사용:
    python scripts/split_dataset.py --inputs data/metadata_real.csv data/metadata_gen_qwen_image_21.csv ... \
        --out data/metadata.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_ai import UNSEEN_GENERATORS  # noqa: E402

SPLIT_RATIO = (0.70, 0.15, 0.15)
SPLITS = ("train", "val", "test")


def read_rows(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def group_key(row: dict) -> str:
    if row["source_type"] == "real":
        return f"real:{row['source_domain']}:{row['look_group'] or row['image_id']}"
    return f"gen:{row['generator']}:{row['image_id']}"


def stratified_group_split(
    rows: list[dict], seed: int = 42
) -> tuple[list[dict], dict]:
    """source_type × category × generator 셀별로 그룹 단위 70/15/15 배정(결정적).

    그룹을 크기 내림차순으로 순회하며 목표 비율 대비 결손이 가장 큰 split에
    배정한다 — 이미지 수 기준 층화 유지 + 그룹 전체가 한 split에만 존재.
    seed 는 호환 서명일 뿐 무시된다 — 배정 순서가 구조적으로 결정적이라
    시드가 결과에 영향을 주지 않는다(독립검증 H1).
    """
    def cell_of(row: dict) -> tuple:
        return (row["source_type"], row["category"], row["generator"])

    groups: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        groups[group_key(row)].append(idx)
    ordered_groups = sorted(
        groups.items(), key=lambda kv: (-len(kv[1]), kv[0])
    )

    assigned: dict[int, str] = {}
    cell_counts: dict[tuple, dict[str, int]] = defaultdict(
        lambda: {"train": 0, "val": 0, "test": 0}
    )
    cell_totals: dict[tuple, int] = defaultdict(int)
    for idx, row in enumerate(rows):
        cell_totals[cell_of(row)] += 1

    for group, indices in ordered_groups:
        touched = {cell_of(rows[i]) for i in indices}
        # 후보 split: 그룹이 건드리는 셀들의 결손 합이 가장 큰 split
        deficits = {}
        for split in SPLITS:
            deficit = sum(
                cell_totals[c] * SPLIT_RATIO[SPLITS.index(split)] - cell_counts[c][split]
                for c in touched
            )
            deficits[split] = deficit
        best = max(SPLITS, key=lambda s: (deficits[s], s))
        for idx in indices:
            assigned[idx] = best
            cell_counts[cell_of(rows[idx])][best] += 1

    out_rows = []
    for idx, row in enumerate(rows):
        row = dict(row)
        row["split"] = assigned[idx]
        out_rows.append(row)

    stats = {
        "total": len(rows),
        "groups": len(groups),
        "by_split": {s: sum(1 for r in out_rows if r["split"] == s) for s in SPLITS},
    }
    return out_rows, stats


def check_leakage(rows: list[dict]) -> list[str]:
    """그룹 누출·unseen 혼입 검사 — 위반 목록 반환(빈 리스트 = 통과).

    그룹 추적은 test_unseen 포함 전수(REAL이 test_unseen에 섞여도 look_group
    분산으로 잡는다 — 독립검증 H2). unseen↔test_unseen 대응은 양방향 검사.
    """
    problems = []
    seen: dict[str, set] = defaultdict(set)
    for row in rows:
        if not row["split"]:
            continue
        seen[group_key(row)].add(row["split"])
    for group, splits in seen.items():
        if len(splits) > 1:
            problems.append(f"그룹 누출: {group} → {sorted(splits)}")
    for row in rows:
        is_unseen = row["generator"] in UNSEEN_GENERATORS
        if is_unseen and row["split"] != "test_unseen":
            problems.append(f"unseen 생성기가 standard split에 존재: {row['image_id']}")
        if row["split"] == "test_unseen" and not is_unseen:
            problems.append(f"test_unseen에 unseen 외 행 혼입: {row['image_id']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True, help="metadata CSV 목록")
    parser.add_argument("--out", required=True, help="병합+split 배정 출력 CSV")
    args = parser.parse_args()

    rows = []
    for path in args.inputs:
        rows.extend(read_rows(path))
    print(f"입력 {len(args.inputs)}개 CSV · {len(rows):,}행")

    unseen_rows = [r for r in rows if r["generator"] in UNSEEN_GENERATORS]
    standard_rows = [r for r in rows if r["generator"] not in UNSEEN_GENERATORS]
    for row in unseen_rows:
        row["split"] = "test_unseen"

    split_rows, stats = stratified_group_split(standard_rows)
    all_rows = split_rows + unseen_rows

    problems = check_leakage(all_rows)
    if problems:
        print("누출 검사 실패:", *problems[:10], sep="\n  ")
        return 1

    columns = list(all_rows[0].keys())
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"split: {stats['by_split']} + test_unseen {len(unseen_rows)} "
          f"(그룹 {stats['groups']:,})")
    for source in ("real", "generated"):
        by = defaultdict(int)
        for r in all_rows:
            if r["source_type"] == source:
                by[r["split"]] += 1
        print(f"  {source}: {dict(by)}")
    print(f"누출 검사 통과 — 출력: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

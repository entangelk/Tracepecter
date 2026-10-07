"""K-Fashion 라벨링데이터 분석 — P01-02 (docs/plan/phase_1_data_pipeline.md).

라벨 zip(스타일 폴더 → JSON per image)을 전수 파싱해 카테고리 설계에 필요한
분포를 산출한다. 확정된 카테고리 규칙(대표 부위 = 원피스 > 아우터 > 상의 >
하의 우선순위)의 검증 수단이기도 하다. 표준 라이브러리만 사용한다.

사용:
    python scripts/analyze_kfashion_labels.py <라벨링데이터.zip 경로> [--out stats.json]

출력: 요약 통계(stdout) + 전체 통계 JSON(--out 지정 시).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter

# 대표 부위 우선순위 — docs/plan/phase_1_data_pipeline.md "카테고리 목록 확정 제안"
PARTS = ("원피스", "아우터", "상의", "하의")
# 쇼핑몰 출처 3단 파일명(예: LIME_193_00.jpg) — look_group 키 후보 패턴.
# jpg/jpeg/png 대소문자 무관(독립검증 H4 — 현재 코퍼스는 jpg/JPG 뿐이나
# P01-03 look_group 생성에서 패턴을 재사용할 경우를 대비).
MALL_FILENAME = re.compile(r"^[A-Za-z0-9]+_\d+_\d+\.(?:[Jj][Pp][Ee]?[Gg]|[Pp][Nn][Gg])$")


def analyze(label_zip: str) -> dict:
    parse_errors = 0
    style_from_folder: Counter = Counter()
    style_from_label: Counter = Counter()
    part_presence: Counter = Counter()
    part_combo: Counter = Counter()
    part_category_values: dict[str, Counter] = {p: Counter() for p in PARTS}
    part_attr_anomaly: Counter = Counter()
    primary_category: Counter = Counter()
    mall_pattern = 0
    total = 0

    with zipfile.ZipFile(label_zip) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        for i, name in enumerate(names):
            style_from_folder[name.split("/")[0]] += 1
            try:
                data = json.loads(zf.read(name))
            except Exception:
                parse_errors += 1
                continue
            total += 1

            labeling = (
                data.get("데이터셋 정보", {}).get("데이터셋 상세설명", {}).get("라벨링")
            )
            if not isinstance(labeling, dict):
                part_combo["<라벨링키없음>"] += 1
                primary_category["<라벨없음>"] += 1
                continue

            styles = labeling.get("스타일")
            if isinstance(styles, list) and styles and isinstance(styles[0], dict):
                style_from_label[styles[0].get("스타일", "?")] += 1
            else:
                style_from_label["<없음/이상>"] += 1

            present = []
            for part in PARTS:
                entries = labeling.get(part)
                if not isinstance(entries, list):
                    part_attr_anomaly[f"{part}:list아님"] += 1
                    continue
                nonempty = [e for e in entries if isinstance(e, dict) and e]
                if not nonempty:
                    continue
                present.append(part)
                for entry in nonempty:
                    if entry.get("카테고리"):
                        part_category_values[part][entry["카테고리"]] += 1
                    else:
                        part_attr_anomaly[f"{part}:카테고리없음"] += 1
            part_presence.update(present)
            part_combo["+".join(present) if present else "<전부없음>"] += 1
            primary_category[present[0] if present else "<라벨없음>"] += 1

            file_name = (
                data.get("데이터셋 정보", {}).get("파일 이름")
                or data.get("이미지 정보", {}).get("이미지 파일명")
                or ""
            )
            if MALL_FILENAME.match(file_name):
                mall_pattern += 1

            if (i + 1) % 200000 == 0:
                print(f"  ... {i + 1}/{len(names)}", file=sys.stderr, flush=True)

    return {
        "total_json": len(names),
        "parsed_ok": total,
        "parse_errors": parse_errors,
        "mall_filename_pattern": mall_pattern,
        "style_from_folder": dict(style_from_folder.most_common()),
        "style_from_label": dict(style_from_label.most_common()),
        "part_presence": dict(part_presence.most_common()),
        "part_combo": dict(part_combo.most_common()),
        "primary_category": dict(primary_category.most_common()),
        "part_category_values": {
            p: dict(c.most_common()) for p, c in part_category_values.items()
        },
        "part_attr_anomaly": dict(part_attr_anomaly.most_common()),
    }


def print_summary(stats: dict) -> None:
    total = stats["parsed_ok"]
    print(f"JSON 총 {stats['total_json']}개 · 파싱 성공 {total} · 오류 {stats['parse_errors']}")
    print("\n[대표 부위 분포] (원피스 > 아우터 > 상의 > 하의 규칙)")
    for part, count in stats["primary_category"].items():
        print(f"  {part}: {count} ({count / total:.1%})")
    print("\n[부위 라벨 존재]")
    for part, count in stats["part_presence"].items():
        print(f"  {part}: {count} ({count / total:.1%})")
    print("\n[부위 조합]")
    for combo, count in stats["part_combo"].items():
        print(f"  {combo}: {count} ({count / total:.1%})")
    print("\n[부위별 카테고리 값]")
    for part in PARTS:
        values = stats["part_category_values"].get(part, {})
        print(f"  {part} ({len(values)}종): " + ", ".join(
            f"{v} {c}" for v, c in list(values.items())[:8]
        ))
    print(f"\n[파일명 3단 패턴(look_group 후보)] {stats['mall_filename_pattern']} "
          f"({stats['mall_filename_pattern'] / total:.1%})")
    if stats["part_attr_anomaly"]:
        print("\n[부위 엔트리 이상] (카테고리 없는 항목 등 — 부위 존재 집계에는 포함)")
        for key, count in stats["part_attr_anomaly"].items():
            print(f"  {key}: {count}")
    print("\n[스타일 상위 10]")
    for style, count in list(stats["style_from_label"].items())[:10]:
        print(f"  {style}: {count} ({count / total:.1%})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label_zip", help="라벨링데이터.zip 경로")
    parser.add_argument("--out", default=None, help="전체 통계 JSON 출력 경로(선택)")
    args = parser.parse_args()

    stats = analyze(args.label_zip)
    print_summary(stats)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(stats, handle, ensure_ascii=False, indent=2)
        print(f"\n전체 통계 저장: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

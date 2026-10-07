"""REAL(K-Fashion) 선별·metadata 빌드 — P01-03 (docs/plan/phase_1_data_pipeline.md).

라벨 zip에서 대표 부위(원피스>아우터>상의>하의)로 층화 샘플링해 이미지를
원천 zip에서 선택적 추출하고, §12 v1.2 스키마의 REAL 행을 가진 metadata CSV를
생성한다. 규칙(부위·look_group)은 kfashion_common(공유 정의)을 따른다.

사용:
    python scripts/build_metadata.py <라벨링데이터.zip> <원천 zip 디렉터리> \
        --out data/metadata_real.csv --images-dir ~/data/tracepector/images \
        --per-category 125 [--seed 42]

경로 계약: CSV의 path 컬럼은 "images/real/<스타일>/<식별자>.jpg" 형식이며
CSV가 있는 디렉터리 기준 상대 경로로 해석한다(src/dataset.py 규칙). 따라서
<CSV 디렉터리>/images 가 --images-dir 물리 경로을 가리키도록(심볼릭 링크 등)
호출자가 준비한다. split 컬럼은 빈 값으로 남기고 P01-06(split)이 배정한다.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image

# -I 격리 모드에서도 공용 모듈을 찾을 수 있게 스크립트 디렉터리를 명시적으로 추가.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kfashion_common import (
    derive_look_group,
    extract_parts,
    parse_image_name,
    primary_category,
)

# §12 v1.2 컬럼(순서 포함) — tests/test_dataset.py 의 리터럴 잠금과 같은 정의.
COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]


def load_candidates(label_zip: str) -> list[dict]:
    """라벨 zip 전수 스캔 → 선별 후보 목록. 부위 라벨 없는 이미지는 제외."""
    candidates = []
    with zipfile.ZipFile(label_zip) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        for i, name in enumerate(names):
            style, file_name = name.split("/", 1)
            stem = file_name[:-5]
            data = json.loads(zf.read(name))
            labeling = (
                data.get("데이터셋 정보", {}).get("데이터셋 상세설명", {}).get("라벨링")
            )
            parts = extract_parts(labeling)
            category = primary_category(parts)
            if category is None:
                continue  # <라벨없음> 0.4% — P01 계획서 제외 대상
            candidates.append({
                "style": style,
                "stem": stem,
                "parts": parts,
                "category": category,
                "image_name": parse_image_name(data),
            })
            if (i + 1) % 200000 == 0:
                print(f"  ... 라벨 스캔 {i + 1}/{len(names)}", file=sys.stderr, flush=True)
    return candidates


def stratified_select(
    candidates: list[dict], per_category: int, seed: int
) -> list[dict]:
    """대표 부위별 층화 샘플링(결정적 — seed 고정)."""
    rng = random.Random(seed)
    by_category: dict[str, list[dict]] = {}
    for record in candidates:
        by_category.setdefault(record["category"], []).append(record)
    selected = []
    for category in sorted(by_category):
        pool = by_category[category]
        take = min(per_category, len(pool))
        chosen = rng.sample(pool, take)
        for record in chosen:
            record = dict(record)
            record["look_group"] = derive_look_group(record["image_name"])
            selected.append(record)
    return selected


def index_source_zips(source_dir: str) -> dict[str, str]:
    """원천 zip 디렉터리에서 스타일 → zip 경로 색인(스타일은 단일 zip에 전량 수록)."""
    style_to_zip: dict[str, str] = {}
    for zip_path in sorted(Path(source_dir).glob("원천데이터_*.zip")):
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if "/" in name:
                    style = name.split("/", 1)[0]
                    style_to_zip.setdefault(style, str(zip_path))
    return style_to_zip


def extract_images(
    selected: list[dict], style_to_zip: dict[str, str], images_dir: Path
) -> tuple[int, int]:
    """선별 이미지를 원천 zip에서 images_dir/real/<스타일>/<식별자>.jpg 로 추출."""
    written, errors = 0, 0
    open_zips: dict[str, zipfile.ZipFile] = {}
    try:
        for record in selected:
            zip_path = style_to_zip.get(record["style"])
            if zip_path is None:
                errors += 1
                continue
            zf = open_zips.setdefault(zip_path, zipfile.ZipFile(zip_path))
            entry = f"{record['style']}/{record['stem']}.jpg"
            out_path = images_dir / "real" / record["style"] / f"{record['stem']}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(entry) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())
                written += 1
            except KeyError:
                errors += 1
    finally:
        for zf in open_zips.values():
            zf.close()
    return written, errors


def write_metadata(selected: list[dict], out_csv: str) -> None:
    """§12 v1.2 REAL 행 CSV 기록. split 은 미배정(빈 값, P01-06 담당)."""
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for record in selected:
            writer.writerow([
                record["stem"],
                f"images/real/{record['style']}/{record['stem']}.jpg",
                1,
                record["category"],
                "|".join(record["parts"]),
                "real",
                "kfashion",
                "",  # generator
                record["style"],
                record["look_group"],
                "",  # prompt_id
                "",  # split — P01-06
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label_zip", help="라벨링데이터.zip 경로")
    parser.add_argument("source_dir", help="원천데이터_*.zip 이 있는 디렉터리")
    parser.add_argument("--out", required=True, help="출력 metadata CSV 경로")
    parser.add_argument("--images-dir", required=True, help="이미지 추출 물리 경로")
    parser.add_argument("--per-category", type=int, default=125,
                        help="대표 부위별 선별 수(기본 125 — 씨드 500)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    candidates = load_candidates(args.label_zip)
    print(f"후보(부위 라벨 보유): {len(candidates):,}")
    selected = stratified_select(candidates, args.per_category, args.seed)
    print(f"선별: {len(selected):,} (부위별 {args.per_category}·seed {args.seed})")

    style_to_zip = index_source_zips(args.source_dir)
    written, errors = extract_images(selected, style_to_zip, Path(args.images_dir))
    print(f"이미지 추출: 성공 {written:,} · 실패 {errors:,}")

    write_metadata(selected, args.out)
    cat_counts = Counter(r["category"] for r in selected)
    lg_covered = sum(1 for r in selected if r["look_group"])
    print(f"메타데이터: {args.out}")
    print(f"  카테고리 분포: {dict(sorted(cat_counts.items()))}")
    print(f"  look_group 커버(파일명 유래): {lg_covered}/{len(selected)} "
          f"({lg_covered / len(selected):.1%}) — 나머지는 P01-05 pHash 클러스터가 보완")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

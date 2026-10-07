"""P01-03 build_metadata 회귀 가드 — §12 v1.2 REAL 행·층화 선별·선택적 추출.

가드 방향:
- under-strict: 부위 우선순위 위반(원피스+상의→상의)·라벨없음 미제외·추출 누락·
  컬럼 누락이 생기면 해당 셀 재실패.
- over-strict: 층화 수 초과 선별·split 임의 배정도 재실패.
"""
import csv
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_metadata import (  # noqa: E402
    COLUMNS,
    extract_images,
    index_source_zips,
    load_candidates,
    stratified_select,
    write_metadata,
)

SCHEMA_V1_2_COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]


def _label_json(parts_present, file_name, image_id):
    """부위 라벨 구조를 흉내 낸 K-Fashion 라벨 JSON(빈 dict 엔트리 포함)."""
    labeling = {"스타일": [{"스타일": "스트리트"}]}
    for part in ("아우터", "상의", "하의", "원피스"):
        labeling[part] = [{"카테고리": "티셔츠"}] if part in parts_present else [{}]
    return {
        "이미지 정보": {"이미지 식별자": image_id, "이미지 파일명": file_name},
        "데이터셋 정보": {
            "파일 이름": file_name,
            "데이터셋 상세설명": {"라벨링": labeling},
        },
    }


def _make_fixture(root: Path):
    """합성 라벨 zip + 원천 zip 을 만들고 경로들을 반환한다.

    구성: 원피스+상의(mall 파일명) 1 · 상의+하의(mall) 2 · 하의 단독(카메라) 1 ·
    원피스 단독(mall) 1 · 라벨없음 1 — 후보 5장 중 라벨없음 제외.
    """
    specs = [
        ("원피스", ("원피스", "상의"), "LIME_001_00.jpg", "1001"),
        ("상의", ("상의", "하의"), "MUN_811_04.jpg", "1002"),
        ("상의", ("상의", "하의"), "MUN_812_02.jpg", "1003"),
        ("하의", ("하의",), "IMG_3951.JPG", "1004"),
        ("원피스", ("원피스",), "Moda_101_03.jpg", "1005"),
        (None, (), "NOLABEL_001.jpg", "1006"),  # 라벨없음 — 제외 대상
    ]
    label_zip = root / "labels.zip"
    source_zip = root / "원천데이터_1.zip"
    with zipfile.ZipFile(label_zip, "w") as lz, zipfile.ZipFile(source_zip, "w") as sz:
        for category, parts, file_name, image_id in specs:
            style = "스트리트"
            lz.writestr(
                f"{style}/{image_id}.json",
                json.dumps(_label_json(parts, file_name, int(image_id)), ensure_ascii=False),
            )
            if category is not None:
                buffer = BytesIO()
                Image.new("RGB", (8, 8), color=(200, 100, 50)).save(buffer, format="JPEG")
                sz.writestr(f"{style}/{image_id}.jpg", buffer.getvalue())
    return label_zip, source_zip


def _run_pipeline(root: Path, per_category=1, seed=42):
    label_zip, source_zip = _make_fixture(root)
    candidates = load_candidates(str(label_zip))
    selected = stratified_select(candidates, per_category, seed)
    images_dir = root / "images"
    style_to_zip = index_source_zips(str(root))
    written, errors = extract_images(selected, style_to_zip, images_dir)
    csv_path = root / "metadata_real.csv"
    write_metadata(selected, str(csv_path))
    return candidates, selected, images_dir, csv_path, written, errors


def test_excludes_unlabeled_and_priority_rule(tmp_path):
    """under-strict: 라벨없음 제외·원피스>상의 우선순위·후보 집계."""
    candidates, _, _, _, _, _ = _run_pipeline(tmp_path)
    assert len(candidates) == 5  # 6장 중 라벨없음 1장 제외
    categories = {c["stem"]: c["category"] for c in candidates}
    assert categories["1001"] == "원피스"  # 원피스+상의 → 원피스 우선
    assert categories["1003"] == "상의"
    by_cat = {}
    for c in candidates:
        by_cat.setdefault(c["category"], []).append(c["stem"])
    assert sorted(by_cat) == ["상의", "원피스", "하의"]


def test_stratified_selection_counts_and_determinism(tmp_path):
    """over-strict: 요청 수 초과 선별 금지 + 동일 seed 재현."""
    _, selected1, _, _, _, _ = _run_pipeline(tmp_path, per_category=2)
    counts = {}
    for r in selected1:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    assert counts == {"상의": 2, "원피스": 2, "하의": 1}  # 하의는 후보 1장뿐
    _, selected2, _, _, _, _ = _run_pipeline(tmp_path, per_category=2)
    assert [r["stem"] for r in selected1] == [r["stem"] for r in selected2]


def test_metadata_rows_match_schema_v12(tmp_path):
    """§12 v1.2 REAL 행 리터럴 — 헤더·필드 수·값 규약(split 미배정 포함)."""
    _, _, _, csv_path, _, _ = _run_pipeline(tmp_path)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == SCHEMA_V1_2_COLUMNS
    assert all(len(row) == 12 for row in rows[1:])
    for row in rows[1:]:
        assert row[2] == "1"  # label REAL
        assert row[5] == "real" and row[6] == "kfashion"
        assert row[7] == "" and row[10] == ""  # generator·prompt_id 미정의
        assert row[11] == ""  # split 미배정 — P01-06
        assert row[3] in ("상의", "하의", "아우터", "원피스")
        assert row[1] == f"images/real/스트리트/{row[0]}.jpg"


def test_extract_images_opens_each_zip_once(tmp_path, monkeypatch):
    """zip 경로당 1회만 open — setdefault 함정 회귀 가드(2026-10-07 야간 결함).

    under-strict: dict.setdefault(k, ZipFile(k)) 형태로 돌아오면(매 반복마다
    중앙 디렉터리 재파싱 — 3,000장 추출이 수 시간 걸리던 원인) 재실패.
    """
    import build_metadata as bm

    label_zip, _ = _make_fixture(tmp_path)
    candidates = load_candidates(str(label_zip))
    selected = stratified_select(candidates, 2, 42)
    style_to_zip = index_source_zips(str(tmp_path))

    calls = []
    real_zipfile = bm.zipfile.ZipFile

    class CountingZipFile(real_zipfile):
        def __init__(self, path):
            calls.append(str(path))
            super().__init__(path)

    monkeypatch.setattr(bm.zipfile, "ZipFile", CountingZipFile)
    written, errors = extract_images(
        selected, style_to_zip, tmp_path / "images"
    )
    assert errors == 0 and written == len(selected)
    assert len(calls) == 1  # 전 행이 같은 zip → 정확히 1회 open


def test_extraction_writes_images_and_look_group(tmp_path):
    """선택적 추출 실물 검증 + look_group 파일명 유래 도출."""
    _, selected, images_dir, _, written, errors = _run_pipeline(tmp_path, per_category=2)
    assert errors == 0
    assert written == len(selected)
    for record in selected:
        image_path = images_dir / "real" / record["style"] / f"{record['stem']}.jpg"
        assert image_path.exists()
        with Image.open(image_path) as img:
            img.verify()
    by_stem = {r["stem"]: r["look_group"] for r in selected}
    assert by_stem.get("1001") == "LIME_001"  # mall 3단 → PREFIX_NNN
    # 카메라 원본(IMG_3951.JPG)은 빈 값 — P01-05 pHash 보완 대상
    camera = next((r for r in selected if r["stem"] == "1004"), None)
    if camera:
        assert camera["look_group"] == ""

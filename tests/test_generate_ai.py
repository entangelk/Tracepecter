"""P01-04 generate_ai 회귀 가드 — 프롬프트 매트릭스·작업 계획·§12 v1.2 Generated 행.

가드 방향:
- under-strict: 부위 층화 깨짐·prompt_id 미기록·CSV 스키마 위반 재실패.
- over-strict: unseen(sd35_medium)을 train 로스터에 넣거나 층화 초과 선별 재실패.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_ai import (  # noqa: E402
    BACKGROUNDS,
    CATEGORY_OUTFITS,
    FACE_VARIANTS,
    GENERATORS,
    PROMPT_FORMS,
    UNSEEN_GENERATORS,
    plan_jobs,
    write_metadata_rows,
)

SCHEMA_V1_2_COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]


def test_plan_jobs_stratified_and_deterministic():
    """부위 균등 층화·결정성·프롬프트 매트릭스 요소 포함."""
    jobs1 = plan_jobs("qwen_image_21", 8, seed=42)
    jobs2 = plan_jobs("qwen_image_21", 8, seed=42)
    assert [j["seed"] for j in jobs1] == [j["seed"] for j in jobs2]  # 결정적

    cats = {}
    for j in jobs1:
        cats[j["category"]] = cats.get(j["category"], 0) + 1
    assert cats == {c: 2 for c in CATEGORY_OUTFITS}  # 8/4부위 = 2씩

    for j in jobs1:
        assert j["prompt_id"][:2] in PROMPT_FORMS
        assert j["prompt_id"][2:4] in BACKGROUNDS
        assert j["prompt_id"][4:] in FACE_VARIANTS
        # DB-03 프롬프트 정합 — 얼굴 노출 변형 문구가 프롬프트에 반영
        assert FACE_VARIANTS[j["prompt_id"][4:]] in j["prompt"]
        assert j["parts"] == CATEGORY_OUTFITS[j["category"]][0]


def test_roster_train_unseen_disjoint():
    """over-strict: unseen 생성기는 train 로스터에 없어야 한다(§10 Test B 분리)."""
    assert set(GENERATORS).isdisjoint(UNSEEN_GENERATORS)
    assert len(GENERATORS) >= 3  # §9 최소 3종 이상


def test_write_metadata_rows_schema_v12(tmp_path):
    """§12 v1.2 Generated 행 리터럴 — label 0·generator·prompt_id 기록·split 미배정."""
    jobs = plan_jobs("z_image_turbo", 8, seed=1)
    out = tmp_path / "metadata_gen_z_image_turbo.csv"
    write_metadata_rows(jobs, "z_image_turbo", 1, str(out))
    with open(out, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == SCHEMA_V1_2_COLUMNS
    assert len(rows) == 9  # 헤더 + 8행
    for i, row in enumerate(rows[1:]):
        assert row[0] == f"gen_{i + 1:06d}"
        assert row[1] == f"images/generated/z_image_turbo/gen_{i + 1:06d}.png"
        assert row[2] == "0"  # label GENERATED
        assert row[5] == "generated"
        assert row[6] == ""  # source_domain null
        assert row[7] == "z_image_turbo"
        assert row[8] == "" and row[9] == ""  # style·look_group null
        assert row[10]  # prompt_id 기록
        assert row[11] == ""  # split 미배정 — P01-06

"""K-Fashion 라벨 공용 파싱 규칙 — analyze_kfashion_labels.py·build_metadata.py 공유.

카테고리 규칙의 canonical 정의는 docs/plan/phase_1_data_pipeline.md
"카테고리 목록 확정" 절(승인 2026-10-07). 두 스크립트가 이 모듈을 통해 같은
규칙을 쓴다 — 스크립트별 복제 금지(드리프트 방지).
"""
from __future__ import annotations

import re

# 대표 부위 우선순위(순서가 규칙) — 원피스 > 아우터 > 상의 > 하의
PARTS = ("원피스", "아우터", "상의", "하의")

# 쇼핑몰 출처 3단 파일명(예: LIME_193_00.jpg) — look_group 키 후보 패턴.
# jpg/jpeg/png 대소문자 무관(독립검증 H4).
MALL_FILENAME = re.compile(r"^[A-Za-z0-9]+_\d+_\d+\.(?:[Jj][Pp][Ee]?[Gg]|[Pp][Nn][Gg])$")


def extract_part_entries(labeling: object) -> dict[str, list[dict]]:
    """라벨링 섹션에서 부위별 "비어있지 않은" 라벨 엔트리를 우선순위 순으로 반환.

    부위 키는 모든 JSON에 리스트로 존재하며 라벨 없는 경우 빈 dict 엔트리로
    나타난다(독립검증 확인) — 비어있지 않은 dict 존재만 부위 라벨 존재으로 본다.
    이 판정이 없으면 부위 존재가 전부 100%가 된다.
    """
    result: dict[str, list[dict]] = {}
    if not isinstance(labeling, dict):
        return result
    for part in PARTS:
        entries = labeling.get(part)
        if isinstance(entries, list):
            nonempty = [e for e in entries if isinstance(e, dict) and e]
            if nonempty:
                result[part] = nonempty
    return result


def extract_parts(labeling: object) -> list[str]:
    """라벨링 섹션에서 라벨된 부위를 우선순위 순으로 반환."""
    return [part for part in PARTS if part in extract_part_entries(labeling)]


def primary_category(parts: list[str]) -> str | None:
    """부위 목록에서 대표 부위. parts 는 extract_parts 결과(우선순위 순)."""
    return parts[0] if parts else None


def derive_look_group(file_name: str) -> str:
    """3단 파일명(PREFIX_NNN_MM.jpg)에서 동일 룩 그룹 키(PREFIX_NNN) 도출.

    패턴 밖(카메라 원본·SNS 등)은 빈 문자열 — pHash 클러스터(P01-05)가 보완한다.
    """
    if MALL_FILENAME.match(file_name):
        stem = file_name.rsplit(".", 1)[0]
        return stem.rsplit("_", 1)[0]  # PREFIX_NNN
    return ""


def parse_image_name(data: dict) -> str:
    """라벨 JSON에서 원본 이미지 파일명(데이터셋 정보.파일 이름 우선) 추출."""
    return (
        data.get("데이터셋 정보", {}).get("파일 이름")
        or data.get("이미지 정보", {}).get("이미지 파일명")
        or ""
    )

# HANDOFF.md

> 마지막 자가 검수: 2026-10-07 · 23줄

## 현재 상태

- 프로젝트는 문서 부트스트랩 단계. 코드·데이터·실험 산출물 없음.
- Git repository 미생성 — P00-01에서 수행. 커밋이 없는 것이 정상 상태.
- 문서 체계 구축 완료: `docs/sot.md`(SoT·precedence·버전 로그), `docs/plan/00_index.md` + `docs/plan/phase_0_initialization.md`, `docs/decision_briefs/`(DB-01 Resolved 포함), `docs/README.md`.
- 프로젝트 정의: Fashion Photo Realism Scorer — 착용컷 패션 이미지가 대상(DB-01). 제품 사양 최신본은 `docs/project.md` v1.1.

## 다음 작업 (우선순위 순)

1. P00-01 — git init + Python 환경 (`docs/plan/phase_0_initialization.md`)
2. P00-02 — repo 골격 + `README.md` + `configs/baseline.yaml`
3. P00-03 — training skeleton(`src/model.py`·`src/dataset.py`·`src/train.py`)
4. 소유자 액션 — AIHub K-Fashion 다운로드(P01 선행 조건)

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침). 초기 커밋에 포함되지 않는 것이 정상.
- P01 상세 계획 시: 축소 카테고리 목록 확정(K-Fashion 라벨 분포), AI 생성기(≥3종) 접근 수단 확인, 얼굴 영역 처리 정책(DB-01 후속 고려사항).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

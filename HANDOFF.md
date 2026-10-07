# HANDOFF.md

> 마지막 자가 검수: 2026-10-07 · 22줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 구현 → 독립검증 초회 합격(hardening 7건) → 보강 → 재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- 실행 환경: venv = `~/.venvs/tracepecter`(ext4, CPU torch). `python -m src.train --config configs/baseline.yaml --smoke` 로 skeleton 검증, `python -m pytest` 로 회귀(10 cells).
- `model.encoder: stub` — 실제 SigLIP/DINO 연결, CUDA 빌드 전환, §15 잔여 전처리, 의존성 exact pin 은 P02.

## 다음 작업 (우선순위 순)

1. 소유자 액션 — AIHub K-Fashion 다운로드(P01 선행 조건)
2. P01 상세 계획 — 카테고리 목록 확정(K-Fashion 라벨 분포), AI 생성기 ≥3종 접근 수단 확인, 얼굴 영역 처리 정책(DB-01 후속)
3. P01 착수 — 데이터 파이프라인(§27 Phase 1)

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림 — 2026-10-07 사고 기록).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

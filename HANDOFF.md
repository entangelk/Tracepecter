# HANDOFF.md

> 마지막 자가 검수: 2026-10-07 · 21줄

## 현재 상태

- P00(프로젝트 초기화) 구현 완료 — 독립검증 대기. 합격 시 `docs/plan/00_index.md` 에서 P00 을 Complete 로 처리한다.
- 실행 환경: venv = `~/.venvs/tracepecter`(ext4, CPU torch wheel). 런타임 진입은 `~/.venvs/tracepecter/bin/python -m pytest` / `-m src.train` 사용.
- `python -m src.train --config configs/baseline.yaml --smoke` 로 실데이터 없이 skeleton 검증 가능(8장 synthetic, 1 epoch).
- `model.encoder: stub` — 실제 SigLIP/DINO 연결은 P02. CUDA 빌드 전환도 P02 에서 결정.

## 다음 작업 (우선순위 순)

1. P00 독립검증 → 검증기록(`docs/verifications/2026-10-07/`) 확인 → 차단·비차단 전부 보강 → 합격
2. 소유자 액션 — AIHub K-Fashion 다운로드(P01 선행 조건)
3. P01 상세 계획 — 카테고리 목록 확정(라벨 분포), AI 생성기 ≥3종 접근 확인, 얼굴 영역 처리 정책(DB-01 후속)

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

# HANDOFF.md

> 마지막 자가 검수: 2026-10-07 · 25줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 구현 → 독립검증 초회 합격(hardening 7건) → 보강 → 재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- P01 상세 계획서 작성 완료(2026-10-07, 소유자 검토 대기) — 라벨링데이터 전수 분석 기반 카테고리 4부위(상의·하의·아우터·원피스) 확정 제안 + metadata schema v1.2 제안 포함. 결정 대기: DB-02(생성기)·DB-03(얼굴 처리).
- 실행 환경: venv 는 P00 작업 머신 기준 `~/.venvs/tracepecter`(ext4, CPU torch) — **이 머신에는 없음**(아래 주의 참조). skeleton 검증 `python -m src.train --config configs/baseline.yaml --smoke`, 회귀 `python -m pytest`(10 cells).
- `model.encoder: stub` — 실제 SigLIP/DINO 연결, CUDA 빌드 전환, §15 잔여 전처리, 의존성 exact pin 은 P02.

## 다음 작업 (우선순위 순)

1. 소유자 결정 대기 — P01 계획서([`docs/plan/phase_1_data_pipeline.md`](docs/plan/phase_1_data_pipeline.md)) 검토·승인 + [DB-02](docs/decision_briefs/DB-02_P01_ai-generators.md)(생성기 수단)·[DB-03](docs/decision_briefs/DB-03_P01_face-policy.md)(얼굴 처리) 결정. 카테고리 4부위 확정 제안도 계획서 검토 시 함께 승인.
2. 소유자 진행 중 — K-Fashion 원천 이미지 다운로드(2026-10-07 기준 수 시간 예상). 라벨링데이터(Training)는 완료·분석 마침.
3. P01 착수(계획서 승인 후) — P01-02(카테고리·스키마 확정)는 이미지 없이 즉시 가능. P01-01·P01-03은 원천 수신 완료 후. P01-04는 DB-02 해결 후.

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신, 2026-10-07)**: RTX 3060 12GB를 소유자의 다른 AI 모델 작업이 점유 중. 학습·생성 등 GPU 작업은 그 작업 종료 후 남는 시간에만 수행(큐잉 금지 — 소유자 지시).
- **venv(이 머신, 2026-10-07)**: `~/.venvs/tracepecter` 없음 — P00 작업 머신과 다름. P01 코드 슬라이스 착수 시 P00-01 절차로 재구성. 시스템 python3에는 PIL·pytest 있음(torch 없음).
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림 — 2026-10-07 사고 기록).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

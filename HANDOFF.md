# HANDOFF.md

> 마지막 자가 검수: 2026-10-07 · 25줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- P01(데이터 파이프라인) **In Progress** — 계획서 승인(2026-10-07). P01-01 완료(원천 정합 — 매핑 불일치 0.0000%, 유효 967,806장), P01-02 완료(카테고리 4부위·schema §12 v1.2)·독립검증 재검증 합격([기록](docs/verifications/2026-10-07/p01_plan_schema_docker.md)), P01-03 완료(REAL 씨드 500장 — `data/metadata_real.csv`, 부위별 125×4, split 미배정). DB-02(생성기=로컬 오픈소스 무비용)·DB-03(얼굴=무처리) Resolved.
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07, venv 대체) — `Dockerfile`·`compose.yaml`. `docker compose run --rm dev python -m pytest`(15 cells), `... python -m src.train --config configs/baseline.yaml --smoke` 로 검증. 의존성 canonical은 `requirements.txt`.
- `model.encoder: stub` — 실제 SigLIP/DINO 연결, CUDA 프로파일, §15 잔여 전처리, 의존성 exact pin 은 P02.

## 다음 작업 (우선순위 순)

1. P01-05(dedup·look_group 보완) — REAL 씨드 500장 대상 pHash 근사중복 클러스터링(§13). CPU 작업, 지금 가능.
2. P01-04(AI 생성 파이프라인) 설계 — 5종 구성(Qwen-Image 보유·Z-Image 등) VRAM 12GB 적합성 보고. 본 생성은 GPU 여유 시에만.
3. P01-06(split) — P01-04·P01-05 완료 후 look_group·generator 기준 group split + unseen test. 이후 P02 착수 가능(씨드 Real+Gen split 확보 시).

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신, 2026-10-07)**: RTX 3060 12GB를 소유자의 다른 AI 모델 작업이 점유 중. 학습·생성 등 GPU 작업은 그 작업 종료 후 남는 시간에만 수행(큐잉 금지 — 소유자 지시). GPU 서비스는 필요 시점에 compose에 추가.
- 데이터 대량 읽기는 `/mnt/f`(9p)가 느리다 — 서브셋을 ext4로 복사해 작업한다(P00 교훈). 컨테이너 `/data` 마운트도 동일.
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림 — 2026-10-07 사고 기록).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

# HANDOFF.md

> 마지막 자가 검수: 2026-10-08 · 27줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- P01(데이터 파이프라인) **In Progress** — 계획서 승인(2026-10-07). P01-01 완료(원천 정합 — 매핑 불일치 0.0000%, 유효 967,806장), P01-02 완료(카테고리 4부위·schema §12 v1.2)·독립검증 재검증 합격([기록](docs/verifications/2026-10-07/p01_plan_schema_docker.md)), P01-03 완료(REAL 3,000장 750×4 — `data/metadata_real.csv`, P01-07 선행분, 씨드 500은 git 이력), P01-05 완료(look_group 100% 커버 — pHash 클러스터링). DB-02(생성기=로컬 오픈소스 무비용)·DB-03(얼굴=무처리) Resolved.
- P01-04 진행 중 — `scripts/generate_ai.py`(train 4종+unseen 1종 어댑터, §9 변형)·ComfyUI GPU 서비스(`Dockerfile.comfyui`, compose gpu profile) 구축. qwen_image_21 씨드 124장 커밋(2182daa). z_image(DiT·VAE 완료, 인코더 qwen_3_4b 다운로드 중)→sdxl→playground→sd35 순차 진행.
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07, venv 대체) — `Dockerfile`·`compose.yaml`. `docker compose run --rm dev python -m pytest`(18 cells), `... python -m src.train --config configs/baseline.yaml --smoke` 로 검증. 의존성 canonical은 `requirements.txt`.
- `model.encoder: stub` — 실제 SigLIP/DINO 연결, CUDA 프로파일, §15 잔여 전처리, 의존성 exact pin 은 P02.

## 다음 작업 (우선순위 순)

1. P01-04 잔여 — z_image_turbo 씨드 생성(`--count 125 --seed 42`, qwen과 동일 패턴) → sdxl → playground → sd35(unseen) 시드 생성·검증·커밋. 모델 다운로드는 `python3 scripts/chunk_dl.py 8`(자동 이어받기).
2. P01-06(split) — Generated 씨드 확보 후 look_group·generator 기준 group split + unseen test. 완료 시 P02 착수 게이트 통과.
3. P01-07(규모 확장) — Generated 3,000+ 확장 → §27 Phase 1 완료. Playground v2.5 13.9GB fp16 `--lowvram` 유지 결정 재확인(세션 4 이월 사항).

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신, 2026-10-08 아침)**: 여유 관측(660MiB/12GB) — 소유자 진행 지시로 생성 진행 중. 소유자의 다른 AI 작업 점유 시 GPU 작업은 중단(큐잉 금지 — 소유자 지시).
- **이 머신은 예기치 않은 전원 단절이 반복됨**(09-21·09-24·10-08, Kernel-Power 41). 장시간 백그라운드 작업은 setsid + 디스크 기반 재개 가능 상태로 둘 것. HF 대량 다운로드는 `scripts/chunk_dl.py` 사용 — `curl -C -`와 `-r` 동시 사용 금지(범위 겹침 어펜드 오염, 2026-10-07 사고).
- 데이터 대량 읽기는 `/mnt/f`(9p)가 느리다 — 서브셋을 ext4로 복사해 작업한다(P00 교훈). 컨테이너 `/data` 마운트도 동일.
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림 — 2026-10-07 사고 기록).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

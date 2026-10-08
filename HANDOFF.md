# HANDOFF.md

> 마지막 자가 검수: 2026-10-08 · 27줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- P01(데이터 파이프라인) **In Progress** — 계획서 승인(2026-10-07). P01-01 완료(원천 정합 — 매핑 불일치 0.0000%, 유효 967,806장), P01-02 완료(카테고리 4부위·schema §12 v1.2)·독립검증 재검증 합격([기록](docs/verifications/2026-10-07/p01_plan_schema_docker.md)), P01-03 완료(REAL 3,000장 750×4 — `data/metadata_real.csv`, P01-07 선행분), P01-04 완료(2026-10-08 — 생성기 5종 씨드 620장: train 4종 + unseen sd35_medium, `data/metadata_gen_*.csv`, gen_ID 전역 연속·유일), P01-05 완료(look_group 100% 커버 — pHash 클러스터링). DB-02·DB-03 Resolved.
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07, venv 대체) — `Dockerfile`·`compose.yaml`·`Dockerfile.comfyui`(GPU). `docker compose run --rm dev python -m pytest`(18 cells), `... python -m src.train --config configs/baseline.yaml --smoke` 로 검증. 의존성 canonical은 `requirements.txt`.
- 생성 인프라: ComfyUI GPU 컨테이너(compose gpu profile, 소유자 모델 ro 마운트) — 5종 전 생성기 모델 확보 완료(`/mnt/f/AI/ComfyUI-models`, 38GB). 12GB 초과 체크포인트도 자동 lowvram 스트리밍으로 동작.
- `model.encoder: stub` — 실제 SigLIP/DINO 연결, CUDA 프로파일, §15 잔여 전처리, 의존성 exact pin 은 P02.

## 다음 작업 (우선순위 순)

1. P01-07(규모 확장) — Generated 3,000+ 확장(생성기별 증량, `generate_ai.py --count`·`--start-index` 이어서) 후 `split_dataset.py` 재실행·비율/누출 재검증 → §27 Phase 1 완료.
2. P02 착수 가능(§35 thin-slice) — 씨드 split 확보로 게이트 통과(`data/metadata.csv`).
3. **보류 결정(소유자)**: Test B(test_unseen) 평가 시 REAL 이미지 재사용 여부 — §10 예시는 "TEST: Real images + Generator D"로 읽히나 현 구성은 gen-only(독립검증 H3). 평가 설계 확정 시점(P02+)에 결정 필요.

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신)**: RTX 3060 12GB. 소유자의 다른 AI 작업 점유 시 GPU 작업은 중단(큐잉 금지 — 소유자 지시). 12GB 초과 체크포인트는 ComfyUI 자동 lowvram 스트리밍으로 동작(2026-10-08 확인).
- **이 머신은 예기치 않은 전원 단절이 반복됨**(09-21·09-24·10-08, Kernel-Power 41). 장시간 백그라운드 작업은 setsid + 디스크 기반 재개 가능 상태로 둘 것. HF 대량 다운로드는 `scripts/chunk_dl.py`(v4.1) — `curl --retry` 금지(내부 재시도가 range 재스트리밍하며 append 오염), `-C -`와 `-r` 조합 금지.
- `pgrep -f` 생존 점검 시 감시자 셸 self-match 오탐 주의 — 앵커 패턴(`^python3 -u scripts/...`) 사용(2026-10-08 사고).
- 데이터 대량 읽기는 `/mnt/f`(9p)가 느리다 — 서브셋을 ext4로 복사해 작업한다(P00 교훈). 컨테이너 `/data` 마운트도 동일.
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림 — 2026-10-07 사고 기록).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

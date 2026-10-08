# HANDOFF.md

> 마지막 자가 검수: 2026-10-09 · 29줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- **P01(데이터 파이프라인) Complete (2026-10-09)** — §27 Phase 1 완료 조건 전부 충족. 최종 `data/metadata.csv` **6,000행**(REAL 3,000 K-Fashion + Generated 3,000 = 5종 × 600): train 3,780 / val 820 / test 800 + test_unseen 600(sd35_medium 전량). 누출 0, 층화 축은 **source_type × category × generator**(train 생성기별 420/92/88 — generator별 평가 가능화, P01-07 검증 H1). P01-06·P01-07 독립검증 모두 최종 합격([P01-06](docs/verifications/2026-10-08/p01_06_split.md) · [P01-07](docs/verifications/2026-10-09/p01_07_scale_expansion.md) — 각 보강 라운드 포함).
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07) — `Dockerfile`·`compose.yaml`·`Dockerfile.comfyui`(GPU, 생성 완료로 현재 정지 상태). `docker compose run --rm dev python -m pytest`. 의존성 canonical은 `requirements.txt`.
- 생성 인프라: 5종 전 생성기 모델 확보 완료(`/mnt/f/AI/ComfyUI-models`, 38GB). 재사용 시 `docker compose --profile gpu up -d comfyui`.
- P02 baseline: `configs/baseline.yaml`은 frozen SigLIP, smoke는 stub/CPU. CUDA `training` profile과 `src/evaluate.py` 제공. 실학습 확인 전이며 상태는 [P02 계획](docs/plan/phase_2_baseline.md) 참고.

## 다음 작업 (우선순위 순)

1. **P02 실학습·평가 확인** — `COMPOSE_BAKE=false docker compose --profile training build train`, `GIT_COMMIT=$(git rev-parse HEAD) docker compose --profile training run --rm train`. 이미지 기본 경로는 `$HOME/data/tracepector/images`(`IMAGE_DIR`로 변경), `/images`로 읽기 전용 마운트.
2. Test B REAL은 Standard test REAL 재사용([DB-04](docs/decision_briefs/DB-04_P02_unseen-real.md)). train/val 제외. 평가: `docker compose --profile training run --rm train python -m src.evaluate --checkpoint checkpoints/baseline/best.pt --device cuda`.
3. 전원 단절 시 동일 config로 train `--resume`(epoch별 `last.pt`). GEN pHash/embedding 중복 점검은 후속 작업.

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신)**: RTX 3060 12GB. 소유자의 다른 AI 작업 점유 시 GPU 작업은 중단(큐잉 금지 — 소유자 지시). 생성 컨테이너는 현재 정지(필요 시 compose gpu profile).
- **이 머신은 예기치 않은 전원 단절이 반복됨**(09-21·09-24·10-08, Kernel-Power 41). 장시간 백그라운드 작업은 setsid + 디스크 기반 재개 가능 상태로 둘 것. HF 대량 다운로드는 `scripts/chunk_dl.py`(v4.1) — `curl --retry` 금지(재스트리밍 오염), `-C -`+`-r` 금지.
- `pgrep -f` 생존 점검 시 감시자 셸 self-match 오탐 주의 — 앵커 패턴(`^python3 -u scripts/...`) 사용.
- 대량 생성 재개 시 `generate_ai.py`는 재개 가드 내장(완료 PNG 스킵). gen_ID는 전역 연속(현재 1~3,003 사용) — 추가 배치는 3,004부터.
- 데이터 대량 읽기는 `/mnt/f`(9p)가 느리다 — 서브셋을 ext4로 복사해 작업한다(P00 교훈).
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

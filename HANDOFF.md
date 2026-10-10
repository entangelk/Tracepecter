# HANDOFF.md

> 마지막 자가 검수: 2026-10-10 · 31줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- **P01(데이터 파이프라인) Complete (2026-10-09)** — §27 Phase 1 완료 조건 전부 충족. 최종 `data/metadata.csv` **6,000행**(REAL 3,000 K-Fashion + Generated 3,000 = 5종 × 600): train 3,780 / val 820 / test 800 + test_unseen 600(sd35_medium 전량). 누출 0, 층화 축은 **source_type × category × generator**(train 생성기별 420/92/88 — generator별 평가 가능화, P01-07 검증 H1). P01-06·P01-07 독립검증 모두 최종 합격([P01-06](docs/verifications/2026-10-08/p01_06_split.md) · [P01-07](docs/verifications/2026-10-09/p01_07_scale_expansion.md) — 각 보강 라운드 포함).
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07) — `Dockerfile`·`compose.yaml`·`Dockerfile.comfyui`(GPU, 생성 완료로 현재 정지 상태). `docker compose run --rm dev python -m pytest`. 의존성 canonical은 `requirements.txt`.
- 생성 인프라: 5종 전 생성기 모델 확보 완료(`/mnt/f/AI/ComfyUI-models`, 38GB). 재사용 시 `docker compose --profile gpu up -d comfyui`.
- primary: **SigLIP**, 실행 설정 `configs/primary.yaml`, checkpoint `checkpoints/baseline/best.pt`. DINO 비교 모델은 `checkpoints/dino/best.pt`. [비교 근거·실험 기록](experiments/p03_comparison/README.md)과 [P03 계획](docs/plan/phase_3_baseline_comparison.md) 참고.
- scoring: `experiments/p05_calibration/calibration.json`(checkpoint hash 결합), `src.score` CLI. score=`100*sigmoid(logit/T)`, threshold는 확률에서 유도. [calibration 보고서](experiments/p05_calibration/README.md) 참고. Test B NLL/Brier 소폭 악화는 실패 분석 대상이다.
- P06 실행: `docker compose --profile training run --rm -T train python -m src.failure_analysis --config configs/failure_analysis.yaml` → `reports/errors/*/manifest.csv`(이미지 사본은 비추적)·`experiments/p06_failure_analysis/`. Test B NLL/Brier 악화는 sd35 확신 FP 12장 때문으로 분해됐다.
- Test B는 Standard test REAL 448 + `test_unseen` FAKE 600(sd35_medium), 총 1,048장([DB-04](docs/decision_briefs/DB-04_P02_unseen-real.md)). train/val REAL 제외, 두 테스트 간 REAL 공유.

## 다음 작업 (우선순위 순)

1. **P06-02b 독립검증** — [보고서](experiments/p06_failure_analysis/face_mask/README.md)·[config](configs/face_mask_diagnostic.yaml)·`src/face_mask.py`. 결과: 사전 규칙상 "의존 근거 있음"(GEN 얼굴 흰 원 +10.19점, 전환 36/581 = 6.2%)이지만 약 70%는 회색 원(가림 일반) 효과다. 검증 포인트: 검출기 기준을 검토군 103장에 맞춰 정한 점(검토군 밖은 표본 육안 확인만 함), Haar 얼굴 정밀도 약 75%·커버리지 61%, 전환 36장 육안 분류(얼굴 30·머리 경계 2·옷 4)의 재현, 수치와 report.json의 일치. 재현: `docker compose --profile training run --rm -T train python -m src.face_mask --config configs/face_mask_diagnostic.yaml`(검출 약 12분).
2. **P06-02c 표본 확장 재진단(검증 합격 후)** — 기존 config는 사전 고정본이므로 수정하지 말고 **새 config로 다시 사전 고정**한다. 후보: val 820장 포함(train은 학습 표본이라 제외), 얼굴 검출 개선(측면 포함, 정밀도 향상 — 새 의존성은 소유자 확인), 조건별 bootstrap 신뢰구간, 흰색 고유 효과(흰 원 − 회색 원)의 구간 추정. 신규 데이터 수집은 P06 범위 밖이다.
3. **P06-04 오류 패턴 문서** — P06-03 완료(2026-10-10: 소유자 35건 + 에이전트 블라인드 103건, 체감 판정 일치 19/35, [P06 계획](docs/plan/phase_6_failure_analysis.md) 진행 상황 참고). 불일치 16건 재확인, 얼굴 노출·구도 편향 정리(P06-02·02b), DB-03 얼굴 트리거 판정. 검토 페이지 재생성: `DATA_DIR="/mnt/h/tracepector/images" docker compose run --rm dev python -m scripts.build_review_page` → `F:\devel\Tracepecter\reports\errors\review\index.html`를 Windows 브라우저로 연다.
4. GEN pHash/embedding 근사중복 점검·최종 독립 REAL/FAKE holdout·사람 평가가 남는다. 현재 Test A/B는 개발 평가이며 신규 수집·split 변경은 하지 않았다.
5. score 실행: `docker compose --profile training run --rm train python -m src.score --image /images/<path> --calibration experiments/p05_calibration/calibration.json --device cuda`. artifact는 `checkpoints/baseline/best.pt`에 결합된다. 재현 fitting은 `GIT_COMMIT=$(git rev-parse HEAD) docker compose --profile training run --rm train python -m src.calibrate --config configs/calibration.yaml`.

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신)**: RTX 3060 12GB. 소유자의 다른 AI 작업 점유 시 GPU 작업은 중단(큐잉 금지 — 소유자 지시). 생성 컨테이너는 현재 정지(필요 시 compose gpu profile).
- **이 머신은 예기치 않은 전원 단절이 반복됨**(09-21·09-24·10-08, Kernel-Power 41). 장시간 백그라운드 작업은 setsid + 디스크 기반 재개 가능 상태로 둘 것. HF 대량 다운로드는 `scripts/chunk_dl.py`(v4.1) — `curl --retry` 금지(재스트리밍 오염), `-C -`+`-r` 금지.
- `pgrep -f` 생존 점검 시 감시자 셸 self-match 오탐 주의 — 앵커 패턴(`^python3 -u scripts/...`) 사용.
- 대량 생성 재개 시 `generate_ai.py`는 재개 가드 내장(완료 PNG 스킵). gen_ID는 전역 연속(현재 1~3,003 사용) — 추가 배치는 3,004부터.
- **소유자 대기 작업**: vhdx 압축(`F:\WSL\Ubuntu\ext4.vhdx`, 약 58G 회수 — `wsl --shutdown` 후 diskpart `compact vdisk`)은 소유자가 직접 실행한다.
- 데이터 대량 읽기는 `/mnt/f`(9p)가 느리다 — 서브셋을 ext4로 복사해 작업한다(P00 교훈).
- **저장 위치 이전(2026-10-10)**: Ubuntu vhdx가 `F:\WSL\Ubuntu`에 있어 F: 용량이 바닥났다. 생성·학습 이미지·comfy_output·K-Fashion zip·checkpoint를 H:(외장 SSD) `/mnt/h/tracepector/{images,comfy_output,data,checkpoints}`로 옮기고 compose 기본 경로를 바꿨다(`IMAGE_DIR`·`DATA_DIR`·`CHECKPOINT_DIR`·`COMFY_OUTPUT_DIR`로 재지정 가능). 9p 경유라 학습 I/O가 ext4보다 느릴 수 있다. Z:(USB HDD)는 I/O 오류(disk 이벤트 51)로 사용 금지. checkpoint는 Z:에서 H:로 복구했고 best.pt sha256이 실험 기록과 일치한다(baseline `151244…`, DINO `456c99…`). `hf_cache`는 불완전 복사라 삭제했으므로 첫 실행 시 재다운로드된다. Training `라벨링데이터.zip`도 H:로 옮겼고 sha256 `63b9fb8a…` 일치. Z:에만 남은 것은 파이프라인에 불필요한 `014.KFashion` 저작도구뿐이다.
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림).
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

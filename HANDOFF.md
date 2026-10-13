# HANDOFF.md

> 마지막 자가 검수: 2026-10-13 · 43줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- **P01(데이터 파이프라인) Complete (2026-10-09)** — §27 Phase 1 완료 조건 전부 충족. 최종 `data/metadata.csv` **6,000행**(REAL 3,000 K-Fashion + Generated 3,000 = 5종 × 600): train 3,780 / val 820 / test 800 + test_unseen 600(sd35_medium 전량). 누출 0, 층화 축은 **source_type × category × generator**(train 생성기별 420/92/88 — generator별 평가 가능화, P01-07 검증 H1). P01-06·P01-07 독립검증 모두 최종 합격([P01-06](docs/verifications/2026-10-08/p01_06_split.md) · [P01-07](docs/verifications/2026-10-09/p01_07_scale_expansion.md) — 각 보강 라운드 포함).
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07) — `Dockerfile`·`compose.yaml`·`Dockerfile.comfyui`(GPU, 생성 완료로 현재 정지 상태). `docker compose run --rm dev python -m pytest`. 의존성 canonical은 `requirements.txt`.
- 생성 인프라: 5종 전 생성기 모델 확보 완료(`/mnt/f/AI/ComfyUI-models`, 38GB). 재사용 시 `docker compose --profile gpu up -d comfyui`.
- primary: **SigLIP**, 실행 설정 `configs/primary.yaml`, checkpoint `checkpoints/baseline/best.pt`. DINO 비교 모델은 `checkpoints/dino/best.pt`. [비교 근거·실험 기록](experiments/p03_comparison/README.md)과 [P03 계획](docs/plan/phase_3_baseline_comparison.md) 참고.
- scoring: `experiments/p05_calibration/calibration.json`(checkpoint hash 결합), `src.score` CLI. score=`100*sigmoid(logit/T)`, threshold는 확률에서 유도. [calibration 보고서](experiments/p05_calibration/README.md) 참고. Test B NLL/Brier 소폭 악화는 P06에서 분해했다(아래).
- **P06(Failure analysis) Complete (2026-10-11)** — [오류 패턴 문서](experiments/p06_failure_analysis/patterns/README.md). 슬라이스별 독립검증 합격. 핵심: 얼굴이 보이지 않는 GEN이 REAL로 통과하는 단축 단서(개입 실험 확정)와, 그 원인인 얼굴 노출 비대칭(REAL 학습 0.4% 대 GEN 64.5%). DB-03 트리거 발동 → DB-06 C로 확정(P08).
- P06 실행: `docker compose --profile training run --rm -T train python -m src.failure_analysis --config configs/failure_analysis.yaml` → `reports/errors/*/manifest.csv`(이미지 사본은 비추적)·`experiments/p06_failure_analysis/`. Test B NLL/Brier 악화는 오답 쪽으로 기운 12장(sd35 GEN 10, REAL FN 2) 때문으로 분해됐다.
- 얼굴 검출 모델(P06-02c): YuNet `/mnt/h/tracepector/checkpoints/face/face_detection_yunet_2023mar.onnx`(컨테이너 `/app/checkpoints/face/`, sha256은 `configs/face_mask_ci.yaml`).
- Test B는 Standard test REAL 448 + `test_unseen` FAKE 600(sd35_medium), 총 1,048장([DB-04](docs/decision_briefs/DB-04_P02_unseen-real.md)). train/val REAL 제외, 두 테스트 간 REAL 공유.

## 다음 작업 (우선순위 순)

1. **P08 진행 중**([계획](docs/plan/phase_8_face_anonymization.md)) — 계획 독립검증 4라운드 합격(2026-10-11, [기록](docs/verifications/2026-10-11/p08_plan_db06.md)). DB-06은 C로 확정됐고, `project.md`는 v1.4다(§15·§22·§23).
   - 순서: P08-01 측정(이미지만) → P08-02 익명화 모듈 → P08-03 진단·채택 규칙 사전 고정(**재학습 결과 전에 커밋**) → P08-04 재학습 → P08-05 재calibration → P08-06 판정. P08-07 holdout 설계는 병행하며 P07의 관문이 아니다.
   - **다음은 P08-05 재calibration이다.** 새 checkpoint는 `checkpoints/anonymized/best.pt`(이 머신의 H: mount), [학습 기록](experiments/p08_anonymized/training/README.md)을 참고한다. `configs/calibration_anonymized.yaml`에 새 checkpoint·얼굴 캐시를 지정하고 출력은 `experiments/p08_anonymized/calibration/`로 분리한다. 진단 config·표본은 [사전등록 계약](experiments/p08_anonymized/diagnostic/README.md)을 고정해 사용한다. 전처리·좌표 캐시·실행 계약은 [P08 전처리 기록](experiments/p08_anonymized/README.md)을 참고한다. P08 측정·캐시 CSV는 LF, 기존 실험에 연결된 `data/metadata.csv`는 CRLF로 체크아웃한다(`.gitattributes`).
   - 익명화 규격은 `configs/anonymize.yaml`(k=1.2). 사전 크기 관문 실패는 보존하며 사전등록의 `real_size` 관문으로 크기 단서를 진단한다. 재현율 관문 미통과면 재학습 전에 소유자에게 묻는다.
   - 채택 규칙: §20 AUC 기준과 '단서 해소'를 모두 만족할 때만 `configs/primary.yaml`을 교체한다. 기존 baseline artifact는 덮어쓰지 않는다. 미채택이면 P07은 대기하고 P08을 다시 시도한다(Q5).
   - 작업 절차(소유자 요청): 구현·자가 확인·커밋 후 서브에이전트 한 명의 독립검증을 받고, 차단·비차단 모두 보강·추적검증 합격까지 진행한다.
   - P07(API)은 P08의 전처리 계약과 채택 artifact를 기다린다.
2. GEN pHash/embedding 근사중복 점검·최종 독립 REAL/FAKE holdout(얼굴이 보이는 실사 포함, [P06-04 수집 방향](experiments/p06_failure_analysis/patterns/README.md#다음-데이터-수집-방향))·사람 평가가 남는다. 현재 Test A/B는 개발 평가이며 신규 수집·split 변경은 하지 않았다.
3. score CLI는 익명화 규격이 없는 P05 baseline을 거부한다. 현재 서빙 가능한 채택 artifact는 없고 P08-05·06을 기다린다. baseline 평가·calibration은 원본 입력을 허용한다. 익명화 비교 평가는 `src.evaluate --anonymize configs/anonymize.yaml --face-cache experiments/p08_anonymized/face_boxes.csv`(별도 비교 checkpoint 경로 사용: 출력은 checkpoint 디렉터리에 기록된다).

## 주의

- `docs/guides/`, `CLAUDE.md`, `AGENTS.md`는 `.gitignore`로 Git 비추적(로컬 작업 지침).
- **GPU(이 머신)**: RTX 3060 12GB. 소유자의 다른 AI 작업이 GPU를 크게 점유하면 GPU 작업은 중단한다(큐잉 금지 — 소유자 지시). ai_writte_system 컨테이너가 떠 있어도 점유가 낮으면 실행해도 된다(소유자 2026-10-11). 생성 컨테이너는 현재 정지(필요 시 compose gpu profile).
- **이 머신은 예기치 않은 전원 단절이 반복됨**(09-21·09-24·10-08, Kernel-Power 41). 장시간 백그라운드 작업은 setsid + 디스크 기반 재개 가능 상태로 둘 것. HF 대량 다운로드는 `scripts/chunk_dl.py`(v4.1) — `curl --retry` 금지(재스트리밍 오염), `-C -`+`-r` 금지.
- `pgrep -f` 생존 점검 시 감시자 셸 self-match 오탐 주의 — 앵커 패턴(`^python3 -u scripts/...`) 사용.
- 대량 생성 재개 시 `generate_ai.py`는 재개 가드 내장(완료 PNG 스킵). gen_ID는 전역 연속(현재 1~3,003 사용) — 추가 배치는 3,004부터.
- **소유자 대기 작업**: vhdx 압축(`F:\WSL\Ubuntu\ext4.vhdx`, 약 58G 회수 — `wsl --shutdown` 후 diskpart `compact vdisk`)은 소유자가 직접 실행한다.
- 데이터 대량 읽기는 `/mnt/f`(9p)가 느리다 — 서브셋을 ext4로 복사해 작업한다(P00 교훈).
- **저장 위치 이전(2026-10-10)**: Ubuntu vhdx가 `F:\WSL\Ubuntu`에 있어 F: 용량이 바닥났다. 생성·학습 이미지·comfy_output·K-Fashion zip·checkpoint를 H:(외장 SSD) `/mnt/h/tracepector/{images,comfy_output,data,checkpoints}`로 옮기고 compose 기본 경로를 바꿨다(`IMAGE_DIR`·`DATA_DIR`·`CHECKPOINT_DIR`·`COMFY_OUTPUT_DIR`로 재지정 가능). 9p 경유라 학습 I/O가 ext4보다 느릴 수 있다. Z:(USB HDD)는 I/O 오류(disk 이벤트 51)로 사용 금지. checkpoint는 Z:에서 H:로 복구했고 best.pt sha256이 실험 기록과 일치한다(baseline `151244…`, DINO `456c99…`). `hf_cache`는 불완전 복사라 삭제했으므로 첫 실행 시 재다운로드된다. Training `라벨링데이터.zip`도 H:로 옮겼고 sha256 `63b9fb8a…` 일치. Z:에만 남은 것은 파이프라인에 불필요한 `014.KFashion` 저작도구뿐이다.
- mutation testing 전 pre-flight: `git status --short` 가 비어 있어야 한다(커밋 후 mutation).
- pytest 실행 시 exit code 를 파이프 뒤에서 확인할 것(`| tail` 이 exit 를 가림).
- 테스트의 stub 학습·calibration은 비결정적이다(threshold 0.5~0.517, 원인 미조사). stub의 threshold 값에 기대는 테스트를 만들지 말 것.
- 페이즈 상태 갱신 시 `docs/plan/00_index.md`와 해당 페이즈 문서를 함께 갱신할 것.

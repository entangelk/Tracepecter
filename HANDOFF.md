# HANDOFF.md

> 마지막 자가 검수: 2026-10-20 · 45줄

## 현재 상태

- P00(프로젝트 초기화) **Complete** — 독립검증 초회+재검증 합격. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- 현재 `data/metadata.csv`는 **6,000행**(REAL 3,000 K-Fashion + GEN 3,000): train 3,780 / val 820 / test 800 / test_unseen 600(sd35_medium 전량). **선언된 ID·look_group 교차는 0이지만 실제 같은 룩의 train/test 최소 4쌍·train/val 최소 4쌍이 존재한다. 데이터 독립성 감사 판정은 불합격이다.** P08 사전등록 통계 관문 통과와 구분한다.
- 실행 환경: **Docker Compose**(소유자 결정 2026-10-07) — `Dockerfile`·`compose.yaml`·`Dockerfile.comfyui`(GPU, 생성 완료로 현재 정지 상태). `docker compose run --rm dev python -m pytest`. 의존성 canonical은 `requirements.txt`.
- 생성 인프라: 5종 전 생성기 모델 확보 완료(`/mnt/f/AI/ComfyUI-models`, 38GB). 재사용 시 `docker compose --profile gpu up -d comfyui`.
- primary: **SigLIP**, 실행 설정 `configs/primary.yaml`, checkpoint `checkpoints/anonymized/best.pt`(P08-06 채택). DINO 비교 모델은 `checkpoints/dino/best.pt`. [비교 근거·실험 기록](experiments/p03_comparison/README.md)과 [P03 계획](docs/plan/phase_3_baseline_comparison.md) 참고.
- scoring: `experiments/p08_anonymized/calibration/calibration.json`(checkpoint hash 결합), `src.score` CLI. score=`100*sigmoid(logit/T)`, threshold는 확률에서 유도. [calibration 보고서](experiments/p08_anonymized/calibration/README.md) 참고.
- **P06(Failure analysis) Complete (2026-10-11)** — [오류 패턴 문서](experiments/p06_failure_analysis/patterns/README.md). 슬라이스별 독립검증 합격. 핵심: 얼굴이 보이지 않는 GEN이 REAL로 통과하는 단축 단서(개입 실험 확정)와, 그 원인인 얼굴 노출 비대칭(REAL 학습 0.4% 대 GEN 64.5%). DB-03 트리거 발동 → DB-06 C로 확정(P08).
- P06 실행: `docker compose --profile training run --rm -T train python -m src.failure_analysis --config configs/failure_analysis.yaml` → `reports/errors/*/manifest.csv`(이미지 사본은 비추적)·`experiments/p06_failure_analysis/`. Test B NLL/Brier 악화는 오답 쪽으로 기운 12장(sd35 GEN 10, REAL FN 2) 때문으로 분해됐다.
- 얼굴 검출 모델(P06-02c): YuNet `/mnt/h/tracepector/checkpoints/face/face_detection_yunet_2023mar.onnx`(컨테이너 `/app/checkpoints/face/`, sha256은 `configs/face_mask_ci.yaml`).
- Test B는 Standard test REAL 448 + `test_unseen` FAKE 600(sd35_medium), 총 1,048장([DB-04](docs/decision_briefs/DB-04_P02_unseen-real.md)). train/val REAL 제외, 두 테스트 간 REAL 공유.

## 다음 작업 (우선순위 순)

1. **[P09 누출 수리](docs/plan/phase_9_leakage_repair.md)의 P09-01 우선순위 검토 계속** — 상태 In Progress, [후보·첫 검토 기록](experiments/p09_leakage_repair/r1/grouping/README.md). DB-07은 우선순위 검토·미검토 범위 명시로 Resolved다. 그룹 최종 확정·재분할·학습은 미착수다.
   - 먼저 감사 `audit_lock.json`의 입력·원자료 hash를 검증하고 `visual_review.csv` 확정 8쌍·미확정 6쌍을 구별한다. embedding 자료는 평가→train 최근접 1개뿐이므로 전체 REAL 관계 후보를 split 무관하게 확장해야 한다. pHash≤10 또는 cosine≥.99만으로 거르지 않는다.
   - 새 출력은 `data/versions/p09_r1/metadata.csv`·`checkpoints/leakage_repair/r1/`·`experiments/p09_leakage_repair/r1/`로 분리한다. 기존 metadata·primary·checkpoint·calibration·감사 원자료·소유자 주석은 보존한다.
   - 재현 명령은 [감사 보고서](experiments/p08_anonymized/leakage_audit/README.md), embedding cache는 비추적 `reports/errors/review/p08_leakage_probe/`에 있다. GEN prompt·seed 공유는 실제 중복과 구별하고 generator holdout 계약을 유지한다. 새 split도 개발 평가이며 신규 미접촉 holdout이 아니다.
2. **P07(API + Demo) 상세 계획·구현** — 누출 수리 범위 검토를 먼저 이어간다. 현재 artifact와 공통 전처리 계약은 [P08 진단](experiments/p08_anonymized/diagnostic/README.md)을 참고하며 데모 구현 가능 상태와 모델 일반화 근거를 구분한다.
   - 먼저 `docs/project.md` §22·§23과 [페이즈 인덱스](docs/plan/00_index.md)를 바탕으로 P07 상세 계획을 작성한다. API·persistence schema 경계는 `docs/guides/api-and-persistence-schemas.md`를 따른다.
   - artifact는 `checkpoints/anonymized/best.pt` + `experiments/p08_anonymized/calibration/calibration.json`, 실행 설정은 `configs/primary.yaml`. checkpoint에 결합된 익명화 규격과 같은 전처리를 적용한다.
   - `POST /score`와 데모에 가린 얼굴 수(`faces_anonymized`)·artifact 조합 식별자(`model_version`)를 포함하고 원본 미리보기·익명화 표시를 제공한다. 기존 score CLI는 실제 이미지로 동작한다([README](README.md#calibrated-image-score)).
   - 소유자 301장 확인의 원본·변환본·최종 주석을 보존한다. 현재 추가 소유자 검토 요청은 없으며 cohort 변경 시 주석 ID·사전등록 적용 범위부터 재확인한다. P08-07 실사 holdout은 기존 결정대로 P07 관문이 아니다.
3. 감사의 pHash/embedding 후보 추가 검토·최종 독립 REAL/FAKE holdout(얼굴이 보이는 실사 포함, [P06-04 수집 방향](experiments/p06_failure_analysis/patterns/README.md#다음-데이터-수집-방향))·사람 평가가 남는다. 현재 Test A/B는 개발 평가이며 신규 수집·split 변경은 하지 않았다.
4. score CLI는 채택된 P08 calibration artifact로 실행한다([README](README.md#calibrated-image-score)). 익명화 키가 없는 P05 baseline은 score에서 거부하고, offline 평가·calibration에서만 원본 입력으로 허용한다.

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

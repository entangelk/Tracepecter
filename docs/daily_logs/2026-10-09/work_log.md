# 2026-10-09 work log

## Goals

- (세션 5 속행) P01-07 배치 2 마무리 — 잔여 생성기(sdxl·playground·sd35) 완료 확인·검증·커밋, 최종 split 재실행·재검증, §27 Phase 1 완료 처리, 독립검증(소유자 지시: 비차단 보강 포함 합격까지 반복).

## Completed work

### P01-07 배치 2 완성 — Generated 3,000장

- 야간 자동 진행(무인): sdxl b2 완료(10-08 23:54, 실측 ~19s/장 — 씨드 실행 대비 3배 빠름, 무경합·웜 캐시로 추정) → playground b2 완료(10-09 02:22, ~33s/장) → sd35 b2 완료(05:53) → `ALL_B2_DONE`. 총 소요 ~16시간(예상 30시간의 절반).
- 생성기별 검증·커밋(각 476행 · 카테고리 119×4 · gen_ID 범위 내 유니크 · 기존 전체와 교집합 0 · 샘플 20/20 PIL 정상): sdxl(1576-2051)·playground(2052-2527)·sd35(2528-3003).
- **통합 검증**: 11개 CSV + REAL = 6,000행, image_id 전역 유일(교집합 0 전수 확인). Generated 합계 3,000 = §7 최소 목표 충족.

### 최종 split 재실행·재검증 (P01-06 Outstanding 요건)

- `data/metadata.csv` 재배정: train 3,780 / val 812 / test 808 + test_unseen 600. real 70.0/15.1/14.9%, generated 70.0/15.0/15.0%, 셀별(source_type×category) 층화 25%±1pp, 그룹 누출 0.

### P01 완료 처리 — §27 Phase 1 완료 조건 전부 충족

- 충족 근거: 최소 6,000장 ✓ · Real ≥3,000 ✓ · Generated ≥3,000 ✓ · 카테고리 4부위 구성 ✓ · metadata.csv ✓ · train/val/test split ✓ · unseen generator test(test_unseen 600) ✓.
- 반영: `docs/plan/phase_1_data_pipeline.md` P01-07 완료 + 결과 비고, `docs/plan/00_index.md` P01 → Complete, HANDOFF 재작성(다음 = P02 착수), CHANGELOG 행.
- 생성 컨테이너 정지(GPU 반환 — 재사용 시 compose gpu profile).

### P01-07 독립검증·hardening (소유자 지시: 비차단 항목까지 반영·합격까지 반복)

- 독립검증([기록](../verifications/2026-10-09/p01_07_scale_expansion.md)): **합격** — blocking 0. §27 조건 7개 원천 재계산 충족, 무결성(키 집합·필드 불변·byte 동일 재실행), seed 43 실증(반사실: seed 42 재사용 시 생성기당 31쌍 정확 중복 발생 — 설계 동기 입증), mutation 7건 전건 재실패.
- hardening 4건 반영:
  - **H1(실질 결함): 생성기×split 퇴화** — 결정적 배정의 그룹키 사전순 소진으로 qwen·playground 600장이 전량 train에만 배정(§19 generator별 ROC-AUC를 val/test에서 측정 불가). §14가 generator를 층화 차원으로 명시하므로 **셀 정의를 source_type×category×generator로 확장**해 해소 — train 생성기별 420/92/88, REAL은 generator 공백이라 배정 불변(0행), 총량 동일. 가드에 generator 축 셀 비율 어설션 추가.
  - H2: 계획서 비고 gen_ID "전역 연속" 부정확 → 249·374·499 공백 3 명시로 정정.
  - H3: 10-08 work log 반사실 서술 정정(중복은 각 블록이 아닌 첫 카테고리 블록 31쌍만).
  - H4(계승): GEN pHash 위임·Test B REAL 재사용 보류 — HANDOFF 유지.
- 검증: split 재실행 누출 0, 가드 6셀·전체 28 cells passed.

### P01-07 추적 검증 — 합격 재확정

- 추적 검증 판정: **합격**(신규 blocking 0) — H1 해소를 diff·데이터에서 독립 재확인(생성기별 420/92/88×4, REAL 0행 불변, 3축 셀 편차 ≤0.33pp, P01-06 잠금 의미 잔존). **MU3 역방향 mutation**으로 H1 가드 실증(generator 축 제거 시 3축 셀 어설션이 퇴화 서명에서 정확 재실패). H2·H3 정정 확인.
- HANDOFF 최종 갱신(split 수치 820/800, 검증 완료 상태) — 세션 마무리·다음 작업자 인계.

## Issues found

- 없음(배치 2 전 구간 rc=0, 재기동 0회 — 재개 가드는 예비로만 존재).

## Decisions

- P01-07 검증은 데이터·split 최종 산출물에 대한 독립검증으로 진행(생성 프로세스 자체는 생성기별 검증으로 이미 잠금) — 소유자 지시 프로세스(비차단 보강 포함 합격까지 반복) 그대로 적용.

## Next steps

- P02 착수 — 페이즈 계획서(`docs/plan/phase_2_*.md`) 작성 후 baseline 모델 구현. 게이트 개방 상태.
- 보류(소유자 결정, P02 평가 설계 전): Test B(test_unseen) 평가 시 REAL 이미지 재사용 여부 · GEN 근사중복 pHash 점검 시점(P02+ encoder 연결 권장).

## P02 착수 — 후속 세션

### 목표

- 핸드오프의 다음 작업인 frozen SigLIP baseline을 구현하고 실제 데이터 학습·Test A/B 평가까지 확인한다.

### 구현·검증

- `src/model.py`: vision-only SigLIP pooled feature, pretrained config 기반 차원 유도, frozen encoder eval/no-grad 유지. head는 train mode를 유지하며 freeze 해제도 지원한다.
- `src/dataset.py`: 원본 CSV의 split 선택과 평가용 category/generator/source projection, Docker `/images` 마운트 지원. 약한 crop/resize·brightness/contrast 추가, 평가 transform은 결정적이다.
- `src/train.py`: validation BCE 기반 `best.pt`, epoch별 `last.pt`(optimizer/RNG 포함)와 동일 config 재개, config·metadata SHA256·학습 이력의 JSON 기록. smoke는 stub/CPU로 유지한다.
- `src/evaluate.py`: Test A/B 및 category/generator/source별 metric. ROC-AUC는 동률 threshold를 묶어 계산하며 PR-AUC는 trapezoidal 면적이다. 단일 클래스 AUC는 null로 기록한다.
- `Dockerfile.training`·compose `training` profile: 기존 ComfyUI CUDA 기반 환경 재사용, 런타임 의존성 exact pin. 학습용 서비스는 ComfyUI 서버를 기동하지 않는다.
- 검증: 신규 테스트 구현 전 import 실패 확인. 기존 CPU 환경 전체 32 passed, 이후 재개/마운트 가드 추가 및 exact pin CUDA 환경 전체 **33 passed**. 기존 dedup fixture의 Pillow deprecation 경고 12건은 동작 실패가 아니다. 독립검증·mutation testing은 수행하지 않았다.

### 발견 이슈

- CPU dev 이미지에는 git 실행 파일이 없다. `GIT_COMMIT` 환경변수를 우선 읽고 git이 있을 때만 조회하도록 수정했다. smoke의 commit은 없을 수 있지만 실학습에는 명시 전달한다.
- 이 머신 Docker Compose의 기본 Bake 빌드가 panic을 낸다. `COMPOSE_BAKE=false docker compose --profile training build train`으로 빌드 확인했다.
- 실제 pretrained 가중치 다운로드·실학습 검증은 진행 중이다. 아직 P02 Complete로 판정하지 않는다.

### 소유자 결정

- [DB-04](../../decision_briefs/DB-04_P02_unseen-real.md) 옵션 A 선택: Standard test REAL 재사용. train/val REAL을 포함하지 않고 테스트 간 공유 표본 수를 기록한다. §10 및 SoT 버전 로그에 반영했다.

### 다음 단계

- 실제 pretrained encoder와 CUDA 데이터 경로 확인 후 10 epoch 학습, best checkpoint에서 Test A/B 평가 및 실험 기록 보관.
- 이후 P03 비교, GEN pHash/embedding 중복 점검은 별도 후속 범위.

- 후속 확인: 소유자가 Test B의 FAKE=`test_unseen` 600장 정의를 재확인했다. CSV 실측 REAL 448 + Generated 600 = 1,048장. 최종 평가 독립성에 대한 질문에는 개발 중 테스트 결과로 모델/설정을 선택한다면 별도 미사용 REAL/FAKE holdout을 권고한다고 설명했다. 신규 데이터 수집이나 기존 split 변경은 아직 착수하지 않는다.
- 재개 검증 추가: augmentation 포함 연속 3 epoch와 2 epoch 후 RNG를 바꿔 재개한 결과의 학습 이력·전체 모델 state가 동일함을 확인했다. 변경된 config로 재개는 거부한다.

- 공식 pretrained 가중치 로드 성공(vision 차원 768, vision 누락 key 없음; 원본의 text_model/logit key는 vision-only 로딩에서 제외). 모델 revision을 `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`로 고정했다.

- 최종 CUDA 환경 전체 **34 passed**(기존 Pillow 경고 12건), CPU exact pin 이미지 빌드도 성공. 실학습 provenance를 고정하기 위해 구현·계획·결정을 먼저 커밋한 뒤 실험을 실행한다. 이는 mutation 검증용 커밋이 아니며 mutation은 수행하지 않는다.

- CPU exact pin 환경도 전체 34 passed. Python 3.12에서 2-worker DataLoader가 멀티스레드 fork 경고를 내므로 학습/평가 worker를 spawn으로 명시하고 smoke는 worker 0으로 고정한다. CUDA 초기화 후 fork도 피하는 동일 원인의 국소 보강이다.

- 전처리 검토 보강: 세로 원본에 square RandomResizedCrop을 바로 적용하면 fallback 중앙 crop이 면적 5% 제한을 벗어날 수 있다. SigLIP의 square resize 후 약한 crop을 적용하도록 순서를 수정하고 세로 이미지 회귀 가드를 추가했다.

### P02 실학습·평가 결과

- 최종 CPU 전체 **35 passed**(기존 dedup fixture Pillow 경고 12건만 잔존). spawn worker의 fork 경고는 사라졌다. Dockerfile의 torch/torchvision 버전 중복 선언을 제거하여 `requirements.txt` constraint로 CPU wheel을 선택한다.
- 구현 commit `37ba16a42e47d0a70f2f84be8309fe6a338669c6`에서 기존 metadata split 불변으로 10 epoch CUDA 학습. 이미지 6,000장 전부 경로 존재 확인. GPU 외부 compute 프로세스가 조회되지 않는 상태에서 시작했고 학습 중 약 1.8GB를 사용했다.
- best는 epoch 10(validation BCE 0.013387, ROC-AUC 0.999874). epoch 7/9의 validation 악화 때 이전 best를 보존함도 실제 실행에서 확인했다.
- Test A(800장): ROC-AUC 0.999937, Accuracy 0.995000. Test B(REAL 448 + unseen FAKE 600 = 1,048): ROC-AUC 0.999766, Accuracy 0.988550. category/generator/source별 지표와 PR-AUC·Precision·Recall·F1을 JSON에 보관했다.
- [실험 스냅샷](../../../experiments/p02_siglip_baseline/README.md): config, metadata SHA256, 구현 commit, checkpoint SHA256, 전체 학습/평가 지표. 바이너리와 전체 로그는 `checkpoints/baseline/`에 비추적 보관한다.
- P02 상태와 인덱스를 Complete로 함께 갱신. 이는 P02 실행 조건의 완료이며, 독립검증 합격 또는 최종 제품 성공을 의미하지 않는다. 현재 개발 평가의 수치 기준은 충족하나 단일 REAL source, GEN 근사중복 미점검, 별도 최종 holdout 미확보가 남는다.

### 현재 다음 작업

- P03 계획 작성 후 동일 split의 DINO baseline 비교.
- GEN pHash/embedding 점검과 최종 미사용 REAL/FAKE holdout 설계는 후속 범위. 신규 수집이나 기존 split 변경은 수행하지 않았다.

- 최종 산출물 점검: 실제 best checkpoint의 config가 baseline YAML과 동일하고 epoch 10임을 확인했다. checkpoint의 encoder 전체 tensor는 동일 revision의 pretrained 가중치와 값이 전부 일치한다(head만 학습됨). canonical constraint 기반 CPU 빌드와 버전 조회 성공, Compose config·변경 문서 링크·실험 표본 수·metadata hash·`git diff --check` 이상 없음.

## P03 — 후속 세션

### 목표·진행

- 소유자의 “이어서 진행”에 따라 P03 DINO baseline 학습·비교·primary 선정까지 진행한다.
- `docs/plan/phase_3_baseline_comparison.md`에 비교 조건과 결과 확인 전 선정 규칙을 기록하고 인덱스를 In Progress로 갱신했다.
- DINOv2-base adapter(CLS pooled feature, pretrained config 기반 차원), `model.normalization`의 train/val/evaluate 전달, `configs/dino.yaml`과 latency/크기 비교 CLI를 추가했다. 기존 SigLIP checkpoint의 필드 누락은 mean/std 0.5로 해석한다.
- 원본은 공식 DINO processor의 mean/std이며 configs가 실행값을 소유한다. checkpoint 및 실험 config는 스냅샷이다. 모든 소비 경로를 회귀 테스트로 확인한다.
- DINO 신규 가드 2건이 구현 전 각각 unknown encoder/정규화 인자 미지원으로 실패함을 확인했고 집중 6 passed. 전체 회귀는 진행 중이다.

### 선택·제외

- 동일 split/seed/학습 설정/MLP/224 square geometry로 비교한다. DINO의 native shortest-edge/center-crop 대신 공통 geometry를 사용하며 정규화는 pretrained 값에 맞춘다.
- primary 선정은 validation ROC-AUC 차이 ≥0.001이면 높은 모델, 미만이면 batch-1 GPU median latency 우선. 통계적 동등성으로 해석하지 않으며 Test 결과로 규칙을 변경하지 않는다.
- 독립 최종 holdout, GEN 근사중복 점검, calibration은 현재 작업 범위에서 제외한다. 모델 revision과 checkpoint 경로는 별도로 고정해 P02 결과를 보존한다.

### 다음 단계

- pretrained 로드와 전체 회귀 확인, GPU 여유 확인 후 DINO 10 epoch 학습·Test A/B 평가·latency 비교.

- 전체 CPU 회귀 **38 passed**(기존 Pillow 경고 12건). 불완전한 정규화 `{}`는 기본값으로 숨기지 않고 거부하며 필드 누락만 기존 기본값을 사용한다. 공식 DINO pretrained 로드 성공, revision `f9e44c814b77203eaa57a6bdbbd535f21ede1415`, 차원 768.

### P03 결과·검증

- 구현 commit `c6ab048`에서 DINO 10 epoch CUDA 학습, best epoch 10(validation BCE 0.015003, ROC-AUC 0.999772). P02와 metadata SHA256·공통 학습 설정 동일, P02 checkpoint/snapshot 보존.
- DINO Test A: AUC 0.999937 / Accuracy 0.996250. Test B: AUC 0.998618 / Accuracy 0.979008. 카테고리·generator·source별 지표와 config·checkpoint hash를 `experiments/p03_dino_baseline/`에 보관한다.
- 동일 RTX 3060에서 float32 batch 1, warmup 10·측정 100·CUDA 동기화로 비교: SigLIP median 9.633ms, DINO 12.407ms. parameter 93,475,585 vs 87,171,841, checkpoint 356.65 vs 332.61MiB. decode/전처리/HTTP는 측정 범위 밖이다.
- validation ROC-AUC 차이 0.000102 <0.001이므로 사전 latency 규칙으로 **SigLIP primary** 선정. DINO의 더 작은 모델 크기 tradeoff도 report에 보존. Test 결과를 보고 규칙을 변경하거나 추가 튜닝하지 않았다.
- 실제 DINO checkpoint의 config가 `configs/dino.yaml`과 동일하고 epoch 10임을 확인. encoder 전체 tensor는 같은 revision의 pretrained 원본과 일치한다. 최종 training 이미지 빌드 성공. CPU 전체 38 passed 및 최종 CUDA 집중 4 passed, 독립검증·mutation 미수행.
- [P03 비교](../../../experiments/p03_comparison/README.md)·원시 benchmark JSON·primary config 생성, P03/인덱스 Complete 동시 갱신. 현재 baseline 결과로는 §17 LoRA에 진입하지 않으며 P05 calibration이 다음 실행 대상이다.

### 후속 항목

- P05 계획/score calibration. 최종 제품 일반화는 별도 미사용 REAL/FAKE holdout과 GEN 근사중복 점검 후 확인해야 한다. 현재 지표는 개발 데이터 비교이며 전체 encoder 계열의 일반적 우열을 증명하지 않는다.

- 최종 확인: 변경 문서 링크, benchmark warmup/repeats/latency 표본 100개, 두 모델의 공통 training config·224 입력, metadata hash 불변, Compose config 및 `git diff --check` 통과. Tracepecter 학습/평가/비교 컨테이너 잔여 없음.

## P05 — 후속 세션

### 목표·구현

- 소유자의 진행 지시에 따라 primary SigLIP의 validation 기반 calibration·threshold·0~100 score 및 실제 이미지 scoring을 구현한다.
- P05 계획/인덱스 In Progress, config로 fitting 범위·반복·ECE bin을 고정. raw logit API를 추가하고 기존 probability/head/checkpoint 구조는 유지한다.
- provider 독립 수치 모듈 `src/calibration.py`, 실행 `src/calibrate.py`, 이미지 scoring `src/score.py`. checkpoint IO/hash helper는 기존 evaluate 경계에서 공유한다. 원본 checkpoint는 수정하지 않는다.
- temperature는 bounded log-T golden-section search, validation NLL 최소(1 포함하여 비악화). threshold는 validation balanced accuracy 최대로 고정. 동일 입력 score 결정성·checkpoint hash 결합·val-only fitting을 확인한다.
- validation prediction은 `image_id,logit`만 저장하고 label은 canonical metadata에서 읽는다. temperature/확률 threshold는 artifact가 소유하며 score와 score threshold는 유도한다.

### 검증·이슈

- 구현 전 신규 테스트는 calibration 모듈 부재로 실패. 집중 수치/model 7 passed, 전체 42 passed(기존 Pillow 경고 12건).
- 검토 보강: 단일 클래스에서도 정의되는 NLL/Brier/ECE를 fitting 검증과 묶어 거부하던 문제를 새 가드로 재현했다. fitting/threshold에는 양 클래스 조건을 유지하고 지표는 허용한다. 새로운 전체 검증 및 실데이터 실행은 진행 중이다.

### 결정·범위

- Test fitting은 하지 않는다. 현재 score는 REAL/Generated 라벨의 calibrated probability proxy이며 사람 체감 realism과의 일치는 별도 사람 평가가 필요하다.
- API/demo는 P07, 실패 분석은 P06. 독립 최종 holdout·GEN 근사중복은 미수행 후속 항목으로 유지한다.

### 다음 단계

- 최종 회귀·구현 commit 후 val 820 prediction 추출·calibration fitting·고정 Test A/B 평가·이미지 score 확인.

- 단일 클래스 지표의 신규 가드가 구현 전 정확히 재실패했고 보강 후 CUDA 집중 **10 passed**. 통합 테스트에서 test 이미지의 내용을 바꿔도 fitted temperature/threshold가 그대로인 점, val ID만 prediction에 포함되는 점, 동일 이미지 score 결정성, 잘못된 checkpoint/온도 거부를 확인했다.

### P05 실제 결과

- 최종 CPU 전체 **43 passed**(기존 Pillow 경고 12건), CUDA 집중 10 passed. 구현 commit `7a5cea1`에서 val 820 raw logit 추출 및 fitting.
- temperature 0.7984784236465634, probability threshold 0.6966991081858492 → score threshold 69.66991081858492. validation balanced accuracy 기준 threshold이며 Test로 재조정하지 않았다.
- Validation NLL 0.013387→0.012745, Brier 0.003519→0.003457, ECE 0.004870→0.004565. Test A 세 calibration 지표도 개선.
- **Test B NLL 0.027139→0.027630, Brier 0.007783→0.007925로 약간 악화**, ECE 0.011638→0.010769는 개선. 이 결과로 temperature를 다시 선택하지 않았으며 unseen calibration 개선으로 일반화하지 않는다. Threshold 적용 Accuracy는 Test A 0.995→0.99375(1건 하락), Test B 0.988550→0.989504(1건 상승).
- 실제 validation REAL score 96.8916108567802(photographic_like), Generated 0.00000508163371905043(synthetic_like). 같은 REAL 반복 scoring 결과 동일. 표본 2개로 전체 일반화를 판정하지 않는다.
- validation prediction ID 집합이 canonical val과 정확히 동일(820), metadata SHA256 불변, checkpoint SHA256이 P02 원본과 같음 확인. 최종 training 이미지 빌드 성공.
- [P05 기록](../../../experiments/p05_calibration/README.md)과 calibration/metrics/config/validation prediction 산출물 보관. P05/인덱스 Complete 동시 갱신. 기능·validation 결정의 완료이며 독립검증 또는 사람 체감 score 검증은 미수행이다.

### 현재 다음 작업

- P06 failure analysis 계획과 사례 분석. Test B calibration NLL/Brier 악화도 검토한다.
- GEN 근사중복·미사용 최종 REAL/FAKE holdout·사람 평가 확보는 후속 항목이다.

- 최종 재현: 저장한 validation CSV logit과 canonical metadata label만으로 temperature/threshold를 다시 계산해 artifact 값과 1e-12 이내 일치. 링크/Compose/diff 체크 정상, Tracepecter 실행 컨테이너 잔여 없음.

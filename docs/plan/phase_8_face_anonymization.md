# P08 — 공통 얼굴 익명화 재학습

**상태:** In Progress (2026-10-11 착수. 계획 독립검증 4라운드 합격, [기록](../verifications/2026-10-11/p08_plan_db06.md))

`docs/project.md` §27의 Phase 0~6 밖에서 [DB-06](../decision_briefs/DB-06_P06_face-exposure.md)(C, 2026-10-11)으로 생긴 페이즈다. 상위 사양은 `project.md` v1.4 §15(학습·평가 전처리), §22(추론 전처리), §23(데모 표시)이다. P07(API)은 이 페이즈가 정한 전처리 계약과 채택된 artifact를 쓴다.

## 목표

[P06-04](../../experiments/p06_failure_analysis/patterns/README.md)에서 확인한 두 단서를 학습·평가·추론의 같은 전처리로 없앤다.

- 얼굴이 보이면 GEN(얼굴이 보이는 비율: REAL 학습 0.4%, GEN 학습 64.5%)
- 흰 원이면 REAL(K-Fashion 익명화)

방법: 검출된 모든 얼굴에 K-Fashion과 같은 형태의 흰 원을 두 클래스 모두에 씌운다. 그 뒤 primary 모델을 다시 학습·calibration하고, 단서가 사라졌는지를 사전 고정한 규칙으로 판정한다.

## 선행 조건

- P06 Complete. DB-06 Resolved(C).
- 고정 입력:
  - `data/metadata.csv`(split 불변)
  - YuNet 모델(`/mnt/h/tracepector/checkpoints/face/face_detection_yunet_2023mar.onnx`, sha256 `8f2383e4…`)
  - baseline checkpoint `checkpoints/baseline/best.pt`(sha256 `151244…`)
  - P05 artifact `experiments/p05_calibration/calibration.json`
- 기존 baseline checkpoint·calibration artifact·P05/P06 산출물은 덮어쓰지 않는다.

## 범위·검증

1. **P08-01 원 규격·검출 관문 측정** (이미지만 사용, 모델 결과 없음)
   - 현재 상태: **Complete (2026-10-13)**. 학습 GEN 재현율 87/98(88.78%) 관문 통과, sd35 소유자 확인 반영 후 보고 전용 64/74(86.49%), 보조 크기 보고 포함. [전체 검증](../verifications/2026-10-13/p08_01_full_slice.md) 라운드 2 합격 확정([측정 기록](../../experiments/p08_anonymized/measure/README.md)).
   - 측정 전에 기준을 적고 커밋한다(`configs/anonymize_measure.yaml`): 표본 seed·크기, "맞췄다"의 기준, 판정 방법.
   - 원 모양·크기: REAL train 무작위 표본에서 확인된 원 150개 이상을 잰다. 방법은 순백 연결 성분에 타원을 맞춘 후보를 만들고, 사람이 모든 후보를 확인하며, 후보가 없는 표본의 누락도 일부 확인하는 것이다. 세부는 `configs/anonymize_measure.yaml`에 있다. Hough 검출기는 타원을 놓치므로 쓰지 않는다.
     - 지름 비율 k가 얼굴 상자 × [1.0, 1.6] 밖이어야 크기가 맞춰지면 관문 미통과다(얼굴을 덮지 못하거나 과대).
     - **측정 후 소유자 결정(2026-10-11)**: 분포 맞춤 k=0.646은 얼굴보다 작으므로 쓰지 않고, `configs/anonymize.yaml`의 k=1.2를 사용한다. 사전 크기 관문 실패는 그대로 보존하며, P08-03에서 원 크기 단서를 별도 진단한다. 사전 고정 `configs/anonymize_measure.yaml`은 바꾸지 않는다.
     - 크기는 이미지 너비 대비로 잰다. 맞춤 기준은 이 척도에 적용한다. 보조 척도로 사람 영역 대비 크기도 보고한다: REAL은 K-Fashion 부위 rect 합집합 높이, GEN은 rect가 없으므로 측정 표본에서 사람 영역을 손으로 표시한다. 보조 척도에는 관문을 두지 않는다. 방법은 `anonymize_measure.yaml`에 적는다.
     - 맞춤 기준: 합성 원 크기 분포의 1사분위·중앙값·3사분위가 각각 REAL의 ±15% 안이어야 한다. 타원 비율이 20% 이상이면 REAL 축비 분포에서 뽑은 타원을 쓴다.
   - 경계 질감: REAL 원 경계의 번짐 폭(순백에서 배경까지의 전이 픽셀 수)을 잰다. 합성 원도 같은 폭으로 경계를 처리하고, 전이 폭 중앙값이 REAL의 ±1px 안이면 맞춘 것으로 본다(GEN은 PNG라 경계가 선명하다).
   - YuNet 재현율 관문:
     - 학습 GEN 무작위 150장 이상(seed 고정)에 "사람이 보기에 얼굴이 보이는가(측면·부분 포함, 눈·코·입 중 둘 이상)"를 표시한다.
     - 표시는 블라인드로 한다(검출 상자를 보지 않음). 에이전트가 전수 1차 표시하고, 소유자가 불일치와 무작위 20%를 확인한다.
     - 검출 설정은 P06-02c와 같다(score 0.9, 최소 크기 너비 × 0.04). 바꾸면 새 표본에서 다시 잰다. test GEN(sd35)도 같은 방식으로 따로 보고한다.
     - **관문**: 보이는 얼굴 재현율 점추정이 80% 이상이고 양성 표본이 80장 이상이면 통과다. Wilson 구간도 함께 보고한다.
     - 양성이 80장 미만이면 같은 seed 순서로 표본을 50장씩 늘려 표시한다(최대 400장). 그래도 미달이면 관문 미통과다.
     - 관문 미통과면 P08-04 전에 소유자에게 검출 보강 여부를 묻는다.
   - REAL 원 위 검출: 기존 흰 원이 있는 REAL에서 YuNet이 원 근처에 얼굴을 잡는 비율을 잰다.
2. **P08-02 익명화 전처리 모듈**(`src/anonymize.py`, config `configs/anonymize.yaml`)
   - 현재 상태: **Complete (2026-10-13)**. [독립검증 합격](../verifications/2026-10-13/p08_02_anonymize_module.md), 비차단 H1·H2 회귀 보강·변이 재실패 확인([작업 기록](../daily_logs/2026-10-13/work_log.md)). [전처리·캐시 계약](../../experiments/p08_anonymized/README.md).
   - 학습·평가·추론이 같은 함수를 쓴다. 검출된 얼굴은 모두 가린다(여러 명이면 전부).
   - 익명화는 증강(`src/dataset.py`의 transform)보다 먼저 원본 이미지에 적용한다.
   - 얼굴이 기존 원과 겹쳐도 같은 규칙으로 칠한다(추론 경로에는 원 검출기가 없으므로 예외를 두지 않는다).
   - 학습·평가용 얼굴 좌표 캐시(계보는 아래 계약 절)와 즉시 검출 경로의 결과가 같아야 한다.
   - 검증:
     - 캐시 경로와 즉시 경로의 결과 일치, 결정성
     - 캐시 행 누락·해시 불일치 거부
     - 얼굴 없는 이미지는 그대로 통과
     - 여러 얼굴 모두 칠함, 겹침 규칙
     - checkpoint 결합 계약(아래)의 양방향 셀:
       - 키 없는 legacy checkpoint는 평가 도구에서 원본 입력으로 동작한다.
       - 키가 있는데 내용·sha256이 틀리면 거부한다.
       - score CLI와 API는 키가 없거나 `null`이어도 거부한다.
       - 키가 `null`인 checkpoint는 평가 도구에서 원본 입력으로 동작한다.
       - 새 학습 config에 키가 없으면 거부한다.
3. **P08-03 진단·채택 규칙 사전 고정** — 학습 결과를 보기 전에 config(`configs/anonymized_diagnostic.yaml`)를 커밋한다.
   - 현재 상태: **Complete (2026-10-13)**. [독립검증 라운드 2 합격](../verifications/2026-10-13/p08_03_diagnostic_preregistration.md), 차단·비차단 모두 보강. [진단 계약·표본](../../experiments/p08_anonymized/diagnostic/README.md)은 재학습 결과 전에 커밋됐다. 실제 진단 실행기는 P08-06에서 구현한다.
   - 2×2 평가: {baseline, 새 모델} × {원본 입력, 익명화 입력}에서 val·Test A·Test B 지표를 낸다. 재학습 효과와 입력 변화 효과를 나눠 보기 위해서다.
   - 단서 진단:
     - (a) P06-04 집계를 새 모델에 다시 돌린다. GEN 오류가 얼굴 상태(익명화됨 / 얼굴 없음 / YuNet이 놓친 측면 얼굴)에 몰리는지 본다. 놓친 얼굴은 익명화 뒤 더 강한 GEN 단서가 될 수 있으므로 따로 센다.
     - (b) REAL의 원래 흰 원을 합성 원으로 바꿨을 때의 score 변화(원 모양 단서가 남았는지)
     - (c) P06-02c 개입 실험의 새 모델판: 익명화된 GEN 얼굴의 원을 회색으로 바꾸거나 제거했을 때의 score 변화(흰색·가림 의존이 남았는지)
     - (d) 원 크기 단서(소유자 결정 2026-10-11): REAL의 기존 원을 GEN의 k=1.2 원 수준으로 키웠을 때 score 변화. 표본·확대 규칙·구간 판정은 P08-03 config에서 학습 결과 전에 고정한다. 기존 원을 줄이거나 가려진 얼굴을 복원하지 않는다.
   - "단서 해소" 판정 규칙(구간 기준)은 이 config에서 정한다.
   - **primary 채택 규칙(소유자 결정 2026-10-11)**:
     - 새 모델이 §20 기준(Standard Test ROC-AUC ≥ 0.90, Unseen ≥ 0.80)을 익명화 입력에서 만족하고, "단서 해소" 판정을 받으면 `configs/primary.yaml`을 교체한다.
     - 아니면 primary를 교체하지 않고(baseline artifact 그대로) 소유자에게 보고한다. 이 경우 **P07은 대기하고 P08을 다시 시도**한다(검출 보강·원 규격 조정). 재시도도 미채택이면 그때 소유자에게 다시 묻는다(소유자 결정 2026-10-11, Q5). §22(모든 추론에 익명화)는 바꾸지 않는다.
4. **P08-04 재학습**
   - 현재 상태: **Complete (2026-10-13)** — 10 epoch·best epoch10, [독립검증 라운드 2 합격](../verifications/2026-10-13/p08_04_anonymized_training.md)·H1까지 보강([학습 기록](../../experiments/p08_anonymized/training/README.md)). 다음은 P08-05다.
   - `configs/anonymized.yaml`은 `configs/primary.yaml`과 같은 설정(SigLIP frozen + MLP, 10 epoch, seed 42)에 익명화 규격만 더한 것이다.
   - checkpoint는 `checkpoints/anonymized/`에 저장한다.
   - baseline 비교값은 기존 checkpoint를 다시 평가해 얻는다(재학습하지 않음). 학습 결정성은 입증되지 않았다(테스트 stub 비결정성 V1).
5. **P08-05 재calibration** — P05 절차를 `configs/calibration_anonymized.yaml`로 실행하고, 결과는 `experiments/p08_anonymized/calibration/`에 둔다. `configs/calibration.yaml`(P05 artifact 경로)은 쓰지 않는다. 검증: P05와 같은 회귀 가드.
   - 현재 상태: **Complete (2026-10-19)** — [독립검증 라운드 2 합격](../verifications/2026-10-19/p08_05_anonymized_calibration.md) — temperature 0.968747, 확률 threshold 0.383150([calibration 기록](../../experiments/p08_anonymized/calibration/README.md)).
6. **P08-06 진단 실행·채택 판정** — P08-03 config를 그대로 실행하고 사전 규칙으로 판정한다. 채택되면 `configs/primary.yaml`과 HANDOFF·README를 갱신한다.
   - 현재 상태: **In Progress (2026-10-20, 독립검증 대기)** — 최종 얼굴 상태 고정 후 2×2·개입·얼굴 상태 집중을 실행했다. 사전 관문 전부 통과(Test A AUC 0.999867 / Test B 0.999647), 익명화 primary를 반영했다([진단·채택 기록](../../experiments/p08_anonymized/diagnostic/README.md)). CLI 재개 exit 0·결과 byte 동일. 소유자가 별도 에이전트 검증을 승인했으며 아직 독립검증 합격은 아니다.
7. **P08-07 얼굴이 보이는 실사 평가 holdout 설계** — K-Fashion 밖 출처·라이선스·규모를 정한다. 출처 선택은 결정 브리프로 올린다. **P07의 관문이 아니다**(소유자 결정 2026-10-11: 측정 결과는 준비되는 대로 사후 보고).

## 계약·소유권

- **익명화 규격의 소유자는 `configs/anonymize.yaml`이다.** 검출기 모델 경로·sha256, score threshold, 최소 크기, 원 모양·크기 비율, fill, 경계 처리를 담는다.
  - 구현 시 `docs/sot.md` §2에 소유 행을 추가한다.
  - `configs/face_mask_ci.yaml`의 검출기 블록은 P06-02c의 고정된 진단 스냅샷이다. 필요해서 생긴 중복이므로 고치지 않는다.
- **checkpoint 결합**: 학습 시 checkpoint에 저장되는 config에 익명화 규격 내용 전체와 그 sha256을 넣는다. 평가·calibration·score·API 같은 하류는 checkpoint에 저장된 규격만 쓴다. fail closed 규칙은 키의 유무로 나눈다.
  - 새 학습 config는 익명화 키를 반드시 적는다(규격, 또는 명시적 `null`). 키가 없으면 학습을 거부한다.
  - 키가 있는데 내용·sha256이 맞지 않거나 YuNet 파일 sha256이 다르면 모든 하류가 거부한다.
  - 키가 없는 legacy checkpoint(기존 baseline·DINO)와 키가 `null`인 checkpoint는 평가·calibration 도구에서만 원본 입력으로 동작한다. 익명화 입력으로 평가하려면 규격을 명시적으로 넘겨야 한다.
  - score CLI와 API는 키가 없거나 `null`인 checkpoint도 거부한다(§22: 모든 추론은 익명화).
  - 이 규칙을 구현하는 커밋에서 HANDOFF·README의 baseline score 실행 예시도 함께 고친다(baseline은 키가 없어 score CLI에서 거부된다).
- **얼굴 좌표 캐시**: `experiments/p08_anonymized/face_boxes.csv`(Git 추적)로 둔 파생 artifact다.
  - 키: `image_id`, 이미지 sha256, 검출기 sha256, 검출 파라미터 해시
  - 값: 얼굴 상자 목록. 얼굴이 없는 이미지도 빈 목록 행으로 남겨 "검출 안 함"과 "얼굴 없음"을 구분한다.
  - 행이 없거나 키가 다르면 거부한다. `data/metadata.csv`에 열을 추가하지 않는다.
- **추론 계약 세부**(P07에서 구현, 이 페이즈에서 확정):
  - YuNet 누락·불일치 시 점수를 내지 않는다.
  - 응답에 가린 얼굴 수(`faces_anonymized`)를 넣는다(§23 데모 표시용).
  - `model_version`은 checkpoint·calibration artifact·익명화 규격의 sha256 조합을 식별한다.

## 완료 조건

- P08-01 측정 기록, 원 규격 고정, 재현율 관문 통과(또는 소유자 결정).
- 익명화 모듈의 경로 일치·결정성·거부 계약 회귀 테스트.
- P08-03 config가 P08-04 결과보다 먼저 커밋되어 있을 것(git 순서로 확인).
- 새 checkpoint·calibration artifact와 2×2 지표 표.
- P08-06 사전 규칙 판정과 채택/유지 결과 반영.
- 슬라이스별 독립검증 합격.
- 한계를 명시: 얼굴이 보이는 실사에서의 FN은 P08-07 holdout 없이는 측정할 수 없다.

## 제외·병행

- 제외: split 변경, 신규 데이터 수집(P08-07은 설계만), encoder 변경, LoRA(P04 조건 불변), DINO 재학습.
- 병행 가능: P08-07 설계, GEN 근사중복 점검.
- GPU 작업은 소유자의 다른 작업 점유가 낮을 때만 하고 큐잉하지 않는다(2026-10-11 기준).

## 관련 결정 브리프

- [DB-06](../decision_briefs/DB-06_P06_face-exposure.md) — Resolved: C(공통 흰 원 익명화 + 얼굴 노출 실사 평가 holdout).
- [DB-03](../decision_briefs/DB-03_P01_face-policy.md) — DB-06이 A(무처리)를 대체한다.

# P08-03 진단·채택 규칙 사전등록

상태: **Complete (2026-10-13)**. [독립검증 라운드 2 합격](../../../docs/verifications/2026-10-13/p08_03_diagnostic_preregistration.md), 차단 B1~B3·비차단 H1~H2 모두 해결. [P08 계획](../../../docs/plan/phase_8_face_anonymization.md) §P08-03이 범위를 소유하고 [configs/anonymized_diagnostic.yaml](../../../configs/anonymized_diagnostic.yaml)이 표본·개입·판정 규칙의 정본이다. 새 모델 학습·예측·calibration은 실행하지 않았다.

## 범위·실행 순서

이 슬라이스는 config·표본 명세·입력 해시를 사전 고정한다. 진단 모델 실행기는 P08-06에 구현한다. P08-04는 사전등록 config/manifest 커밋 이후에만 시작하고, P08-06은 이 규칙을 바꾸지 않고 실행한다. 결과를 본 뒤 표본·허용폭을 바꾸면 같은 실험의 판정으로 취급하지 않는다. 재시도는 새 사전등록·이유·커밋을 남긴다.

```bash
docker compose run --rm -T dev python -m scripts.p08_preregister
```

선택된 REAL 기하는 width/cx/cy/major/minor/angle이 모두 유한한 숫자여야 하고 width·두 축은 양수, major≥minor여야 한다. 화면 가장자리의 음수 중심은 허용한다. 잘못된 기하는 출력 전에 거부한다.

재생성은 동일 바이트일 때만 허용한다. 다른 입력·config로 기존 파일을 덮어쓰는 것은 거부한다. 동일 커밋의 config·입력 raw-byte 해시는 `preregistration.json`에 있고 3개 CSV의 해시도 함께 보존한다. 입력 파일의 줄바꿈도 해시에 포함한다. CSV는 LF다. 주석 완성 파일 `face_review.csv`는 빈 양식과 다른 파일이며 예측 전 커밋·해시 고정이 필요하다.

## 2×2 평가

baseline(P05 artifact의 checkpoint)·candidate(P08-05 artifact의 checkpoint) 각각에 원본·익명화 입력을 적용해 val·Standard Test A·Unseen Test B를 평가한다. Test B는 Standard test REAL을 재사용하며 train/val REAL을 섞지 않는다. 동일 Test REAL은 서로 독립적인 두 표본으로 간주하지 않는다.

각 모델의 temperature·probability threshold는 자신의 artifact 값으로 고정하고 양 입력에 동일하게 적용한다. 원본/익명화 조건별로 다시 fitting하거나 최적 threshold를 고르지 않는다. checkpoint·artifact·익명화 snapshot/YuNet·cache 이미지 hash를 모두 검증한 뒤 조건을 구성한다. 원본 입력 비교는 offline 진단 전용 bypass이며 checkpoint 규격 검증을 없애거나 score/API의 익명화 필수 계약을 완화하지 않는다. 새 모델의 원본 입력 경로는 P08-06 실행기에서 제공한다.

각 조합에 ROC-AUC·PR-AUC·accuracy·precision·recall·F1·NLL·Brier·ECE(10 equal-width bins)를 보고하고 generator·category·source_domain별 분해도 보존한다. 채택 AUC는 candidate의 익명화 Test A/B 값만 쓴다. ROC/PR 계산은 기존 `src.evaluate` 계약을 유지한다.

## 표본·주석

- **REAL 개입**: P08-01에서 확인한 원 150개·149장, 전부 train이다. 선택은 이미지 측정에 근거하며 모델 결과와 무관하다. 원 기하의 정본은 candidates CSV이고 confirmed 값의 정본은 review CSV다. 같은 이미지의 모든 원을 함께 편집하고 한 번 예측해 이미지 단위로 bootstrap한다. 여러 원을 독립 이미지처럼 세지 않는다.
- **GEN 개입**: test/test_unseen에서 하나 이상 검출된 이미지, generator 정렬 후 image_id 정렬·`random.Random(seed)`의 순차 shuffle·generator별 처음 최대 40장. 생성기 순서는 고정되고 부족한 생성기는 전부 포함한다. 각 이미지의 **모든 캐시 얼굴**을 처리한다. 선택 결과는 162장(playground_25·qwen_image_21·sd35_medium·sdxl 각 40, z_image_turbo 2)이다. 선정은 예측과 무관하다.
- **얼굴 상태 진단**: 모든 test/test_unseen GEN 952장. 원본과 익명화본을 함께 보고 원본에서 보이는 얼굴 수와 익명화 후 남은 얼굴 수를 표시한다. 눈·코·입 중 둘 이상이 보이는 부분·측면 얼굴도 포함한다. 검출 수만으로 상태를 대체하지 않는다.
- 에이전트가 전수 표시하며, 소유자는 원본 보임 수와 검출 수가 다르거나 남은 얼굴이 하나 이상인 경우를 전부 확인한다. 나머지에서는 seed로 image_id 정렬·shuffle 후 `ceil(0.20*n)`을 확인한다. 소유자 값이 최종 우선한다. 최종 `confirmed=1`은 전체 확인 절차 충족을 뜻하며 소유자가 모든 이미지를 직접 표시했다는 뜻은 아니다. 952개의 고유 ID를 빠짐없이 포함하고 두 얼굴 수는 정수이며 `0 ≤ uncovered_visible_faces ≤ visible_faces`여야 한다. 주석/소유자 확인 목록과 해시는 예측 전에 고정한다.
- 상태 우선순위: 남은 얼굴 ≥1이면 `missed_visible_face`(일부 가림·검출 오인도 포함); 원본 보임 수=0이면 `no_visible_face`; 원본 보임 수>0이고 남은 얼굴=0이면 `anonymized`. 사람이 보기에 얼굴이 남아 있는데 다른 사람만 검출된 경우를 익명화 완료로 처리하지 않는다.

## 개입 기하·순서

모든 reference는 해당 이미지의 정상 익명화 입력이다. REAL shape/size variant는 **정상 익명화 RGB** 위에 confirmed 기존 원만 추가 overlay하여 다른 위치의 모든 YuNet 마스크도 보존한다. GEN gray/restore variant만 원본 RGB에서 구성한다. 각 variant에는 checkpoint의 resize·정규화만 적용한다. 증강은 없다. variant를 만든 뒤 일반 익명화 함수를 다시 호출하면 회색/복원 조건이 흰 원으로 되돌아가므로 재적용하지 않는다. snapshot·파일 검증은 variant에서도 생략하지 않는다.

- (b) **real_shape**: 기존 타원을 포함하는 원을 동일 중심에 덧칠한다. 반지름 = 측정 장축/2 + edge guard. 기존 익명화 영역을 줄이거나 숨겨진 얼굴을 복원하지 않는다. fill·Gaussian alpha·좌표 반올림은 checkpoint 익명화 커널과 같다.
- (d) **real_size**: 같은 중심에서 반지름 = `max(real_shape 반지름, width*GEN 목표 지름비/2 + edge guard)`. 목표 비율은 P08-01 `report.json`의 `synthetic.selected_size.synthetic_quartiles[1]`(k=1.2 GEN 중앙값, **0.1631602984208327**)이다. 이 측정은 당시 대표 얼굴 표본에서 유도된 값이며 새 전체 얼굴 캐시에서 재추정하지 않는다. 절대 목표 크기·원별 실제 확장비·이미지 경계 clipping을 보고한다. 이미 큰 원은 축소하지 않고 그대로 두며 해당 개입의 확장 없는 이미지 수를 보고한다.
- edge guard = `3*checkpoint edge_sigma + 1px`(현재 2.5px). 흰 overlay가 원본 픽셀을 복원하지 않으므로 기존 익명화 영역은 유지된다. Gaussian·OpenCV rasterization·round 규칙은 P08-02 커널과 동일하다. 여러 원은 candidate_id 순으로 칠한다.
- (c) **gen_gray**: 정상 익명화와 같은 모든 얼굴 좌표·원 기하·σ로 원본에서 `[128,128,128]`을 칠한다.
- (c) **gen_restore**: 해당 원본 GEN 이미지를 사용해 합성 원을 제거한 대조를 만든다. 새로운 face restoration/inpainting은 하지 않는다.

REAL shape와 size를 분리해 같은 중심의 모양/경계 변화와 추가 면적 변화의 효과를 각각 reference 대비 보고한다. 기존 REAL에 얼굴 정보가 없으므로 GEN 복원 대조와 동등한 얼굴 정보 실험은 할 수 없다.

## 판정 계산

단서 진단(a/b/c/d)은 candidate checkpoint·calibration만 사용한다. baseline은 2×2 비교에 사용한다.

**얼굴 상태 집중(a)**: GEN 전체의 FP rate를 세 상태에서 집계한다. 세 쌍 각각의 rate 차이에 Wilson 기반 Newcombe 독립 두 집단 차이 95% 구간을 사용한다. 각 상태 최소 20장이고 모든 차이 구간이 닫힌 범위 `[-0.10, +0.10]` 안이면 통과한다. 상태 부재·주석 미완료·표본 부족은 미확정이다. generator별 수·FP rate도 보고하되 통과 표본을 만들기 위해 합치거나 사후 상태를 바꾸지 않는다.

Wilson 구간은 반올림 전 값을 사용한다. Newcombe: rate `p1,p2`, 각각의 Wilson `(L1,U1),(L2,U2)`에 대해 하한은 `p1-p2-sqrt((p1-L1)^2+(U2-p2)^2)`, 상한은 `p1-p2+sqrt((U1-p1)^2+(p2-L2)^2)`이며 [-1,1]로 제한한다. confidence 0.95의 표준정규 분위수를 사용한다.

**개입(b/c/d)**: 각 조건마다 최소 80개 고유 이미지가 필요하다. 두 관문을 모두 만족해야 통과한다.

1. 이미지별 `abs(variant score-reference score)`를 구해 평균을 내고, seed 고정·20,000회 이미지 bootstrap의 양측 percentile 95% 구간 상한이 **5점 이하**인지 확인한다. n개 이미지 인덱스를 복원추출해 각 resample에 n개를 뽑으며 **반복 인덱스를 허용**한다. 같은 이미지의 여러 원은 공동 편집·한 예측으로 고정하고 원별로 독립 추출하지 않는다. 각 조건에서 image_id 정렬 후 `numpy.random.Generator(numpy.random.PCG64(seed))`를 초기화하고 `integers(0, n, size=(20000, n))`로 행별 추출 인덱스를 만든다. `numpy.percentile(..., [2.5, 97.5], method="linear")`로 구간을 계산한다. 같은 표본군의 조건은 같은 seed로 같은 bootstrap 추출을 사용한다. 서로 다른 표본군 사이에는 paired 추출이라고 주장하지 않는다. signed 평균·분포·generator 분해도 별도로 보고한다.
2. reference에서 맞았으나 variant에서 틀린 이미지 수를 전체 개입 이미지 수로 나눈 위험에 Wilson 양측 95% 구간을 구하고 상한이 **0.05 이하**인지 확인한다. 오답 전환 0개라도 Wilson 상한은 양수이므로 작은 표본을 확신으로 처리하지 않는다. 반대 전환도 보고하되 관문에서 상쇄하지 않는다.

허용 경계는 포함한다. NaN/무한대·필요 예측 누락·중복 이미지·표본 부족은 미확정이며, 일부 유효 표본만으로 통과시키지 않는다. 신뢰구간이 허용폭을 벗어나면 관문 실패다. 이것은 ‘유의차 없음’ 판정이 아니라 고정 허용폭 안에 구간이 들어가는 운영상 등가성 기준이다. 5점·5%·10%p는 P08 개발 진단용 허용폭이며 사용자 체감·외부 holdout에서 검증된 한계값은 아니다. 다중 비교는 모두 통과해야 하는 교집합 관문으로 운영하며 각 95% 구간을 가족 전체의 동시 95% 구간이라고 주장하지 않는다.

## 채택·한계

candidate 익명화 입력의 Test A ROC-AUC ≥0.90·Test B ≥0.80(`project.md` §20)을 만족하고 **face_concentration·real_shape·real_size·gen_gray·gen_restore 전부 통과**하면 P08-06에서 primary 교체·소유자 보고를 수행한다. 미확정도 채택하지 않는다. 실패하면 기존 baseline artifact를 유지하고 P07은 대기, P08을 재시도한다. 재실패면 소유자에게 다시 묻는다(Q5). 재학습 결과를 보고 허용폭을 넓히지 않는다.

REAL 개입은 학습 표본으로 일반화 증명이 아니고 기존 모양이 거의 원형이라 shape 효과는 제한적이다. GEN은 검출된 얼굴만 개입할 수 있으며 z_image_turbo 표본 2장은 generator별 등가성 근거가 아니다. 얼굴 상태·generator가 교란될 수 있으므로 집중 집계만으로 인과적 단서 해소라고 주장하지 않고 개입 관문과 함께 판단한다. 얼굴이 보이는 실사의 FN은 P08-07 외부 holdout 없이는 측정할 수 없다. 이 holdout은 P07 관문이 아니다.

`src.failure_analysis`·`scripts.p06_patterns`·`EditedDataset`을 새 모델에 그대로 실행하면 일부 경로가 원본 입력이나 기존 대표 얼굴 규칙을 사용한다. P08-06은 이 사전등록 계약을 구현한 별도 실행기를 사용하고, 기존 P06 파일과 artifact는 덮어쓰지 않는다.

## P08-06 얼굴 상태 확인 (2026-10-20)

소유자 다운로드 301행은 얼굴 수가 아니라 눈·코·입의 개수로 표시한 값이었다(소유자 확인). 받은 바이트는 `face_review_owner_features.csv`로 그대로 보존했다. 얼굴 기준은 바꾸지 않고, 보이는 요소 0~1개는 얼굴 0개, 2~4개는 얼굴 1개로 변환한 `face_review_owner.csv`를 기존 merge 입력으로 사용했다. 요소 2개인 20장과 에이전트가 여러 얼굴로 표시했던 소유자 확인 대상 2장은 원본·익명화 쌍으로 시각 확인했다. 여러 얼굴의 요소를 합산하는 일반 변환 규칙은 아니며, 이번 소유자 표시의 대상 인물에만 적용한 변환이다.

소유자 변환값으로 에이전트 45행이 바뀌었고, 최종 952행은 익명화 607 / 얼굴 없음 237 / 남은 얼굴 있음 108이다. 소유자가 직접 본 범위는 301장이며 나머지는 기존 에이전트 주석이다. 원본·변환본·최종본 및 선행 주석/확인 목록의 해시는 `face_review_lock.json`으로 고정한다. 이 파일들과 최종 주석을 커밋하기 전에는 candidate 진단 예측을 실행하지 않는다.

## P08-06 실행기

`src/diagnostic.py`는 고정 확률·주석에서 Wilson/Newcombe 구간, paired bootstrap, 채택 여부를 계산한다. `scripts/p08_diagnostic.py`는 입력·checkpoint·snapshot·주석/HEAD 바이트를 검증하고 원본/익명화 2×2와 네 개입을 실행한다. 모델별 fitting 값은 원래 calibration artifact에서 읽으며 다시 최적화하지 않는다. 기존 익명화 커널은 `src/anonymize.py`의 `paint_circles`를 공유한다. 일반 score 경로의 규격 검증은 그대로다.

```bash
docker compose --profile training run --rm -T train \
  python -u -m scripts.p08_diagnostic --device cuda
```

예측은 모델·조건별 `baseline_*.csv`/`candidate_*.csv`의 이미지 ID·logit으로 저장하고 배치마다 flush/fsync한다. 마지막 불완전 행만 복구하여 재개하며 중복·다른 cohort·비유한 logit은 거부한다. `execution.json`은 사전등록·주석 고정 커밋·calibration·checkpoint·실행 코드·라이브러리·device를 결합하므로 다른 실행의 예측을 섞지 않는다. `result.json`은 2×2 전체/분해 지표, 다섯 관문, 채택 판정, REAL 원별 목표 크기·실제 확장·경계 clipping과 크기 개입에서 확장 없는 이미지 수를 보존한다. 원본·회색·복원 입력 모두 이미지/cache hash를 검증한다.

주석과 설정은 입력 정본이고, logit은 모델 예측 원자료다. 확률·score·FP·지표·판정은 이 정본에서 유도하는 보고용 projection이다. checkpoint/calibration, split, §20 기준, 진단 허용폭을 바꾸지 않는다. Bootstrap은 사전 고정된 20,000×n 복원추출로 O(20,000n) 시간·공간이며 n은 REAL 149 / GEN 162로 제한된다.

## P08-06 진단 결과 (2026-10-20)

**추가 감사 주의:** [테스트 누출 적대적 감사](../leakage_audit/README.md)에서 같은 룩의 train/test·train/val 교차를 최소8쌍 확인했다. 아래 AUC와 사전 관문 계산은 재현되지만, 누출 없는 독립 성능으로 해석할 수 없다. 기존 artifact와 split은 수리하지 않았다.

사전 규칙 판정은 **채택**이다. Test A/B AUC 기준과 다섯 단서 관문을 모두 통과하여 `configs/primary.yaml`을 익명화 모델로 전환했다. [독립검증 및 B1 보강 추적검증도 합격](../../../docs/verifications/2026-10-20/p08_06_diagnostic.md)하여 P08-01~06을 Complete로 표시한다. 기존 baseline checkpoint·calibration은 비교용으로 보존한다.

### 2×2 비교

모델별 temperature·threshold는 원래 artifact 값으로 고정했다. 아래는 val/Test A/Test B ROC-AUC이며, 전체 지표와 category/generator/source 분해는 `result.json`에 있다. Test A 800장, Test B 1,048장은 REAL 448장을 공유한다.

| 모델 | 입력 | val AUC | Test A AUC | Test B AUC | Test A accuracy | Test B accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | original | 0.999874 | 0.999937 | 0.999766 | 0.993750 | 0.989504 |
| baseline | anonymized | 0.998202 | 0.998998 | 0.995919 | 0.982500 | 0.938931 |
| candidate | original | 0.999693 | 0.999880 | 0.999717 | 0.996250 | 0.985687 |
| candidate | anonymized | 0.999796 | 0.999867 | 0.999647 | 0.993750 | 0.983779 |

기존 모델에 익명화만 적용하면 Test B accuracy가 0.989504 → 0.938931로 떨어지지만, 익명화 재학습 모델은 0.983779이다. 새 모델이 무처리 baseline보다 모든 지표에서 개선됐다는 주장은 하지 않는다. 채택은 사전 AUC 기준과 단서 관문으로 판정했다.

### 단서 관문

| 개입 | 이미지 | 평균 절대 score 변화 | 평균 절대 변화 95% 구간 | 맞음→틀림 | 전환 위험 95% 상한 | 판정 |
| --- | --- | --- | --- | --- | --- | --- |
| real_shape | 149 | 0.0905점 | [0.0460, 0.1518]점 | 0 | 2.513% | 통과 |
| real_size | 149 | 1.0526점 | [0.3640, 1.9466]점 | 0 | 2.513% | 통과 |
| gen_gray | 162 | 0.4407점 | [0.0981, 0.9322]점 | 0 | 2.316% | 통과 |
| gen_restore | 162 | 0.8474점 | [0.1332, 1.8535]점 | 0 | 2.316% | 통과 |

절대 score 변화의 구간 상한은 모두 5점 이하이며, 맞음→틀림 위험 구간 상한도 5% 이하이다. 0건 관측을 위험 0으로 확정하지 않았다. REAL 크기 개입은 149장 중 8장에서 추가 확장이 없었고, 원별 실제 크기·확장비·경계 clipping은 `result.json.geometry`에 보존했다.

| 얼굴 상태 | 이미지 | GEN→REAL 오류 | FP rate |
| --- | --- | --- | --- |
| anonymized | 607 | 10 | 1.647% |
| no_visible_face | 237 | 5 | 2.110% |
| missed_visible_face | 108 | 5 | 4.630% |

세 쌍의 FP rate 차이 95% 구간은 모두 사전 허용폭 ±10%p 안에 들어 얼굴 상태 집중 관문도 통과했다. 익명화됨 대 남은 얼굴 있음의 구간은 [-8.784, -0.017]%p로 0을 포함하지 않는다. 따라서 ‘차이가 없다’가 아니라 **사전 운영 허용폭 안**이라는 판정이다. generator·얼굴 상태의 교란, 얼굴이 보이는 실사 holdout 미평가, REAL 학습 표본 개입, z_image_turbo 개입 2장의 한계는 유지한다.

### 실행·재현 확인

- 구현 커밋 `1102343`, 최종 주석 고정 커밋 `0c4eb6e`. 2,369개 고유 입력 이미지(평가 2,220 + REAL 개입 149)와 모든 결합 해시를 검증했다.
- GPU 실행은 이 머신의 RTX 3060에서 수행했다. 시작 전 1,044MiB·7%로 다른 연산 점유가 낮았다. 실행 identity는 `execution.json`, 8개 예측 CSV의 해시는 `result.json.prediction_sha256`에 있다.
- 처음 `setsid --wait` 래퍼가 결과 저장 후 `wait: Success`·exit 1을 남겼다. Docker daemon이 직접 관리하는 detached 컨테이너로 재개하여 Python CLI exit 0(`cli_exit_code.txt`)을 확인했다. 예측을 다시 하지 않고 저장된 CSV를 읽었으며 재생성한 `result.json`은 최초 결과와 byte 동일했다.
- 저장된 8개 CSV의 SHA-256·고유 ID·cohort 완전성을 확인하고, 원자료에서 bootstrap과 Wilson 상한을 별도 수식으로 재계산했다. 상태별 FP도 다시 집계했다. P08-05의 candidate 익명화 Test A/B AUC·accuracy와 일치하며 NLL 차이는 최대 4.3e-12다.
- 단위/통합/채택 연결 테스트와 전체 CPU suite를 실행했다. 상세 명령·결과는 [작업 기록](../../../docs/daily_logs/2026-10-20/work_log.md). 구현자의 자가 검증이며 독립검증 합격을 뜻하지 않는다.

- 독립검증: 원자료·2369개 이미지·기하·모든 구간을 재계산해 일치했다. B1(calibration 실제 계산 회귀 경계 누락)을 보강했고, M7~M12가 guarding cell에서 모두 재실패했다. 최종 전체 CPU는 209 passed / 1 skipped(실제 YuNet 학습 opt-in), [검증 기록](../../../docs/verifications/2026-10-20/p08_06_diagnostic.md) 참고.

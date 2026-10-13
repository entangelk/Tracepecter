# P08-03 진단·채택 규칙 사전등록

상태: 사전등록 구현·자가 확인, 독립검증 대기. [P08 계획](../../../docs/plan/phase_8_face_anonymization.md) §P08-03이 범위를 소유하고 [configs/anonymized_diagnostic.yaml](../../../configs/anonymized_diagnostic.yaml)이 표본·개입·판정 규칙의 정본이다. 새 모델 학습·예측·calibration은 실행하지 않았다.

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

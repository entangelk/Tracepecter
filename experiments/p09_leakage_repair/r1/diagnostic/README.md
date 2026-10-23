# P09 새 cohort 진단 사전등록

새 학습 결과 전에 config·표본·주석 계보를 고정한다. 규칙 정본은 [configs/p09_r1_diagnostic.yaml](../../../../configs/p09_r1_diagnostic.yaml)이며 P08 seed·다섯 관문·허용폭·주석 정의를 그대로 유지한다. 새 metadata·후보 calibration·출력 디렉터리와 REAL review의 train 투영만 다르다. 기존 P08 진단 산출물은 변경하지 않는다.

## 적용 범위와 표본

- REAL shape/size 개입은 P08에서 확인한 기존 원 중 **새 train에 속한 107개 원·107장** 전부다. 배정 성분은102개다. `real_disc_review_train.csv`는 기존 review를 새 train ID로 필터한 투영이며 confirmed 값을 수정하거나 새 확인으로 표시하지 않았다. 후보 기하·측정 목표0.1631602984208327은 기존 측정 정본을 그대로 참조한다. 새 val/test에 옮겨간 확인 원은 개입 표본에서 제외한다.
- GEN 개입은 새 test/test_unseen 중 검출된 얼굴이 있는 이미지에서 기존 generator 정렬·ID 정렬·seed shuffle·최대40장 규칙으로 고정했다. playground_25/qwen_image_21/sd35_medium/sdxl 각40장, z_image_turbo1장, 총161장이다. 부족분을 다른 생성기로 채우지 않는다. 원본의 모든 캐시 얼굴을 함께 편집한다.
- 얼굴 상태 진단 대상은 새 test/test_unseen GEN952장 전부다. 원본·익명화 규격과 이미지 hash가 불변인 이전 최종 주석650장을 `prior_face_review.csv`로 보존한다. 이 중 소유자 원본 확인 ID는207장이다. 기존 소유자301장의 전체 명단·원본·요소→얼굴 변환·최종 주석·lock은 그대로 보존한다.
- 새로 포함된302장은 미확인이다. `annotation_lineage.csv`는 각 대상 ID의 과거 최종/소유자 확인 유무만 표시한다. 이 투영은 새 cohort의 최종 확인이 아니며 `face_review_template.csv`는 전부 빈 양식이다. 학습 전 표본·방법·ID를 고정하지만 새 `face_review.csv`·소유자 확인 목록·주석 lock의 완성/커밋은 **candidate 진단 예측 전**에 수행한다. 학습 validation 결과로 주석 대상·정의를 바꾸지 않는다.
- 후속 에이전트 검토는 미확인302장을 포함해 새 cohort의 ID를 빠짐없이 충족해야 한다. 소유자 확인은 새 전체 agent 주석에 동일한 불일치 전수+seed20% 규칙을 적용한다. 과거 소유자 확인은 같은 ID·원본·익명화에 한해 재사용하고 새 확인 목록에서 부족한 ID는 미완료로 둔다. 과거207장만으로 새 확인 절차가 끝났다고 간주하지 않는다.

## 통계·채택 규칙

P08의 운영상 등가성 관문을 변경하지 않는다. 이미지 단위로 같은 이미지의 모든 원을 공동 편집하고 이미지1개당 예측1개를 사용한다. paired score bootstrap은 **image 단위**, PCG64·기존 seed·20,000회·양측95% linear percentile이며 같은 표본군의 조건은 동일 추출을 사용한다. REAL107장은 최소80장 조건을 만족한다. 성분102개를 별개의107개 독립 룩으로 해석하지 않으며 train 개입은 일반화 증명이 아니다.

얼굴 상태는 이전과 같은 세 상태와 Newcombe/Wilson 구간·각 상태 최소20장을 사용한다. 상태/주석/표본 부족은 미확정이며 채택하지 않는다. score 구간 상한5점·오답 전환 구간 상한5%·상태 차이 구간±10%p를 결과에 맞춰 바꾸지 않는다. 익명화 Test A/B의 AUC와 다섯 관문을 모두 충족해야 채택을 검토한다. 미검토946,311쌍·GEN 계보 공유·개발 표본 노출과 외부 holdout의 한계는 그대로다. 실패/미확정 시 현 primary를 유지하고 Q5를 임의 폐기하지 않는다.

## 실행·계보 경계

`preregistration.json`은 새 metadata·config·기존 cache·기하·측정·baseline artifact와 세 manifest의 raw-byte hash를 고정한다. 학습 준비 lock은 추가로 과거 주석 원본·주석 투영·학습 sample ID·학습 소스를 고정한다. [준비 도구](../training/prepare.py)는 split lock 검증 후 같은 바이트의 재생성만 허용하며 모델 예측을 하지 않는다.

P09-04에서 새 val ID만으로 후보를 재보정한다. P08의 fitting parameter를 복사하지 않는다. config의 baseline은 기존 P05 artifact를 보존하는 비교 정본이며 그 학습·보정 metadata는 옛 버전이다. 기존 `scripts.p08_diagnostic`는 두 모델의 metadata hash가 같아야 하므로 P09 config를 그대로 실행하면 거부한다. 후속 실행기는 각 artifact의 원래 학습/보정 계보를 보존하고 **새 평가 cohort를 명시적으로 분리**해야 한다. 기존 hash 혼용 방어를 제거하거나 baseline artifact의 metadata hash를 새 값으로 덮어쓰지 않는다. baseline 비교는 이미 개발에 노출된 표본의 기술적 비교이며 대응표본 일반화 개선의 증거로 쓰지 않는다.

```bash
docker compose run --rm -T dev \
  python -m experiments.p09_leakage_repair.r1.training.prepare
```

이 파일·config·manifest를 사전 커밋한 뒤에만 P09-03 학습을 시작한다. 후보 진단 예측·최종 채택은 이번 준비 범위가 아니다.

# P09 r1 얼굴 주석·소유자 확인 대기

후보 진단 예측 전에 GEN952장 전부의 주석을 고정하기 위한 자료다. [사전등록](README.md)의 대상·정의·seed·최소 확인 비율을 유지했다. 모델 점수와 후보 진단 예측을 사용하지 않고 원본/익명화 이미지로만 검토했다. 아직 최종 `face_review.csv`와 `face_review_lock.json`은 없으며 confirmed 완료로 표시하지 않는다.

## 에이전트 검토와 보존 근거

- 이전 최종 주석650장은 `prior_face_review.csv`에서 그대로 투영했다. 이전 소유자 확인의 원본·요소→얼굴 변환·최종 주석·lock을 보존한다.
- 신규302장은 원본/익명화 전체와 상단 확대를 시각 대조했다. `visual_review_new.csv`에 얼굴 수·남은 얼굴 수·시트 위치·근거를 기록했다. 눈·코·입 중 둘 이상이 보이는 얼굴1개를 세며 측면/부분 얼굴도 포함한다. 입만 보이는 경계9장은 추가 소유자 확인 표시를 했다.
- `face_review_agent.csv`는 기존650장+신규302장, 총952장이다. 신규 시트38개·원본/익명화 쌍302개와 렌더 코드/목록의 hash는 `visual_review_evidence.json`에 있다. 이미지 사본은 `reports/errors/review/p09_leakage_repair/r1/face_review/`에 비추적으로 보존했다.
- 소유자 확인 전 원본952장의 이미지 hash를 변경 없는 얼굴 cache와 대조하고 학습 준비 lock의 입력 hash도 확인했다. 이미지·cache·익명화가 동일한 과거 소유자 주석만 재사용했다.

## 소유자 확인 범위

| 구분 | 전체 확인 | 이전 확인 재사용 | 새 확인 대기 |
| --- | ---: | ---: | ---: |
| 보임 수≠검출 수 또는 남은 얼굴≥1 | 119 | 86 | 33 |
| 나머지833장의 seed 고정20%(올림) | 167 | 25 | 142 |
| 시각 경계 추가(앞의 두 집합에 없는 항목) | 5 | 0 | 5 |
| 합계 | **291** | **111** | **180** |

시각 경계9장 중4장은 이미 사전등록 최소 목록에 들어 있어 중복 추가하지 않았다. 최소286장을 줄이거나 점수에 따라 표본을 바꾸지 않았다. `face_review_owner_check.csv`는 전체291장, `face_review_owner_reused.csv`는 재사용111장, `face_review_owner_pending.csv`는 부족180장이다. 이 분할·agent 주석·기존 owner 근거·config·사전등록·렌더 페이지는 `owner_review_lock.json`의 raw-byte hash로 고정했다.

## 확인 방법과 다음 실행

이 머신의 [점수 비공개 검토 페이지](../../../../reports/errors/review/p09_leakage_repair/r1/face_review/owner/index.html)를 브라우저에서 열고180장 모두 두 값을 선택한 뒤 **CSV 저장**을 누른다. 값은 눈·코·입의 요소 개수가 아니라 **얼굴 개수**다. 한 사람의 얼굴은1개이며 익명화 후 남은 얼굴은 원본에서 보이는 얼굴보다 클 수 없다. 페이지는 약65MiB인 자체 포함 파일이며 선택 내용은 페이지를 닫으면 초기화된다.

생성 명령(기존 고정 근거가 있으면 덮어쓰지 않고 거부):

```bash
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p09_face_review prepare
```

소유자가 저장한 CSV를 받은 뒤에만 실행한다:

```bash
docker compose run --rm -T dev python -m scripts.p09_face_review merge \
  --owner-file <repository-relative-owner-csv>
```

병합기는 부족180장과 정확히 같은 ID 집합·중복 부재·정수·0≤남은 얼굴≤보이는 얼굴을 검증하고, 새 owner 원본을 별도 보존한다. 이전111장과 합친 owner291장의 값을 agent보다 우선하며 나머지는 agent 값을 사용한다. 불완전 입력이나 고정 근거 변경 시 최종 파일을 만들지 않는다.

**최종 주석과 lock을 먼저 커밋**한 다음에만 `python -m scripts.p09_diagnostic --config configs/p09_r1_diagnostic.yaml --device cuda`를 실행한다. 이 실행기는 기존 baseline 학습/보정 metadata 계보를 보존하고 새 평가 cohort를 분리한다. 후보는 새 metadata·익명화 규격·고정 학습 결과 checkpoint hash와 일치해야 한다. P08 기본 실행기의 동일metadata 방어는 그대로 유지한다. 현재 진단 결과·다섯 관문·채택 여부는 미확정이며 primary는 유지한다.

## 수령·최종 고정 (2026-10-25)

소유자 180행은 얼굴 수가 아니라 P08과 같은 눈·코·입 개수였다(소유자 확인, 선택지 0~4). 원본 바이트는 `face_review_owner_new_features.csv`로 보존하고, 요소 0~1개는 얼굴 0개·2~4개는 얼굴 1개로 변환한 값을 merge에 넣었다(`face_review_owner_new.csv`). 요소 2개·에이전트 불일치 19장과 에이전트 다중 얼굴 2장은 예측 전에 원본/익명화 쌍으로 시각 확인했다. 결과는 952행·에이전트 대비 14행 변경이며, 의미·변환·확인 ID·전 hash는 `face_review_lock.json`에 고정했다.

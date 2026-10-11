# P06-02b 원형 얼굴 가림 의존 진단 — 독립검증 기록

## Verdict

**조건부 합격** — (추적 검증, HEAD `0b494d1`) `main()`이 판정·전환 helper에 넘기는 인자(calibration threshold, 대조 조건 이름 두 개, 표본 label)를 report 수준에서 잠그는 셀이 없다. 변이 N5·N6·N18이 생존했다. 이 셀을 추가하면 닫힌다. 그 밖의 1차 Blocking B1·B3·B4와 B2의 나머지 항목은 해소됐다. 상세는 아래 "추적 검증(보강 라운드)" 절에 있다.

1차 판정(HEAD `aad9440`, 이력 보존):

**조건부 합격** — 사전 고정 판정 규칙(발동/미발동, 5% 경계, "각 대조보다 큼")·전환 계산(calibration threshold, 미처리 표본 원본 logit 유지)·조건 적용(fill, 얼굴 원 크기)·검출 기준(min_edge_fraction, min_fill 단독)에 대한 회귀 잠금을 추가하고, 전환 방향(양방향 vs "REAL 판정으로 바뀐")과 off_face 제외 168장·`detected_disc` r+3 확장의 계약 공백을 config에서 해소해야 한다.

판정 근거:

- 보고 수치(README A/B 표, AUC, 평균 score, 변화량, 전환 수, 부가 주장)는 CSV에서 독립 재계산한 값과 **전부 일치**한다. 전체 재실행 결과 `report.json`·`predictions.csv`는 **byte 동일**하다. "의존 근거 있음"은 사전 규칙을 config 문구대로 적용해도 그대로 나온다.
- 육안 표본 점검(검토군 밖)도 구현자 주장과 정합한다. REAL 원 검출 32/32 정확, 원 미검출 48장 중 누락 1장, GEN 원 검출 37/37 오검출, 전환 36장 블라인드 분류는 얼굴 32·옷 4.
- 그러나 진단의 결론을 만드는 분기(판정 규칙, 전환 계산, 조건 적용)를 잠그는 테스트가 없다. 변이 12개 중 2개만 테스트를 깨뜨렸다. 가이드의 "경계 행렬 빈칸 = blocking" 조항에 따라 합격이 아니다.

## Subject metadata

- 일자: 2026-10-11
- 요청자: 소유자(독립검증 지시)
- 검증자: Claude Code 서브에이전트(독립검증자, 대상 슬라이스에 기여하지 않음)
- 검증 대상: P06-02b 원형 얼굴 가림 의존 진단 — `src/face_mask.py`, `tests/test_face_mask.py`, `experiments/p06_failure_analysis/face_mask/{README.md,detections.csv,predictions.csv,report.json}`
- 작업 원천: commit `aad9440`(`main`, working tree clean)
- 정준 계약: `configs/face_mask_diagnostic.yaml`(전체 37행, 1차 계약), `docs/plan/phase_6_failure_analysis.md`(:12-14 범위, :18-28 실험 전 정의, :37-42 완료 조건, :64-73 P06-02b 진행·결과), `docs/decision_briefs/DB-03_P01_face-policy.md`:29(사후 관찰 트리거, P06-02b가 입력으로만 관여)
- 고정 입력: `experiments/p05_calibration/calibration.json`, `checkpoints/baseline/best.pt`, `data/metadata.csv`

## Scope

1. 고정 입력 불변(calibration·checkpoint·metadata 해시)
2. 계약 ↔ 구현 정합(config 리터럴, 대상 모집단, 조건 적용, 전환 정의, 판정 규칙)
3. 보고 수치 독립 재계산(README ↔ report.json ↔ CSV)
4. 검출기 과적합 위험: 검토군 밖 원 검출 육안 표본 점검
5. Haar 얼굴 검출 범위·정밀도
6. 전환 36장 블라인드 육안 분류
7. 전체 재실행·결정성
8. 테스트(초점·전체) 및 테스트 감사(경계 행렬)
9. 변이 테스트
10. 복잡도

## Methodology

스크립트는 모두 저장소 밖 scratchpad(`/tmp/claude-1000/-mnt-f-devel-Tracepecter/a84d7a78-ae59-41e7-80eb-9e419fef0396/scratchpad/`)에 두었다. 구현 코드는 재사용하지 않고 pandas/numpy로 독립 계산했다. AUC는 쌍 비교(동점 0.5)로, 확률은 `1/(1+exp(-logit/T))`로 직접 계산했다.

```bash
# 1. 고정 입력
sha256sum experiments/p05_calibration/calibration.json /mnt/h/tracepector/checkpoints/baseline/best.pt data/metadata.csv
# 3. 재계산
python3 $S/recompute.py            # detections.csv·predictions.csv·metadata.csv만 읽는다
# 4~6. 육안 시트(박스·원 오버레이, 검토군 103장 제외, seed 고정 무작위)
python3 $S/sheets.py; python3 $S/sheets2.py   # Read 도구로 시트를 열어 판정
# 7. 재실행(출력만 scratch로 돌림, 커밋 산출물 미변경)
sed 's#^output_dir:.*#output_dir: /scratch/rerun#' configs/face_mask_diagnostic.yaml > $S/rerun_config.yaml
docker compose --profile training run --rm -T -v $S:/scratch train python -m src.face_mask --config /scratch/rerun_config.yaml
cmp $S/rerun/{detections.csv,predictions.csv,report.json} experiments/p06_failure_analysis/face_mask/...
# 8. 테스트
docker compose run --rm dev python -m pytest tests/test_face_mask.py -q   # 종료코드 직접 확인
docker compose run --rm dev python -m pytest -q
# 9. 변이: $S/mutate.sh <ID> <old> <new>
#   - 매번 git status --short 빈 상태 확인 → 문자열 치환 → 초점 테스트 → git checkout -- src/face_mask.py → git status --short 빈 상태 확인
```

재실행 전 `nvidia-smi`: 1,029 MiB 사용, 사용률 3%, compute 프로세스 없음. 다른 GPU 작업이 없어 실행했다.

## Findings

### 1. 고정 입력 불변

- calibration.json sha256 `eb9e6396…`. 내용은 T `0.7984784236465634`, threshold `0.6966991081858492`, checkpoint_sha256 `151244…`이고, 마지막 변경은 `314a36b`(P05)다.
- `/mnt/h/tracepector/checkpoints/baseline/best.pt` sha256 `151244676027…`. artifact와 일치하고, `load_calibration`(`src/score.py:21`)이 실행 시에도 검사한다.
- `data/metadata.csv` sha256 `039cbdd1…`. calibration artifact의 `metadata_sha256`과 일치하고, 마지막 변경은 `af13dc6`(P01-07)다.
- report.json의 `temperature`·`threshold_probability`·`checkpoint_sha256`도 위 값과 같다.

### 2. 계약 ↔ 구현 정합

- **config 리터럴**: `disc_detector`·`face_detector`·`disc_diameter_per_face`·`conditions`·`dependence_rule`은 `**settings[...]`로 코드에 그대로 전달된다(`src/face_mask.py:143-144,162,170-171,217-221`). 코드 안에 따로 복제된 리터럴은 없다. config 주석의 "반지름 0.9 안쪽"·"둘레 180점"은 `src/face_mask.py:23,40`과 같다.
- **대상 모집단**: `targets = sorted(set(standard) | set(unseen))`(`:136`)이고, `evaluation_indices`(`src/evaluate.py:52-58`)는 Test A = split test(800), Test B = test REAL 448 + test_unseen 600이다. 재계산 결과 고유 1,400장(GEN 952, REAL 448)으로, plan :20과 config :24에 일치한다. `original` 예측 1,400행도 일치한다.
- **미처리 표본 원본 logit 유지**: `combined = logits['original'] | logits[name]`(`:204`)으로 config :24 문구와 일치한다. 재계산 AUC(조건별 A/B)가 report.json과 소수 5자리까지 같다.
- **score → 판정**: `apply_temperature`(`src/calibration.py:8-12`)로 확률을 만들고 `threshold_probability`와 `>=`로 비교한다(`:203`). plan :18의 정의(`p_cal >= threshold` → REAL)와 일치한다.
- **판정 규칙 적용**: `:218-221`은 "주 조건 평균 상승 > 각 대조"와 "전환 수/대상 수 ≥ 0.05"이며, config :32-33과 같은 구조다. 재계산 결과 +10.192 > +7.199, +10.192 > +1.906, 36/581 = 0.0620 ≥ 0.05이므로 "의존 근거 있음"이 맞다.
- **불일치 1(전환 방향)**: config :33은 "대상 GEN 중 **REAL 판정으로 바뀐** 비율"이다. 코드 `:203`은 `(after >= threshold) != (before >= threshold)`로 **양방향** 전환을 센다. 이번 데이터에서는 대상 GEN 581장 중 원래 threshold 이상인 표본이 0장이라 REAL→GEN 전환이 불가능했고(재계산 down = 0, 4조건 모두), 결과에는 영향이 없다. 그러나 계약 문구와 구현이 다르다. `real_disc_gray`의 "FN 전환"(config :34, REAL→GEN 방향)도 같은 양방향 카운터를 쓴다. → Blocking B3
- **불일치 2(spec-silent 강제)**:
  - (a) `off_face_disc`(`:75-82`)는 대칭 위치 → +3r → −3r 순서로 자리를 찾는다. 자리가 없으면 None을 돌려주고, `_edit_for`(`:118-120`)가 그 표본을 조건에서 뺀다(581 − 413 = **168장**). config :24·:28은 "해당 클래스·검출 표본"과 "위치와 무관한 흰 원"만 말한다. 배치 규칙과 "자리 없음 → 제외"는 계약에 없다.
  - (b) `detected_disc`는 반지름을 `r + 3`으로 키워 칠한다(`:114`). config :29에는 없다.
  - (c) `r < 6` 후보 제외(`:41`), Hough 상위 30개(`:39`), 둘레 표본 r−3/r+4(`:47`), `minDist`·`param1`(`:32`)도 config 밖 상수다. (c)는 검출기 내부 구현값이라 hardening으로 분류한다. (a)·(b)는 조건 정의 자체를 바꾸므로 → Blocking B4
- **대조군 모집단 불일치(계약상 미규정, 결과 강건성 점검)**: 위치 대조는 413장, 주 조건은 581장에서 평균을 낸다. 같은 413장으로 맞추면 주 +9.020 / 회색 +6.297 / 얼굴 밖 +1.906이다. 부등식은 유지된다. 다만 같은 413장에서 주 조건 전환은 20/413 = **4.8%**로 5% 아래다. 사전 규칙은 581장 기준이라 판정이 틀린 것은 아니지만, 5% 기준까지의 여유가 작다(36장 vs 경계 29.05장). → Hardening H3

### 3. 보고 수치 독립 재계산

| README 주장 | 재계산 | 일치 |
| --- | --- | --- |
| REAL 원 train 515/2,100, val 142/452, test 134/448 | 515, 142, 134 | ✓ |
| GEN 원 train 14/1,680, val 6/368, test 5/352, test_unseen 12/600 (합 37) | 14, 6, 5, 12 | ✓ |
| 단축 규칙 AUC A 0.642 / B 0.640 | 0.64245 / 0.63955 | ✓ |
| GEN 오검출 제외 A ≈ 0.650 | 0.64955 (B도 0.64955) | ✓ |
| 원 있는 REAL 134, 평균 99.94, FN 0 / 원 없는 REAL 314, 평균 99.22, FN 4 | 134, 99.938, 0 / 314, 99.225, 4 | ✓ |
| 주 조건 GEN 581, 0.31 → 10.51, +10.19, 전환 36 (6.2%) | 581, 0.313 → 10.505, +10.192, 36 (0.0620) | ✓ |
| 회색 581, 0.31 → 7.51, +7.20, 28 (4.8%) | 581, 0.313 → 7.512, +7.199, 28 (0.0482) | ✓ |
| 얼굴 밖 413, 0.38 → 2.28, +1.91, 5 (1.2%) | 413, 0.378 → 2.284, +1.906, 5 (0.0121) | ✓ |
| REAL 회색 134, 99.94 → 99.67, −0.27, 0 | 134, 99.938 → 99.671, −0.267, 0 | ✓ |
| 얼굴 검출 581 = GEN 952의 61% | 581/952 = 61.0% | ✓ |
| 얼굴 밖 제외 168 | 581 − 413 = 168 | ✓ |
| 주 조건 AUC A 0.99914 / B 0.99812 (원본 0.99994 / 0.99977) | 0.99914 / 0.99812 (0.99994 / 0.99977) | ✓ |
| 36장 중 26장 sd35_medium | sd35 26, playground 6, qwen 3, z_image 1 | ✓ |
| 회색 전환 28장 중 27장은 흰 원에서도 전환 | 교집합 27 | ✓ |
| 효과의 약 70%는 회색 원으로도 생김 | 7.199/10.192 = 70.6% | ✓ |
| 흰색 추가분 +3.0점, 전환 8장 | +2.993점, 순차이 36 − 28 = 8 | △ (집합 기준으로는 흰 원에서만 전환 9장, 회색에서만 1장) |
| 정밀도 보정 대상 약 435장 대비 약 7% | 581 × 0.75 = 435.75, 30/435.75 = 6.9% | ✓ |
| Test A REAL FN 4장 전부가 원 없음 | 원 있음 FN 0 + 원 없음 FN 4 | ✓ |

report.json(`disc_prevalence`, `shortcut_rule`, `model_by_real_disc`, `conditions.*`, `dependence_evidence: true`)도 위 재계산과 전부 같다. 검토군 103장 기준 "눈 판정 원 13, 오검출 0"도 재계산 결과 REAL 13 / GEN 0이다. `review_agent.csv`의 "원형 얼굴 가림" 메모 13건과도 같다.

### 4. 검출기 과적합 위험(검토군 밖 원 검출)

검토군 103장을 제외하고 seed 20261011로 무작위 추출했다. 원을 오버레이한 시트를 Read 도구로 열어 판정했다.

- REAL 원 있음: **32/32**가 실제 익명화 원이었다(모두 얼굴 위치). 구현자 16/16과 합치면 48/48이다.
- REAL 원 없음: 48장 중 **1장 누락**(`834114`)이다. 확대해 보니 원이 약간 회색조이고 흰 칼라와 맞닿아 있어 `white_min`·경계 조건에서 빠진 것으로 보인다. 구현자 결과(16장 중 1장, `582998`)와 합치면 2/64(3.1%)다. REAL 원 없음 2,189장(검토군 외)에 대입하면 누락은 약 40~70장, 출현율로는 +2~3%p 수준이다.
- GEN 원 검출: **37/37 전수가 오검출**이다(배경 보케·하이라이트, 얼굴 위 0). 구현자 주장과 일치한다.
- **A절 주장에 대한 영향**: 이진 단서의 AUC는 (TPR + TNR)/2이다. REAL 누락 3%가 TPR을 약 +0.01 바꾸고, GEN 오검출 제거는 +0.007이다. 따라서 "약 0.64~0.65"는 ±0.01 안에서 유지된다. 과적합 위험이 A절 결론(정밀도는 높지만 REAL의 약 30%만 덮어 단독 분리력이 약함)을 뒤집지는 않는다. 다만 표본 점검이므로 검출기 재현율의 신뢰구간은 넓다(누락 2/64, 95% Wilson 상한 약 11%).

### 5. Haar 얼굴 검출 범위·정밀도

- 범위: detections.csv에서 Test 대상 GEN 952장 중 얼굴 상자가 있는 것이 581장(61.0%)이다. 6,000장 중 GEN 전체로는 2,054/3,000이다.
- 정밀도(박스가 실제 얼굴에 걸친 비율, 검토군·전환 36장 제외):
  - Test 대상 581장 모집단 무작위 24장(seed 7): **17/24 = 71%**(95% Wilson 약 51~85%). 구현자의 약 75%(9/12)와 정합한다.
  - 전 split GEN 무작위 48장: 28/48 = 58%(약 44~71%). train/val의 거리 배경 이미지에서 배경·몸통 오검출이 많다.
- 판정 영향: 사전 규칙은 검출기가 정한 대상 기준이라 정밀도가 판정 계산에 직접 들어가지 않는다. 실제 얼굴 대상 수로 보정하면 30~32장 / (581 × 0.58~0.75) = 6.9~9.5%로 오히려 커진다. 결론 방향은 유지된다.

### 6. 전환 36장 블라인드 분류

구현자의 표본별 분류는 공개되어 있지 않다(README에는 합계만 있음). 36장을 seed로 섞은 뒤 얼굴 상자(빨강)와 덧씌울 원(청록)을 그린 시트 3장을 먼저 판정하고, 그 뒤 합계를 비교했다.

- 얼굴 32(이 중 측면·머리 경계 애매 2장: `gen_002720`, `gen_002543`), 옷·몸 4(`gen_001085` 허리, `gen_001397` 허리·셔츠, `gen_000549` 코트, `gen_002759` 코트 라펠)
- 구현자: 얼굴 30, 머리 경계 2, 옷 4. 옷 4장은 일치하고, 애매 2장을 얼굴로 세느냐의 차이일 뿐이다. 판정은 "실제 얼굴만으로도 5% 이상"으로 동일하다.

### 7. 전체 재실행·결정성

- 실행 시간 10분 59초, 종료코드 0. `dependence_evidence: true`이고 출현율 출력도 동일하다.
- `report.json`: **byte 동일**. `predictions.csv`: **byte 동일**(3,109행, logit 최대 차이 0.0).
- `detections.csv`: **1행 다름**. `gen_000806`(train, qwen_image_21)의 얼굴 상자가 커밋본은 (374, 68, 104, 104), 재실행은 (579, 455, 104, 104)다. 두 상자가 같은 크기(104 × 104)라 `max(faces, key=w*h)`(`src/face_mask.py:67`)의 동점 처리가 `detectMultiScale` 반환 순서에 좌우된다. 오버레이로 확인하니 커밋본 상자(374, 68)는 실제 얼굴이고 재실행 상자(579, 455)는 배경이다. train 표본이라 진단 모집단(Test A ∪ B)에 없어 보고 결과에는 영향이 없다. 하지만 검출 산출물은 실행 간 비결정적이다. → Hardening H1

### 8. 테스트·테스트 감사

- `docker compose run --rm dev python -m pytest tests/test_face_mask.py -q` → 6 passed, 종료코드 0
- `docker compose run --rm dev python -m pytest -q` → 56 passed(경고 12), 종료코드 0. 파이프 없이 `$?`를 직접 기록했다.

경계 행렬(계약 → 잠그는 테스트):

| 계약 분기 | 발동 측 잠금 | 미발동 측 잠금 | 상태 |
| --- | --- | --- | --- |
| 흰 원 검출(배경과 붙은 원 포함) | `test_detects_disc_even_when_merged_with_white_background`(`tests/test_face_mask.py:26`) | — | 있음 |
| 흰 사각형·흰 벽·잡음 = 원 아님 | — | `test_rejects_white_regions_that_are_not_discs`(`:36`). 단 `min_edge_fraction`·`min_fill` 각각을 단독으로 잠그지는 않는다(변이 M6, M7 생존). | **부분** |
| 개별 임계(white_min, outside_max, radius_ratio) | 없음 | 없음 | 빈칸 |
| 얼굴 상자 → 원 지름 1.4배 | 없음(`disc_for_face` 테스트 없음, M5 생존) | — | **빈칸** |
| off_face 배치(같은 크기, 비중첩, 자리 없으면 None) | `test_off_face_disc_keeps_size_and_avoids_face`(`:47`) | 같은 테스트 `:51` | 있음(단 제외 자체가 계약 밖, B4) |
| 조건 fill 255/128 적용 | `test_paint_disc_only_changes_inside`(`:54`)는 `paint_disc` 인자만 확인 | — | **빈칸**(`_edit_for`가 spec fill을 쓰는지 미잠금, M9 생존) |
| 조건 labels 필터 | CLI 테스트(`:108-109`) | 같은 곳 | **흡수됨**(M8 생존: 얼굴 검출이 GEN에서만 실행되고 fixture의 원이 REAL에만 있어 상위 층이 막는다. 실제 데이터의 GEN 원 오검출 37장에 `real_disc_gray`가 적용되는 회귀는 잡지 못한다) |
| 대상 모집단 A ∪ B | CLI 테스트 `:109`(test_unseen 포함) | — | 있음(M10 사망) |
| 미처리 표본 원본 logit 유지 | 없음(M4 생존) | — | **빈칸** |
| 전환 = calibration threshold 기준 | 없음(M3 생존) | — | **빈칸** |
| 판정 규칙 발동(상승 > 각 대조 ∧ 전환 ≥ 5%) | 없음. `isinstance(..., bool)`만 있다(`:112`). | — | **빈칸** |
| 판정 규칙 미발동(대조 이상 / 전환 < 5%) | — | 없음(M1, M2 생존) | **빈칸** |
| 5% 경계값(=0.05 포함) | 없음 | 없음 | **빈칸** |
| 출현율·단축 AUC | CLI `:100-103` | — | 있음 |

추가 관찰: 테스트의 `DETECTOR` 딕셔너리(`tests/test_face_mask.py:11-12`)는 config 값을 복제한 것이다. config 리터럴이 바뀌어도 테스트는 이를 감지하지 못한다. → Hardening H6

### 9. 변이 테스트

트리는 `aad9440`에서 clean이었다. 변이마다 `git status --short` 빈 상태 확인 → `src/face_mask.py` 문자열 치환 → 초점 테스트 → `git checkout -- src/face_mask.py` → `git status --short` 빈 상태 재확인. 12회 모두 복원 후 clean이었다.

| ID | 변이(`src/face_mask.py`) | 결과 | 깨진 셀 |
| --- | --- | --- | --- |
| M1 | `:219` 주 조건 > 대조 → `<` | 생존 | — |
| M2 | `:220-221` 전환 비율 조건 → `True` | 생존 | — |
| M3 | `:203` threshold → 0.5 | 생존 | — |
| M4 | `:204` 미처리 표본 logit → 0.0 | 생존 | — |
| M5 | `:72` 지름/2 제거(반지름 2배) | 생존 | — |
| M6 | `:49` edge 조건 제거 | 생존 | — (fill 조건이 흡수) |
| M7 | `:41` fill 조건 제거 | 생존 | — (edge 조건이 흡수) |
| M8 | `:161` labels 필터 제거 | 생존 | — (얼굴 검출 GEN 한정·fixture가 흡수) |
| M9 | `:120` fill → 항상 255 | 생존 | — |
| M10 | `:136` 대상 → Test A만 | 사망 | `test_face_mask_cli_reports_prevalence_shortcut_and_conditions` |
| M11 | `:120` off_face 자리 없음 → 얼굴 위치로 대체 | 생존 | — |
| M12 | `:49` edge ≥ 0.35 → > 0.65(과잉 엄격) | 사망 | `test_detects_disc_even_when_merged_with_white_background` |

M6과 M7은 두 층 방어(fill·edge)가 서로를 흡수한 경우다. 각 층을 단독으로 잠그는 단위 셀이 없다.

### 10. 복잡도

- 검출은 6,000장을 1회 순회한다. 이미지당 Hough 후보 ≤ 30개 × 마스크 O(HW)이고, Haar는 1회다. 총 O(N·HW)이며 실측 약 11분이다.
- 예측은 조건당 대상 표본만 추론한다(1,400 + 581 + 581 + 413 + 134). 재시도·무한 루프는 없다.

## Issues / Risks

### Blocking (계약 의무)

- **B1 사전 판정 규칙 미잠금**: `src/face_mask.py:218-221`의 발동/미발동 분기, "각 대조보다 큼", `min_gen_flip_fraction` 0.05 경계(≥, 포함)를 잠그는 셀이 없다. `tests/test_face_mask.py:112`는 bool 타입만 본다. M1·M2가 생존했다.
  - 조치: 조건별 shift·flips를 주입하는 단위 셀을 추가한다. 발동 1건, 각 대조 이상 → 미발동 2건, 전환 0.0499 → 미발동, 정확히 0.05 → 발동. 판정 계산을 순수 함수로 분리하거나 report 입력을 fixture로 구성한다.
- **B2 전환 계산·조건 적용 미잠금**:
  - calibration threshold 사용(`:203`, M3)
  - 미처리 표본 원본 logit 유지(`:204`, M4)
  - 조건 fill이 spec 값으로 칠해지는지(`:120`, M9)
  - 얼굴 상자 → 지름 1.4배(`:72`, M5)
  - `min_edge_fraction`·`min_fill` 단독 거부(M6, M7)
  - labels 필터가 GEN 원 오검출에 `real_disc_gray`를 적용하지 않는지(M8)
  - 조치:
    - CLI 테스트에 threshold 경계 근처 logit을 갖는 고정 모델(또는 `predict_logits` monkeypatch)을 넣어 전환 수를 정확히 단언한다.
    - 미처리 표본의 combined logit = original을 단언한다.
    - `_edit_for` 반환 fill과 반지름을 단언한다.
    - 원이 있는 GEN fixture를 추가해 `real_disc_gray` 대상에서 빠지는지 확인한다.
    - 원형이지만 둘레가 전부 흰 배경인 경우(edge 0)와 링 모양(fill < 0.97)을 각각 거부하는 셀을 추가한다.
- **B3 전환 방향의 계약 ↔ 구현 불일치**: config :33 "REAL 판정으로 바뀐"과 :34 "FN 전환"은 단방향이다. 반면 `src/face_mask.py:203`은 양방향 `!=`다. 이번 결과에는 영향이 없다(대상 GEN 중 원래 threshold 이상 0장, REAL→GEN 전환 0).
  - 조치: 소유자가 정한다. 코드를 단방향(GEN: before < th ≤ after, REAL: before ≥ th > after)으로 고치거나, 다음 config(P06-02c)에 "양방향"을 명시한다. 어느 쪽이든 회귀 셀을 추가한다.
- **B4 spec-silent-but-code-enforced**:
  - (a) off_face 배치 규칙과 "자리 없음 → 조건 제외"(168장, `:75-82,118-120`)
  - (b) `detected_disc` 반지름 r + 3 확장(`:114`)
  - 조치: config(또는 P06-02c config)에 배치 순서·제외 규칙·확장 픽셀을 명시하고, 대조 비교 모집단(581 vs 413)을 맞출지도 함께 정한다.

### Hardening recommendations (비차단)

- **H1 얼굴 상자 동점 비결정성**(`src/face_mask.py:67`): 재실행에서 `gen_000806` 1행이 바뀌었다. 조치: 키를 `(w*h, -y, -x)` 같은 결정적 순서로 바꾸고, 같은 이미지를 두 번 검출해 상자가 같은지 확인하는 셀을 추가한다.
- **H2 사전 고정의 증빙**: config가 결과와 같은 커밋(`aad9440`)으로 처음 들어와, "결과 전 고정"을 git으로 확인할 수 없다(work_log :29의 서술뿐이다). 조치: P06-02c부터 config만 먼저 커밋한 뒤 실행한다.
- **H3 판정 여유 보고**: 5% 기준까지 여유가 7장(36 vs 29.05)이다. 같은 413장 모집단에서는 20/413 = 4.8%다. 조치: README에 민감도로 적고, P06-02c bootstrap 구간에 전환 비율 CI를 포함한다.
- **H4 얼굴 정밀도 표기**: "약 75%"는 12장 기준이다. 본 검증 대상 모집단 표본은 17/24(71%), 전 split 표본은 28/48(58%)이다. 조치: README `### 얼굴 검출 품질과 민감도`에 표본 수와 구간을 함께 적는다.
- **H5 "전환 8장" 표현**: 순차이 36 − 28 = 8이다. 집합 기준으로는 흰 원에서만 전환 9장, 회색에서만 1장이다. 조치: README `### 해석` 첫 항목에 "순차이"라고 명시한다.
- **H6 테스트 리터럴 복제**(`tests/test_face_mask.py:11-12`): 조치: `configs/face_mask_diagnostic.yaml`의 `disc_detector`를 읽어 쓴다.
- **H7 검출기 내부 상수**(`src/face_mask.py:32,39,41,47`): 조치: P06-02c config로 옮기거나 config 주석에 고정값으로 기록한다.

## Outstanding items

- 커밋·push 없음. 저장소에서 쓴 파일은 이 기록 하나다. 재실행 산출물은 scratchpad에만 있다.
- 다음 단계: B1~B4 해소(소유자 결정 B3·B4 포함) → 추적 검증. P06-02c 사전 고정 config에 B3·B4·H1~H3을 반영하면 함께 닫을 수 있다.
- DB-03 트리거 판정은 P06-04 범위다. P06-02b README는 이에 대한 판정을 주장하지 않으므로 이 검증에서 판정하지 않았다.

## Reproduction

```bash
cd /mnt/f/devel/Tracepecter
S=<scratchpad>
sha256sum experiments/p05_calibration/calibration.json /mnt/h/tracepector/checkpoints/baseline/best.pt data/metadata.csv
python3 $S/recompute.py
sed 's#^output_dir:.*#output_dir: /scratch/rerun#' configs/face_mask_diagnostic.yaml > $S/rerun_config.yaml
docker compose --profile training run --rm -T -v $S:/scratch train python -m src.face_mask --config /scratch/rerun_config.yaml
for f in detections.csv predictions.csv report.json; do cmp $S/rerun/$f experiments/p06_failure_analysis/face_mask/$f; done
docker compose run --rm dev python -m pytest tests/test_face_mask.py -q; echo $?
docker compose run --rm dev python -m pytest -q; echo $?
git status --short   # 빈 출력 확인 후 $S/mutate.sh <ID> '<old>' '<new>' 반복
```

## 추적 검증(보강 라운드) — 2026-10-11, HEAD `0b494d1`

### Verdict

**조건부 합격** — `main()` → helper 연결(`src/face_mask.py:233` threshold·label 인자, `:239` 대조 조건 이름)을 report 수준에서 잠그는 셀이 없다(변이 N5·N6·N18 생존). CLI 테스트에서 `edited_decision_flips`·`dependence_evidence`를 predictions.csv와 calibration artifact로 독립 재계산해 단언하면 닫힌다.

판정 근거:

- 1차 B1(판정 규칙)·B3(전환 방향)·B4(사후 명시)는 해소됐다. B2는 helper 단위 잠금이 생겼고 해당 변이가 모두 죽었다.
- 남은 공백은 B2의 한 갈래다. 1차 M3은 호출 지점에서 threshold를 0.5로 바꾸는 변이였다. 같은 지점의 변이(N5)가 여전히 생존한다. 계산이 helper로 옮겨 가 helper는 잠겼지만, `main()`이 helper에 넘기는 값은 잠기지 않았다.
- 보고 수치는 새 산출물에서 독립 재계산한 값과 전부 일치한다. 산출물 변화(gen_000799 1장)는 tie-break로 완전히 설명된다. CPU 검출 재실행 결과는 byte 동일하다.

### 대상·원천

- commits `00926f1`(판정 규칙·전환 방향·조건 선택 테스트, 이 기록의 1차본 포함), `05a1f83`(min_fill 단독 잠금), `0b494d1`(tie-break 재실행, README 사후 명시)
- `git diff aad9440 HEAD --stat`: config는 **변경 없음**(사전 고정본 유지, 소유자 결정 B4와 일치). 변경 파일은 `src/face_mask.py`, `tests/test_face_mask.py`, 산출물 4종, 이 기록이다.
- 소유자 결정(2026-10-11, 조정자 전달):
  - B3: 코드를 config 문구(맞던 판정 → 틀린 판정 단방향)에 맞춘다.
  - B4: config는 유지하고, README에 사후 명시한다. P06-02c config에서 사전 고정한다.

### 코드 변경 확인

- `largest_face`(`src/face_mask.py:70-72`): 키 `(w*h, -y, -x)`. 넓이 최대 → y 최소 → x 최소로, README의 "위·왼쪽"과 일치한다.
- `select_edits`(`:128-134`): 기존 루프를 그대로 옮겼다. 동작 변화는 없다.
- `decision_flips`(`:137-140`): `(before >= th) == real` ∧ `(after >= th) != real`이다. GEN은 before < th ≤ after만, REAL은 before ≥ th > after만 센다. config :33-34 문구(단방향)와 일치한다(B3 해소).
- `dependence_evidence`(`:143-147`): 기존 식과 같다. `>` 엄격, `>=` 비율 경계 포함이다.
- 잔여 관찰: report.json의 `conditions.*.sets.*.decision_flips`는 여전히 `_condition_metrics`(`src/failure_analysis.py:83`)의 양방향 정의다. 같은 report 안에 전환 정의가 두 개 있다. 이번 실행은 역방향 전환이 0이라 값은 같다. → Hardening R2

### 테스트·감사

- `docker compose run --rm dev python -m pytest tests/test_face_mask.py -q` → 19 passed, 종료코드 0
- `docker compose run --rm dev python -m pytest -q` → 69 passed, 종료코드 0
- `SETTINGS`를 config에서 읽는다(`tests/test_face_mask.py:14-16`, 1차 H6 해소).
- 새 셀은 1차 경계 행렬의 빈칸을 채운다. 대응 관계는 다음과 같다.
  - edge 단독: `:51`
  - fill 단독: `:57`
  - tie-break: `:64`
  - 지름 1.4배: `:71`
  - labels·fill·r+3·off_face 제외: `:75-90`
  - 전환 방향·threshold: `:93-98`
  - 판정 규칙 7개 매개 셀(0.05 포함 경계, 0.049, 대조 동률, 각 대조 초과, None, 대상 0): `:101-112`
  - 미처리 표본 원본 logit: `:181-183`
- 감사 결과:
  - 판정 규칙 셀은 발동(정확히 0.05)과 미발동(각 조항 단독 위반)을 모두 갖춘다.
  - 전환 셀은 과소 측(GEN→REAL, REAL→FN 집계)과 과잉 측(0.5~0.7 이동, 역방향)을 모두 갖춘다.
  - 남은 공백: CLI 테스트의 판정 단언은 여전히 `isinstance(..., bool)`(`:180`)이다. CLI에서 전환 수는 단언하지 않는다. → Blocking R-B1

### 변이 테스트(본 검증자 직접 수행)

변이마다 `git status --short` 빈 상태 확인 → `src/face_mask.py` 치환 → 초점 테스트 → `git checkout -- src/face_mask.py` → `git status --short` 빈 상태 재확인. 18회 모두 clean이었다.

| ID | 변이 | 결과 | 깨진 셀 |
| --- | --- | --- | --- |
| N1 | `:146` 주 > 대조 → `<` | 사망 | `test_dependence_rule…[1-20-shifts0-True]` |
| N2 | `:147` 비율 조항 → True | 사망 | `…[49-1000-shifts1-False]` |
| N3 | `:147` `>=` → `>` | 사망 | `…[1-20-shifts0-True]` |
| N4 | `:140` 양방향 전환 | 사망 | `test_decision_flips_counts_only_correct_to_wrong_at_calibrated_threshold` |
| **N5** | `:233` main이 threshold 대신 0.5 전달 | **생존** | — |
| **N6** | `:239` 대조를 회색 하나로 | **생존** | — |
| N7 | `:227` 미처리 표본 logit → 0 | 사망 | `test_face_mask_cli_reports_prevalence_shortcut_and_conditions` |
| N8 | `:77` 지름/2 제거 | 사망 | `test_disc_for_face_uses_long_side_times_diameter_ratio` |
| N9 | edge 조건 제거 | 사망 | `test_disc_detector_requires_dark_edge_even_when_filled` |
| N10 | fill 조건 제거 | 사망 | `test_disc_detector_requires_filled_inside_even_with_edge` |
| N11 | `:132` labels 필터 제거 | 사망 | `test_select_edits_follows_condition_labels_position_and_fill` |
| N12 | `:125` fill → 255 고정 | 사망 | 같은 셀 |
| N13 | off_face 자리 없음 → 얼굴 위치 대체 | 사망 | 같은 셀 |
| N14 | `:119` r+3 → r | 사망 | 같은 셀 |
| N15 | tie 키 → 넓이만 | 사망 | `test_largest_face_breaks_area_ties_deterministically` |
| N16 | `:140` after `>=` → `>`(정확히 threshold) | 생존 | — |
| N17 | main이 select_edits에 label 전부 0 전달 | 사망 | CLI 셀 |
| **N18** | `:233` main이 decision_flips에 label 전부 0 전달 | **생존** | — |

- 구현자 주장(1차 M1–M9·M11 + 양방향·tie 키·r+3, 13/13 사망)은 helper 내부 변이에 대해서는 재현된다(N1–N4, N7–N15).
- 호출 지점 변이 N5·N6·N18은 생존한다.
  - N5: 실제 데이터에서 전환 수가 바뀐다. 0.5 기준이면 주 조건 전환이 36보다 커질 수 있다.
  - N6: 판정 조항 "두 대조 조건보다 각각"이 한 대조로 줄어든다.
  - N18: `real_disc_gray`의 FN 전환이 GEN 방향으로 계산된다.
- N16은 확률이 threshold와 정확히 같은 경우다. 실질 발생 확률은 0에 가까워 hardening으로 분류한다.

### 산출물 변화와 결정성

- `git diff aad9440 HEAD`의 산출물 변화:
  - detections.csv 1행: `gen_000799`가 (328, 493, 68, 68) → (351, 129, 68, 68)
  - predictions.csv 3행: gen_000799의 white/gray/offface logit
  - report.json: 세 GEN 조건의 `after`·`edited_mean_shift`와 집합별 GEN `mean_score`·`mean_score_shift`
  - 전환 수·AUC·판정은 변화 없다.
- gen_000799(test, qwen_image_21)의 두 상자는 넓이가 같다(68 × 68). 새 키는 y가 작은 (351, 129)를 고른다. 오버레이로 확인하니 옛 상자는 **무릎(바지)**, 새 상자는 **얼굴**이다. README 주장과 일치한다.
- aad9440 시점 두 실행(커밋본, 1차 재실행)에서 gen_000799는 둘 다 (328, 493)이었다. 따라서 이 변화는 실행 간 흔들림이 아니라 tie 규칙 변경에서 나온 것이다. gen_000806은 새 규칙으로 (374, 68)(얼굴)에 고정되며, 커밋본과 같다.
- **CPU 검출 재실행**(HEAD 코드, 6,000장, dev 컨테이너, 6분 43초) → `detections.csv`와 **byte 동일**. 명령:

  ```bash
  docker compose run --rm -T -e PYTHONPATH=/app -v $S:/scratch -v /mnt/h/tracepector/images:/images:ro dev python /scratch/redetect.py
  ```

- **GPU 전체 재실행은 하지 않았다.** `nvidia-smi` 사용률이 15~39%로 지속됐고, 소유자의 `ai_writte_system` 컨테이너(embedding, generation_worker 등)가 실행 중이었다. GPU 정책(소유자 작업 중 시작·큐잉 금지)에 따랐다. predictions.csv의 HEAD 재현은 미검증이다. 다만 변화가 gen_000799 3행에 국한되고, 그 원인(상자 교체)은 위에서 확인했다. → Outstanding

### 보고 수치 재계산(새 산출물)

`recompute.py`(1차와 동일 스크립트)와 Wilson 구간 계산:

| README 주장 | 재계산 | 일치 |
| --- | --- | --- |
| 주 0.31 → 10.51, +10.20, 36 (6.2%) | 0.313 → 10.512, +10.199, 36 (up 36 / down 0) | ✓ |
| 회색 0.31 → 7.52, +7.20, 28 | 0.313 → 7.517, +7.204, 28 | ✓ |
| 얼굴 밖 0.38 → 2.27, +1.89, 5 | 0.378 → 2.269, +1.892, 5 | ✓ |
| REAL 99.94 → 99.67, −0.27, 0 | 99.938 → 99.671, −0.267, 0 | ✓ |
| AUC 0.99914 / 0.99812 (원본 0.99994 / 0.99977) | 동일 | ✓ |
| Wilson 36/581 = 4.5~8.5% | 4.51~8.46% | ✓ |
| 413장 매칭: 흰 +9.03, 회색 +6.30, 얼굴 밖 +1.89, 흰 전환 20/413 = 4.8% | +9.030, +6.304, +1.892, 20 | ✓ |
| 9/12 Wilson 47~91% | 46.8~91.1% | ✓ |
| 순차이 8, 집합 9/1 | 36 − 28 = 8, 흰 원 단독 9, 회색 단독 1 | ✓ |
| 약 70%, +3.0점 | 7.204/10.199 = 70.6%, +2.995 | ✓ |
| A절 표·AUC 0.642/0.640/0.650, REAL 원 유무 score·FN | 1차와 동일(검출·original logit 불변) | ✓ |

### README 사후 명시 절 ↔ 코드 문자 대조

- 얼굴 밖 원:
  - 후보 순서 `width − x`, `x + 3r`, `x − 3r`, 중심 거리 ≥ 2r, 이미지 안(`r ≤ cx ≤ width − r`, `r ≤ y ≤ height − r`)은 `src/face_mask.py:84-86`과 일치한다.
  - 자리 없음 → 제외·원본 logit은 `:124-125`, `:227`과 일치한다(168장, 재계산 581 − 413).
- r + 3: `:119`와 일치한다.
- tie-break "넓이가 같으면 위·왼쪽": `:72` 키와 일치한다.
- 검출 상수:
  - `minDist` = 너비 × 0.05, `param1` 100: `:32`
  - 상위 30: `:39`
  - r < 6 제외, 0.9r 안쪽: `:40-41`
  - r − 3 / r + 4 180점: `:23,47`
  - 5×5 Gaussian σ 1.5 순백 마스크: `:31`
  - 모두 일치한다. 누락은 Hough `dp=1`, `minRadius`/`maxRadius`의 `int()` 절사뿐이다(사소, R3).
- H2(사전 고정 증빙 한계)는 README `## 한계`에, H3(Wilson·413 매칭)·H4(n = 12, 구간, 독립 표본)·H5(순차이·집합)는 해당 절에 반영됐다.

### Issues / Risks

#### Blocking (계약 의무)

- **R-B1 main → helper 연결 미잠금**(1차 B2의 잔여): `src/face_mask.py:233`(threshold·label 인자)과 `:239`(대조 조건 이름)이 바뀌어도 모든 셀이 통과한다(N5, N6, N18).
  - 조치: CLI 테스트(`tests/test_face_mask.py:140-184`)에 다음 두 단언을 추가한다.
    - (a) 조건별 `edited_decision_flips`가 predictions.csv의 logit, `calibration.json`의 T·threshold, 표본 label로 독립 계산한 단방향 전환 수와 같다.
    - (b) `report['dependence_evidence']`가 report의 `gen_gray_face`·`gen_white_offface` shift와 config `min_gen_flip_fraction`으로 다시 계산한 값과 같다.
  - stub 모델 logit이 threshold 근처에 오지 않아 (a)가 약할 수 있다. 그렇다면 `predict_logits`를 monkeypatch해 전환이 생기는 logit을 주입한다.

#### Hardening recommendations (비차단)

- **R1** `tests/test_face_mask.py:96-97`: after가 threshold와 정확히 같은 경우(`>=` 포함)를 단언하는 케이스를 추가한다(N16).
- **R2** `src/failure_analysis.py:83`의 `sets.*.decision_flips`(양방향)와 `edited_decision_flips`(단방향)가 한 report에 공존한다. README나 report 키 이름에 정의 차이를 명시한다. 또는 P06-02c에서 단방향 helper로 통일한다.
- **R3** README 사후 명시 절에 Hough `dp=1`과 반지름 범위의 `int()` 절사도 적는다(P06-02c config 사전 고정 시 포함).

### Outstanding items

- GPU 전체 재실행(HEAD)은 소유자 GPU 작업으로 보류했다. GPU가 비면 다음을 실행해 predictions.csv·report.json byte 동일을 확인한다.

  ```bash
  docker compose --profile training run --rm -T -v $S:/scratch train python -m src.face_mask --config /scratch/rerun_config.yaml
  ```

- 이 기록의 추적 라운드 수정분은 커밋하지 않았다(working tree 변경).

### Reproduction(추적 라운드)

```bash
git status --short                      # 빈 출력
docker compose run --rm dev python -m pytest tests/test_face_mask.py -q; echo $?
docker compose run --rm dev python -m pytest -q; echo $?
python3 $S/recompute.py
$S/mutate2.sh <ID> '<old>' '<new>'      # N1~N18
docker compose run --rm -T -e PYTHONPATH=/app -v $S:/scratch -v /mnt/h/tracepector/images:/images:ro dev python /scratch/redetect.py
cmp $S/redetect.csv experiments/p06_failure_analysis/face_mask/detections.csv
```

# 2026-10-11 work log

## Goals

- P06-02b 원형 얼굴 가림 의존 진단의 독립검증을 받는다. blocking과 비차단 항목을 반영하고, 합격할 때까지 추적 검증을 반복한다.

## Completed work

### P06-02b 독립검증 루프 (5라운드, 최종 합격)

- 검증 기록: [p06_02b_face_mask.md](../../verifications/2026-10-11/p06_02b_face_mask.md). 검증자는 구현 맥락을 받지 않은 서브에이전트이고, 1~5차를 같은 에이전트가 맡았다.
- 1차(`aad9440`) 조건부 합격.
  - 보고 수치는 CSV 재계산 값과 전부 일치했다.
  - GPU 재실행 결과 report.json과 predictions.csv가 byte 동일했다.
  - 문제는 판정 규칙·전환 계산·조건 적용을 잠그는 테스트가 없다는 점이었다(변이 12개 중 10개 생존).
- 보강 내용:
  - `src/face_mask.py`: `largest_face`·`select_edits`·`decision_flips`·`dependence_evidence`로 분리했다. 전환은 config 문구대로 맞던 판정이 틀린 쪽으로 넘어간 경우만 센다(B3). 넓이가 같은 얼굴 상자는 위·왼쪽을 고른다(H1).
  - `tests/test_face_mask.py`: 6셀에서 22셀로 늘었다. 검출 기준은 config에서 읽는다(H6). 추가한 셀은 다음과 같다.
    - 검출기 edge·fill 단독 셀
    - tie-break, 원 크기, 조건 적용(labels·fill·r+3·off_face 제외) 셀
    - 전환 방향·threshold 경계 셀, 판정 규칙 행렬(0.05 경계 포함)
    - `main()` 연결 셀: 3가지 경우(얼굴 밖 최대·회색 최대·발동), `predict_logits`·threshold 0.7 monkeypatch
  - README: 사후 명시 절을 추가했다(B4·H7: off_face 배치·제외 168장, r+3, tie-break, Hough 상수). 이 밖에 경계 여유(H3), 얼굴 정밀도 n과 구간(H4), 순차이 8장 표현(H5), config·결과 동시 커밋 한계(H2), 두 가지 전환 정의(R2)를 적었다.
- 재실행(HEAD 코드, GPU): 전환 수 36/28/5/0, AUC, 판정은 같다.
  - gen_000799(test GEN)의 얼굴 상자가 무릎에서 실제 얼굴로 바뀌었다(동점 상자).
  - 그 결과 평균 변화가 흰 원 +10.19 → +10.20, 얼굴 밖 +1.91 → +1.89로 바뀌었다. README는 재실행 값으로 고쳤다.
- 추적 라운드:

| 라운드 | HEAD | 판정 | 남은 blocking |
| --- | --- | --- | --- |
| 2차 | `0b494d1` | 조건부 합격 | R-B1: `main()`이 helper에 넘기는 threshold·label·대조 목록 미잠금 |
| 3차 | `ff4636e` | 조건부 합격 | T-B1: 판정 True 방향 미잠금 |
| 4차 | `403b2d6` | 조건부 합격 | F-B1: 회색 대조 제거 미잠금 |
| 5차 | `c057ada` | **합격** | 없음 |

### 변이 테스트 (구현자 측, 커밋된 clean tree에서 `git checkout`으로 복원)

| 변이 | 위치 | 실패한 셀 |
| --- | --- | --- |
| M1 대조 비교 `>` → `<` | `dependence_evidence` | `test_dependence_rule_fires_only_when_both_conditions_hold[1-20-…-True]` |
| M2 전환 비율 조건 → `True` | `dependence_evidence` | `test_dependence_rule_…[49-1000-…-False]` |
| M3 helper threshold → 0.5 | `decision_flips` | `test_decision_flips_counts_only_correct_to_wrong_at_calibrated_threshold` |
| M4 미처리 표본 logit → 0.0 | `main()` combined | `test_face_mask_cli_reports_prevalence_shortcut_and_conditions` |
| M5 얼굴 원 반지름 2배 | `disc_for_face` | `test_disc_for_face_uses_long_side_times_diameter_ratio` |
| M6 edge 조건 제거 | `detect_disc` | `test_disc_detector_requires_dark_edge_even_when_filled` |
| M7 fill 조건 제거 | `detect_disc` | `test_disc_detector_requires_filled_inside_even_with_edge` |
| M8 labels 필터 제거 | `select_edits` | `test_select_edits_follows_condition_labels_position_and_fill` |
| M9 fill → 항상 255 | `_edit_for` | `test_select_edits_…` |
| M11 off_face 자리 없음 → 얼굴 위치 | `_edit_for` | `test_select_edits_…` |
| M13 양방향 전환 | `decision_flips` | `test_decision_flips_…` |
| M14 tie key 제거 | `largest_face` | `test_largest_face_breaks_area_ties_deterministically` |
| M15 r+3 제거 | `_edit_for` | `test_select_edits_…` |
| N5 호출부 threshold → 0.5 | `main()` | `test_face_mask_cli_wires_…[offface]` |
| N6 대조 → 회색만 | `main()` | `test_face_mask_cli_wires_…[offface]` |
| N16 `after >=` → `>` | `decision_flips` | `test_decision_flips_…` |
| N18 label 전부 GEN | `main()` | `test_face_mask_cli_wires_…[offface]` |
| N19 기준 → 1.01 | `main()` | `test_face_mask_cli_wires_…[white]` |
| N20 판정 → False | `main()` | `test_face_mask_cli_wires_…[white]` |
| N21 주 조건 → 회색 | `main()` | `test_face_mask_cli_wires_…[white]` |
| N22 artifact threshold → 0.5 | `main()` | `test_face_mask_cli_wires_…[offface]` |
| N23 판정 → True | `main()` | `test_face_mask_cli_wires_…[offface]` |
| N24 대조 → 얼굴 밖만 | `main()` | `test_face_mask_cli_wires_…[gray]` |

## Issues found

- 전환 방향 계약 불일치(B3)
  - 문제: config는 "REAL 판정으로 바뀐"(한 방향)인데 코드는 `!=`(양방향)로 셌다.
  - 결과: 이번 실행에는 역방향 전환이 없어 수치 영향은 없었다. 코드를 config에 맞췄다.
- 얼굴 상자 동점 비결정성(H1)
  - 문제: Haar 검출 순서에 따라 동점 상자 선택이 달랐다. 커밋본은 gen_000799에서 무릎 상자를 썼다.
  - 결과: 결정적 규칙으로 고친 뒤 실제 얼굴 상자를 고른다. 수치가 조금 바뀌었고 판정은 같다.
- stub calibration threshold 비결정성(V1, 비차단)
  - 문제: 테스트의 stub 학습·calibration을 세 번 돌리자 threshold가 0.517, 0.510, 0.5로 달랐다. 그래서 threshold 연결 가드가 실행에 따라 무력해질 수 있었다.
  - 결과: 해당 셀에서 threshold를 0.7로 고정했다. `src/train.py`는 seed를 고정하므로 원인은 다른 곳에 있고, 아직 조사하지 않았다.
- 경계 여유: 전환율 6.2%의 95% Wilson 구간은 4.5~8.5%다. 세 GEN 조건을 같은 413장으로 맞추면 4.8%로 5% 기준 아래다. 사전 규칙상 판정은 성립하지만 경계에 가깝다. P06-02c에서 구간을 넣어 재확인한다.

## Decisions

- B3(소유자 결정): 사전 고정 config 문구를 정본으로 하고 코드를 맞춘다. 사전 등록본을 사후에 고치면 사전 고정의 의미가 약해지기 때문이다.
- B4(소유자 결정): 기존 config는 고치지 않는다. 코드에만 있던 규칙은 README에 "사후 명시"로 적고, P06-02c의 새 config에서 사전 고정한다.

## Verification

- `tests/test_face_mask.py` 22 passed, 전체 72 passed(dev 컨테이너, exit 0).
- 전체 진단 GPU 재실행 1회(HEAD 코드). 0b494d1 이후 `src/`는 바뀌지 않았다.
- 검증자의 HEAD GPU 재실행은 소유자의 다른 GPU 작업(ai_writte_system) 때문에 하지 않았다. 판정 조건은 아니다. CPU 검출 재실행은 byte 동일했다.

## Next steps

- P06-02c 표본 확장 재진단: 새 config를 결과보다 먼저 커밋한다. val 포함, bootstrap 구간, 사후 명시 세부의 사전 고정, 두 전환 정의 정리를 포함한다.
- P06-04 오류 패턴 문서.
- V1: stub 학습·calibration 비결정성의 원인을 조사한다(비차단).

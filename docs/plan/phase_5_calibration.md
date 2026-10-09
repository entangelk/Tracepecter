# P05 — Score calibration

**상태:** Complete (2026-10-09)

## 목표·선행 조건

§18·§27 Phase 5에 따라 primary SigLIP checkpoint와 validation split으로 calibration parameter·threshold·0~100 score를 정의한다. 기존 P02/P03 checkpoint와 평가 스냅샷은 보존한다.

## 범위·검증

1. sigmoid 이전 logit 노출 → 기존 확률 출력 및 checkpoint 호환·포화 logit 회귀 가드.
2. temperature scaling·threshold 선정 → validation NLL 비악화, 양수 온도·단조 score·threshold 양방향 가드.
3. validation prediction CSV와 calibration artifact 생성 → val 행만 포함, checkpoint/metadata SHA256 결합.
4. Test A/B에 고정 parameter 적용 및 이미지 score CLI → baseline 비변경, 숫자 범위·동일 입력 결정성·artifact 불일치 거부.

## 실험 전 정의

- `p_cal = sigmoid(logit / T)`, `realism_score = 100 * p_cal`. REAL=1.
- T는 validation NLL 기준으로 선택한다. log(T) bounded golden-section search를 사용하고 T=1 및 양 끝값도 비교하므로 validation NLL이 raw보다 나빠지는 parameter를 선택하지 않는다. 범위/반복 수는 `configs/calibration.yaml`이 소유한다.
- threshold는 validation balanced accuracy 최대값으로 선택한다. 후보는 0/1·관측된 calibrated probability·0.5다. 동점이면 0.5에 가까운 값, 다시 동점이면 작은 값을 사용한다. `p_cal >= threshold`가 photographic_like이다. score threshold는 확률 threshold에서 유도하고 별도 저장하지 않는다.
- ECE는 equal-width bin의 REAL class probability와 관측 REAL 비율 차이(표본수 가중)다. NLL·Brier·ECE를 기록한다. ECE/Brier 개선을 강제하지 않고 실제 전후를 보고한다.
- Test A/B는 고정 artifact 적용 후의 진단 평가이며 fitting/threshold 선정에 사용하지 않는다. Test B 구성은 DB-04 유지.

## 계약·소유권

원본 logit은 모델, label/split은 metadata가 소유한다. validation CSV는 `image_id,logit`만 저장하며 label은 canonical metadata에서 읽는다. calibration artifact는 method·temperature·확률 threshold·checkpoint/metadata hash를 소유하고 inference가 소비한다. 0~100 score와 classification은 이 값에서 유도한다. 원래 checkpoint를 수정하지 않는다.

## 완료 조건·한계

validation prediction·parameter·threshold·score 정의·calibrated Test A/B 및 이미지 scoring이 동작하고 회귀 검증된다. 같은 입력은 같은 score이고 score 순서는 logit 순서와 일관된다. REAL/Generated 라벨의 확률 calibration이며 사람 체감 realism과의 일치는 별도 평가가 필요하다. GEN 근사중복·독립 최종 holdout·사람 평가는 후속 범위다.

방법 참조: [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html).

## 완료 근거

- [P05 artifact/지표/보고서](../../experiments/p05_calibration/README.md): val 820 ID/logit, temperature 0.79847842, probability threshold 0.69669911(score 69.67), 고정 Test A/B 적용.
- validation NLL/Brier/ECE 개선. Test B ECE는 개선됐으나 NLL/Brier는 조금 악화됐음을 명시했고 parameter를 Test에 맞춰 변경하지 않았다.
- CPU 전체 43 passed, CUDA 집중 10 passed. 실제 REAL/Generated score 및 같은 REAL 반복 결과 동일, val-only ID 집합·원본 checkpoint/metadata hash 보존 확인. 독립검증·mutation은 미수행.
- calibration/scoring 기능 및 validation 기준 결정 조건을 충족한다. 사람 체감 일치 또는 unseen calibration 전면 개선까지 판정하지 않는다.
- 다음은 P06 failure analysis(특히 Test B calibration 악화 포함).

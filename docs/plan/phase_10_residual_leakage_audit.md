# P10 — P09 미검토 후보의 잔여 누출 감사

**상태:** Waiting for Decision ([DB-09](../decision_briefs/DB-09_P10_residual-review-scope.md))

## 목표

P09-01이 미검토로 남긴 초기 후보 946,311쌍 가운데 현재 primary split(`data/versions/p09_r1/metadata.csv`)의 경계를 넘는 같은 class 쌍을 검토한다. 실제 누출을 찾고, 검토하지 않은 대역에는 잔여율의 상한을 남긴다. HANDOFF 다음 작업 2번의 "감사의 pHash/embedding 후보 추가 검토"에 해당한다(소유자 선택 2026-11-07).

## 선행 조건

- P09 Complete. 입력은 `grouping/candidate_run_01/input_lock.json`·`grouping/final/group_lock.json`·`split/split_lock.json`에 고정된 후보·판정·metadata다. 시작 전 이 hash들을 대조하고, 다르면 원인을 확인하기 전에 재사용하지 않는다.
- 비추적 전체 후보 `reports/errors/review/p09_leakage_repair/r1/candidate_run_01/candidates.csv.gz`의 hash는 `evidence_lock.json`과 대조한다.
- DB-09 결정(검토 범위·판정 주체).

## 범위

| ID | 작업 | 완료 증거 | 상태 |
| --- | --- | --- | --- |
| P10-01 | 경계 교차 미검토 후보 추출·대역 분류·고정 seed 표본 선택 | `experiments/p10_residual_leakage_audit/selection/`의 선택 목록·대역별 모수·입력 lock, 결정성·경계 계산 테스트 | Planned |
| P10-02 | 시각 판정(P09와 같은 판정 체계: 확정·다른 룩·미확정), 확정 관계의 directed top-10 확장 | 판정 CSV·비교 이미지 hash lock, 소유자 확인이 결정된 경우 확인 원본·최종본 | Planned |
| P10-03 | 결과 보고 | 경계별 확정·미확정 수, 표본 대역의 잔여율과 95% 상한(Clopper–Pearson), 한계 | Planned |

- 판정 체계와 이미지 비교 도구는 P09의 것을 재사용한다(`scripts/p09_review_pairs.py`). 새 코드는 선택·집계에 한정한다.
- 출력은 새 경로 `experiments/p10_residual_leakage_audit/`에 둔다. 비교 이미지 사본은 비추적 `reports/errors/review/p10_residual_leakage_audit/`에 둔다.

## 완료 조건

- 결정된 범위의 모든 쌍에 판정이 있고, 새 확정 관계의 directed 이웃 중 미처리가 0이다.
- r1 경계를 넘는 확정 관계 수를 보고하고, 1건 이상이면 r2 수리와 한계 기록 중 하나를 고르는 결정 브리프를 작성한다.
- 표본 대역은 쌍 비율과 상한으로만 보고하고 "누출 없음"이라고 주장하지 않는다.

## 병행 작업과 제외

- r1 metadata·`configs/primary.yaml`·checkpoint·calibration·P09 lock과 판정은 바꾸지 않는다. 재분할·재학습은 범위 밖이다.
- 신규 수집, 최종 독립 holdout, 사람 평가, P04 LoRA는 제외한다.
- GPU가 필요 없다(P09 embedding cache와 원본 이미지 사용).

## 관련 결정 브리프

- [DB-07](../decision_briefs/DB-07_P09_review-coverage.md)(Resolved): P09 우선순위 범위.
- [DB-09](../decision_briefs/DB-09_P10_residual-review-scope.md)(Open): P10 범위와 판정 주체.

# 2026-11-07 작업 기록

## 목표

- HANDOFF의 남은 작업 중 소유자가 고른 "감사의 pHash/embedding 후보 추가 검토"를 P10으로 진행한다.

## 완료한 작업

- P10 계획과 DB-09 작성(`7c557f8`). P09 미검토 946,311쌍 중 현재 r1 split 경계를 넘는 같은 class 쌍을 집계했다. REAL 426,596쌍, GEN 10,029쌍이다. P09 판정을 cosine 대역별로 나눈 확정률(REAL .91–.92 4/219, .85–.90 0/376)을 근거로 검토 범위 선택지를 제시했다. 작업하면서 DB 인덱스의 DB-08 상태가 Open으로 남아 있던 것을 Resolved로 바로잡았다.
- DB-09 소유자 결정: 결정 1 A(상위 전수 + 하위 층화 표본), 결정 2 R1(에이전트 1차 판정 + 경계 교차 확정·미확정만 소유자 확인)(`41de116`).
- P10-01(`7d9533d`): `scripts/p10_select.py`를 추가했다. P09 r1 metadata·그룹 lock·전체 후보 queue의 hash를 대조하고, 같은 split·기존 판정·다른 class 쌍을 제외한 뒤 대역별로 선택한다(seed `20261107`, 대역 이름별 독립 난수). 선택 결과는 712쌍이며 모집단 수가 DB-09 집계와 일치한다. 테스트 5개(대역 경계 .90 포함/.8999 제외, test_unseen 경계 GEN 포함, 미검토 GEN 대역 집계, 같은 split·기존 판정·다른 class 제외, 표본 크기·입력 순서 무관·seed 의존, 실데이터 lock 변조 거부)를 넣었다. 새 경로에 다시 실행해 `pairs.csv`·`summary.json` hash가 같음을 확인했다.
- P10-02 에이전트 판정: `scripts/p10_review_sheets.py`로 원본 hash를 확인한 비교 시트 89장을 만들고 712쌍을 모두 판정했다(`review/agent_verdicts.csv`).
  - REAL ≥.90 236쌍: 확정 6, 미확정 3, 다른 룩 227. 확정 6쌍은 모두 r1 경계를 넘는다(train↔val 3, train↔test 2, val↔test 1).
  - REAL 하위 표본 300쌍과 GEN 176쌍은 모두 다른 룩이다. GEN 176쌍 중 prompt 공유는 2쌍, seed 공유는 0쌍이다. 독립 렌더는 다른 룩으로 판정하고, 판정 사유에 계보 공유 여부를 적었다.
- 이웃 확장: `scripts/p10_neighbors.py`가 P09 `review_neighbors`에 P09 최종 판정과 P10 판정을 함께 넣어 호출한다. 결과 101쌍은 모두 P10 확정 성분에서 나왔다. P09에서 이미 닫힌 성분에서는 새 이웃이 0쌍이었다. 101쌍 모두 다른 룩이었고, 다시 계산한 미처리 이웃은 0쌍이다.
- 소유자 확인 페이지: `scripts/p10_owner_review.py`로 경계 교차 확정·미확정 9쌍의 이미지 내장 HTML을 만들었다(에이전트 판정 비공개, CSV 저장). 확인 대상은 `review/owner_pending.csv`, 페이지·입력 hash는 `owner_pending.lock.json`에 고정했다. `owner_pairs` 필터 양방향 테스트를 추가했다(테스트 6 passed).
- [감사 보고](../../../experiments/p10_residual_leakage_audit/README.md)를 쓰고, 대역별 집계와 Clopper–Pearson 상한(0/100 → 3.62%)을 `review/summary.json`에 기록했다. 계획·인덱스·HANDOFF·CHANGELOG·인포그래픽을 갱신했다.

## 판단과 근거

- P09 비교 도구(`p09_review_pairs.py`)는 P09 후보 목록 구조에 묶여 있다. 고치면 P09 source hash가 달라지므로 같은 배치의 P10 전용 시트 스크립트를 따로 두었다.
- 확정 기준은 P09와 같다. 같은 옷차림이 같은 촬영 세트에서 찍힌 다른 컷이면 확정이다. 같은 촬영 공간에서 착장만 다른 사례(창가 스튜디오, 콘크리트 벽 등)는 다른 룩으로 판정했다. 옷은 같은데 공간이나 소품이 다른 3쌍은 미확정으로 남겼다.
- P09 계획 완료 조건의 "알려진 같은 룩 교차 0"은 이번 잠정 결과로 성립하지 않는다. r1 artifact는 바꾸지 않았다. 수리 여부는 소유자 확인 뒤 별도 결정 브리프로 다룬다.

## 다음 작업

- 소유자가 `reports/errors/review/p10_residual_leakage_audit/owner/index.html`에서 9쌍을 고르고 저장한 CSV를 받는다. 받으면 최종 판정을 고정한다. 소유자가 미확정을 확정으로 바꾼 쌍이 있으면 그 성분의 directed 이웃을 추가로 검토한다.
- 확정이 1건 이상이면 r2 수리(재분할·재학습·재보정)와 한계 기록 중 하나를 고르는 결정 브리프를 쓴다.

# P10 잔여 누출 감사 — r1 경계 교차 미검토 후보

**상태: 에이전트 판정과 이웃 확장 완료, 소유자 확인 대기(DB-09 R1).** [P10 계획](../../docs/plan/phase_10_residual_leakage_audit.md) · [DB-09](../../docs/decision_briefs/DB-09_P10_residual-review-scope.md) · [P09 그룹 근거](../p09_leakage_repair/r1/grouping/README.md).

## 요약

P09가 미검토로 남긴 후보 중 현재 primary split(`data/versions/p09_r1/metadata.csv`)의 경계를 넘는 같은 class 쌍만 대상으로 했다. 상위 대역은 전수 검토하고 하위 대역은 고정 seed 표본으로 검토했다. 이웃 확장까지 합쳐 813쌍을 판정했다.

- **REAL cosine ≥.90(236쌍 전수): 같은 룩 확정 6쌍, 미확정 3쌍.** 모두 r1 split 경계를 넘는다. 확정 6쌍은 train↔val 3, train↔test 2, val↔test 1이다. 평가 쪽 이미지는 val 4장(1240756·1233583·956837·520383)과 test 3장(218797·424673·1083989)이다.
- REAL 하위 표본 300쌍(.85–.90, .80–.85, <.80 각 100)과 GEN 176쌍(≥.95 전수 76, .90–.95 표본 100)에서는 같은 룩이 0건이다.
- 확정 6쌍의 12장에서 directed top-10 이웃 101쌍을 추가로 판정했고 모두 다른 룩이었다. 재계산한 미처리 이웃은 0이다.
- 판정자는 에이전트(Claude) 1명이다. 경계 교차 확정·미확정 9쌍은 소유자 확인 전까지 잠정 결과다. 이 감사는 r1 metadata·primary·checkpoint·calibration을 바꾸지 않았다.

## 대역별 결과

| 대역 | 모집단(쌍) | 검토 | 확정 | 미확정 | 95% 상한(쌍 비율) | 상한 환산(쌍) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| REAL ≥.90 | 236 | 236(전수) | 6 | 3 | — | — |
| REAL .85–.90 | 4,419 | 100 | 0 | 0 | 3.62% | 160 |
| REAL .80–.85 | 17,130 | 100 | 0 | 0 | 3.62% | 620 |
| REAL <.80 | 404,811 | 100 | 0 | 0 | 3.62% | 14,661 |
| GEN ≥.95 | 76 | 76(전수) | 0 | 0 | — | — |
| GEN .90–.95 | 1,677 | 100 | 0 | 0 | 3.62% | 61 |
| GEN <.90 | 8,276 | 0 | — | — | 미검토 | — |

상한은 표본 100쌍에서 0건일 때의 양측 95% Clopper–Pearson 상한(1−0.025^(1/100))이다. 쌍 비율이며 누출 이미지 수나 성능 영향이 아니다. 대역이 큰 REAL <.80은 상한 환산이 크다. 이 숫자는 "누출이 그만큼 있다"는 뜻이 아니라 표본 100쌍으로는 그 이하를 보장하지 못한다는 뜻이다. P09 판정에서도 <.85 대역의 확정은 339쌍 중 3쌍뿐이었고, 그 3쌍도 확정 성분의 이웃 조회에서 나왔다.

## 판정 기준

- **REAL**: P09와 같은 기준이다. 같은 옷차림이 같은 촬영 세트(배경·소품·바닥)에서 찍힌 다른 컷이면 확정이다. 같은 촬영 공간이라도 착장이 다르면 다른 룩이다. 같은 제품이라도 배경·코디가 다르면 다른 룩이다. 옷은 같은데 촬영 공간이나 이너·신발이 달라 판단하기 어려우면 미확정으로 남긴다.
- **GEN**: 선택된 GEN 176쌍 중 prompt를 공유하는 쌍은 2쌍이고, noise seed를 공유하는 쌍은 0쌍이다. 비슷한 주제(갈색 롱코트, 빨강 홀터 원피스 등)를 독립적으로 렌더링한 결과다. 인물·배경·세부가 다른 독립 렌더는 다른 룩으로 판정했고, 거의 같은 이미지인 근사중복만 확정 대상으로 봤다. P09는 GEN 100쌍 중 66쌍을 미확정으로 두었는데, 이번에는 계보 정보를 함께 확인해 이 기준을 명시적으로 적용했다. 판정 사유에 각 쌍의 prompt/seed 공유 여부를 적었다.

## 경계 교차 확정·미확정(소유자 확인 대상)

| # | 쌍 | split | 에이전트 판정 | 근거 |
| --- | --- | --- | --- | --- |
| 12 | 1240756 / 218797 | val / test | 확정 | 회색 체크 티어드 원피스와 흰 선반 촬영 세트, 가방 유무만 다름 |
| 38 | 1233583 / 1233589 | val / train | 확정 | 갈색 후드 재킷·흰 티·회색 무지 배경의 전신/확대 컷 |
| 52 | 956837 / 956848 | val / train | 확정 | 검정 플레어 미니스커트·레깅스·운동화와 나무 스툴/마른 가지 세트 |
| 94 | 424663 / 424673 | train / test | 확정 | 카키 밴딩 바지·흰 티와 유리병 마른 가지 세트의 전신/확대 컷 |
| 120 | 1083989 / 1083999 | test / train | 확정 | 아이보리 턱 와이드 바지·파란 티와 그림 액자/헤링본 바닥 세트 |
| 131 | 1082948 / 520383 | train / val | 확정 | 흰 크롭 바지·파란 티와 책 선반/스툴 세트 |
| 34 | 568403 / 568442 | test / train | 미확정 | 같은 콘크리트 벽·검정 롱코트이나 이너·부츠 색이 다름 |
| 58 | 489659 / 918978 | val / train | 미확정 | 같은 린넨 재킷·반바지 세트이나 배경·가방이 다름 |
| 102 | 889872 / 947039 | train / test | 미확정 | 갈색 재킷·청바지가 비슷하나 촬영 공간이 다름 |

소유자 확인은 판정을 숨긴 독립 HTML 페이지로 받는다. 페이지는 비추적 `reports/errors/review/p10_residual_leakage_audit/owner/index.html`(약 2MB, 이미지 내장)이며 브라우저로 열어 9쌍을 모두 고르고 **CSV 저장**을 누른다. 확인 대상과 페이지 hash는 [owner_pending.csv](review/owner_pending.csv)와 `owner_pending.lock.json`에 고정했다.

## 해석과 한계

- 상위 대역 전수 결과는 P09 경계 재감사 범위 밖에서 **r1 split의 같은 룩 교차가 남아 있음**을 보여 준다(소유자 확인 전 잠정 6쌍). 평가 표본 대비 규모는 val 820장 중 4장, test 800장 중 3장이다. P09 계획 완료 조건의 "알려진 같은 룩 교차 0"은 이제 성립하지 않는다. 소유자 확인으로 1건 이상 확정되면 계획대로 r2 수리와 한계 기록 중 하나를 고르는 결정 브리프를 올린다.
- 하위 대역은 표본 상한만 있다. 개별 누락을 찾지 않았다. GEN <.90 8,276쌍은 미검토다.
- 후보 자체가 P09의 탐색 범위(이미지별 top-10 합집합·REAL pHash≤26·GEN pHash≤10)에서 나왔다. 그 밖의 쌍은 이 감사의 모집단에 없다.
- 단일 판정자이며 독립검증이 아니다. 경계 교차가 아닌 "다른 룩" 판정에는 사람 확인이 없다.

## 산출물

| 경로 | 내용 |
| --- | --- |
| `selection/` | 대역별 선택 712쌍, 모집단 수, 입력 lock(r1 metadata·그룹 lock·전체 후보 queue hash) |
| `review/agent_verdicts.csv` | 712쌍 판정·사유·시트 위치 |
| `neighbors_round_01/` · `review/agent_verdicts_neighbors_round_01.csv` | 확정 성분 directed top-10 이웃 101쌍과 판정 |
| `neighbors_closure/` | 두 판정을 모두 넣은 재계산, 미처리 0쌍 |
| `review/summary.json` | 대역별 집계·상한·경계별 확정/미확정 수 |
| `review/owner_pending.csv` · `.lock.json` | 소유자 확인 9쌍과 페이지 hash |

비교 시트(712쌍 89장, 이웃 101쌍 13장)와 각 `sheets_lock.json`은 비추적 `reports/errors/review/p10_residual_leakage_audit/`에 있다.

## 재현

```bash
python3 -m scripts.p10_select --out /tmp/p10_selection
python3 -m scripts.p10_review_sheets --selection experiments/p10_residual_leakage_audit/selection \
  --out /tmp/p10_sheets --image-root /mnt/h/tracepector/images
OPENBLAS_NUM_THREADS=1 python3 -m scripts.p10_neighbors \
  --reviews experiments/p10_residual_leakage_audit/review/agent_verdicts.csv \
  experiments/p10_residual_leakage_audit/review/agent_verdicts_neighbors_round_01.csv --out /tmp/p10_closure
docker compose run --rm -T dev python -m pytest tests/test_p10_select.py -q
```

모든 출력 경로는 존재하지 않아야 한다. 이미지 경로는 이 머신의 예시다. 선택은 seed `20261107`과 대역 이름으로 결정된다. 입력 순서를 바꿔도 결과가 같다는 점을 테스트로 확인했다.

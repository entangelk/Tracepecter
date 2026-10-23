# P09-01 후보 확장과 1차 시각 검토

**상태: DB-07의 우선순위 범위 종결, 배정 그룹 고정. 전체 후보 독립성 통과를 의미하지 않는다.** [P09 계획](../../../../docs/plan/phase_9_leakage_repair.md) · [DB-07](../../../../docs/decision_briefs/DB-07_P09_review-coverage.md).

## 입력과 재현

P08 감사 lock의 input 3·source 8·artifact 13개 SHA-256이 모두 일치한다. 47개 cache 청크의 총 6,000×768 feature를 읽고 identity·shape·유한값을 검사했다. metadata hash가 고정한 행 순서로 P08의 2,220개 최근접 query를 재계산해 target cosine과 최대 cosine이 2e-6 이내임을 확인했다. 이는 cache 순서의 일관성 근거이며 과거의 모든 sample 입력을 암호학적으로 증명하는 ledger는 아니다. 새 모델 추론·GPU 실행은 하지 않았다.

```bash
# 모든 출력 디렉터리는 새 경로여야 한다. 기존 출력이 있으면 거부한다.
OPENBLAS_NUM_THREADS=1 python3 -m scripts.p09_group_candidates \
  --out experiments/p09_leakage_repair/r1/grouping/candidate_run_01 \
  --queue reports/errors/review/p09_leakage_repair/r1/candidate_run_01
python3 -m scripts.p09_review_pairs \
  --run experiments/p09_leakage_repair/r1/grouping/candidate_run_01 \
  --out reports/errors/review/p09_leakage_repair/r1/visual_batch_01_reproduced \
  --image-root /mnt/h/tracepector/images --start 0 --count 48
python3 -m scripts.p09_filename_sequences \
  --label-zip '/mnt/h/tracepector/data/K-Fashion 이미지/Training/라벨링데이터.zip' \
  --out experiments/p09_leakage_repair/r1/grouping/filename_run_01
docker compose run --rm -T -e OPENBLAS_NUM_THREADS=1 dev python -m pytest \
  tests/test_p09_group_candidates.py tests/test_deduplicate.py \
  tests/test_split_dataset.py tests/test_p08_leakage_audit.py -q
```

위 호스트 절대 경로는 2026-10-20 이 머신의 배치 예시이며 환경에 맞게 인자를 바꾼다. 후보 계산은 CPU·NumPy/Pillow를 사용한다. Docker에서 실이미지를 읽으려면 image root를 read-only mount한다.

## 후보 생성 범위

- REAL 3,000장 전부를 split과 무관하게 비교한 top-10 합집합과 pHash≤26, 기존 REAL 그룹, 옛 최근접/시드 검토/교차 pHash를 포함했다.
- GEN은 3,000장 전부의 top-10과 pHash≤10을 사용했다. REAL/GEN을 넘는 옛 후보도 근거와 함께 보존하지만 다른 class의 그룹 결합은 거부한다.
- 원본 파일명은 metadata의 ID 경로에서 복원할 수 없다. Training 라벨 zip에서 JSON 3,000개를 읽고 기존 `parse_image_name`·`derive_look_group`으로 별도 유래 표를 저장했다. 782장에 파일명 그룹이 있고 15쌍 모두 기존 그룹 안이라 새 관계는 없었다. zip 전체와 개별 JSON hash를 저장했다.
- 숫자 ID의 근접은 촬영 시퀀스 근거로 쓰지 않았다. prompt/seed 공유도 같은 룩의 확정 관계로 쓰지 않는다.

| 출력 | 결과 |
| --- | --- |
| 전체 후보 | 947,696쌍, 압축 CSV는 `reports/errors/review/p09_leakage_repair/r1/candidate_run_01/candidates.csv.gz`, 비추적 |
| REAL/REAL | 924,265쌍(REAL pHash≤26만 907,609쌍) |
| GEN/GEN·다른 class | 23,363·68쌍 |
| 우선순위 후보 | 47,456쌍, `candidate_run_01/priority_candidates.csv` |
| 옛 검토 | 확정 8·미확정 6, `candidate_run_01/seed_review.csv` |
| GEN의 train 대비 prompt+seed 공유 | val 0 / test 0 / test_unseen 420; positive prompt 공유는 108 / 132 / 480 |

후보 이유는 중복되므로 이유별 수의 합은 전체 쌍 수와 다르다. 전체 후보 수는 동일 이미지·같은 룩 확정 수가 아니다. `candidate_run_01/input_lock.json`에 cache 47개·입력·코드·출력·비추적 queue의 hash를 고정했다. 파일명 유래는 `filename_run_01/`의 별도 보충 artifact이며 첫 queue를 덮어쓰지 않았다.

## 첫 배치 실이미지 검토

옛 14쌍과 기존 그룹 내부 관계를 제외한 REAL 우선순위 후보 23,984쌍에서 cosine 내림차순·ID 동점 순서의 첫 48쌍을 비교했다. 원본 hash를 감사와 대조한 비교 이미지 6장을 보고 판정했으며 시각 근거를 `visual_review_batch_01.csv`에 기록했다. 판정자는 Codex(root)이며 독립검증으로 주장하지 않는다. 작거나 모호한 관계는 확정을 보류했다.

- 같은 룩 18·다른 룩 25·미확정 5쌍.
- 새 확정 관계의 split은 train/train 9·train/val 4·train/test 1·val/test 4다. 옛 확정 8쌍과 별개이며 같은 성분의 여러 관계를 포함하므로 독립된 누출 그룹 수와 다르다.
- 새 사례: `1283747/1283767/646833`의 흰 상의·보라 바지·끈구두와 커튼/꽃병/스툴; `1335623/1335625/1335639/705886`의 베이지 원피스·검정 샌들과 몰딩/야자 배경. 옛 시드를 시작점으로 추이 관계가 확장된다.
- 반면 청바지의 비슷한 구도라도 신발·상의·찢김/밑단·소품이 다른 사례가 많다. cosine 임계값으로 자동 확정하지 않는다.

초기 REAL 그룹+옛 확정 8+새 확정 18의 연결 성분을 6,000 ID에 투영한 `provisional_groups_after_batch_01.csv`는 5,907성분이다. GEN 3,000장은 이번 배치에서 미검토라 단독 성분이다. 첫 배치 시점에는 미확정 6+5쌍을 결합하지 않았다. 최종 공동 배정은 아래 후속 범위에서 별도로 처리했다. `batch_01_lock.json`에 검토·투영·이미지 hash·재현용 비교 이미지를 고정한다.

## 후속 우선순위 검토와 최종 배정

소유자는 전수 수동 검토 대신 우선순위 검토와 미검토 범위 명시를 선택했다(DB-07). 초기 REAL 500·GEN 100쌍은 작업자가 정한 실행 범위다. REAL 500쌍은 확정40·다른 룩442·미확정18이며, GEN 100쌍은 다른 룩34·미확정66이다. GEN은 비슷한 의상 윤곽의 다른 렌더가 많아 같은 룩으로 확정하지 않았다.

확정 관계와 연결된 배정 성분의 각 멤버에서 **자신의 같은 class top-10**을 조회했다. 자신을 제외하고 cosine 내림차순·ID 동점 순서로 이웃을 고른다. 타인의 top-10에 들어오는 모든 역방향 이웃까지 재귀 확장하지 않는다. 첫 이웃714쌍, 다음54쌍을 처리했고 `neighbor_closure.json`의 재계산에서 미처리 이웃은0이다. 확정된 시각 관계의 별칭으로만 기존 판정을 투영하고, 옛 pHash 그룹이나 보수적 공동 배정을 시각적 동일성 근거로 쓰지 않는다.

반복 이미지 출력을 줄이기 위해 원본 hash를 확인한 이미지별 카탈로그를 사용했다. `neighbor_catalog.csv`·`reference_catalog.csv`·`neighbor_catalog_review.csv`가331개 새 이미지와 기준 성분/판정을 추적한다. **관계 행 수는 모든 쌍을 새 원본 나란히 보기로 검토한 횟수가 아니다.** 직접 비교, 이미지별 카탈로그 비교, 확인된 시각 관계를 통한 기존 판정의 투영, 불확실성 보존을 포함한다. 비교 자료에서 추가로 발견한 관계는 `visual_review_catalog_extra.csv`에 구별했다.

- `491169/491172`: 크림 무칼라 재킷·흰 이너·청바지의 train/test 다른 컷.
- `723640/723642`: 갈색 상의·회색 트위드 짧은 치마의 val/test 전신/확대 컷.
- `664930`: 기존 `664910/976218`의 청재킷·꽃무늬 원피스·벽돌 출입문/계단 촬영 시퀀스에 연결.
- `1135750/498574`: 잔 도트 프릴 상의·청바지·빨간 구두와 창문 그림자가 일치하며 옛 그룹 안의 관계다.

### 시각적 동일성과 배정 제약 구별

옛 pHash 그룹에 다른 착장이 함께 포함된 사례가 있었다. `1333531`의 초록 원피스와 `1335623`의 베이지 원피스, `108028`의 마네킹과 `979061`의 실사 착장은 같은 시각적 룩으로 취급할 수 없다. 옛 그룹을 분해하지 않는 계획에 따라 공동 배정 제약만 보존했다.

`final/visual_reviews.csv`는 시각 판정을 보존한다. 미확정269쌍은 `final/conservative_constraints.csv`로 별도 투영해 같은 split에 둔다. 다른 룩이라는 판정은 보수적 배정 성분 안에 함께 존재할 수 있다. 서로 다른 룩을 하나의 확정 관계로 묶는 모순은 거부하지만, 같은 split 그룹에 두는 조치는 허용한다. 신규 GEN 그룹이 unseen 생성기와 standard 생성기를 함께 묶으면 최종 고정을 거부한다.

| 최종 산출물 | 결과 |
| --- | --- |
| `final/visual_reviews.csv` | 관계1,386행: 확정53·다른 룩1,064·미확정269 |
| 확정 관계의 기존 split | train/test14·train/val15·val/test6·train 내부16·val 내부1·test 내부1 |
| `final/group_mapping.csv` | 6,000 ID 전부, 배정 성분5,692개 |
| 최대 배정 성분 | REAL89장(하의67·상의13·아우터9), 그다음 REAL44장·GEN19장. 같은 룩 수가 아닌 보수적 배정 크기 |
| 전수 후보와의 교집합 | 검토 관계 중1,385쌍이 초기 후보에 포함, 범위 밖 추가1쌍 |
| 미검토 초기 후보 | **946,311쌍**. 다른 룩으로 판정하거나 자동 병합하지 않음 |
| `final/group_lock.json` | metadata·감사·관계 입력·코드·출력 hash 결합 |
| `evidence_lock.json` | 그룹 lock과 카탈로그·파일명/초기 후보 lock·비추적 비교 이미지 hash 결합 |

최대89장 그룹은 여러 착장을 포함하는 공동 배정 단위다. 이 성분을 ‘같은 룩89장’으로 설명하지 않는다. P09-02에서 성분을 쪼개지 않고 배정할 때 목표 비율·셀별 표본/성분 수에 미치는 영향을 확인해야 한다.

### 재현과 버전

```bash
# 누적 검토 CSV가 준비된 뒤 확정 멤버의 새 이웃을 생성한다.
# 옛14쌍은 도구가 암묵적으로 가져오므로 --neighbors-from에 중복 전달하지 않는다.
OPENBLAS_NUM_THREADS=1 python3 -m scripts.p09_group_candidates \
  --out /tmp/p09_neighbors_check --queue /tmp/p09_neighbors_queue \
  --neighbors-from \
  experiments/p09_leakage_repair/r1/grouping/visual_review_batch_01.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_batch_02.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_gen_batch_01.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_neighbors_round_01.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_catalog_extra.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_neighbors_round_02.csv
# 0개 이웃·고정 source/review hash를 확인한 neighbor_closure.json으로 최종 투영 재현
python3 -m scripts.p09_finalize_groups --out /tmp/p09_groups_check
# GEN은 --label 0 --unique-images, REAL은 기본 --label 1로 비교 자료 생성 가능
```

초회 `candidate_run_01`의 코드는 `6547a54` 시점이다. 후속 코드에는 시각 관계/배정 제약 구별과 이웃·최종 고정 경로가 추가됐으며 기존 lock을 덮어쓰지 않았다. 초회 lock의 source hash와 현재 source가 다른 것은 이 버전 차이다. `neighbors_directed_round_01`은 후속 구현의 directed 규칙과 후보 집합을 대조한 탐색 산출물이다. 역방향 후보까지 포함한 미사용 탐색과 rich CSV 투영 결함으로 실패한 실행의 부분 출력은 비추적 `reports/errors/review/p09_leakage_repair/r1/`에 보존했다. 최종 도구는 필요한4열만 생성 snapshot에 투영하며 원래 rich CSV를 보존한다.

## 남은 작업

P09-01은 DB-07의 한정 범위에서 종결했다. 현재 새 metadata와 경계 대조는 [P09-02 보고서](../split/README.md)를 참조한다. 다음은 P09-03의 새 cohort 진단 사전등록과 재학습이다. 기존 `data/metadata.csv`·primary·checkpoint·calibration은 보존본이며 학습은 미착수다.

범위 밖 누락·촬영 출처/압축 교란·개발에 노출된 평가 표본 문제는 남는다. 그룹 고정 자체는 split 변경이 아니며, P09-02 재분할 이후에도 평가는 개발 평가다. 누출 완전 제거·미접촉 일반화 성능을 주장하지 않는다.

## 검증

- 최신 Docker 집중30 passed(4.39초): 후보/캐시/원본 hash, 추이 관계, 옛 그룹/공동 배정과 시각 동일성 구별, directed 이웃, rich CSV CLI 연결, 최종 GEN holdout 충돌/정상 경계.
- 마지막 CLI 투영 가드와 최종화2셀 추가 전 전체 CPU227 passed / 1 skipped(47.50초), 이후 추가3셀 포함 위 집중30 passed. skip은 기존 실제 YuNet opt-in smoke이며 기존 Pillow warning12개 외 실패가 없다.
- 별도 BFS 자가 대조로 기존 그룹·확정/미확정 관계의 연결 성분과 최종5,692성분이 정확히 같음을 확인했다. 모든6,000 ID·옛 그룹·확정 관계 보존 및 최대 크기를 확인했다. 별도 작업자의 독립검증으로 표현하지 않는다.
- 생산 코드 변이·GPU 실행·재분할은 하지 않았다. 기존 감사24개 hash와 최종 lock/source/output hash를 대조했다. 기존 artifact는 변경하지 않았다.

# P09-01 후보 확장과 1차 시각 검토

**상태: 우선순위 검토 진행 중, 최종 그룹 미확정.** [P09 계획](../../../../docs/plan/phase_9_leakage_repair.md) · [DB-07](../../../../docs/decision_briefs/DB-07_P09_review-coverage.md).

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

초기 REAL 그룹+옛 확정 8+새 확정 18의 연결 성분을 6,000 ID에 투영한 `provisional_groups_after_batch_01.csv`는 5,907성분이다. GEN 3,000장은 이번 배치에서 미검토라 단독 성분이다. 미확정 6+5쌍은 미해결이며 자동 결합하지 않았다. `batch_01_lock.json`에 검토·투영·이미지 hash·재현용 비교 이미지를 고정한다.

## 남은 작업과 결정

소유자는 우선순위 검토로 조정하고 미검토 범위를 명시하도록 선택했다(DB-07). 전체 후보를 확정 관계로 오인하지 않는다. 최종 그룹 lock 이전에 추가 우선순위·확정 성분 이웃을 검토한다. 현재 P09-02 metadata는 생성하지 않았으며 데이터 독립성 통과를 선언하지 않는다.

## 검증

후보·hash·cache·연결 성분·원본 파일명·실이미지 변조 거부의 새 9셀을 포함해 Docker 집중 23 passed. 전체 CPU 회귀는 마지막 2셀 추가 전에 221 passed / 1 skipped(50.20초), 이후 추가 2셀 포함 집중 23 passed다. skip은 기존 opt-in YuNet smoke이며 기존 Pillow warning 12개 외 실패가 없다. 코드 변이는 하지 않았다. 공개 CLI의 `--help`, 기존 출력 거부, 후보/이미지/투영 hash를 확인한다. 기존 metadata·primary·학습/보정 artifact는 변경하지 않는다.

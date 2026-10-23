# P09-02 결정적 그룹 재분할

**상태: 한정 검토 범위의 재분할·경계 대조 완료. 전체 후보 독립성 통과가 아니다.**

[P09 계획](../../../../docs/plan/phase_9_leakage_repair.md) · [고정 그룹과 검토 한계](../grouping/README.md) · [작업 기록](../../../../docs/daily_logs/2026-10-23/work_log.md).

## 입력·소유권·보존

- 원본 `data/metadata.csv`의 6,000개 ID·12열 schema를 보존한다. 변경 가능한 값은 REAL의 `look_group`과 전체 `split`뿐이다. `grouping/final/group_mapping.csv`의 5,692개 배정 성분이 유일한 배정 단위다. GEN 그룹은 별도 매핑을 소비하며 REAL용 `look_group`에 복제하지 않는다.
- `group_lock.json`의 metadata·감사24개 파일·관계 입력·코드·출력·이웃 closure hash를 검증했다. `evidence_lock.json`의 그룹 lock·보충 artifact와 초기 후보 출력·전체 queue hash도 대조했다. 옛 source hash는 해당 버전의 근거로 보존하며 덮어쓰지 않았다.
- 원본 이미지 6,000장의 파일 SHA-256을 P08 `image_audit.jsonl`의 ID별 hash와 대조했다. 새 metadata의 모든 경로와 불변 필드는 원본과 같다. 기존 metadata·primary·checkpoint·calibration·301장 주석·감사 원자료를 변경하지 않았다.
- 새 metadata의 정본은 `data/versions/p09_r1/metadata.csv`다. metadata hash와 생성 코드 hash, 검증한 입력·출력 hash는 [split_lock.json](split_lock.json)에 저장한다. 얼굴 상자 cache에 split을 복제하지 않는다.

## 배정 결과

기존 분할기의 그룹 크기 내림차순·그룹 키 사전순 규칙과 source_type×category×generator 셀별 목표 결손 합을 재사용했다. 입력/매핑의 행 순서를 바꿔도 ID별 배정과 출력 행 정렬은 같다. 기존 그룹을 분해하거나 표본을 삭제하지 않았으며 sd35는 전량 `test_unseen`을 유지한다.

| split | REAL | GEN | 합계 |
| --- | --- | --- | --- |
| train | 2,100 | 1,680 | 3,780 |
| val | 452 | 368 | 820 |
| test | 448 | 352 | 800 |
| test_unseen | 0 | 600 | 600 |

- 기존 split과 ID별 배정이 달라진 이미지는 2,464장이다. 전체 표본 수가 같다고 동일 평가 cohort로 해석하지 않는다.
- 배정 성분·옛 그룹·확정53쌍·미확정269쌍·옛 확정8쌍의 split 교차는0이다. 최대 성분89장은 여러 착장을 포함하는 보수적 공동 배정 단위이며 그대로 보존했다.
- [split_report.json](split_report.json)의 `cells`에 셀×split별 목표/실제 수·비율·독립 배정 성분 수·최대 성분 크기를 기록했다. 모든 standard 셀은 train/val/test에 표본이 있고 두 class도 각 split에 존재한다. 셀별 실제 비율은 목표에서1%p 미만 차이다. 성분 수는 시각적으로 확정된 독립 룩 수를 의미하지 않는다.
- Test B는 새 standard test의 REAL448장과 sd35 GEN600장이다. 실제 소비자인 `MetadataDataset`과 `evaluation_indices`의 연결 테스트로 train/val REAL 제외와 새 test REAL 재사용을 확인했다.

## 새 경계의 검토 범위 대조

초기 우선순위 REAL500·GEN100을 원래 후보에서 다시 선택하고 고정 판정 포함 여부를 확인했다. 선택 규칙과 확정 성분 멤버의 자신의 같은 class directed top-10은 split에 의존하지 않는다. 원본 metadata 순서와 hash가 결합된 cache47개를 재검증하고 2,220개 최근접 query를 재계산한 후, 동일한 최종 검토 입력으로 directed 이웃을 다시 생성했다. 미처리 후보는0이다. 새 split으로 바꿔도 조회되는 범위가 같으므로 기존 판정을 재사용한다.

고정 판정1,386행 전부를 새 경계로 재투영한 결과는 [review_boundaries.csv](review_boundaries.csv)에 저장했다. 이는 새로운 원본 나란히 보기1,386회를 뜻하지 않으며 직접 비교·이미지 카탈로그·확정 시각 관계 투영·불확실성 보존이라는 기존 검토 방식을 유지한다.

| 새 교차 경계 | 다른 룩 판정 | 확정 동일 룩 | 미확정 |
| --- | --- | --- | --- |
| train↔val | 141 | 0 | 0 |
| train↔test | 166 | 0 | 0 |
| val↔test | 4 | 0 | 0 |
| standard↔test_unseen | 0 | 0 | 0 |

범위 안 미해결 교차가 없어 그룹 보강으로 돌아갈 필요는 없다. 범위 밖 **미검토 초기 후보946,311쌍**은 그대로 남으며 다른 룩으로 판정하지 않았다.

## GEN 계보와 평가 한계

새 train 대비 계보 공유 이미지 수다. metadata의 `prompt_id`가 아닌 원본 PNG에서 추출해 고정한 full positive prompt와 noise seed를 사용했다.

| 공유 기준 | val | test | test_unseen |
| --- | --- | --- | --- |
| prompt | 362 | 346 | 597 |
| prompt+noise_seed | 360 | 344 | 596 |

같은 prompt/seed는 같은 이미지 또는 동일 룩의 증거가 아니므로 자동 결합하지 않았다. 숫자 seed만 같다는 이유로도 결합하지 않는다. 기존 split과 계보 공유가 달라졌으므로 성능 변화 해석 시 함께 보고해야 한다. 신규 GEN의 확정 시각 동일 룩 판정은 없으며 미확정 관계만 보수적 공동 배정했다.

수리한 데이터도 이미 개발에 노출된 평가 표본이다. 범위 밖 누락, 단일 REAL 출처, 해상도/압축 교란, GEN 계보 중복의 위험은 남는다. 누출 완전 제거·신규 미접촉 일반화를 주장하지 않는다. 현재 primary 채택 경로를 변경하지 않았으며 재학습·보정·진단은 별도 후속이다.

## 재현·소비

저장소 루트에서 실행하며 출력 경로는 존재하지 않아야 한다. 아래 호스트 이미지 경로는 이 머신의 예시다.

```bash
python3 -m scripts.p09_resplit \
  --out /tmp/p09_fresh_metadata.csv \
  --report /tmp/p09_fresh_split \
  --image-root /mnt/h/tracepector/images

docker compose run --rm -T dev python -m pytest \
  tests/test_p09_split.py tests/test_p09_resplit.py tests/test_split_dataset.py \
  tests/test_p09_group_candidates.py tests/test_baseline.py -q
```

원본 `path` 문자열을 유지했으므로 새 버전 metadata를 학습·평가·보정에서 소비할 때는 기존 `image_root: /images`를 반드시 명시한다. image_root 없이 CSV 부모 기준으로 읽는 경로는 사용하지 않는다. 12열 loader 및 기존 score의 checkpoint·익명화 계약은 변경하지 않았다.

새 분할기는 `--group-mapping`도 제공하지만 이 옵션만으로 lock 검증·이미지 hash 대조·경계 감사가 실행되지는 않는다. P09 실행과 재현에는 위의 `scripts.p09_resplit`을 사용한다.

## 검증

- 구현 전 새 테스트의 미구현 함수 import 실패를 확인했다. 구현 후 Docker 집중39 passed(38.38초), 전체 CPU242 passed / 1 skipped(50.47초), 최종 queue hash 검사 추가 후 P09 집중12 passed(2.76초). skip은 기존 실제 YuNet opt-in smoke이고 Pillow 경고12개는 기존 항목이다.
- under-strict 가드는 추이/다중 셀/GEN 그룹 분산·잘못된 매핑·검토 미해결 교차·unseen 혼입·옛 Test B REAL 재사용을 막는다. over-strict 가드는 정상 공동 배정·다른 룩의 split 교차·같은 prompt를 공유하는 서로 다른 GEN의 분할·정상 경로 계산을 허용한다.
- 원본6,000장 파일 hash 대조, 실제 metadata 생성, 새 출력 경로에서 재현 hash 대조와 전체 CPU 회귀를 수행했다. 최초 구현의 자가 검증에는 별도 작업자의 독립검증이나 생산 코드 변이가 포함되지 않았다.

## 독립검증 지적의 회귀 보강

[독립검증](../../../../docs/verifications/2026-10-23/p09_02_resplit.md)은 실물 재현을 확인했으나 B1 GEN 그룹·B2 검토 scope·B3 보고/실행 경계의 회귀 공백 때문에 조건부 합격이었다. 후속 보강에서는 생산 코드·metadata·고정 lock을 바꾸지 않고 테스트만 추가했다.

- GEN 공동 배정 fixture는 개별 배정 시 서로 갈라지는 g0/g4를 사용한다. 정상 그룹 보존과 공유 prompt 자동 병합 금지를 함께 확인한다.
- `tests/test_p09_resplit.py`는 scope의 정상/누락, 보고서의 셀·class·그룹·불변 필드, 실제 CLI의 lock·이미지 hash·덮어쓰기·계보 보고를 직접 실행한다. 임시52장 fixture를 사용하며 실데이터 출력은 쓰지 않는다.
- 독립검증에서 살아남은3개 변이를 포함한9개 변이가 모두 해당 명명 셀에서 재실패했다. checkpoint 커밋 후 각 변이의 clean gate·백업·바이트 복원·clean 상태를 확인했다. 정확한 변이와 셀은 [작업 기록](../../../../docs/daily_logs/2026-10-23/work_log.md)에 보존한다. 이는 구현자의 보강 검증이며 기존 독립검증 판정을 소급 변경하지 않는다.

보강 후 복원 상태에서 집중53 passed(3.36초), 전체 CPU263 passed / 1 skipped(49.61초). 기존 실제 YuNet opt-in smoke와 Pillow 경고12개 외 실패가 없다.

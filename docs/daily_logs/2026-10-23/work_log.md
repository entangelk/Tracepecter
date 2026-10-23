# 2026-10-23 작업 기록

## 목표

- 소유자가 핸드오프의 다음 작업인 P09-02 진행을 승인했다. 고정 배정 그룹을 소비해 새 metadata를 생성하고 새 split 경계를 검증한다. 재학습은 P09-03의 별도 범위다.

## 완료한 작업

- `scripts/split_dataset.py`에 선택적 배정 매핑 소비를 추가했다. 기존 실행 경로를 유지하며 REAL의 `look_group`과 전체 `split`만 변경한다. GEN의 공동 배정도 별도 매핑으로 유지하고 prompt/seed는 자동 결합에 사용하지 않는다.
- `scripts/p09_resplit.py`로 입력·코드·그룹 출력 lock 검증, 새 버전 출력, 원본 이미지 hash 대조, 셀별 수/그룹/목표 비율, 고정 시각 판정의 경계별 재투영과 GEN 계보 교차를 기록한다. 기존 출력이 있으면 거부한다.
- 회귀 테스트를 먼저 추가해 미구현 함수 import 실패를 확인한 뒤 구현했다. 누락/중복/빈 ID 매핑, 옛 그룹 분해, class 혼합, unseen 충돌 거부와 정상 다중 셀·추이·GEN 그룹, 행 순서 결정성, 불변 필드, CLI, 새 Test B REAL 선택을 검증한다.
- 새 metadata는 원본 6,000개 ID와 12열을 유지한다. train 3,780 / val 820 / test 800 / test_unseen 600. 셀별 실제 비율은 목표에서 1%p 미만 차이이며 빈 셀/class는 없다. 기존 metadata·primary·checkpoint·calibration은 보존한다.

## 발견한 문제

- metadata의 `path`는 CSV 위치 기준으로 해석되지만 새 버전의 경로 문자열은 기존 값 그대로다. 소비자들은 이미 `image_root`를 지원하므로 loader를 바꾸지 않고 이후 학습·평가 설정에서 `/images`를 명시한다. CLI 소비 테스트로 경로 계산을 확인했다.
- 새 split에서 train과 실제 prompt+seed를 공유하는 GEN은 val 360 / test 344 / test_unseen 596장이다. 이는 실제 근사중복 판정이 아니며 현재 계약상 자동 결합하지 않는다. 기존 평가와 같은 독립성/표본 구조로 해석하지 않는다.

## 결정과 한계

- 기존 결정적 크기 내림차순·키 동점 규칙과 셀별 결손 합 알고리즘을 재사용한다. 새로운 최적화기나 모델 변경은 도입하지 않는다.
- 기존 시각 판정 1,386행을 모든 새 경계에서 재조회했다. 확정·미확정 교차는 없고, 다른 룩 판정의 교차는 train/test 166·train/val 141·val/test 4쌍이다. 이는 새 원본 시각 검토 1,386회를 수행했다는 뜻이 아니다.
- 초기 REAL500·GEN100 우선순위 포함 여부를 재검증했다. 고정 source/입력으로 directed top-10을 재계산해 미처리 이웃0을 재확인했다. 범위 밖 미검토946,311쌍과 개발 평가의 한계는 그대로다.

## 검증

- Docker 집중39 passed(38.38초), 전체 CPU242 passed / 1 skipped(50.47초). skip은 기존 실제 YuNet opt-in smoke이며 기존 Pillow 경고12개 외 실패가 없다. 생산 코드 변이·GPU 실행은 하지 않았다.
- 원본6,000장 SHA-256 일치와 별도 출력 경로에서 metadata·경계 CSV·보고서의 바이트 단위 재현 일치를 확인했다. metadata SHA-256은 `5a323684dbf157a1db38201f8fe8007185a7809f2ab1ab9564f225faed682161`이다. 최종 queue hash 검사 후 P09 집중12 passed(2.76초). 최종 산출물 근거는 `experiments/p09_leakage_repair/r1/split/README.md`다.

## 다음 작업

- P09-03 진입 전 새 cohort의 단서 진단 적용 범위·주석 ID·bootstrap 단위를 사전등록하고 커밋한다. 그 뒤 GPU 여유를 확인해 기존 frozen SigLIP encoder의 head를 새로 초기화하여 학습한다.

## P09-02 독립검증 B1~B3 회귀 가드 보강

### 목표·결정

- 소유자는 독립검증의 조건부 합격 사유 B1~B3 보강을 요청했다. 생산 코드와 고정 데이터·lock을 변경하지 않고 빠진 회귀 증거를 추가한다. 기존 독립검증 기록의 판정은 당시 결과로 보존하며 이번 보강을 독립 재검증으로 표현하지 않는다.

### 완료한 작업

- B1: `tests/test_p09_split.py`의 GEN 공동 배정 표본을 g0/g1에서 g0/g4로 변경했다. 개별 이미지 배정이면 train/test로 갈라지므로 그룹 소비를 무시하는 변이를 검출할 수 있다. 정상 매핑에서는 함께 배정하고 공유 prompt의 다른 GEN은 세 split에 존재한다.
- B2: `tests/test_p09_resplit.py`에서 REAL500·GEN100의 작은 결정적 후보 fixture로 정상 선택·seed/옛 그룹/cross-class 제외·범위 밖 후보 허용·후보 hash/최소 수/검토 포함/closure 누락 거부를 직접 검증한다.
- B3: 보고서의 실제 수·목표·비율·성분 수·최대 성분과 unseen 셀을 명시 값으로 검증한다. 불변 필드/GEN look_group 변경·새 그룹/옛 그룹 교차·빈 평가 셀·빈 class를 각각 거부한다.
- 고정 lock과 이미지52장짜리 자체 완결 fixture로 실제 CLI를 실행한다. 새 metadata·검토 경계 CSV·source/input/output lock·full prompt/seed 공유 집계·이미지 hash 대조를 확인하며 이미지 변경·ledger ID 누락·기존 출력·그룹 근거/보충 입력/queue 변조는 출력 전에 거부한다. 실데이터·GPU·대량 이미지 I/O는 필요 없다.

### 검증·후속

- 보강 직후 Docker 집중33 passed(2.88초). 변이 전 checkpoint `eaa009f`를 커밋하고 `git status --short` 빈 출력을 실제 확인했다. 각 변이 직전에도 같은 gate를 실행했고, 각 실행 후 백업 바이트로 복원·바이트 일치·clean 상태를 확인했다. 아래9개 변이는 모두 해당 단일 명명 셀에서 `1 failed`, exit1이었다.
- 복원 후 집중53 passed(3.36초), 전체 CPU263 passed / 1 skipped(49.61초). skip은 기존 실제 YuNet opt-in smoke이고 Pillow 기존 경고12개 외 실패가 없다. 생산 소스2개가 checkpoint 및 기존 split lock hash와 같고, metadata hash도 기존 값과 같음을 재확인했다.
- 이후 프로젝트 다음 작업은 기존과 같이 P09-03 진단 사전등록과 재학습이다.

### 변이와 명명 회귀의 대응

| 변이 | 위치·교체 | 재실패한 셀 | 결과 |
| --- | --- | --- | --- |
| B1_gen_group | `scripts/split_dataset.py:67`: `key = allocation_groups[row['image_id']] if allocation_groups is not None else group_key(row)` → `key = allocation_groups[row['image_id']] if allocation_groups is not None and row['source_type'] == 'real' else group_key(row)` | `tests/test_p09_split.py::test_groups_determinism_and_no_prompt_merging` | 1 failed, exit1 |
| B2_missing_review | `scripts/p09_resplit.py:98`: `if any(tuple(sorted((r['a'], r['b']))) not in reviewed for r in selected):` → `if False:` | `tests/test_p09_resplit.py::test_priority_scope_rejects_incomplete_evidence[missing_review]` | 1 failed, exit1 |
| B3_empty_class | `scripts/p09_resplit.py:73`: `if {r['label'] for r in rows if r['split'] == split} != {'0', '1'}:` → `if False:` | `tests/test_p09_resplit.py::test_split_report_rejects_contract_violations[empty_class]` | 1 failed, exit1 |
| over_different_look | `scripts/p09_resplit.py:37`: `if review['verdict'] != 'different_look':` → `if True:` | `tests/test_p09_split.py::test_review_crossings_both_directions` | 1 failed, exit1 |
| old_group_defence | `scripts/split_dataset.py:124`: `if any(len(values) != 1 for values in old_groups.values()):` → `if False:` | `tests/test_p09_split.py::test_invalid_mapping_rejected[old_group]` | 1 failed, exit1 |
| image_hash | `scripts/p09_resplit.py:161`: `if sha256(path) != image['sha256']:` → `if False:` | `tests/test_p09_resplit.py::test_resplit_cli_rejects_bad_evidence_without_output[image]` | 1 failed, exit1 |
| output_overwrite | `scripts/p09_resplit.py:114`: `if args.out.exists() or args.report.exists():` → `if False:` | `tests/test_p09_resplit.py::test_resplit_cli_rejects_bad_evidence_without_output[out_exists]` | 1 failed, exit1 |
| lineage_report | `scripts/p09_resplit.py:151`: `report['generation_train_overlap'] = overlap` → `report['generation_train_overlap'] = {}` | `tests/test_p09_resplit.py::test_resplit_cli_report_lineage_and_locks` | 1 failed, exit1 |
| ledger_identity | `scripts/p09_resplit.py:156`: `if {r['image_id'] for r in images} != set(by_id):` → `if False:` | `tests/test_p09_resplit.py::test_resplit_cli_rejects_bad_evidence_without_output[ledger_ids]` | 1 failed, exit1 |

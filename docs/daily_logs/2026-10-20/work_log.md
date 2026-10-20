# 2026-10-20 작업 기록

## 목표

- P08-06 소유자 확인 CSV를 수령하고 예측 전에 최종 얼굴 상태를 고정한다.
- 사전등록 진단·채택 규칙을 구현·실행하고, 채택 결과와 독립검증을 반영한다.

## 완료한 작업

- 다운로드 `face_review_owner.csv` 301행의 열·ID·정수 범위를 기존 merge 도구로 검증했다.
- 소유자는 눈·코·입의 개수를 셌다고 확인했다. 원본 바이트는 진단 디렉터리의 `face_review_owner_features.csv`로 보존했다(sha256 `c1d2478b81c16a8dbb7831bb46d830b0618a1f37329e43c67ca7cccfdfac3cab`).
- 같은 기준(눈·코·입 중 둘 이상)으로 요소 0~1 → 얼굴 0, 요소 2~4 → 얼굴 1로 변환했다. 요소 2개 20장을 비교 이미지로 확인했고, 기존 에이전트 다중 얼굴 주석 2건(gen_001311·gen_002236)은 원본 크기로 확인했다. 배경 인물의 불명확한 이목구비를 얼굴로 세는 기존 값보다 소유자 표시를 우선했다. 이 변환은 이번 대상 인물의 요소 표시 해석이며 여러 사람의 합산 요소를 변환하는 일반 규칙이 아니다.
- `docker compose run --rm -T dev python -m scripts.p08_face_review merge`: 952행·소유자 301행·에이전트 대비 45행 변경. 최종 상태는 익명화 607 / 얼굴 없음 237 / 남은 얼굴 있음 108.
- `face_review_lock.json`에 원본·변환본·최종본·선행 입력의 SHA-256과 확인한 ID를 고정했다. HANDOFF와 페이즈 상태를 수령 상태로 갱신했다.

- 검증: `docker compose run --rm -T dev python -m pytest tests/test_p08_face_review.py -q` → 3 passed. 별도 데이터 검사로 원본 바이트 동일성, 변환식, 301개 확인 ID, 952개 최종 ID, confirmed·정수 범위, 소유자 우선 병합, SHA-256·LF를 확인했다. `git diff --check` 통과. 진단 모델 예측은 아직 실행하지 않았다.

- P08-06 실행기를 구현했다. 사전등록 config/입력/manifest, 최종 주석·HEAD, calibration/checkpoint/snapshot/YuNet/cache 이미지 hash를 선행 검증한다. 2×2 평가와 REAL shape/size·GEN gray/restore 조건만 별도 구성한다. 원본 bypass는 offline 진단에만 둔다.
- 판정 수식은 `src/diagnostic.py`에 두고, 이미지 개입은 기존 `src/anonymize.py`의 같은 rasterization/Gaussian 커널을 공유한다. 모델별 temperature·threshold는 양 입력에 고정하며 재fitting하지 않는다.
- 예측은 배치마다 fsync하는 조건별 LF CSV로 보존한다. 실행 identity가 다르면 재개를 거부하고, 중단된 마지막 CSV 행만 제거한다. 보고서는 logit에서 파생하며 코드·주석·모델 hash로 계보를 기록한다.
- 진단·개입·재개·해시·커밋 검증·고정 calibration의 양방향 가드를 추가했다. 최초 수치 테스트는 구현 전 `ModuleNotFoundError`로 실패한 뒤 구현 후 집중 38 passed를 확인했다. 전체 CPU `docker compose run --rm -T dev python -m pytest -q`는 206 passed / 1 skipped(실제 YuNet opt-in), 45.69초.

- GPU 진단: 구현 `1102343`, 주석 고정 `0c4eb6e`. 2,369개 입력 이미지 hash 확인 후 8개 조건별 CSV에 총 9,651개 logit을 저장했다. candidate 익명화 Test A AUC 0.9998668324 / Test B 0.9996465774. 얼굴 상태 집중·real_shape·real_size·gen_gray·gen_restore 전부 통과했다.
- 개입 평균 절대 변화의 95% 상한은 순서대로 0.151751 / 1.946554 / 0.932232 / 1.853471점으로 5점 이하다. 맞음→틀림은 모두 0건, Wilson 상한은 REAL 2.5134% / GEN 2.3163%로 5% 이하다. 얼굴 상태별 FP는 익명화 10/607, 없음 5/237, 남음 5/108이며 세 차이 구간이 ±10%p 안이다. 차이 0 또는 모든 단서의 인과적 제거를 주장하지 않는다.
- 저장된 CSV의 고유 ID·cohort·SHA-256을 확인하고, 별도 NumPy PCG64 bootstrap·Wilson 수식으로 네 개입 구간을 재계산했다(일치). 상태별 FP를 재집계했고 P08-05 Test A/B AUC·accuracy가 동일했다. NLL 차이는 최대 4.3e-12다.
- 재개 실행은 기존 CSV를 사용하며 Python CLI exit 0(`cli_exit_code.txt`), `result.json` 최초 실행과 byte 동일을 확인했다. score CLI 실이미지 확인(`src.score --image /images/real/스포티/998959.jpg --calibration experiments/p08_anonymized/calibration/calibration.json --device cuda`)은 exit 0, score 92.676153346304·photographic_like였다.
- 사전 채택 규칙에 따라 `configs/primary.yaml`을 `configs/anonymized.yaml`과 같은 설정으로 전환했다. README·SoT의 현재 checkpoint/calibration 소유 경로를 갱신하고 P05 baseline artifact는 보존했다. 이전 학습 비교 테스트는 이동하는 primary 대신 원래 비교 정본인 `configs/baseline.yaml`을 사용하도록 바꿨다.
- 경계 자가 검토로 80장/79장·오답 구간 상한 동등 경계, 회색 조건의 두 얼굴, 기존 큰 원 축소 금지·clipping·기존 가림 보존을 추가했다. 새 primary 연결 테스트는 변경 전 실패를 확인한 뒤 설정 변경 후 통과했다. 집중 테스트는 25 passed / 1 skipped. primary 전환 후 최종 전체 CPU suite는 208 passed / 1 skipped, 51.02초. `git diff --check` 통과.

## 발견한 문제

- 독립검증 1차는 조건부 합격(B1)이다. 원자료·실제 구현·판정은 독립 일치했지만 평가 확률 T→1.0(M7), 단서 확률 T→1.0(M8), 실제 분류 threshold→0.5(M9)를 새 suite가 잡지 못했다. M1~M6은 guarding cell에서 재실패했고 원복 후 전체 208 passed/1 skipped를 확인했다.
- B1 보강: fixture threshold를 baseline .42 / candidate .53으로 바꿔 T=1과 모델별 T=2/3 및 threshold=.5와 artifact threshold가 실제 분류 차이를 만들도록 했다. 저장 logit에서 별도 sigmoid·혼동행렬·NLL/Brier/ECE 수식을 계산해 2×2의 모든 cohort 수치를 assertion한다. 단서 경계는 실제 domain 함수에 위임하는 spy로 candidate 확률·threshold·전체 ID 연결을 독립 수식과 비교한다. runtime 코드·실제 예측·판정은 바꾸지 않았다.

- 첫 detached 실행의 `setsid`가 곧바로 종료되어 `--wait`로 재시작했다. 두 번째는 결과 저장까지 수행했으나 래퍼가 `setsid: wait: Success`·exit 1을 반환했다. Docker daemon 직접 관리 detached 컨테이너로 재개하여 CLI 자체 exit 0과 결과 재현성을 확인했다. 컨테이너 감독과 디스크 재개 상태로 터미널/전원 단절을 대비한다.

- 최초 병합은 구조상 유효했으나 얼굴 수와 이목구비 수의 의미가 달랐다. candidate 진단 예측을 실행하기 전에 발견했고, 소유자 의미 확인 후 변환하여 잘못된 수를 최종 주석으로 고정하지 않았다.

## 결정

- 소유자가 이번 구현도 서브에이전트 한 명의 독립검증까지 진행하도록 명시적으로 승인했다. 지적은 차단·비차단 모두 보강하고 추적검증한다.

- 얼굴 수를 셌다는 첫 답변 후 구체적인 4/4 사례를 제시했으며, 소유자는 눈·코·입 각각을 센 것이라고 명확히 했다. 사전등록의 얼굴 기준·표본·판정 허용폭은 유지한다.

## 다음 작업

- 누출 감사 보고서·검증 기록·확인 쌍을 읽고 REAL 그룹 보강 및 GEN 렌더 계보 검토 범위를 계획한다. 확인된 8쌍은 전수 목록이 아니므로 후보 확장이 필요하다.
- 기존 artifact를 보존하면서 새 그룹·metadata·split·checkpoint·calibration의 버전별 경로와 재분할→재학습→재calibration 절차를 정한다. 수리 구현은 미착수이며 알려진 test 4장만 제외하는 방식으로 종료하지 않는다.
- 그다음 P07(API + Demo) 상세 계획을 이어간다. P08-07 외부 holdout은 기존 결정대로 P07 비관문이며 최종 독립 평가·사람 평가는 별도 후속이다.

## 독립검증 최종 결과

- 1차 대상 `c2ba42d`, B1 보강 `eba8784`. 구현하지 않은 별도 에이전트가 정본/구현/테스트/fixture 경계, 9651개 예측·2369개 원본 이미지·checkpoint/YuNet/cache/hash·전 기하·수치·baseline 불변을 독립 확인했다.
- B1 보강 후 추적 M7~M12 전부 정확한 회귀 셀에서 재실패했고 HEAD 원복·원본 byte동일·clean을 매번 확인했다. 집중 26 passed / 1 skipped(4.64초), 전체 209 passed / 1 skipped(45.53초), 기존 Pillow warnings 12개. 추가 차단·비차단 지적 없음, 최종 **합격**.
- 독립검증이 runtime 오류를 발견한 것은 아니다. 실제 예측·판정은 최초 결과와 동일하며, 보강은 테스트 경계를 대상으로 했다. 원자료 전체 재계산 근거는 [검증 기록](../../verifications/2026-10-20/p08_06_diagnostic.md)에 보존했다.
- P08-01~06을 Complete로 갱신하고 HANDOFF의 다음 작업을 P07 상세 계획·API·Demo로 전환했다. P08-07 holdout 설계는 P07 비관문 후속으로 명시했다.

### 변이와 guarding cell

각 변이 전 clean pre-flight와 원복 후 byte동일/clean을 실행 확인한 독립검증이다. 경로·치환 전체 및 재현 코드는 검증 기록에 있다.

| 변이·실제 변경 | 위치 | guarding cell | 관측 |
| --- | --- | --- | --- |
| M1 절댓값 제거 | `src/diagnostic.py:42` | `test_intervention_bootstrap_is_paired_absolute_with_replacement` | 재실패 |
| M2 score 구간 상한 <=→< | `src/diagnostic.py:52` | 위 셀 | 재실패 |
| M3 채택 all→any | `src/diagnostic.py:100` | `test_adoption_requires_both_aucs_and_every_cue_gate` | 재실패 |
| M4 REAL overlay normal→original | `scripts/p08_diagnostic.py:174` | `test_variants_preserve_other_masks_all_discs_and_no_second_anonymization` | 재실패 |
| M5 calibration SHA→상수 | `scripts/p08_diagnostic.py:118` | `test_stub_end_to_end_fixed_calibration_and_resume` | 재실패 |
| M6 Newcombe 닫힌 경계→열린 경계 | `src/diagnostic.py:89` | `test_concentration_minimum_interval_boundaries_and_bad_predictions` | 재실패 |
| M7 평가 확률 T→1 | `scripts/p08_diagnostic.py:241` | `test_stub_end_to_end_fixed_calibration_and_resume` | 1차 생존 → B1 보강 후 accuracy assertion 재실패 |
| M8 cue 확률 T→1 | `scripts/p08_diagnostic.py:291` | `test_cue_boundary_uses_candidate_temperature_threshold_and_all_predictions` | 1차 생존 → 확률 mapping assertion 재실패 |
| M9 평가 threshold→.5 | `scripts/p08_diagnostic.py:242` | `test_stub_end_to_end_fixed_calibration_and_resume` | 1차 생존 → accuracy assertion 재실패 |
| M10 calibration 지표 T→1 | `scripts/p08_diagnostic.py:243` | 위 셀 | NLL assertion 재실패 |
| M11 cue threshold→.5 | `scripts/p08_diagnostic.py:295` | `test_cue_boundary_uses_candidate_temperature_threshold_and_all_predictions` | .53 assertion 재실패 |
| M12 ECE bins→1 | `scripts/p08_diagnostic.py:243` | `test_stub_end_to_end_fixed_calibration_and_resume` | ECE assertion 재실패 |

## 추가 요청 — 테스트 누출 적대적 감사

- 소유자가 높은 AUC를 의심해 누출 재점검·적대적 검증을 요청했다. 기존 채택 규칙의 계산을 다시 통과시키는 대신 데이터 독립성을 반박하는 쪽으로 조사했다.
- 전수 지문/PNG 렌더 계보/frozen embedding·수집 단서·JPEG/상수/셔플 대조를 수행했다. [감사 보고서](../../../experiments/p08_anonymized/leakage_audit/README.md), [검증 기록](../../verifications/2026-10-20/test_leakage_adversarial.md).
- 같은 룩의 교차를 최소8쌍 확인했다(검토14쌍 중 test4/val4). 완전 동일 파일·decoded RGB는0이고, 기존 ID/look_group 문자열 교차 검사만으로 이 누출을 잡지 못한다.
- actual embedded PNG 기준 sd35 420/600이 train 다른 생성기와 같은 positive prompt·seed다. 원본 header3개만 쓰는 train-only ridge도 두 test accuracy1.0이다. 원본 class/source 교란은 확인되지만 현재 CNN이 header를 읽는다고 주장하지 않는다.
- 동결 모델 JPEG 공통 조건에도 AUC는 높고, 확인된 몇 장을 제거해도 거의 불변이다. 현재 고성능 전체를 한 원인으로 확정하지 않았다. 실제 모델·metadata·split은 변경하지 않았다.

### 변이 검증 결과

전수 감사와 도구를 `c66c726`에 커밋한 뒤 최초·매 변이 전에 `git status --short`가 빈 것을 실제 실행 확인했다. 각 변이는 try/finally에서 HEAD 복원 후 원본 byte동일·clean을 확인했다. 원본 데이터·checkpoint는 변이하지 않았다.

| 변이 | 파일·실제 변경 | guarding cell | 관측 |
| --- | --- | --- | --- |
| M1 | `scripts/p08_leakage_audit.py:73` `if len({r['split'] for r in v})>1` → `if False` | `tests/test_p08_leakage_audit.py::test_cross_split_fingerprints_find_duplicates_without_flagging_unrelated_images` | exit 1, 재실패·원복 확인 |
| M2 | `scripts/p08_leakage_audit.py:73` `if len({r['split'] for r in v})>1` → `if len({r['split'] for r in v})>0` | `tests/test_p08_leakage_audit.py::test_cross_split_fingerprints_find_duplicates_without_flagging_unrelated_images` | exit 1, 재실패·원복 확인 |
| M3 | `src/train.py:70` `split = "train" if "metadata_csv" in config["data"] else None` → `split = None` | `tests/test_p08_leakage_audit.py::test_real_training_configuration_reads_only_train_and_validation_rows` | exit 1, 재실패·원복 확인 |
| M4 | `src/calibrate.py:45` `val = [i for i, row in enumerate(dataset.rows) if row.split == 'val']` → `val = list(range(len(dataset.rows)))` | `tests/test_calibration.py::test_calibration_cli_uses_only_validation_and_rejects_unanonymized_score` | exit 1, 재실패·원복 확인 |
| M5 | `src/evaluate.py:55` `real = [i for i in standard if rows[i].label == 1]` → `real = [i for i,row in enumerate(rows) if row.label == 1]` | `tests/test_baseline.py::test_split_and_test_b_real_reuse` | exit 1, 재실패·원복 확인 |

정상 fixture는 실제 train/val ID만 읽는 것을 허용하며, test 혼입 시 실패한다. 감사 지문 대조는 진짜 cross-split 동일 지문은 찾고 split 내부 중복·다른 지문은 오탐하지 않는다. 누출 방어 테스트가 실패할 수 있음을 확인한 사실과 실제 데이터에 같은 룩 교차가 있다는 사실을 구분한다.

재현은 `mutation_results.json`의 file/old/new/cell을 하나씩 적용하고 해당 pytest cell을 실행한 뒤 복원한다. **반드시 clean checkpoint 이후에만** 실행한다. 전체 pytest 출력도 같은 artifact에 보존했다.

- 추가 감사 최종 검증: 변이5종 모두 guarding cell 재실패·byte 원복·clean 확인. 집중16 passed(3.74초), 전체214 passed/1 skipped(45.22초), 기존 Pillow warning12개. GPU probe exit0, 기존 score·metadata·primary·checkpoint 보존. 감사 판정은 데이터 독립성 **불합격**이며 기존 P08 명시 통계 관문 계산 통과와 구분한다.
- HANDOFF·P08 진단 문서·phase 상태 설명에 새 반례와 해석 제한을 반영했다. 기존 외부 holdout 비관문 결정을 변경하지 않았으며 재분할/재학습은 미착수다.

## 오늘 작업 종료

- 소유자 요청에 따라 오늘은 문서 정리와 핸드오프를 끝으로 종료한다. 다음 작업의 첫 단계는 누출 수리 범위 설계이며 추가 학습·데이터 변경은 시작하지 않는다.
- HANDOFF의 과거 “누출 0” 표현을 선언된 그룹 검사와 실제 같은 룩 교차의 차이로 교체했다. 후보 확장 시 놓치기 쉬운 거리 기준, 감사 원자료·cache 위치, 기존 artifact 보존 및 수리 순서를 남겼다.
- 이 마무리는 HANDOFF·작업 기록만 변경한다. 코드·metadata·모델·calibration은 그대로이며 마지막 실행 검증은 위 감사의 전체 214 passed / 1 skipped다. 문서 마무리에서는 테스트를 재실행하지 않고 링크·행 수·diff를 확인한다.


## 핸드오프 후속 — P09 누출 수리 계획

### 목표

- 핸드오프의 최우선 작업인 누출 수리 범위·실행 계획을 구체화한다. 이번 단위는 문서 작성이며 재분할·재학습은 실행하지 않는다.

### 완료한 작업

- `docs/plan/phase_9_leakage_repair.md`에 P09-01~04를 정의했다. REAL 후보 확장·쌍별 검토·추이 연결 그룹·새 split 교차 재감사 후 새 학습/보정으로 진행한다.
- `data/versions/p09_r1/metadata.csv`, `checkpoints/leakage_repair/r1/`, `experiments/p09_leakage_repair/r1/` 경로를 예약했다. 기존 schema·artifact·감사 lock·소유자 주석을 보존한다.
- 페이즈 인덱스에 P09 Planned를 등록하고 P08 후속 링크·HANDOFF의 다음 시작점을 갱신했다. CHANGELOG에 수리 설계 범위를 기록했다.

### 확인한 문제와 처리

- 기존 embedding 최근접 2,220행은 평가→train 1개 이웃이므로 전체 연결성을 증명하지 못한다. 계획에 split 무관 REAL 후보 확장과 연결 성분 경계 재검토를 추가했다.
- 미확정 후보를 다른 룩으로 취급하지 않는다. 해소가 안 되면 보수적인 공동 배정과 이유를 기록하도록 했다. 탐색 top-k·pHash 범위는 검토 후보 생성 규칙이며 실제 동일 룩 판정 기준과 구분했다.
- GEN prompt+seed 공유와 실제 이미지 근사중복을 구분했다. sd35 실제 근사중복이 standard 생성기와 확인돼 계약을 함께 충족할 수 없는 경우에만 소유자 결정을 제기한다.

### 결정·범위

- 사용자 요청은 핸드오프 확인 후 다음 작업 진행이다. 핸드오프 최우선의 계획 작성 범위를 수행했으며 신규 수집·P07 구현·GPU 실행은 이번 단위에서 착수하지 않았다.
- 기존 generator holdout·P08 채택 결과·외부 holdout P07 비관문 결정은 유지한다. P09 재분할 평가도 개발 평가로 명시하며 독립 일반화 성능으로 격상하지 않는다.
- 소유자 추가 결정을 요구하는 현재 사양 충돌은 발견하지 않았다. 계획의 후보 탐색 수치·경로는 작업자가 정한 실행 설계이며 소유자 결정으로 기록하지 않는다.

### 검증

- 감사 lock의 input 3개·source 8개·artifact 13개 SHA-256이 현재 파일과 모두 일치한다. checkpoint 대용량 바이너리나 이미지 6,000개를 이번 문서 검증에서 재해시하지 않았으며 기존 lock의 검증 범위와 구분한다.
- 변경 문서의 로컬 Markdown 링크 163개가 모두 존재하고 P09 ID 유일성·Planned 상태 일치를 확인했다. 보존 경로를 점검하고 `git diff --check`를 통과했다. 코드·공개 schema 변경이 없어 pytest·학습·변이 검증은 수행하지 않는다.

### 다음 작업

- P09-01: 감사 입력 검증 뒤 기존 cache identity/행 순서를 대조하고 split 무관 후보 확장 도구·검토 자료부터 구현한다. 그룹 고정 이전에는 새 split·학습을 만들지 않는다.


## P09-01 후보 도구·첫 검토

### 목표

- 감사 입력을 보존하며 split 무관 후보·시각 검토 자료·잠정 연결 성분을 생성한다.

### 완료한 작업

- `scripts/p09_group_candidates.py`: 감사 24개 hash 검증, cache identity·47청크 shape·2,220 최근접 재계산 뒤 REAL top-10/pHash26·GEN top-10/pHash10·옛 후보를 전수 열거했다. 총 947,696쌍은 비추적 gzip, 우선순위 47,456쌍은 추적 CSV로 보존했다. 거리로 판정하지 않으며 기존 출력 덮어쓰기를 거부한다.
- `scripts/p09_review_pairs.py`: 원본 hash 확인 후 검토 배치를 생성한다. REAL 상위 48쌍을 시각 검토해 확정18·다른 룩25·미확정5를 이유와 함께 기록했다. 새 확정 교차는 train/val4·train/test1·val/test4이며 train 내부9도 있다.
- `scripts/p09_filename_sequences.py`: 원본 파일명이 없는 ID 경로의 한계를 보완해 라벨 JSON3,000개를 선택 읽기했다. 782장에 파일명 그룹이 있고 후보15쌍 모두 기존 그룹 안이다. 원본 zip·JSON hash와 유래를 보존했다.
- 새9셀에 후보 누락/오탐, 추이 연결/미확정 자동결합 금지, GEN prompt/seed 단독 결합 금지, 입력/cache/원본 변조·누락 거부와 정상 수용을 명시했다.

### 발견한 문제·결정

- REAL pHash26만907,609쌍이어서 전수 수동 검토·모든 미확정 자동 공동 배정은 부적절하다. 소유자는 **우선순위 검토로 조정하고 미검토 범위를 명시**하도록 선택했다. DB-07에 근거·선택지·Resolved 결과를 기록하고 계획·인덱스에 반영했다.
- 작업자가 정한 초기 REAL500·GEN100 및 확정 그룹 이웃 확장 범위는 소유자가 별도로 지정한 수량이 아니다. 미검토 후보를 다른 룩으로 판정하거나 자동 병합하지 않는다.
- 현재 잠정5,907성분은 최종 그룹이 아니다. 추가 검토·미확정 처리 전 재분할하지 않는다. 기존 데이터·모델·보정·감사 원자료는 보존했다.

### 검증

- 새 테스트는 구현 전 모듈 부재로 collection 실패했고 구현 후 통과했다. Docker 집중21 passed, 전체221 passed/1 skipped(50.20초), 이후 추가2셀 포함 집중23 passed(4.39초). skip은 기존 실제 YuNet opt-in smoke, Pillow warning12개 외 실패 없음. 새9셀은 호스트에서도 통과했다.
- CLI 도움말과 실데이터 실행, 원본 대조 후48쌍 비교 이미지 재생성을 확인했다. 생산 코드 변이·GPU 실행·재분할은 하지 않았다.

### 다음 작업

- 확정 그룹 주변과 추가 REAL/GEN 우선순위 검토를 이어간다. 검토 범위·미검토 건수·잔여 불확실성을 고정한 뒤 최종 그룹 후보를 만든다.

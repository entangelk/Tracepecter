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

- P07(API + Demo) 상세 계획을 작성하고 채택 artifact·공통 전처리 계약으로 구현한다.
- P08-07 실사 holdout 설계·GEN 근사중복 점검·사람 평가는 별도 후속으로 남긴다.

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

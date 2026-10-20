# P08 테스트 누출 적대적 감사

## 대상·범위

- 요청: 소유자가 높은 성능에 대해 테스트 누출을 재점검하고 적대적으로 검증하도록 요청했다.
- 날짜: 2026-10-20. 대상 HEAD `7e5433a`, 현재 metadata 6000장·P08 채택 checkpoint/calibration.
- 검증자: Codex(root). P08-06 구현 참여자이며 이번 결과를 별도 에이전트 독립검증으로 주장하지 않는다. P01 그룹 구성과 데이터·수집 출처·실행 경로를 추가 감사했다.
- 정본: `docs/project.md` §8(같은 룩의 근사 이미지 train/test 분리), §13(pHash+embedding), §14(group split); P01 계획; P08 진단 계약. 기존 명시 관문 계산과 데이터 독립성은 서로 다른 표면이다.

## 방법과 결과

[전체 감사 보고서](../../../experiments/p08_anonymized/leakage_audit/README.md)에 명령·표본·원자료·정량 결과를 보존했다. 요약을 근거 없이 반복하지 않고 관련 입력을 직접 검사했다.

- 원본 6000개 파일/decoded RGB 지문과 pHash, 모든 PNG 3000개 실제 full positive prompt/seed를 전수 읽었다. 원본 SHA는 학습 전 고정 face cache의 6000개 해시와 전부 일치한다.
- 실제 익명화 입력 6000장 frozen embedding과 train 최근접을 계산하고 REAL 후보 14쌍을 시각 확인했다. 최소8쌍에서 같은 옷·촬영 세트의 다른 컷이 교차한다. train/test4쌍·train/val4쌍이며 모두 기존 pHash10을 넘고 그룹ID가 다르다.
- 원본 헤더 3개(width,height,log bytes)만으로 train-only ridge가 Test A/B accuracy1.0을 낸다. 이미지 tensor만 보는 실제 모델이 헤더를 직접 읽는다는 주장은 하지 않는다.
- 현재 학습 코드·데이터 경로·과거 실행 commit을 대조했고 직접 test fitting 경로를 발견하지 못했다. 실제 코드와 같은 metadata 설정의 loader를 stub 실행하여 train/val ID 집합을 관측했다.
- 같은 JPEG 조건 대조, 상수 tensor·상수 logit·평가 labels 셔플과 train labels 셔플 대조를 실행했다. 누출 후보 몇 장 제거·새 prompt/seed 부분집합에서도 AUC는 높다. 이는 실제 누출 부재나 source 일반화를 증명하지 않는다.

## 차단·비차단

### 데이터 독립성 차단

1. 확인된 동일 룩 교차 8쌍. `experiments/p08_anonymized/leakage_audit/visual_review.csv`가 사례의 정본이다. 기존 `scripts/deduplicate.py`에는 embedding 층이 없고 `scripts/split_dataset.py`는 선언된 look_group 값만 검사한다. 값이 다르게 붙은 같은 촬영 시퀀스를 검증하지 못한다.
2. 기존 테스트는 개발 판단에 이미 노출됐고 REAL 출처가 하나다. 현재 수치를 미접촉·출처 독립 일반화로 확정할 근거가 없다. 이 한계는 기존 P08 통계 관문 구현의 오류와 구분한다.

### 추가 설계 위험

- sd35 GEN 600 중420은 train 다른 generator와 positive prompt+seed가 같다. 현 generator holdout 계약 위반은 아니나 새로운 생성 시나리오의 holdout은 아니다.
- 형식·해상도·용량과 class의 교란, K-Fashion 한 REAL 출처. 통일 JPEG 대조에도 AUC가 높아 압축 하나만을 원인으로 확정하지 않는다.
- 사전학습 원자료와의 중복, 전체 REAL 동일 룩 연결성은 아직 배제하지 못했다. 8쌍은 하한이며 전체 누출 수의 추정이 아니다.

## 판정

**불합격** — 평가 데이터 독립성에 실제 반례가 있다. 직접 fitting 혼입·완전 복제는 확인되지 않았지만 같은 룩의 train/test 및 train/val 교차가 확인됐다.

생산 모델·split·calibration은 수리하지 않았다. 원자료가 바뀌지 않은 기존 점수의 산술적 재현성은 유지한다. 소유자의 요청은 점검이므로 후속 수리 범위는 이 보고 후 결정한다.

## 변이·검사

감사 도구 양성/음성 대조와 실제 loader 관측 가드는 통과했다(집중 5 passed, 기존 split 포함10 passed). `c66c726` checkpoint 이후 누출 방어 변이5종이 모두 정확한 셀에서 재실패했고 원복했다. 아래 표와 원자료를 참고한다.

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

## 최종 검사·재현 범위

- 변이 원복 후 집중 16 passed (3.74초), 전체 CPU 214 passed / 1 skipped (45.22초). opt-in 실제 YuNet 학습 smoke는 실행하지 않았으며, 실제 YuNet·cache로 수행한 6000장 GPU 감사와 구분한다. 기존 Pillow deprecation warning12개 외 실패 없음.
- GPU 감사 CLI exit0. 현재 원본6000개·동결 모델·재압축 결과를 저장했다. `audit_lock.json`에 input/source/artifact SHA-256을 고정했고 실제 실행 중인 probe source hash도 일치한다.
- 생산 `src/`·기존 `configs/`·`data/metadata.csv`·checkpoint/calibration을 수정하지 않았다. 새 테스트가 누출 방어를 깨면 실패한다는 확인은 실제 데이터의 누출을 수리한 것이 아니다.
- 사용자에게 동일 룩 train/test·train/val 교차를 진행 중에 알렸다. 모델·split을 고치는 대신 이번 감사 범위의 반례·한계·수리 권고를 보존했다.

주요 코드 근거: `src/train.py:70`의 split 선택, `src/train.py:79`의 val 선택, `src/calibrate.py:45`의 val fitting 인덱스, `src/evaluate.py:53`의 Test B 구성. 사례는 `visual_review.csv:2`·`:3` 등을 통해 ID와 원본 경로를 추적한다. 코드 줄 번호는 감사 커밋의 파일 기준이다.

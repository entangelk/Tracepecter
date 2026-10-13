# 2026-10-13 작업 기록

## 목표

- 갱신된 AGENTS.md §6에 따라 검증된 보조 크기 측정 작업을 독립된 커밋으로 보존한다.

- 소유자가 저장한 학습 GEN 40장 표시를 반영하고 P08-01 재현율과 다음 작업을 갱신한다.
- sd35 소유자 검토 자료를 준비하고 저장·최종 판정 흐름을 검증한다.

## 수행 내용

- 다운로드 폴더의 `recall_labels_owner.csv`를 확인했다. 40개 ID가 사전 확인 목록과 정확히 일치하며, 값은 모두 0/1이다. 보임 31장·안 보임 9장이다.
- CSV 저장물에 실제 줄바꿈 대신 문자 `\n`이 들어 있어 줄바꿈만 복원하고 `experiments/p08_anonymized/measure/recall_labels_owner.csv`에 보관했다. 다운로드 원본은 변경하지 않았다.
- 기존 에이전트 표시와 달라진 ID는 `gen_000333`, `gen_001836`, `gen_001364`다. 소유자 판정을 우선 적용했다.
- 기존 검출 CSV로 별도 계산한 값은 전체 150장 중 양성 98장·검출 87장, 재현율 88.78%다. 양성 ≥80장·재현율 ≥80% 기준을 충족한다.
- CPU 전용 기존 측정 명령이 정상 종료(exit 0)하여 `report.json`을 갱신했다. 중단 요청 시점에는 이미 계산이 완료되어 추가 재계산은 필요하지 않았다. 모델 score·재학습·GPU는 사용하지 않았다.
- sd35 검토 자료를 준비했다: 불일치 13장 + 나머지 87장 중 사전 seed의 무작위 20%(17장), 총 30장. `reports/errors/review/p08_sd35/index.html`에 이미지가 포함된 블라인드 페이지를 만들었다.
- `scripts/p08_measure.py`의 기존 선택 로직을 공통 함수로 추출했다. `owner --pool test_gen_sd35`는 고정된 검출 CSV를 사용하므로 검토 자료 생성에 전체 재검출이 필요하지 않다. 선택은 불일치 ID set과 단일 순회로 O(n)이다.
- 학습 GEN 파일명은 유지하고 sd35 확인 목록·빈 양식·최종 표시 파일에 `_sd35`를 붙였다. `scripts/p08_owner_review.html`의 다운로드 이름도 대상에 맞게 생성한다. 최종 표시는 소유자 CSV가 소유하며, 목록·페이지·보고서는 파생 자료다. CSV 열은 기존 `image_id,owner_face_visible`을 유지한다.
- `measure`는 두 pool의 소유자 파일을 따로 읽고 같은 선택 기준으로 필요한 확인 ID를 계산한다. sd35 확인이 전부 끝나면 `owner_final`로 기록하되 보고 전용이므로 `passed=null`을 유지한다. 학습 GEN의 관문과 표시 파일을 보존한다.
- 이번 `report.json`의 sd35 대기 ID는 새 검토 목록과 기존 검출 CSV·`recall_summary`로 갱신했다. 재현율 61/71과 나머지 측정값은 바꾸지 않았다.
- sd35 다운로드 CSV의 30개 ID·0/1 값을 검증하고 `recall_labels_owner_sd35.csv`에 보관했다. 정상 줄바꿈이라 변환은 없었다. 보임 26장·안 보임 4장, 기존 표시와 다른 ID는 `gen_002761`, `gen_002997`, `gen_002559`다.
- 고정된 검출 CSV와 기존 `owner_check_rows`·`read_owner_labels`·`recall_summary`로 재계산했다. 최종 sd35 재현율은 64/74(86.49%), Wilson 95% 76.88~92.49%다. 30장 확인 목록과 소유자 ID가 정확히 일치하고 독립적인 행 합산과도 일치한다. `owner_final`, 누락 없음, `passed=null`, `gate_applies=false`다. 전체 이미지 재검출은 반복하지 않았다.
- 측정 README, P08 계획·인덱스, HANDOFF의 다음 작업을 보조 크기 측정·전체 슬라이스 독립검증으로 갱신했다. P08-01 전체 완료로 처리하지 않았다.

## 보조 크기 측정

- `scripts/p08_person_size.py`를 추가했다. REAL은 K-Fashion 라벨 ZIP의 부위 rect 합집합 높이를 쓰고, GEN은 수동 표시한 보이는 사람 높이를 쓴다. 관문을 추가하지 않으며 기존 `report.json`은 수정하지 않는다.
- 외부 REAL rect는 라벨 ZIP이 소유한다. GEN 사람 범위는 `person_height_gen.csv`가 소유한다. 표본 manifest·rect 발췌·측정 CSV·보고서는 파생 자료이며 모든 입력 SHA256을 보고서에 기록했다. 새 CSV는 LF로 저장해 Git의 줄바꿈 정규화가 입력 해시를 바꾸지 않게 했다.
- 학습 재현율 표본에서 검출 양성·소유자 반영 얼굴 보임 87장을 대상으로, 기존 REAL seed `20261011`의 정렬·shuffle 순서 앞 50장을 고정했다. 전체 GEN 얼굴 검출 1,084장에서 직접 뽑은 표본은 아니다.
- 320×480 표시 크기 시트 10개를 보고 에이전트가 50장의 최상단·최하단 사람 범위를 수동 표시했다. 원본 해상도는 832×832 또는 832×1216이며, 표시 좌표/480을 이미지 높이 대비 비율로 저장했다. 배경 인물·소품은 제외하고 프레임 밖 신체는 추정하지 않았다. 29장의 표시가 프레임 경계에 닿았다. 수 px의 육안 경계 오차가 가능한 보조 측정이다.
- 실행: `docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev python -m scripts.p08_person_size --label-zip '/data/K-Fashion 이미지/Training/라벨링데이터.zip'` (CPU 전용).
- REAL 150개의 지름/의복 높이 사분위는 0.12406 / 0.14229 / 0.18582, GEN 50개의 지름/보이는 사람 높이 사분위는 0.12481 / 0.13501 / 0.20806이다. 분모·표본이 다르므로 이 수치로 기존 이미지 너비 대비 크기 관문 실패를 바꾸지 않는다.
- 코드의 계산 검증은 자가 확인이며, P08-01 전체 슬라이스 독립검증을 대신하지 않는다.

## 검증

- `report.json`은 `owner_final`, `passed=true`, 누락 ID 없음이다. 별도 계산한 87/98과 일치한다.
- 재계산 전후 검출 CSV·확인 목록 CSV의 행과 값은 동일하다. 재생성된 줄바꿈만 기존 파일 형식으로 복원했다. 원 크기·경계·sd35 결과·입력 provenance도 동일하다.
- 구현 전 집중 테스트에서 sd35 최종 표시 판정·별도 검토 자료 생성·공통 선택 함수의 4개 사례가 실패했다. 구현 후 관련 회귀 명령 `docker compose run --rm -T dev python -m pytest tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q`: **49 passed**.
- `node tests/test_p08_owner_review.cjs`: **2 passed**. 미완료 확인은 저장하지 않으며, 완료 확인은 보임(1)·안 보임(0) 둘 다 보존하고 실제 CSV 줄바꿈·대상별 파일명으로 저장한다.
- 실제 생성된 sd35 페이지도 Node VM에서 실행해 JPEG 30장·고유 ID 30개·0/1 CSV 30행·별도 다운로드 파일명을 확인했다. 브라우저 육안 표시는 소유자의 작업이며 이 테스트가 대신하지 않는다.
- 갱신 문서의 로컬 링크 존재 여부와 `git diff --check`를 확인했다. 전체 슬라이스 독립검증은 별도 후속 작업이다.

- 보조 계산 구현 전에는 신규 모듈 부재로 테스트 수집이 실패했다. 구현 후 관련 회귀 명령 `docker compose run --rm -T dev python -m pytest tests/test_p08_person_size.py tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q`: **54 passed**. rect 겹침·음수 원 좌표·빈/퇴화 rect·수동 범위 0/1 경계·NaN/역전 거부·소유자 표시 적용·별도 보조 보고와 원래 관문 실패 보존을 확인했다.

- 보조 측정 재실행에서 파생 CSV 2개·rect 발췌 JSON·보고서 JSON의 SHA256이 최초 산출물과 동일했다. 각 행의 지름/분모와 사분위도 별도 표준 라이브러리 계산으로 일치했다. 규격 config 2개와 기존 `report.json`은 HEAD와 동일하다.

## 발견한 문제

- 이전 다운로드 파일에는 문자 `\n`이 들어 있었지만, 현재 템플릿과 기존 생성 페이지의 저장 코드를 직접 실행하면 실제 줄바꿈이 나온다. 이를 소스 결함이라고 단정한 앞선 기록은 정정했다. 다운로드 형식 문제의 발생 경로는 확정하지 못했으며 줄바꿈 생성 코드 자체는 변경하지 않았다.
- sd35에서 필요한 확인 ID를 전달하지 않고 `gate_applies`로 최종 표시 상태까지 제한하던 흐름은 sd35 검토 지원과 함께 수정했다. 일부 확인은 최종 표시로 처리하지 않으며, 전부 확인해도 학습 관문을 sd35에 적용하지 않는다.

## 사용자 확인

- 소유자는 앞으로 작업 단위로 검증 후 커밋하면서 진행할 것을 요청했다. 현재 브랜치에서 작업을 보존하며 push는 하지 않는다. AGENTS.md §6의 파괴적 검증 전 체크포인트 커밋 요구도 계속 적용한다.

- 소유자가 눈·코·입 중 둘 이상이 보이는 경우에만 보임으로 표시했다고 확인했다. 하나만 보이면 안 보임으로 표시했다. 사전 측정 기준과 동일하며 기준 변경은 없다.

## 전체 검증 지적 보강

- 소유자가 `docs/verifications/2026-10-13/p08_01_full_slice.md`를 확인하고 보강할 것을 요청했다. 원 검증기록의 판정은 변경하지 않는다.
- B1: 현행 σ 선택 구현은 유지하고 `test_edge_sigma_includes_both_tolerance_bounds_and_keeps_first_match`에 하한 경계·상한 경계·매칭 없음 3개 사례를 추가했다. 첫 매칭 후에도 더 좋은/동일 매칭이 있는 grid로 최소 σ 유지까지 잠근다.
- H1: 소유자 CSV가 표시 값의 정본이며 `report.json`은 파생 보고서다. `provenance.owner_labels_sha256`에 두 pool별 원본 CSV SHA256을 기록한다. 없는 표시 파일은 null이다. 현재 보고서에는 해시만 추가했으며 기존 측정 수치는 보존했다. 기존 통합 테스트에 absent/present 양방향 해시 가드를 추가했다.
- H2: P08 측정 스크립트의 CSV writer 5곳을 LF로 통일했다. 측정 CSV 3종의 raw LF 회귀 가드를 추가했다. 기존 CSV의 열·값은 바꾸지 않는다.
- H3/H4: 기존 config를 사후 변경하지 않는다. 보조 표본 선정은 사전등록이 아니고 사람 높이는 에이전트 육안 표시(소유자 재확인 없음)라는 한계를 README에 명시했다. P08-03 진단 설계 시 표본·규칙을 결과 전에 고정해야 한다.
- 구현 전 집중 테스트는 H1 필드 부재로 3 failed / 15 passed, 보강 후 18 passed다. B1 선택 코드는 변경하지 않았으므로 정상 코드에서 새 3개 사례는 처음부터 통과했다.
- 변이 전 체크포인트는 `8972d1e`다. 첫 변이 전 실제 `git status --short`가 빈 값임을 확인했으며, 각 변이 직전에도 같은 명령 결과가 빈 값인지 확인했다. 복원은 커밋된 HEAD 바이트로 했고 소스 byte 동일·트리 clean을 매번 확인했다.

| 변이 | 파일·위치 | 재실패 셀 | 결과 |
| --- | --- | --- | --- |
| M1: `<= tolerance_px` → `< tolerance_px` (닫힌 경계 배제) | `scripts/p08_measure.py:337` | `test_edge_sigma_includes_both_tolerance_bounds_and_keeps_first_match[lower_inclusive_first_match]`, `[upper_inclusive_first_match]` | 2 failed, 1 passed(무매칭), exit 1 |
| M2: `chosen is None and` 제거 (최소 σ 대신 마지막 매칭) | `scripts/p08_measure.py:337` | 위 하한·상한 경계 셀 | 2 failed, 1 passed(무매칭), exit 1 |

- 변이별 실행 명령: `docker compose run --rm -T dev python -m pytest tests/test_p08_measure.py -k test_edge_sigma_includes_both_tolerance_bounds_and_keeps_first_match -q --tb=short`. 이 확인은 구현자의 자가 확인이며 독립 추적 검증을 대신하지 않는다.
- 복원 후 관련 전체 회귀: `docker compose run --rm -T dev python -m pytest tests/test_p08_person_size.py tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q` **57 passed**. `node tests/test_p08_owner_review.cjs` **2 passed**.
- 현재 소유자 CSV 두 해시는 원본 바이트와 일치하고, 기존 측정 결과·선택 규격·사전등록 config는 변경 전과 동일하다. 측정 CSV 3종은 LF 재직렬화 시 byte 동일하다. 작업 트리에 CRLF로 남아 있던 sd35 확인 목록·빈 양식은 Git blob과 같은 LF로 정규화했다. 문서 링크·`git diff --check`도 확인했다.

## P08-01 종결·당일 마감

- 소유자가 합격 기록을 확인하고 남은 비차단 보강 후 오늘 작업을 마무리하도록 요청했다. 검증자 커밋 `8f5346e`의 라운드 2 판정은 합격이며, B1 해소와 H1~H4 반영 확인을 읽었다.
- 라운드 2 잔여 R1: P08 입력 CSV 4개(`real_disc_candidates.csv`, `real_disc_review.csv`, `recall_labels_agent.csv`, train 빈 양식)를 CRLF에서 LF로 정규화했다. 파싱한 행·값은 동일하며 Git blob과 byte 동일하다. 보조 보고서의 입력 해시 3개만 갱신했다.
- 추가로 공통 `data/metadata.csv`도 worktree CRLF·blob LF임을 확인했다. 이 파일은 기존 실험 해시에 결합돼 있으므로 바이트를 변경하지 않고 `.gitattributes`로 체크아웃 CRLF를 유지한다. P08 측정 CSV는 체크아웃 LF로 지정했다. 사전 규격·소유자 표시·기존 주 측정 수치는 바꾸지 않는다.
- 보조 측정을 CPU로 재실행했고 파생 CSV 2개·rect 발췌 JSON·갱신 보고서 JSON 4종이 기대 산출물과 byte 동일했다. 측정 수치와 기존 주 보고서도 보존했다. 코드 변경은 없어 이미 독립검증된 전체 회귀는 반복하지 않았다.
- `git -c core.autocrlf=false checkout-index --prefix=<임시 디렉터리>/ -- <P08 CSV 14개> data/metadata.csv`와 `core.autocrlf=true` 설정 각각에서 임시 체크아웃을 실행했다. 15개 파일의 바이트가 현재 작업 트리와 동일하며, 보조 보고서에 연결된 입력 해시도 일치했다. `.gitattributes` 설정·합격 판정 첫 줄·문서 상대 링크·staged diff check를 확인했다.
- 측정 README·계획·페이즈 인덱스를 P08-01 Complete로 갱신하고 CHANGELOG에 종결 항목을 추가했다. HANDOFF는 추적 검증 대기를 P08-02 착수로 교체했다. 원 검증기록은 수정하지 않는다.
- 오늘은 P08-02를 착수하지 않고 다음 작업을 명시한 상태로 마무리한다.

## P08-02 익명화 전처리 구현

### 목표

- P08-01 측정·관문을 근거로 모든 얼굴을 같은 함수에서 가린다. 캐시/즉시 결과·증강 전 적용·checkpoint snapshot·fail closed 계약을 검증한다.
- 사용자의 핸드오프 다음 작업 요청은 P08-02 슬라이스 구현으로 해석했다. P08-03 결과 사전 고정과 재학습은 이 작업에서 수행하지 않는다.

### 수행 내용·계약 감사

- `src/anonymize.py`: 규격 필드·범위 검사, canonical JSON 해시, 학습 YAML→snapshot 변환, YuNet 전체 검출, 결정적 원·경계 처리, 무결성 검증 캐시, CPU 생성 CLI를 추가했다. P06 대표 얼굴 선택 함수는 사용하지 않는다. 검출된 작은 얼굴의 최소 크기 경계는 포함한다.
- `src/dataset.py`: 원본 RGB를 익명화한 뒤 기존 transform을 적용한다. `src/train.py`는 train/val에 같은 worker를 전달하고 best/last checkpoint에 전체 규격·해시를 결합한다. `src/evaluate.py`·`src/calibrate.py`·`src/score.py`는 checkpoint 규격을 검증·사용한다. score의 legacy/null 거부는 encoder 구성 이전에 수행한다.
- 정본 `configs/anonymize.yaml` → 학습 진입 snapshot → checkpoint → 평가/calibration/score로 흐른다. 규격 해시는 파생 무결성 값, checkpoint snapshot은 당시 설정 보존에 필요한 의도적 복제다. P06 검출 config는 과거 진단 스냅샷이라 변경하지 않는다. API 구현·응답 변경은 P07 범위다.
- 얼굴 좌표는 `experiments/p08_anonymized/face_boxes.csv`가 소유하는 파생 artifact다. 키는 metadata image_id·이미지 바이트 hash·검출 모델 hash·검출 파라미터 hash이며 값은 모든 상자 목록이다. 모델 경로는 배포 위치이므로 파라미터 hash에서 제외하며 모델 identity는 별도 키로 검증한다. 원 크기·fill·경계 규격은 좌표 검출에 영향이 없어 캐시 해시에 포함하지 않는다. metadata에는 열을 추가하지 않는다.
- 캐시 생성은 각 행 flush와 기존 행 이미지 hash 검증 후 재개를 제공한다. 기존 행 재검증에는 이미지 디코딩이 필요 없으므로 바이트 해시만 검사한다. Dataset 캐시 경로는 매 접근마다 이미지 hash를 검사하며 누락/불일치에 즉시 검출 fallback을 하지 않는다.
- 새 학습 config에는 익명화 YAML 경로 또는 명시적 null이 필수다. 기존 `baseline.yaml`·`dino.yaml`·`primary.yaml`에는 null만 추가했다. 기존 모델 설정·선정·checkpoint·P05/P06 artifact는 변경하지 않았다. 기존 학습 fixture도 명시 null로 갱신하고 P05 score 테스트는 null 거부로 전환했다. 정상 익명화 score 결정성·출력은 신규 통합 셀이 검증한다.
- legacy/null 비교 평가에는 명시적 규격 override를 제공한다. 결합된 규격 덮어쓰기는 거부한다. baseline 평가 명령은 checkpoint 디렉터리에 결과를 쓰므로 별도 비교용 사본 경로를 쓰도록 문서에 명시했다. 새 모델 원본 입력 진단은 P08-03 후속 범위다.
- README·HANDOFF의 기존 baseline score 실행 예시를 제거하고 P08 artifact 대기 상태를 반영했다. 페이즈·인덱스는 독립검증 대기로 맞췄다. 규격의 stale 측정 대기 주석을 고쳤으며 `.gitattributes`에 좌표 캐시 LF를 추가했다.

### 검증

- 회귀 테스트를 먼저 작성했으며 신규 모듈 부재로 수집 실패(exit 2)를 확인했다. Docker 접근은 sandbox에서 거부되어 승인된 Docker 실행 경로를 사용했다.
- 첫 집중 회귀 `tests/test_anonymize.py tests/test_baseline.py tests/test_calibration.py tests/test_train_smoke.py`: **21 passed**.
- 전체 Python suite `docker compose run --rm -T dev python -m pytest -q`: **137 passed**, 기존 Pillow deprecation warning 12개. 이후 신규 경계 커널·규격 범위·모델 로드 전 거부 셀과 관련 변경은 최신 집중 회귀로 확인했다.
- 최종 집중 회귀(같은 4개 파일): **30 passed**. 캐시 재개 경로 정리 후 `tests/test_anonymize.py`를 다시 확인해 **15 passed**. 캐시 검출을 무시하는 변경과 정상 빈 목록·최소 크기 포함·legacy/null 평가·올바른 snapshot 양방향을 잠근다. P08-01 단일 원 경계 커널은 랜덤 RGB/소수 좌표에서 byte 동일하다.
- 실측 생성 명령: `docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev python -m src.anonymize`(CPU). 캐시 6,000행은 metadata ID 전수와 일치하며 train 3,780 / val 820 / test 800 / test_unseen 600, REAL 3,000 / GEN 3,000이다. 얼굴 있음 1,949장·없음 4,051장·다중 얼굴 7장·전체 얼굴 1,957개다.
- 같은 캐시에 `write_face_cache`를 재실행해 6,000장 이미지 바이트 hash를 전수 확인했고 출력 CSV SHA256 `319d5376f71e3c65155857b33fa2e4dc653d2094a7b8f8cbef90812393d15af8`이 byte 동일했다. 원본 이미지·metadata·기존 실험 파일은 수정하지 않았다.
- 실제 split × source_type 7개 층에서 seed 20261013으로 층별 5장(35장)을 뽑았다. 캐시 좌표 목록은 즉시 YuNet 좌표와 float값까지 동일했고, 가린 얼굴 수·최종 이미지 픽셀도 전부 동일했다. 전수 즉시 재검출 동등성을 입증한 것은 아니며 실표본 비교와 stub 회귀로 검증했다.
- 변경 문서 로컬 링크 전수 존재·`git diff --check`를 확인했다. HANDOFF diff는 2행 추가/2행 삭제이고 기존 P08-02 착수·baseline score 실행을 대체했다. 마지막 자가 검수는 42줄로 유지된다. GPU 재학습은 실행하지 않았다.
- 자가 검증이며 독립검증 판정을 대신하지 않는다. 슬라이스 완료는 독립검증 합격 후 갱신한다.

### 발견한 문제·판단

- 초기 원 칠하기 구현에서 fill을 int64 배열로 만들면 측정 커널과 float 정밀도가 달라질 여지가 있었다. float32 alpha·fill로 맞추고 P08-01 `paint_synthetic`과 실제 픽셀의 byte 일치 셀을 추가했다.
- baseline score를 encoder 로드 후에 거부하면 불필요한 모델 로드/다운로드가 먼저 일어날 수 있다. `load_model(require_anonymization=True)`에서 snapshot 검사를 먼저 수행하도록 정리하고 legacy/null 양쪽을 encoder 구성 전 거부하는 셀로 잠갔다.
- 타원은 측정 결과 미채택이며 현재 모듈은 원 규격만 허용한다. 원 크기 관문 실패와 검출 누락 한계는 그대로 유지한다.

## P08-02 합격 후 비차단 보강

### 목표·사용자 요청

- 소유자가 독립검증 합격 기록 `docs/verifications/2026-10-13/p08_02_anonymize_module.md`의 비차단 H1·H2 보강 후 작업 마무리를 요청했다. P08-03을 이번 작업에서 착수하지 않는다.
- 검증자 판정은 합격이고 차단 건은 없다. 원 검증기록은 변경하지 않으며, 보강은 현재 구현의 방어를 잠그는 테스트로 한정한다.

### 수행 내용·첫 검증

- H1: `test_detect_sorts_unordered_overlapping_faces`는 YuNet stub의 역순 겹침 얼굴을 좌표순으로 전부 반환하는지 확인한다. `test_paint_sorts_unordered_overlapping_faces`는 detect를 우회한 비정렬 상자에서도 양 순서의 최종 픽셀이 P08-01 커널을 좌표순으로 적용한 기준 이미지와 동일한지 확인한다. 두 얼굴 보존·원 내부 흰색·배경 보존도 함께 잠근다.
- H2: `test_evaluate_rejects_face_cache_without_anonymization[legacy/null]`은 실제 평가 CLI 인자 경로에 캐시만 지정하면 거부함을 확인한다. 캐시 없는 정상 원본 평가 허용도 같은 셀에서 확인한다. 모델 로드는 stub 처리해 외부 모델·이미지·캐시 파일 없이 해당 경계만 검증한다.
- `docker compose run --rm -T dev python -m pytest tests/test_anonymize.py -q`: **19 passed**. production 코드·규격·실측 캐시는 변경하지 않았다.
- 변이 전 새 테스트와 본 기록을 체크포인트 커밋으로 보존한다. 이후 각 변이 전 실제 `git status --short` 빈 값 확인 → 변이 → 집중 셀 재실패 확인 → HEAD 바이트 복원·byte 일치·clean 확인을 수행한다. 변이 결과와 종결 상태는 후속 기록에 남긴다.

### 변이 검증·종결

- 체크포인트 `aec27b3` 이후 각 변이 직전 `git status --short` 빈 값을 실행·확인했다. 복원은 `git show HEAD:src/anonymize.py`의 바이트를 파일에 쓰고 byte 일치·트리 clean을 확인했다. 원 검증기록과 production 코드는 변경하지 않는다.

| 변이 | 파일·위치 | 재실패 셀 | 결과 |
| --- | --- | --- | --- |
| M1: `return sorted(validate_boxes(boxes))` → `return validate_boxes(boxes)` | `src/anonymize.py:153` | `test_detect_sorts_unordered_overlapping_faces` | 1 failed, exit 1 |
| M2: `for ... in sorted(boxes)` → `for ... in boxes` | `src/anonymize.py:171` | `test_paint_sorts_unordered_overlapping_faces` | 1 failed(겹침 픽셀 불일치), exit 1 |
| M3: `cache_path is not None` 거부 블록 제거 | `src/anonymize.py:89` | `test_evaluate_rejects_face_cache_without_anonymization[legacy]`, `[null]` | 2 failed(정해진 ValueError 대신 하류 KeyError), exit 1 |

- 각 변이 명령은 `docker compose run --rm -T dev python -m pytest tests/test_anonymize.py -k <표의 함수명> -q --tb=short`다. 각각 HEAD 바이트로 복원했고 마지막 `tests/test_anonymize.py -q`는 **19 passed**다. 이번 변경은 테스트 보강뿐이므로 이미 독립검증된 전체 suite·6,000장 캐시 실측은 반복하지 않았다.
- 독립검증자의 최종 `d667327` 전체 suite는 **144 passed**다. 앞선 구현 기록의 137은 중간 실행 수치이고 당시 최종 집중 회귀는 30이었다. 이력을 재작성하지 않고 최종 커밋 기준 수치를 여기 명시한다.
- 사용자 요청에 따라 P08-02를 Complete로 종결했다. 계획·인덱스·전처리 README의 독립검증 대기를 합격·보강 결과로 교체하고, HANDOFF의 다음 작업은 P08-03으로 대체했다. HANDOFF는 42줄이고 완료 서술을 덧붙이지 않았다. CHANGELOG에 종결 항목을 추가했다.
- 새 테스트는 검출·칠하기 순서를 직접 잠그며, 현재 구현·규격·캐시·기존 artifact에 행동 변경은 없다. 문서의 상대 링크와 `git diff --check`를 확인했다.

## P08-03 진단·채택 사전등록

### 목표·사용자 결정

- 소유자는 다음 슬라이스 진행 후 서브에이전트 한 명의 독립검증을 받고 차단·비차단 모두 보강해 합격까지 진행하도록 요청했다. 이 절차를 P08-03에 적용하며, 구현자 자가 확인과 독립 판정을 구분한다.
- 이번 슬라이스는 config·진단 표본·입력 hash 사전 고정이다. 새 모델 재학습·결과 조회·calibration·실제 진단 실행은 하지 않는다. 원본 입력 비교 실행기를 포함한 P08-06 구현 요구를 계약에 고정한다.

### 구현·계약 소유권

- `configs/anonymized_diagnostic.yaml`이 2×2 평가·주석·개입(a/b/c/d)·단서 등가성 구간·채택 규칙을 소유한다. `docs/sot.md`에 소유 행을 추가했다. AUC 숫자는 project.md §20의 실행용 projection이며 config 테스트로 리터럴을 잠근다.
- `scripts/p08_preregister.py`는 예측 없이 metadata·검증된 전체 얼굴 cache·P08-01 confirmed 원과 기하·이미지 측정 보고서만으로 표본 manifest를 만든다. source ID 유일성·metadata/cache 쌍방 ID·검출 model/parameter hash·좌표·주석 lineage·크기 목표를 검사한다. 규칙의 실행값은 config에서 읽는다.
- 표본·원 기하·빈 얼굴 확인 양식은 파생 CSV, `preregistration.json`은 config·7개 입력 raw-byte hash·3개 CSV hash·수량·크기 목표의 파생 기록이다. 규격·측정·metadata의 원본 파일은 바꾸지 않았다. 기존 출력과 다르면 먼저 전 파일을 검사하고 덮어쓰기를 거부한다. 출력까지 전부 같으면 byte 동일 재생성을 허용한다.
- REAL 원 150개는 149개 train 이미지에 속한다. 같은 이미지의 모든 원을 편집하고 이미지 단위로 bootstrap한다. 이는 held-out 일반화 증거가 아니라 개발 진단이라는 한계를 고정했다.
- GEN 개입은 test/test_unseen 검출 표본을 generator별 최대 40장씩 seed 20261013으로 선택한다. 선택 결과는 162장(4종 각 40, z_image_turbo 2)이다. 부족분을 다른 generator로 채우지 않는다. 모든 얼굴을 처리한다.
- GEN 얼굴 확인 대상은 평가 GEN 952장 전체다. 원본의 얼굴 수·익명화 후 남은 얼굴 수를 모델 score 블라인드로 표시해 놓친 얼굴을 없음으로 오인하지 않는다. 주석 완료·소유자 확인 목록/hash는 새 모델 진단 예측 전에 별도 커밋한다. 현재는 빈 양식만 만들었다.
- 크기 확대 목표는 기존 이미지 측정의 k=1.2 GEN 중앙값 0.1631602984208327이다. 기존 원보다 작은 목표면 줄이지 않는다. 측정 대표 얼굴 유도값이라는 한계를 명시하고 전체 캐시로 사후 재추정하지 않는다.
- candidate 단서 관문은 얼굴 상태 FP rate 차이 95% 구간이 ±10%p 안, 각 개입의 평균 절대 score 변화 구간 상한 ≤5점·기존 정답→오답 전환율 Wilson 상한 ≤5%이다. 개입 최소 80이미지·얼굴 상태 최소 20이미지·주석 부재/NaN/표본 부족은 미확정이며 채택하지 않는다. signed 변화·반대 전환으로 효과를 상쇄하지 않는다. 허용폭은 개발용 운영 기준이며 사용자 체감에서 검증된 값은 아니다.
- candidate 익명화 Test A/B AUC 0.90/0.80와 5개 단서 관문을 모두 만족해야 primary를 교체하고 보고한다. 미채택은 baseline 유지·P07 대기·P08 재시도, 재실패는 소유자 결정이다. P08-07 얼굴이 보이는 REAL 외부 holdout은 한계로 남고 P07 관문이 아니다.

### 자가 확인

- 최초 사전등록 집중 회귀 6개 통과 후 source 거부 경계를 추가해 `docker compose run --rm -T dev python -m pytest tests/test_p08_preregister.py -q`: **11 passed**. 결과 혼입 금지·빈 검출 이미지 보존·byte 동일 재생성·입력 변경 거부/기존 출력 보존·cache hash·중복 ID·REAL split·주석/좌표/목표 거부·config 관문을 확인했다.
- 실제 사전등록 생성은 150원/149 REAL 이미지·162 GEN 개입·952 얼굴 확인 양식과 0.1631602984208327 목표로 재현됐다. 후보 checkpoint `/mnt/h/tracepector/checkpoints/anonymized/best.pt`는 이 머신에서 존재하지 않았다. 모델을 로드하거나 예측하지 않았다.
- config의 cue_model과 채택 상태 이름은 첫 커밋 전에 정리했고 사전등록 hash만 재생성했다. manifest 3개의 바이트·표본·기하는 그대로다. 이후 결과 전에 커밋으로 고정한다.
- 독립검증 결과는 별도 검증 기록으로 남긴다. 이번 구현자 확인을 독립 판정으로 취급하지 않는다.

### 독립검증 1차 지적 보강

- 사용자 지시에 따라 한 명의 서브에이전트를 구현자 대화 맥락 없이 스폰했다. 첫 사전등록 커밋은 `77da668`, 독립검증 보고서 커밋은 `a0cbc42`이고 판정은 B1~B3 불합격이다. 보고서 원문은 검증자가 소유하며 구현자는 수정하지 않는다.
- B1: 같은 이미지 한 번 재추출이라는 모호한 문구를 제거했다. 이미지별 공동 편집·한 예측과 bootstrap의 n개 인덱스 복원추출/반복 허용을 구분했다.
- B2: config의 (a) 상태·주석/구간·표본, (b/c/d) 기하/개입, 구간 허용폭·결측·채택 실패 분기를 named 계약 셀로 잠갔다. alpha45/beta43/gamma2+무얼굴1 fixture의 cap40·seed 순차 shuffle golden 제외 ID·부족 생성기 all·원2개/이미지1개 집계·manifest hash를 확인한다. cache 누락/추가/중복·review 중복·REAL label/image_id 불일치 거부 셀도 추가했다.
- B3: 실제 REAL `1287673`은 기존 원과 별개 위치의 YuNet 얼굴을 가진다. REAL shape/size는 정상 익명화 RGB 위의 추가 overlay로 다른 마스크도 보존하고, GEN gray/restore만 원본 기반으로 구성한다. config의 `construction_base`와 문서를 일치시켰다.
- H1: bootstrap `numpy.random.Generator(numpy.random.PCG64(seed))`·행별 `(20000,n)` 정수 복원추출·percentile `method="linear"`를 config/문서에 고정했다. seed·표본·허용폭은 그대로다.
- H2: 선택 REAL 기하의 모든 수치 유한성·너비/축 양수·major≥minor를 출력 전에 검사한다. 음수 중심·등축은 정상 clipping으로 허용하며 양방향 회귀로 잠근다.
- `docker compose run --rm -T dev python -m pytest tests/test_p08_preregister.py tests/test_anonymize.py -q`: **50 passed**. 이 명령은 사전등록 변경과 재사용한 hash/좌표 계약의 관련 회귀이며 GPU 학습을 하지 않는다.
- 새 학습 결과가 없는 상태에서 보강된 config raw hash만 사전등록에 반영했다. 7개 원본 input hash·3개 CSV·REAL149/GEN162/주석952·크기 목표는 최초와 동일하다. config hash는 `b526e3923b95368f7ca99e2d44f87e723109009f21163e82934cab9a2ec605cb`다. source/표본 변경 없이 config 해석·회귀만 고정했다.
- 보강 커밋 후 같은 검증자에게 추적검증을 요청한다. 최종 합격 전 P08-04는 대기한다.

### 독립검증 라운드 2 합격·종결

- 같은 검증자가 `b0b1b84`를 추적검증했고 보고서 커밋 `ce1ba79`에서 **합격**으로 확정했다. B1~B3·H1~H2 모두 해결됐고 남은 차단·비차단 지적은 없다. 구현자 확인과 구별되는 독립 기록이다.
- 검증자가 사전등록 31개·관련 50개 회귀를 재실행해 통과했고 6종 변이(cap 축소·generator 역순·허용폭 확대·REAL 원본 기반·기하 검사 제거·등축 과잉 거부)가 각각 guarding cell을 재실패시켰다. 변이별 위치·셀·결과와 복원 byte/clean 근거는 [독립검증 라운드 2](../../verifications/2026-10-13/p08_03_diagnostic_preregistration.md)에 있다. 구현자가 같은 파괴적 검증을 중복하지 않았다.

| 독립검증자 변이·위치 | 재실패 셀 | 결과 |
| --- | --- | --- |
| `ids[:cap]` → `ids[:1]`, `scripts/p08_preregister.py:81` | `test_stratified_cap_seed_undersized_generator_and_multi_disc_images` | 1 failed |
| generator 정렬 역순, `scripts/p08_preregister.py:78` | 위 표본 셀 | 1 failed |
| score 상한 5→50, `configs/anonymized_diagnostic.yaml` score 블록 | `test_intervention_equivalence_contract_uses_images_and_absolute_effects` | 1 failed |
| REAL shape 기반 normal_anonymized→original, 동일 config interventions 블록 | `test_intervention_construction_preserves_other_real_face_masks` | 1 failed |
| 기하 조건 제거, `scripts/p08_preregister.py:67` | `test_registration_rejects_invalid_real_geometry` | 7 failed, 비숫자는 float 변환이 계속 거부하여 1 passed |
| major<minor→major≤minor, `scripts/p08_preregister.py:69` | `test_registration_allows_finite_clipped_disc_geometry` | 1 failed |

- 독립 재현에서도 7개 원본 hash·3개 CSV는 최초 사전등록과 byte 동일하고 config 해시만 변경됐다. 기존 checkpoint·P05/P06 artifact·metadata·이미지와 새 학습 결과는 변경/생성하지 않았다.
- 계획·페이즈 인덱스·진단 README는 P08-03 Complete로 갱신하고 HANDOFF는 P08-04 재학습으로 대체했다. 소유자의 한 명 독립검증→전 지적 보강→추적 합격 절차를 현재 작업 방식으로 명시했다. HANDOFF는 43줄이며 완료 사건을 덧붙이지 않고 다음 작업과 절차를 유지한다. 문서 링크·diff 검사를 마친 뒤 종결 기록을 커밋한다.

## 다음 작업

- P08-04: primary와 같은 설정의 익명화 학습 config를 만들고 사전등록 고정 상태에서 재학습한다. GPU 점유 정책·기존 artifact 비덮어쓰기·재개 가능한 작업 방식을 지킨다.
- P08-05 calibration 이후 P08-06 진단 실행기를 사전등록 계약대로 구현한다. 얼굴 주석 952장과 확인 목록/hash는 candidate 진단 예측 전에 확정한다.

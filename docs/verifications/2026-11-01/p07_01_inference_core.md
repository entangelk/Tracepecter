# P07-01 공유 추론 코어 독립검증

## 대상 메타데이터

- 날짜: 2026-11-01
- 요청자: 소유자(entangelk), 메인 세션 경유
- 검증자: Claude Opus 5.5 (독립 검증 서브에이전트, 구현에 관여하지 않음)
- 대상: P07-01 공유 추론 코어. 커밋 `bb4cdf2`(DB-08 Resolution 반영 문서), `9d6b0cb`(구현). 비교 기준 부모 `92f8e7f`.
- 정본 규격: `docs/plan/phase_7_api_demo.md`(§계약의 소유권과 데이터 흐름, 슬라이스 표, §P07-01), `docs/decision_briefs/DB-08_P07_response-contract.md` Resolution, `docs/project.md` §22, `docs/plan/phase_8_face_anonymization.md` §계약·소유권(checkpoint 결합)·"추론 계약 세부", `docs/sot.md:24`(calibration artifact 소유 행), `README.md` "Inference 방법"·"Calibrated image score".
- 작업 원천: `main` HEAD `9d6b0cb`, 검증 시작 시 작업 트리 clean.

## 범위

1. 계약 자체 정합성: 위 정본 사이의 모순 여부, DB-08 결정 반영.
2. 구현: `src/inference.py`, `src/score.py`(CLI가 코어 호출), `load_calibration`의 기존 import 경로(`from src.score import load_calibration`) 유지.
3. 회귀 테스트: `tests/test_inference.py` 신규, `tests/test_anonymize.py` 변경분, 거부 경로를 잡는 기존 셀.
4. mutation testing: 경계 행렬의 각 칸이 실제로 무는지.
5. 전체 CPU suite와 실제 artifact CPU smoke, 부모 커밋 CLI와의 점수 동등성.

## 방법

- 계약 범위를 먼저 읽고 경계 행렬을 만든 뒤 코드를 읽었다(아래 행렬).
- 검증 약화 여부: `diff <(git show 92f8e7f:src/score.py | sed -n '/^def load_calibration/,/return artifact/p') <(sed -n '/^def load_calibration/,/return artifact/p' src/inference.py)` → 동일.
- 집중 테스트: `docker compose run --rm -T dev python -m pytest tests/test_inference.py tests/test_anonymize.py tests/test_calibration.py -q` → 35 passed, exit 0.
- 전체 suite: `docker compose run --rm -T dev python -m pytest -q` → 301 passed, 1 skipped, exit 0(50.8s).
- mutation: `git status --short` 빈 상태 확인 후 스크립트(세션 scratchpad의 `mutate.py`)로 `src/inference.py`에 변이를 하나씩 적용 → 지정 셀 실행 → `git checkout -- src/inference.py`. 실행마다 끝에 `git status --short` 빈 문자열을 확인했다. M1~M12는 집중 3파일, M13~M19는 전체 suite로 돌려 다른 파일의 셀이 흡수하는지도 봤다.
- 실제 smoke(CPU): `docker compose --profile training run --rm -T train python -m src.score --image "/images/real/스포티/998959.jpg" --calibration experiments/p09_leakage_repair/r1/calibration/calibration.json --device cpu`.
- `model_version` 독립 재계산: 프로젝트 함수를 쓰지 않고 `hashlib.sha256`으로 checkpoint 파일 바이트, calibration 파일 바이트를 직접 hash하고, checkpoint 내부 `config['anonymization']['sha256']`을 읽어 `sha256(ck + ':' + cal + ':' + anon)[:12]`와 구분자 없는 연결을 둘 다 계산했다.
- 부모 CLI 동등성: `git show 92f8e7f:src/score.py | docker compose --profile training run --rm -T train python - --image ... --calibration ... --device cpu`.

## 경계 행렬

| # | 계약 조항(출처) | 방향 | 잡는 셀 | mutation 결과 |
| --- | --- | --- | --- | --- |
| 1 | 응답 필드는 네 개, `confidence` 없음(DB-08 결정 2, plan §P07-01) | 둘 다 | `test_inference.py:63` 필드 집합 등식, `test_anonymize.py:195` | M11(값 0) 3셀 실패 |
| 2 | `faces_anonymized` = 익명화기가 그린 원 수(plan 소유 표, phase_8 추론 계약) | 과소 | `test_inference.py:63`(=2), `:90`, `test_anonymize.py:196` | M11 실패 |
| 3 | `model_version`: 셋 중 하나만 바뀌어도 값이 바뀜(과소 엄격) | 과소 | `test_inference.py:50`(위치 0·1·2), `:109` | M5(익명화 성분 제거) `[2]` 실패 |
| 4 | `model_version`: 같은 입력이면 같은 값(과잉 엄격) | 과잉 | `test_inference.py:42`, `:78` | — |
| 5 | `model_version` 성분: checkpoint sha256·calibration **파일** sha256·익명화 **규격** sha256 | 과소 | `test_inference.py:72` | M6(파싱 JSON hash) 실패, M7(YuNet 파일 hash) 실패 |
| 6 | `model_version` 유도식: "정해진 순서", "sha256", "앞 12자리" | 과소 | **없음**(`:72`는 같은 `model_version` 함수를 호출해 자기참조) | **M1(sha1)·M2(뒤 12자리)·M3(순서 cal,ck,anon) 모두 생존** |
| 7 | 연결 구분자 | — | 계약 침묵, 코드는 `':'` | M4(구분자 제거) 생존 |
| 8 | `realism_score` = `100*sigmoid(logit/T)`, T는 artifact 소유(plan 소유 표, §22, DB-08 결정 1) | 과소 | **없음** | **M18(T=1.0 고정) 생존**; M19(×100 제거)는 경계 셀이 우연히 잡음 |
| 9 | `classification` threshold는 artifact 소유(DB-08 결정 1, sot.md:24) | 과소 | **없음** — fixture threshold가 0.5(`test_inference.py:36`)이고 경계 셀은 `scorer.threshold`를 직접 덮어씀(`:103`,`:105`) | **M17(threshold=0.5 고정) 생존** |
| 10 | threshold와 같으면 `photographic_like`, 아래면 `synthetic_like` | 둘 다 | `test_inference.py:98` | M8(`>`) 실패 |
| 11 | CLI와 코어가 같은 점수(plan §P07-01) | 둘 다 | `test_inference.py:63`(dict·stdout 등식) | 실제 artifact로도 부모 CLI와 동일(아래) |
| 12 | 1회 로드(plan 슬라이스 표) | 과소 | `test_inference.py:78` | — |
| 13 | 키 없음/`null` checkpoint 거부, encoder 로드 전(phase_8 checkpoint 결합, §22) | 과소 | `test_anonymize.py:247`, `:97` | M10(`require_anonymization=False`) 2셀 실패 |
| 14 | YuNet 누락·불일치 거부(phase_8 추론 계약) | 과소 | `test_anonymize.py:104`(`checkpoint_anonymizer` 단위, Scorer가 같은 함수를 `required=True`로 호출) | 코드 경로 공유로 확인 |
| 15 | 규격 내용·sha256 불일치 거부 | 과소 | `test_anonymize.py:104`, `:208` | — |
| 16 | `load_calibration`: checkpoint hash(plan §P07-01) | 과소 | `test_calibration.py:49` | M16 실패 |
| 17 | `load_calibration`: 버전·방법(plan §P07-01) | 과소 | **없음** | **M13 생존(전체 suite)** |
| 18 | `load_calibration`: 유한 온도(plan §P07-01) | 과소 | 음수만 `test_calibration.py:49`; NaN/inf 없음 | **M15(isfinite 제거) 생존** — 요청 시 `apply_temperature`가 2차 방어하나 시작 시 거부는 사라짐 |
| 19 | `load_calibration`: threshold 범위 [0,1](plan §P07-01) | 과소 | **없음** | **M14 생존(전체 suite)** |
| 20 | 비유한 점수 거부(P07-02 직렬화 계약의 선행) | 과소 | `test_inference.py:119` | M9 실패 |
| 21 | 비RGB 입력 변환 | 과소 | `test_inference.py:90` | M12 실패 |

## 발견 사항

### 1. 계약 정합성

- DB-08 Resolution(결정 1·2·3 A)이 `phase_7_api_demo.md:18,47,64`, `project.md` §22, README "Inference 방법", `00_index.md` P07 행에 같은 의미로 반영됐다. `project.md` §22의 3단계 `thresholds` 예시와 "Threshold는 config에서 관리"가 지워져 `sot.md:24`(threshold 소유자 = calibration artifact)와 충돌이 해소됐다.
- `project.md` §22 "검출기와 원 규격은 config가 소유한다"와 phase_8 "하류는 checkpoint에 저장된 규격만 쓴다"는 정본(config)과 snapshot(checkpoint)의 관계라 모순이 아니다.
- **계약 침묵(구분자)**: `phase_7_api_demo.md:48`은 세 sha256을 "정해진 순서로 이어 붙인 문자열"이라고만 한다. 코드(`src/inference.py:32`)는 `':'`로 잇는다. 실제 artifact에서 `':'` 연결은 `f5bf7f4d004f`, 문자 그대로의 연결은 `8ad600b65b0d`로 값이 다르다. 세 값이 고정 64자 hex라 어느 쪽도 단사이지만, 외부 소비자가 재계산할 식별자이므로 계약이 구분자와 순서를 글자로 고정해야 한다. 작업 기록에는 `:`가 적혀 있으나 작업 기록은 계약이 아니다.
- README 예시 `"realism_score": 82.4`는 반올림된 값처럼 보이지만 실제 출력은 `85.53991233735206`이다. 필드 집합·타입은 일치하고 예시 값은 설명용이므로 차단 사유로 보지 않는다(보강 H3).

### 2. 구현

- `load_calibration`은 부모 `src/score.py`와 바이트 단위로 같다(위 diff). 검증 약화 없음. `src/score.py:9`가 재노출해 `scripts/p06_patterns.py:22`, `scripts/p08_diagnostic.py:29`, `scripts/p09_diagnostic.py:10`, `scripts/p08_leakage_probe.py:21`, `src/failure_analysis.py:22`, `src/face_mask.py:21`, `src/face_mask_ci.py:21`, `tests/test_calibration.py:57`의 import가 그대로 동작한다(전체 suite 통과).
- 거부 순서: `Scorer.__init__`가 `load_calibration`(`src/inference.py:38`) → `load_model(..., require_anonymization=True)`(`:39`)을 부르고, `load_model`은 `torch.load` 직후 `checkpoint_anonymizer(required=True)`(`src/evaluate.py:101`)를 encoder 생성(`:103`)보다 먼저 호출한다. 무익명화 checkpoint는 encoder 로드 전에 거부된다.
- `model_version` 성분: checkpoint는 `artifact['checkpoint_sha256']`(`:46`)로, 같은 생성자에서 `load_calibration`이 파일 hash와 일치함을 확인한 값이다. calibration은 `file_sha256(calibration)`으로 파일 바이트 hash다. 익명화는 `config['anonymization']['sha256']`로, `Anonymizer.__init__`(`src/anonymize.py:127`)가 `spec_hash(spec)`와 같음을 확인한 규격 결합 hash다. 계약의 "checkpoint·calibration 파일·익명화 규격"과 일치하고 순서도 계약의 나열 순서다.
- 분류 `probability >= self.threshold`(`src/inference.py:58`)는 부모 코드와 같은 경계다.
- 독립 재계산한 `model_version` `f5bf7f4d004f`가 실제 CLI 출력과 일치했다.
- CLI/코어 동등성: 실제 artifact·같은 이미지에서 새 CLI `{"realism_score": 85.53991233735206, "classification": "photographic_like", "faces_anonymized": 0, "model_version": "f5bf7f4d004f"}`, 부모 CLI `{"realism_score": 85.53991233735206, "classification": "photographic_like"}`. 점수·분류 완전 일치, 둘 다 exit 0.
- 1회 로드: 모델은 1회지만 `Anonymizer`는 `load_model` 내부(`src/evaluate.py:101`, 결과 버림)와 `src/inference.py:41`에서 두 번 만들어져 YuNet 파일 hash도 두 번 계산된다. 정합성 문제는 아니다(보강 H1).
- calibration 파일은 `load_calibration`에서 한 번 읽고, `model_version`용 hash는 모델 로드 뒤 다시 읽어 계산한다(`:46`). 그 사이 파일이 바뀌면 식별자와 실제 파라미터가 어긋날 수 있다(보강 H2).
- 복잡도: 이미지당 고정 크기 연산, 입력 크기 의존 반복 없음.

### 3. 회귀 테스트

- `tests/test_inference.py` 11개 셀(파라미터 포함), 작업 기록의 개수·집중 35·전체 301/1과 재현 수치가 같다.
- 셀 대부분이 공개 응답 dict를 단언한다. 다만 `model_version` 유도식(`:72`)은 기대값을 같은 `model_version` 함수로 계산해 유도식 자체를 잠그지 못한다(행렬 6).
- 경계 셀(`:98`)은 threshold를 인스턴스에서 덮어써 artifact → threshold 배선을 우회한다. fixture threshold 0.5(`:36`)는 흔한 하드코딩 값과 겹친다(행렬 9).
- 점수 공식은 `0 <= realism_score <= 100` 범위만 단언해 temperature 배선을 잠그지 못한다(행렬 8).
- 거부 경로는 무익명화(행렬 13)·YuNet(14)·checkpoint hash(16)·비유한(20)만 잠겨 있다. P07-01 본문이 나열한 버전·방법·유한 온도·threshold 범위(17~19)는 셀이 없다. 부모 커밋부터 있던 공백이지만 P07-01 계약(`phase_7_api_demo.md:46`)이 이 검증들을 이름으로 열거하고 완료 증거로 "거부 경로 회귀 테스트"(`:40`)를 요구한다.

### 4. mutation testing

| 변이 | 위치 | 결과 |
| --- | --- | --- |
| M1 `hashlib.sha256`→`sha1` | `src/inference.py:33` | 생존(35 passed) |
| M2 `[:12]`→`[-12:]` | `:33` | 생존 |
| M3 순서 ck,cal,anon→cal,ck,anon | `:32` | 생존 |
| M4 구분자 `':'`→`''` | `:32` | 생존(계약 침묵) |
| M5 익명화 성분 제거 | `:32` | `test_model_version_changes_when_any_component_changes[2]` 실패 |
| M6 calibration hash를 파싱 JSON hash로 | `:46` | `test_scorer_response_contract_and_cli_agree` 실패 |
| M7 익명화 hash를 YuNet 파일 hash로 | `:47` | `test_scorer_response_contract_and_cli_agree` 실패 |
| M8 `>=`→`>` | `:58` | `test_classification_boundary_belongs_to_photographic` 실패 |
| M9 비유한 거부 제거 | `:55-56` | `test_non_finite_score_rejected` 실패 |
| M10 `require_anonymization=False` | `:39` | `test_score_rejects_before_encoder_loading[missing]`,`[None]` 실패 |
| M11 `faces_anonymized=0` | `:59` | `test_scorer_response_contract_and_cli_agree`, `test_scorer_converts_non_rgb_input`, `test_anonymized_training_evaluation_calibration_and_score` 실패 |
| M12 RGB 변환 제거 | `:50` | `test_scorer_converts_non_rgb_input` 실패 |
| M13 버전·방법 검사 제거 | `:19-20` | 생존(전체 301 passed) |
| M14 threshold 범위 검사 제거 | `:25-26` | 생존(전체) |
| M15 온도 `isfinite` 제거 | `:23` | 생존(전체) |
| M16 checkpoint hash 검사 제거 | `:21-22` | `test_calibration_cli_uses_only_validation_and_rejects_unanonymized_score` 실패 |
| M17 threshold를 0.5로 고정 | `:45` | 생존(전체) |
| M18 temperature를 1.0으로 고정 | `:44` | 생존(전체) |
| M19 `×100` 제거 | `:57` | `test_classification_boundary_belongs_to_photographic` 실패(우연 흡수, 점수 공식 전용 셀 아님) |

모든 변이 뒤 `git checkout -- src/inference.py`, 마지막 `git status --short` 출력 빈 문자열을 확인했다.

### 5. suite·smoke

- 집중 35 passed, 전체 301 passed / 1 skipped(실제 YuNet smoke, 기존 skip), exit 0.
- 실제 artifact CPU smoke exit 0, 위 출력. checkpoint `checkpoints/leakage_repair/r1/best.pt` hash가 artifact `checkpoint_sha256`과 일치, temperature 0.77704, threshold 0.23513.

## 이슈 / 위험

### 차단(계약 의무)

- **B1 — `model_version` 유도식 잠금 없음.** `phase_7_api_demo.md:48`의 "sha256", "앞 12자리", "정해진 순서"를 독립 기대값으로 고정한 셀이 없다. `tests/test_inference.py:72`는 같은 함수를 호출하는 자기참조 단언이다. M1·M2·M3 생존. 필요: 프로젝트 함수를 쓰지 않고 `hashlib.sha256((ck + SEP + cal + anon...).encode()).hexdigest()[:12]`로 계산한 고정 기대값(golden) 셀.
- **B2 — 구분자 계약 침묵.** `src/inference.py:32`는 `':'`를 쓰지만 계약(`phase_7_api_demo.md:48`)은 "이어 붙인"만 적는다. 실제 artifact에서 두 해석의 값이 다르다(`f5bf7f4d004f` vs `8ad600b65b0d`). 계약에 구분자와 순서를 글자로 적고 B1 셀이 그 값을 잠가야 한다.
- **B3 — artifact 소유 temperature·threshold와 점수 공식 잠금 없음.** `phase_7_api_demo.md:26-28`(소유 표), DB-08 결정 1, `project.md` §22의 `100*sigmoid(logit/T)`. M17(threshold 0.5 고정)·M18(T 1.0 고정) 전체 suite 생존. 원인: fixture threshold 0.5(`tests/test_inference.py:36`), 경계 셀의 인스턴스 덮어쓰기(`:103`,`:105`), 점수 범위만 단언. 필요: 0.5가 아닌 artifact threshold로 생성한 `Scorer`의 분류 경계, 그리고 알려진 logit(예: `forward_logits` stub)과 artifact T로 `100*sigmoid(logit/T)`를 독립 계산해 비교하는 셀.
- **B4 — `load_calibration` 거부 분기 셋 잠금 없음.** `phase_7_api_demo.md:46`이 열거한 버전·방법, 유한 온도(NaN/inf), threshold 범위(<0, >1, NaN)에 셀이 없다(M13·M14·M15 전체 suite 생존). 완료 증거 "거부 경로 회귀 테스트"(`:40`)의 일부다. 과잉 엄격 쪽으로 threshold 0과 1 경계값 허용 셀도 함께 필요하다. M15는 요청 시 `apply_temperature`가 2차로 막지만 시작 시 거부(P07-02 "기동 거부")가 사라진다.

### 보강 권고(비차단)

- **H1** — `Anonymizer` 이중 생성: `src/evaluate.py:101`의 결과를 버리고 `src/inference.py:41`에서 다시 만든다. 동작은 맞지만 docstring의 "한 번만 로드"(`src/inference.py:1`)와 어긋나고 YuNet hash를 두 번 계산한다.
- **H2** — calibration 파일 이중 읽기: `load_calibration`(`src/inference.py:18`)의 읽기와 `file_sha256(calibration)`(`:46`) 사이에 파일이 바뀌면 `model_version`이 실제 파라미터와 다른 파일을 가리킨다. 읽은 바이트 하나로 파싱과 hash를 함께 하면 닫힌다.
- **H3** — `realism_score` 정밀도: README·§22 예시는 `82.4`, 실제는 반올림 없는 float다. 반올림 여부를 계약에 적거나 예시가 설명용임을 밝히면 P07-03 데모 표시(`NN / 100`)와의 혼동을 줄인다.
- **H4** — YuNet 불일치 거부를 `Scorer`/CLI 수준에서 직접 확인하는 셀(현재는 `checkpoint_anonymizer` 단위 셀과 코드 경로 공유로만 보장).

## 판정

**조건부 합격** — B1~B4(`model_version` 유도식 golden 잠금, 구분자 계약 명시, artifact temperature·threshold·점수 공식 잠금, `load_calibration` 버전·방법·유한 온도·threshold 범위 거부 셀)를 닫아야 한다.

- 구현 동작은 계약과 일치한다: 네 필드, artifact 소유 threshold, 익명화 강제와 encoder 전 거부, 규격·파일 hash 기반 `model_version`, 부모 CLI와 같은 점수(실제 artifact로 확인), 검증 코드 바이트 동일.
- 차단은 모두 테스트 잠금 부재와 계약 문구 한 곳의 침묵이다. 계약 조항을 깨는 변이 8개(M1·M2·M3·M13·M14·M15·M17·M18)가 테스트를 통과했다. 계약이 침묵하는 M4는 B2로 따로 다룬다.

## 미결 사항

- P07-01 상태는 `phase_7_api_demo.md:40`에서 "Implemented(독립검증 대기)"다. B1~B4 보강 뒤 재검증이 필요하다(소유자 표준 루프).
- P07-02는 B4의 시작 시 거부 셀에 기대므로 보강 뒤 착수하는 편이 안전하다.
- 작업 트리: 이 기록 외 변경 없음.

## 재현

```bash
cd /mnt/f/devel/Tracepecter
git status --short                       # 빈 출력
docker compose run --rm -T dev python -m pytest tests/test_inference.py tests/test_anonymize.py tests/test_calibration.py -q; echo $?
docker compose run --rm -T dev python -m pytest -q; echo $?
# 변이 예(M17): threshold 하드코딩이 suite를 통과하는지
sed -i "s/self.threshold = artifact\['threshold_probability'\]/self.threshold = 0.5/" src/inference.py
docker compose run --rm -T dev python -m pytest -q; echo $?   # 0이면 생존
git checkout -- src/inference.py && git status --short
# 실제 smoke와 부모 CLI 비교
docker compose --profile training run --rm -T train python -m src.score --image "/images/real/스포티/998959.jpg" \
  --calibration experiments/p09_leakage_repair/r1/calibration/calibration.json --device cpu
git show 92f8e7f:src/score.py | docker compose --profile training run --rm -T train python - \
  --image "/images/real/스포티/998959.jpg" --calibration experiments/p09_leakage_repair/r1/calibration/calibration.json --device cpu
```

---

## 추적검증 1 (2026-11-01, 보강 커밋 `e9f5793`·작업 기록 `a6abf0f`)

### 대상 메타데이터

- 요청자: 소유자(entangelk), 메인 세션 경유
- 검증자: Claude Opus 5.5 (1차와 같은 독립 검증 서브에이전트, 구현에 관여하지 않음)
- 대상: `e9f5793`(`src/inference.py`, `tests/test_inference.py`, `docs/plan/phase_7_api_demo.md`, `docs/project.md`, `README.md`). 비교 기준 `a4cd187`(1차 기록).
- 작업 원천: `main` HEAD `a6abf0f`, 시작 시 작업 트리 clean.

### 범위

1. B1~B4 해소 여부(1차 변이 재실행 + 새 변이).
2. 새 테스트 단언이 계약을 잠그는지(과잉 엄격 가드 포함).
3. 계획의 `model_version` 문구와 코드의 글자 일치.
4. H2 변경(`validate_calibration` 분리, `Scorer`의 바이트 1회 읽기)이 검증을 약화하거나 `from src.score import load_calibration` 호출자를 깨지 않았는지.
5. H1 처리 적정성, H3·H4 반영.
6. 전체 suite, 실제 artifact smoke.

### 방법

- `git show e9f5793`의 전체 diff를 읽었다. 작업 기록의 설명은 대조용으로만 썼다.
- 고정값 독립 계산: `python3 -c "import hashlib;H=('a'*64,'b'*64,'c'*64);print(hashlib.sha256(':'.join(H).encode()).hexdigest()[:12])"` → `30b19c9cb857`(테스트 고정값과 일치).
- 집중: `docker compose run --rm -T dev python -m pytest tests/test_inference.py tests/test_anonymize.py tests/test_calibration.py -q` → 53 passed, exit 0.
- mutation: `git status --short` 빈 출력 확인 뒤 scratchpad의 `mutate2.py`로 `src/inference.py` 변이 22개를 하나씩 적용 → 집중 3파일 실행 → `git checkout -- src/inference.py`. 마지막 `git status --short` 빈 문자열 확인(두 번 실행 모두).
- 전체: `docker compose run --rm -T dev python -m pytest -q` → 319 passed, 1 skipped, exit 0(52.2s).
- smoke: 1차와 같은 CPU 명령 → exit 0, `{"realism_score": 85.53991233735206, "classification": "photographic_like", "faces_anonymized": 0, "model_version": "f5bf7f4d004f"}`(1차 독립 재계산값과 동일).
- 재노출 경로: `docker compose run --rm -T dev python -c "from src.score import load_calibration; ..."`로 실제 artifact를 읽어 threshold `0.23513432654393307` 확인.
- 인코딩 차이 확인: `json.loads`에 UTF-8 BOM 바이트와 BOM 문자열을 각각 넣어 비교.

### mutation 결과

| 변이 | 위치(`src/inference.py`) | 결과 | 무는 셀(`tests/test_inference.py`) |
| --- | --- | --- | --- |
| M1 sha1 | `:36` | 실패 | `test_model_version_formula_is_literal`(:57), `test_scorer_response_contract_and_cli_agree`(:76) |
| M2 뒤 12자리 | `:36` | 실패 | 같음 |
| M3 순서 cal,ck,anon | `:35` | 실패 | 같음 |
| M4 구분자 제거 | `:35` | 실패 | 같음 |
| M5 익명화 성분 제거 | `:35` | 실패 | 위 둘 + `test_model_version_changes_when_any_component_changes[2]`(:63) |
| M8 `>=`→`>` | `:62` | 실패 | `test_classification_uses_artifact_threshold[0.0-photographic_like]`(:126) |
| M10 `require_anonymization=False` | `:43` | 실패 | `test_anonymize.py::test_score_rejects_before_encoder_loading[missing/None]` |
| M13 버전·방법 검사 제거 | `:22-23` | 실패 | `test_invalid_calibration_rejected_at_startup[version…, method…]`(:147) |
| M13b 방법 검사만 제거 | `:22` | 실패 | `[method-platt]` |
| M14 threshold 검사 제거 | `:28-29` | 실패 | `[threshold -1e-9, 1+1e-9, nan]` |
| M14b threshold `isfinite`만 제거 | `:28` | 생존 — **등가 변이**: NaN·inf는 `0 <= x <= 1` 비교에서 이미 거짓이라 관측 가능한 차이가 없다 | — |
| M15 온도 `isfinite` 제거 | `:26` | 실패 | `[temperature nan, inf]` |
| M16 checkpoint hash 검사 제거 | `:24-25` | 실패 | `[checkpoint_sha256 …]`, `test_calibration.py::test_calibration_cli_…` |
| M17 threshold 0.5 고정 | `:49` | 실패 | `test_classification_uses_artifact_threshold[1e-09]`, `test_fixture_threshold_separates_from_default`(:135), `test_threshold_range_endpoints_accepted[0.0/1.0]`(:157) |
| M18 temperature 1.0 고정 | `:48` | 실패 | `test_score_uses_artifact_temperature`(:117), `test_classification_uses_artifact_threshold[1e-09]` |
| M19 ×100 제거 | `:61` | 실패 | `test_score_uses_artifact_temperature`, `test_fixture_threshold_separates_from_default` |
| M20 `Scorer`가 검증 생략 | `:42` | 실패 | `test_invalid_calibration_rejected_at_startup` 10셀 전부 |
| M21 `load_calibration`이 검증 생략 | `:18` | 실패 | 같은 10셀 + `test_calibration.py` 1셀 |
| M22 threshold 0·1 거부(과잉 엄격) | `:28` | 실패 | `test_threshold_range_endpoints_accepted[0.0/1.0]` |
| M23 calibration hash를 파싱 JSON hash로 | `:50` | 실패 | `test_scorer_response_contract_and_cli_agree` |
| M24 온도 `<= 0`→`< 0` | `:26` | 실패 | `[temperature-0.0]` |
| **M25 calibration hash를 파일 재읽기(`file_sha256(calibration)`)로** | `:50` | **생존** | 없음 |

### 발견 사항

- **B1 해소.** `test_model_version_formula_is_literal`(:57)이 같은 함수를 쓰지 않는 `hashlib` 계산과 고정 문자열 `30b19c9cb857`을 둘 다 비교하고, 계약 셀(:76)도 기대값을 독립 계산으로 바꿨다. M1~M5 모두 실패.
- **B2 해소.** `docs/plan/phase_7_api_demo.md:48`이 "checkpoint sha256, calibration 파일 바이트의 sha256, 익명화 규격 binding sha256(각각 소문자 hex 64자)을 이 순서로 `:`로 이은 문자열(`<checkpoint>:<calibration>:<anonymization>`)의 sha256 hex 앞 12자리"로 고쳐졌다. 코드 `src/inference.py:35-36`(`':'.join([checkpoint_sha256, calibration_sha256, anonymization_sha256])`, `hashlib.sha256(...).hexdigest()[:12]`)와 순서·구분자·해시·자릿수가 글자로 일치한다. 성분 출처도 일치한다: `:50`의 `artifact['checkpoint_sha256']`(`:24`에서 파일 hash와 대조), `hashlib.sha256(raw)`(calibration 파일 바이트), `config['anonymization']['sha256']`(`src/anonymize.py:127`에서 `spec_hash(spec)`와 대조된 binding hash). `docs/project.md:781`은 유도 규칙을 계획으로 위임해 값이 한 곳에만 있다.
- **B3 해소.** fixture threshold가 0.37(`tests/test_inference.py:37`)이고, 경계 셀(:126)은 threshold를 calibration **파일**로 바꿔 `Scorer`를 새로 만든다(인스턴스 덮어쓰기 제거). 고정 logit 0.625는 float32에서 정확하다. `test_score_uses_artifact_temperature`(:117)가 `100/(1+exp(-0.625/1.5))`를 `abs=1e-9`로 독립 계산해 비교하고, T 무시 값과 다름도 단언한다. M17·M18·M19 모두 전용 셀이 잡는다. 경계 등호(offset 0)에서 M8이 실패하므로 numpy와 Python sigmoid 사이의 1ulp 차이가 등호 셀을 무력화하지 않음도 확인했다.
- **B4 해소.** `test_invalid_calibration_rejected_at_startup`(:147)이 버전, 방법, 온도 0·음수·NaN·inf, threshold −1e-9·1+1e-9·NaN, checkpoint hash 10개 분기를 `load_calibration`과 `Scorer` 생성 양쪽에서 확인한다. 과잉 엄격 쪽은 `test_threshold_range_endpoints_accepted`(:157)가 0과 1 허용을 잡고(M22 실패), 온도 0 경계는 M24로 확인했다. 온도의 과잉 엄격 쪽(양의 유한 값 허용)은 모든 정상 셀이 T=1.5로 통과하므로 잠겨 있다.
- **H2 / 검증 약화 없음.** `validate_calibration`(`src/inference.py:21-30`)의 본문은 1차의 `load_calibration` 검사 네 줄과 같고, `load_calibration`(:18)과 `Scorer`(:42) 둘 다 이를 거친다(M20·M21이 각각 잡힘). `src/score.py:9` 재노출은 그대로이며 전체 suite와 실제 artifact 읽기로 호출자 동작을 확인했다.
  - 파싱 단계 차이: `Scorer`는 `json.loads(bytes)`, `load_calibration`은 `json.loads(read_text())`다. 확인 결과 bytes 경로는 UTF-8 BOM·UTF-16 파일을 받아들이고, 문자열 경로는 BOM을 `JSONDecodeError`로 거부한다. 내용 검증은 같고 현재 artifact는 BOM 없는 UTF-8이라 정합성 위험은 낮다(보강 H5).
- **새 계약 조항이 잠기지 않음.** 보강으로 `phase_7_api_demo.md:48`에 "calibration hash는 검증에 쓴 것과 같은 바이트에서 계산한다"가 계약으로 들어갔다. 코드(`src/inference.py:41-42,50`)는 이를 지키지만, hash를 파일 재읽기로 되돌린 M25가 집중 셀을 모두 통과했다. 이 조항은 읽기와 hash 사이에 파일이 바뀔 때만 관측되는데, 그 상황을 만드는 셀이 없다. 예를 들어 `src.inference.load_model`을 감싸 생성 도중 calibration 파일을 다시 쓰고, `model_version`이 원래 바이트 hash와 같은지 단언하는 셀이 필요하다. 계약에 들어간 분기라 검증 지침상 차단이다(B5).
- **H1 처리 적정.** `Anonymizer`는 여전히 생성 시 두 번 만들어진다(`src/evaluate.py:101` 검증용, `src/inference.py:45`). docstring(`src/inference.py:1`)만 "생성 시 준비하고 요청마다 다시 읽지 않는다"로 고쳤다. 두 번 모두 기동 시 한 번씩이고 요청 경로에는 없다(`test_scorer_loads_once_and_repeats_identically` :91). P07-02 계약도 "요청마다 다시 읽지 않는다"를 기준으로 쓴다. `load_model`의 검증 호출은 평가·calibration 도구와 공유하는 fail-closed 계약이라, 구조를 두는 판단은 surgical change 원칙에 맞다. 슬라이스 표 `phase_7_api_demo.md:40`의 "1회 로드"는 같은 뜻(요청마다 다시 로드하지 않음)으로 읽힌다. 상향 보고할 사안이 아니다.
- **H3 반영.** `README.md:74`, `docs/project.md:782`에 "형식 예시, 반올림하지 않은 실수"를 적었다. 실제 출력과 일치한다.
- **H4 반영.** `test_detector_mismatch_rejected_by_scorer`(:163)가 `Scorer` 생성에서 YuNet hash 불일치 거부를 정확한 메시지로 확인한다.
- 작업 기록 수치(전체 319 passed / 1 skipped, 고정값 `30b19c9cb857`)를 재현했다.

### 이슈 / 위험

#### 차단(계약 의무)

- **B5 — "검증한 바이트에서 calibration hash를 계산한다" 조항 잠금 없음.** 조항은 `docs/plan/phase_7_api_demo.md:48`, 구현은 `src/inference.py:41-42,50`이다. M25 생존. 닫는 방법은 둘 중 하나다. (a) 생성 도중 파일을 바꾸는 회귀 셀을 추가한다. (b) 이 문장을 계약에서 빼고 구현 메모로 내린다. 어느 쪽이든 계약과 셀이 맞아야 한다.

#### 보강 권고(비차단)

- **H5** — 파싱 인코딩 차이: `src/inference.py:42`(`json.loads(raw)`, BOM·UTF-16 허용)와 `:18`(`read_text()`, BOM 거부). `raw.decode('utf-8')`로 맞추면 두 경로의 입력 허용 범위가 같아진다.
- 1차 H1~H4는 위와 같이 처리됐다. 남은 항목 없음.

### 판정(추적검증 1)

**조건부 합격** — B5(계획 `phase_7_api_demo.md:48`의 "검증에 쓴 것과 같은 바이트에서 calibration hash 계산" 조항을 회귀 셀로 잠그거나 계약에서 내릴 것)를 닫아야 한다.

- B1~B4는 모두 닫혔다. 1차에서 살아남은 M1·M2·M3·M13·M14·M15·M17·M18이 전부 전용 셀에서 실패한다. 새 변이 M20~M24(검증 우회 두 경로, threshold 0·1 과잉 엄격, 온도 0 경계, calibration hash 성분)도 모두 잡힌다.
- 계획의 `model_version` 문구와 코드가 글자로 일치한다. 실제 artifact 값 `f5bf7f4d004f`가 독립 계산값과 같다.
- 검증 약화 없음, 재노출 경로 정상, 전체 319 passed / 1 skipped.
- 남은 차단은 보강이 새로 넣은 계약 문장 하나의 잠금 부재다.

### 미결 사항

- B5를 닫으면 같은 방식으로 추적검증 2를 한다. P07-02 착수는 B5와 독립이므로 소유자 판단에 따른다.
- 작업 트리: 이 기록 외 변경 없음.

### 재현

```bash
cd /mnt/f/devel/Tracepecter
git status --short                       # 빈 출력
docker compose run --rm -T dev python -m pytest tests/test_inference.py tests/test_anonymize.py tests/test_calibration.py -q; echo $?
docker compose run --rm -T dev python -m pytest -q; echo $?          # 319 passed, 1 skipped
# M25: 같은 바이트 조항이 잠겼는지
sed -i "s/hashlib.sha256(raw).hexdigest(),/file_sha256(calibration),/" src/inference.py
docker compose run --rm -T dev python -m pytest tests/test_inference.py -q; echo $?   # 0이면 생존
git checkout -- src/inference.py && git status --short
```

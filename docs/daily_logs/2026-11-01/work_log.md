# 2026-11-01 작업 기록

## 목표

- DB-08 소유자 결정을 반영하고 P07-01 공유 추론 코어를 구현한다.

## 완료한 작업

- DB-08 Resolved: 소유자가 세 결정 모두 권장안 A로 확정했다(2단계 분류·artifact가 threshold 소유, `confidence` 제거, API가 정적 데모 페이지 제공). `project.md` §22 출력 예시를 네 필드(`realism_score`·`classification`·`faces_anonymized`·`model_version`)로 고치고 config 3단계 threshold 예시(40/70)를 지웠다. §24 데모 파일을 `demo/index.html`로 바꿨다. README Inference 예시, P07 계획, 페이즈 인덱스(P07 In Progress)도 갱신했다(`bb4cdf2`).
- P07-01 구현:
  - `src/inference.py`: `load_calibration`을 `src/score.py`에서 옮겼다(기존 `from src.score import load_calibration` 경로는 재노출로 유지). `model_version(checkpoint_sha256, calibration_sha256, anonymization_sha256)`은 세 값을 `:`로 이은 문자열의 sha256 앞 12자리다. `Scorer`가 calibration 검증·`require_anonymization=True` 모델 로드·익명화기·transform을 생성 시 1회 준비하고, PIL 이미지 1장을 응답 dict로 바꾼다. 비유한 확률은 거부한다.
  - `src/score.py`: CLI가 `Scorer`를 호출한다. 출력이 두 필드에서 네 필드로 늘었고 README를 함께 고쳤다.
  - 테스트: `tests/test_inference.py`(11개) — model_version 결정성·세 구성요소 각각의 변화·순서 의존, 응답 필드 집합과 CLI 일치, 1회 로드, RGBA/L 입력 변환, threshold 동일값 photographic_like/바로 아래 synthetic_like, calibration 파일 변경 시 version 변화, NaN 거부. `tests/test_anonymize.py`의 score 필드 단언을 네 필드로 갱신했다.
- 검증: 집중 35 passed, 전체 `docker compose run --rm -T dev python -m pytest -q` 301 passed / 1 skipped.
- 실제 artifact CPU 실행(`src.score ... --device cpu`): REAL `/images/real/스포티/998959.jpg` → 85.5399·photographic_like·얼굴 0, GEN `qwen_image_21/gen_000006.png` → 0.00045·synthetic_like·얼굴 1. 둘 다 `model_version` `f5bf7f4d004f`, exit 0. 10-25 CUDA 실행값 85.5396과 장치 간 수치 차이만 있다.

- 독립검증 1차 **조건부 합격**(`a4cd187`): B1 model_version 공식(해시·순서·12자리) 미고정, B2 구분자 계약 미기재, B3 artifact 온도·threshold 하드코딩 변이 생존, B4 calibration 거부 분기 3개 무테스트. 비차단 H1 익명화기 이중 생성과 docstring 불일치, H2 calibration 이중 읽기, H3 예시 반올림, H4 Scorer 수준 YuNet 불일치 테스트.
- 보강(`e9f5793`): 계획에 `<checkpoint>:<calibration>:<anonymization>` 구분자를 명시하고 고정값 `30b19c9cb857`·독립 hashlib 계산으로 잠갔다. 고정 logit(float32에서 정확한 0.625/-0.375)으로 `100*sigmoid(logit/T)`와 artifact threshold 경계를 calibration 파일 경유로 검증하고, fixture threshold를 0.37로 바꿔 고정 0.5 변형을 가른다. version·method·temperature(0·음수·NaN·inf)·threshold(범위 밖·NaN)·checkpoint hash 거부와 0·1 허용을 load_calibration과 Scorer 생성 양쪽에서 확인한다. `Scorer`는 calibration 바이트를 한 번 읽어 검증과 hash에 같이 쓴다(`validate_calibration` 분리). H1은 기동 시 검증용 생성(`load_model`)이 공유 함수의 계약이라 구조는 두고 docstring을 "요청마다 다시 읽지 않는다"로 고쳤다. 예시가 형식 예시이며 점수는 반올림하지 않는다고 §22·README에 적었다.
- 자체 변이 6종(sha1·순서·threshold 0.5·temperature 1.0·version 검사 제거·temperature<=0 제거) 모두 재실패, 복원 후 트리 깨끗. 전체 319 passed / 1 skipped.
- 추적검증 1 **조건부 합격**(`dfcb82e`): B1~B4 해소 확인, 신규 B5 — 계획의 "검증에 쓴 것과 같은 바이트에서 hash" 조항에 테스트 없음(파일 재읽기 변이 M25 생존). 비차단 H5 — Scorer(`json.loads(bytes)`)는 BOM·UTF-16을 받고 load_calibration(`read_text`)은 거부해 입력 규칙이 달랐다.
- 보강(`4b0116c`): Scorer 생성 중 `load_model` 단계에서 파일을 바꿔도 `model_version`이 원래 바이트 hash이고 temperature도 원래 값임을 확인하는 테스트 추가. 두 로더 모두 `bytes.decode('utf-8')`로 읽고 BOM 파일을 양쪽에서 거부하는 테스트 추가. M25·BOM 변이 재실패, 전체 321 passed / 1 skipped.

## 결정

- `load_calibration`은 코어로 옮기되 기존 import 경로를 재노출로 남겼다. 실험 스크립트 다수가 `src.score`에서 가져오므로 기록된 실험 코드를 건드리지 않기 위해서다.
- CLI 출력은 코어 응답을 그대로 쓴다. 출력 형식을 두 개로 나누지 않는다.

## 다음 작업

- P07-01 독립검증 → 보강 → 합격 후 P07-02 `POST /score`(FastAPI 의존성 추가 필요).

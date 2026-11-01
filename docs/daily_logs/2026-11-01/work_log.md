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

## 결정

- `load_calibration`은 코어로 옮기되 기존 import 경로를 재노출로 남겼다. 실험 스크립트 다수가 `src.score`에서 가져오므로 기록된 실험 코드를 건드리지 않기 위해서다.
- CLI 출력은 코어 응답을 그대로 쓴다. 출력 형식을 두 개로 나누지 않는다.

## 다음 작업

- P07-01 독립검증 → 보강 → 합격 후 P07-02 `POST /score`(FastAPI 의존성 추가 필요).

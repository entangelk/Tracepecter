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
- 추적검증 2 **합격**(`4dfd07f`). 남은 비차단 H6(검증을 두 번째 읽기로 하는 연속 재읽기 변형 M30 생존)도 반영: Scorer 생성 중 calibration 파일 읽기가 1회임을 고정하는 테스트(`f438858`) 추가, M30 재실패 확인. P07-01 Complete.
- P07-02 구현: `requirements.txt`에 fastapi 0.162.0·uvicorn 0.54.0·python-multipart 0.0.33·httpx 0.28.1(TestClient용) 고정, dev 이미지 재빌드. `configs/inference.yaml`(calibration 경로·device cpu·10 MiB·JPEG/PNG/WEBP). `api/main.py`의 `create_app`이 `Scorer`를 1회 만들고 `POST /score`가 크기 413·식별 실패 400·형식 415·디코딩 실패 400·픽셀 폭탄 413으로 거부한다. 응답은 pydantic `ScoreResponse`(네 필드, 분류 Literal 두 개). compose `api` 서비스(profile api, 8000 포트). `tests/test_api.py` 22개 추가, 전체 344 passed / 1 skipped.
- 실제 서버 호출(`docker compose --profile api up -d api`, CPU): REAL `998959.jpg` → 200 `85.53991233735206`·photographic_like·얼굴 0, GEN `gen_000006.png` → 200 `0.00044999178855562543`·synthetic_like·얼굴 1, 둘 다 `f5bf7f4d004f`. CLI 값과 같다. 텍스트 파일 → 400. 확인 후 서버를 내렸다.
- P07-02 독립검증 1차 **조건부 합격**(`820740b`): B1 판정 순서 무테스트(M1·M2 생존), B2 설정 소유·배포값 무테스트(M12·M13·M14 생존), B3 계획 GPU 문구 자기모순(내가 같은 커밋에 넣은 "GPU 미제공"이 기존 "GPU는 설정으로 켠다"와 충돌), B4 "메모리에서만" 문구 부정확(1 MiB 초과 업로드는 Starlette 임시 파일), B5 MPO(다중 프레임 JPEG) 415 거부가 계약에 없음. 비차단 H1 lock 이유 오기, H2 README 거부 설명 부족, H3 Content-Type 무시 무테스트, H4 본문 한도, H5 중복 필드, H6 schema 타입.
- 보강(`4d93758`):
  - B1·B2: 판정 순서·설정 소유를 테스트로 고정했다. 이미지가 아닌 대용량 바이트는 413, 잘린 GIF·BMP는 415, 잘린 PNG·JPEG는 400이다. 설정의 formats와 device는 그대로 쓰인다. 배포 설정값 전체를 테스트로 고정했다.
  - B3: 기존 계획 의도대로 정리했다. GPU는 `device: cuda` 설정과 CUDA 이미지(`train`)에서 같은 uvicorn 명령으로 켠다. 모순 문장은 지우고 README에 명령을 적었다.
  - B4: 계획 문구를 실제 동작으로 고쳤다. 1 MiB 초과 업로드는 요청 동안 이름 없는 임시 파일로 받고, 서버가 경로가 있는 파일로 남기지 않는다.
  - B5: `MPO`를 허용 목록에 넣었다. 계획이 받기로 한 JPEG 파일이고 CLI도 첫 프레임으로 점수를 내므로, API만 거부하는 것은 계약 의도와 어긋난다고 판단했다.
  - H1~H6: lock 이유를 "공유 모델 1개의 CPU·메모리 직렬화"로 정정하고 직렬화 테스트를 추가했다. README 거부 표, Content-Type 무시 테스트, 중복 필드는 마지막 것을 쓴다는 문서·테스트를 넣었다. 본문 한도는 외부 배포 시 앞단 과제로 계획에 적었다. OpenAPI 필드 타입도 단언한다.
  - 자체 변이 M1·M2·M7·M12·M14 모두 재실패, 복원 후 트리 깨끗. `tests/test_api.py` 34 passed.
- GPU 경로 실측: GPU 사용률 15%에서 train 이미지를 재빌드하고 `device: cuda` 임시 설정으로 API를 띄웠다. REAL `998959.jpg` → 200 `85.53958214999422`, 10-25 CUDA CLI 값과 같다. 확인 후 컨테이너를 내리고 임시 설정을 지웠다.
- P07-02 추적검증 **합격**(`9b095c4`·`b3d81e9`): B1~B5 해소, B3·B5 해석과 B4 문구 정정은 계약 안의 정당한 해석으로 판정됐다. 남은 비차단 H7 MPO가 설정과 무관하게 허용되는 변형, H8 GPU 절차가 저장소 설정을 고치게 해 배포값 테스트와 충돌, H9 업로드 비저장 무테스트, H10 README 폭탄 판정 문구 부정확.
- 비차단 보강(`45d4d3f`): JPEG만 허용하면 MPO가 415인지 확인하는 테스트를 넣었다. `create_app`은 인자가 없으면 `TRACEPECTER_INFERENCE_CONFIG`가 가리키는 설정 파일을 쓴다. 이 환경변수는 파일만 고르고 값은 설정 파일이 소유한다. README GPU 절차는 컨테이너 안의 임시 cuda 설정을 쓰고 comfyui 선행 빌드를 적었다. 요청 중 쓰기 모드로 여는 파일이 없는지 확인하는 테스트를 넣었고, 폭탄 판정 문구를 `MAX_IMAGE_PIXELS` 2배 초과로 고쳤다. 계획의 "구현 세부" 표제가 구현자 정리이며 소유자 확정이 아님을 밝혔다. 파일 쓰기 변이와 MPO 자동 허용 변이 모두 재실패. 전체 359 passed / 1 skipped. P07-02 Complete.
- P07-03 구현: `demo/index.html`(의존성 없는 단일 HTML, 라이트·다크 토큰, 모바일 폭)과 `api/main.py`의 `GET /`. 화면 로직은 순수 함수 `render`·`errorMessage`로 두고 `tests/test_p07_demo.cjs`(node, 7개)로 점수 반올림·서버 분류 우선·모르는 분류 거부·필드 `image` 전송·거부별 문구·네트워크 실패를 확인했다. `tests/test_api.py`에 고정 안내 문구 두 개 포함, threshold 값 미포함 테스트를 추가했다(39 passed).
- 실제 화면 확인(CPU API + 로컬 Chrome headless, playwright-core): REAL `998959.jpg` → 응답 85.5399/photographic_like/얼굴 0, 화면 "86 / 100"·"실제 착용 촬영과 유사한 이미지입니다."·"가린 얼굴 없음"·막대 85.5399%. GEN `gen_000006.png`(다크 모드) → 응답 0.00045/synthetic_like/얼굴 1, 화면 "0 / 100"·"생성 이미지와 유사한 특성이 보입니다."·"얼굴 1개를 흰 원으로 가린 뒤 평가했습니다.". 텍스트 파일 → 400, 화면 "이미지 파일을 읽을 수 없습니다."·점수 숨김. 스크린샷은 데이터셋 이미지를 담고 있어 저장소에 넣지 않았다(이미지 사본 비추적 관례).
- P07-03 독립검증 1차 **불합격**(`0283d8f`): B1 연속 업로드에서 늦게 온 이전 응답이 거부 화면 위에 점수를 표시(실제 Chrome에서 REAL→bad.txt 시 오류와 "86 / 100" 동시 표시). B2 성공 후 거부 시 점수 숨김 무테스트(stub 기본값이 hidden), B3 `Math.round` 미고정, B4 EXIF 비적용 무테스트, B5 `accept`가 설정 소유 형식 목록을 복제. 비차단 H1 파일 입력 키보드 초점 불가, H2 413 문구, H3 문구 가시성 무테스트, H4 `.dockerignore`가 `demo/` 제외, H5 1회 읽기 무테스트, H6 깨진 미리보기 아이콘, H7 favicon 404.
- 보강(`04de038`): 요청 번호로 마지막 선택만 반영(B1), node stub의 초기 hidden을 마크업에서 읽고 성공→거부·늦은 성공·늦은 실패·반올림(85.54→86 등)·미리보기 오류 테스트 추가, Python에 EXIF 규칙·`accept="image/*"`·안내 문구 비숨김·1회 읽기·dockerignore 테스트 추가. 입력은 시각적으로만 숨겨 Tab 초점 유지, 413 문구 "파일 크기나 이미지 해상도가 너무 큽니다.", 미리보기 실패 시 안내 문구, `data:` favicon, `.dockerignore`에서 `demo/` 제거. 변이 5종(늦은 응답 무시 제거·점수 숨김 제거·floor·EXIF 제거·형식 목록 복원) 모두 재실패. 실제 Chrome에서 REAL→bad.txt 연속 선택 시 점수 숨김·오류만 표시, Tab 초점이 파일 입력에 간다.
- P07-03 추적검증 1 **조건부 합격**(`78d23ca`): B1~B5 해소, 코드 결함 없음. 계획 구현 세부의 두 분기에 테스트가 없었다. T1은 늦게 온 이전 HTTP 거부를 무시하는지(M17 생존), T2는 새 선택 시 이전 오류를 숨기는지(M20 생존)다. 비차단 H8 입력 초점 무테스트, H9 dockerignore 테스트 경로가 cwd 의존, H10 계획 문구 "허용 형식 숫자".
- 보강(`2100937`): node 테스트 2개(이전 415가 최신 성공 뒤에 도착해도 결과 유지, 새 선택 즉시 오류 숨김), Python 입력 초점 정적 테스트, dockerignore 경로를 `__file__` 기준으로, 계획 문구를 "크기 한도 값과 허용 형식 목록"으로 고쳤다. M17·M20·M21 재실패, node 18/18, 전체 Python 367 passed / 1 skipped.

## 결정

- `load_calibration`은 코어로 옮기되 기존 import 경로를 재노출로 남겼다. 실험 스크립트 다수가 `src.score`에서 가져오므로 기록된 실험 코드를 건드리지 않기 위해서다.
- CLI 출력은 코어 응답을 그대로 쓴다. 출력 형식을 두 개로 나누지 않는다.
- API 형식 판정은 바이트 기준이다. 파일 이름·Content-Type은 클라이언트가 임의로 정하므로 쓰지 않는다. EXIF 회전은 학습과 같게 적용하지 않는다.
- 얼굴 검출기 공유 상태 때문에 요청을 lock으로 직렬화했다. MVP 데모 처리량에서는 충분하고, 병렬화는 범위 밖이다.

## 다음 작업

- P07-03 독립검증 → 합격 후 P07 Complete 처리.

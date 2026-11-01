# P07-02 `POST /score` API 독립검증

## 대상 메타데이터

- 날짜: 2026-11-01
- 요청자: 소유자(entangelk), 메인 세션 경유
- 검증자: Claude Opus 5.5 (독립 검증 서브에이전트, 구현에 관여하지 않음)
- 대상: P07-02 `POST /score` API. 커밋 `35c3a24`, 비교 기준 부모 `76cd1eb`.
- 정본 규격: `docs/plan/phase_7_api_demo.md`(§계약의 소유권과 데이터 흐름, 슬라이스 표, §P07-02 "구현 세부" 포함, §완료 조건), `docs/decision_briefs/DB-08_P07_response-contract.md` Resolution, `docs/project.md` §22·§24·§25, `README.md` "Inference 방법".
- 작업 원천: `main` HEAD `35c3a24`, 검증 시작 시 작업 트리 clean.

## 범위

1. 계약 자체 정합성(계획 내부, 계획 ↔ DB-08 ↔ §22 ↔ README).
2. 구현: `api/main.py`, `configs/inference.yaml`, `compose.yaml`의 `api` 서비스, `requirements.txt` 신규 pin. P07-01 `src/inference.py`는 API가 의존하는 부분만.
3. 회귀 테스트 `tests/test_api.py`(22셀)와 경계 행렬 대응.
4. mutation testing(M1~M15).
5. 전체 CPU suite, stub 프로브, 실제 artifact CPU 서버 smoke와 CLI 값 비교.

## 방법

- 계약 범위를 먼저 읽고 아래 경계 행렬을 만든 뒤 코드를 읽었다.
- 집중 테스트: `docker compose run --rm -T dev python -m pytest tests/test_api.py -q` → 22 passed, exit 0.
- 전체 suite: `docker compose run --rm -T dev python -m pytest -q -p no:cacheprovider` → 344 passed, 1 skipped, exit 0(54.3s).
- stub 프로브: scratchpad의 `probe.py`·`probe2.py`를 `docker compose run --rm -T dev python - < probe.py`로 실행. `create_app(cfg, scorer=stub)`에 stub 호출 객체를 넣어 거부 경로·순서·형식 판정·업로드 spool 동작을 직접 확인했다(저장소에 파일을 만들지 않음).
- mutation: 사전 `git status --short` 빈 출력 확인 → scratchpad `mutate.py <이름>`으로 변이 적용 → `pytest tests/test_api.py -q` → `git checkout -- api/main.py src/inference.py configs/inference.yaml` → 마지막에 `git status --short` 빈 출력 재확인. M10은 `tests/test_inference.py`도 추가 실행.
- 데이터셋 형식 표본: REAL 3372장 중 600장 무작위 표본을 `Image.open(...).format`으로 집계.
- 실제 서버: `docker compose --profile api up -d api` → `GET /openapi.json` 200(약 12초) → `curl -F image=@...` 호출 → `docker compose --profile api down`. CLI 비교는 `docker run ... tracepecter/dev python -m src.score --image ... --calibration experiments/p09_leakage_repair/r1/calibration/calibration.json`. GPU는 쓰지 않았다.

## 경계 행렬

| # | 계약 조항(출처) | 방향 | 잠그는 셀 | mutation 결과 |
| --- | --- | --- | --- | --- |
| 1 | 한도 정확히 = 수락(plan:59, config 10 MiB) | 과잉 엄격 | `test_size_limit_boundary`(at_limit) | M4(`>`→`>=`) 재실패 |
| 2 | 한도 +1바이트 = 413, 점수 없음(plan:53) | 과소 엄격 | `test_size_limit_boundary`(below) | M3(`read(limit)`) 재실패 |
| 3 | 허용 형식 JPEG·PNG·WEBP = 200, DB-08 네 필드(plan:53, DB-08:62) | 과잉 엄격 | `test_accepted_formats_return_contract[3]` | M15·M6 경유 확인 |
| 4 | 디코딩 가능하지만 허용 목록 밖 = 415, 점수 없음(plan:53) | 과소 엄격 | `test_decodable_but_unsupported_format_is_415[GIF,BMP,TIFF]` | M6·M15 재실패 |
| 5 | 이미지 아님·빈 파일·잘린 PNG/JPEG = 400(plan:53·60) | 과소 엄격 | `test_undecodable_bytes_are_400[4]` | — |
| 6 | 형식은 파일 이름이 아니라 바이트(plan:59) | 양방향 | `test_format_is_read_from_bytes_not_filename` | M6 재실패 |
| 7 | 형식은 Content-Type이 아니라 바이트(plan:59) | 양방향 | 없음(모든 셀이 `application/octet-stream`) | 프로브로 동작은 맞음 → H3 |
| 8 | 판정 순서: 크기(413)가 식별 실패(400)보다 먼저(plan:60) | 순서 | **없음** | **M1 생존** → B1 |
| 9 | 판정 순서: 허용 목록 밖(415)이 디코딩 실패(400)보다 먼저(plan:60) | 순서 | **없음** | **M2 생존** → B1 |
| 10 | `DecompressionBombError` = 413(plan:60) | 과소 엄격 | `test_decompression_bomb_is_413` | M5 재실패 |
| 11 | `image` 필드 없음 = 422(plan:60) | 과소 엄격 | `test_missing_or_misnamed_field_is_rejected` | — (FastAPI 소유) |
| 12 | 200 응답에 NaN 없음, 500(plan:54·63) | 방어 | `test_non_finite_score_is_not_serialized` + P07-01 `test_non_finite_score_rejected` | M10 API 셀 생존(2차 방어가 흡수), 코어 셀 재실패 |
| 13 | 모델 1회 로드(plan:55) | 과소 엄격 | `test_model_loaded_once_at_startup` | M8 재실패 |
| 14 | artifact 검증 실패 = 기동 실패(plan:64) | 과소 엄격 | `test_invalid_artifact_blocks_startup[3]` | M9 재실패 |
| 15 | 응답 schema·OpenAPI enum(DB-08:61·62) | 양방향 | `test_openapi_schema_matches_contract` | M11 재실패 |
| 16 | 허용 목록·크기 한도·device는 config 소유(plan:30·59) | 소유권 | 크기만 `test_size_limit_boundary`가 변화시킴. 형식·device는 **없음** | **M12·M14 생존** → B2 |
| 17 | 배포 config 값 10 MiB·JPEG/PNG/WEBP(plan:59, README:81) | 값 | **없음**(테스트는 자체 yaml만 씀) | **M13 생존** → B2 |
| 18 | 동일 입력 동일 출력(plan:56) | 과잉 엄격 | `test_same_input_same_output` | — |
| 19 | 점수 계산 lock 직렬화(plan:62) | 구현 세부 | 없음 | M7 생존 → H1(근거 자체가 사실과 다름) |
| 20 | 원본 이미지 비저장, "메모리에서만"(plan:34) | 방어 | 없음 | 프로브: 1 MiB 초과 시 디스크 임시 파일 → B4 |

## 결과

### 1. 계약 자체 정합성

- DB-08 Resolution(`DB-08:61-62`), §22(`docs/project.md:768-783`), README(`README.md:61-83`), 계획(`phase_7_api_demo.md:22-30,47`)의 응답 네 필드·분류 어휘 두 개·`confidence` 부재·threshold의 artifact 소유는 서로 일치한다.
- **모순(B3)**: `phase_7_api_demo.md:57`은 "기본 device는 CPU로 두고 GPU는 설정으로 켠다"인데, 이번 커밋이 추가한 `phase_7_api_demo.md:64`는 "GPU 실행은 이번 범위에서 제공하지 않는다"이다. 실제로 compose `api` 서비스(`compose.yaml:27-39`)는 CPU 이미지에 `gpus`가 없어 `device: cuda`로 바꿔도 GPU로 켜지지 않는다. "구현 세부(2026-11-01 확정)"(`:58`)는 구현자가 같은 커밋에서 쓴 것이고, 작업 기록 결정 절(`docs/daily_logs/2026-11-01/work_log.md` 결정)에는 GPU 범위 축소에 대한 소유자 결정이 없다.
- **문구와 실제 동작 불일치(B4)**: `phase_7_api_demo.md:34` "요청 처리 후 메모리에서만 쓴다". Starlette 1.10.0의 `UploadFile`은 `SpooledTemporaryFile`(1 MiB)이라 1,048,577바이트부터 디스크 임시 파일로 넘어간다(프로브: 1,048,576 → `rolled=False`, 1,048,577·3 MiB → `rolled=True`, 이름 없는 fd). 요청이 끝나면 닫혀 사라지므로 "저장하지 않는다"(README:81)는 맞지만 "메모리에서만"은 일반적인 사진 크기(1~10 MiB)에서 사실이 아니다. 또 multipart 본문 전체를 받은 뒤에야 413 판정을 한다.
- **규격 침묵·코드 강제(B5)**: MPF가 있는 다중 프레임 JPEG(Ultra HDR·gain map JPEG 등)는 PIL이 format `MPO`로 연다. 설정 목록(`configs/inference.yaml:5`)에 `MPO`가 없어 415가 된다(프로브: `MPO detected as MPO … 415`). 계획은 "JPEG를 받는다"(`:53`)와 "PIL format으로 판정"(`:59`)만 말하고 MPO를 다루지 않는다. 같은 파일을 CLI(`src/score.py:19`)는 점수 낸다. 데이터셋 REAL 표본 600장은 모두 `JPEG`라 학습 분포 영향은 확인되지 않았다.

### 2. 구현

- 거부 순서(`api/main.py:37-48`): `read(limit+1)` → 413 → `Image.open` 실패 400 → format 415 → `convert('RGB')` 실패 400, `DecompressionBombError` 413. 프로브로 계획 순서를 모두 따름을 확인했다: 한도 초과 비이미지 → 413, 헤더가 살아 있는 반쪽 GIF·BMP·TIFF → 415, 반쪽 PNG·JPEG → 400. `HTTPException`은 `OSError` 하위가 아니라 415가 400으로 삼켜지지 않는다. `ImageFile.LOAD_TRUNCATED_IMAGES`는 `False`.
- 형식 판정은 바이트에서만 한다(`:42`). 프로브: PNG 바이트 + `image/gif` → 200, GIF 바이트 + `image/png` → 415.
- 거부 시 모두 `HTTPException`이므로 점수 필드가 응답에 없다. stub 호출 수로 거부 요청이 scorer에 닿지 않음을 확인했다(14요청 중 200인 6건만 호출).
- NaN: 코어가 `ValueError`(`src/inference.py:59-60`)를 내고 500이 된다. 코어 검사를 지워도(M10) Starlette `JSONResponse`의 `allow_nan=False`가 직렬화 단계에서 예외를 내 500이므로 200에 NaN이 실리는 경로는 없다(이중 방어).
- 1회 로드·기동 거부: `create_app`이 `Scorer`를 한 번 만들고(`:31`), 검증 실패 예외는 그대로 올라간다. `uvicorn --factory`(`compose.yaml:39`)에서 factory 예외는 기동 실패다.
- 응답 schema(`:19-23`)와 실제 서버 OpenAPI가 DB-08과 일치: 네 필드 모두 required, `classification` enum `['photographic_like','synthetic_like']`, 타입 number/string/integer/string.
- config 소유: 한도·형식·calibration 경로·device를 `configs/inference.yaml:2-5`에서 읽는다(`api/main.py:27-31`). temperature·threshold 값은 config·API 어디에도 없다(`grep` 확인). 10 MiB는 README·계획 산문에 반복되지만 코드 상수는 없다.
- lock(`:32,49`): 동기 `def` 엔드포인트는 threadpool에서 돌므로 lock은 실제로 직렬화한다. 그러나 주석과 계획(`:62`)의 근거 "얼굴 검출기가 입력 크기 상태를 가진다"는 사실과 다르다. `Anonymizer.detect`는 호출마다 `cv2.FaceDetectorYN.create`로 새 검출기를 만든다(`src/anonymize.py:159`). lock은 해롭지 않고 보수적이다(H1).
- 원본 비저장: 엔드포인트는 바이트·PIL 객체를 지역 변수로만 쓴다. 실제 서버에서 10 MiB+1 업로드 뒤 컨테이너 `/tmp`에는 torch 모듈 디렉터리만 있고 업로드 파일은 없었으며, 저장소 `git status`도 깨끗했다.
- 의존성: `requirements.txt:12-15` exact pin, 이미지에서 fastapi 0.162.0·starlette 1.10.0·Pillow 11.3.0 확인.

### 3. 회귀 테스트

- 각 셀의 assert가 공개 표면(HTTP 상태·JSON 본문·OpenAPI)을 겨냥한다. 크기 경계는 정확히 한도/한도-1 두 방향, 형식은 허용 3종/비허용 3종, 이름 판정은 양방향이다.
- 빈 칸: 행렬 8·9(판정 순서), 16·17(config 소유권·배포 값). 이 칸들은 계약이 명시한 조항이며 해당 변이(M1·M2·M12·M13·M14)가 녹색으로 살아남았다.

### 4. mutation testing

| 변이 | 내용 | 결과(실패 셀) |
| --- | --- | --- |
| M1 | 크기 검사를 디코딩 뒤로 | **생존** |
| M2 | `convert`를 format 검사 앞으로 | **생존** |
| M3 | `read(limit)` | `test_size_limit_boundary` |
| M4 | `>`→`>=` | `test_size_limit_boundary` |
| M5 | `DecompressionBombError` except 제거 | `test_decompression_bomb_is_413` |
| M6 | 파일 이름 확장자로 판정 | `..._is_415[GIF,BMP,TIFF]`, `test_format_is_read_from_bytes_not_filename` |
| M7 | lock 제거 | 생존(H1) |
| M8 | 요청마다 `Scorer` 생성 | `test_model_loaded_once_at_startup`, `test_non_finite_score_is_not_serialized` |
| M9 | 기동 시 `ValueError` 삼킴 | `test_invalid_artifact_blocks_startup[3]` |
| M10 | 코어 `isfinite` 검사 제거 | API 셀 생존(Starlette `allow_nan=False`가 흡수), `tests/test_inference.py::test_non_finite_score_rejected` 재실패 |
| M11 | `classification: str` | `test_openapi_schema_matches_contract` |
| M12 | 형식 목록 코드 하드코딩 | **생존** |
| M13 | 배포 config 100 MiB·GIF 추가 | **생존** |
| M14 | config `device` 무시 | **생존** |
| M15 | 디코딩 except를 `Exception`으로 | `..._is_415[3]`, `test_format_is_read_from_bytes_not_filename` |

사전·사후 `git status --short` 모두 빈 출력.

### 5. suite·smoke

- 전체 suite 344 passed / 1 skipped, exit 0. 작업 기록의 수치와 같다.
- 실제 서버(CPU): REAL `스포티/998959.jpg` → 200 `{"realism_score":85.53991233735206,"classification":"photographic_like","faces_anonymized":0,"model_version":"f5bf7f4d004f"}`. 같은 이미지 CLI 출력과 바이트 단위로 같다. GEN `qwen_image_21/gen_000006.png` → 200 `0.00044999178855562543`·synthetic_like·얼굴 1·`f5bf7f4d004f`(작업 기록 수치와 같음). 텍스트 파일 400, 10 MiB+1 바이트 413, 필드명 `file` 422. 동시 4요청 응답 모두 동일.

## 문제·위험

### Blocking(계약 의무)

- **B1 — 판정 순서 조항에 잠금 없음**. `phase_7_api_demo.md:60`은 크기(413) → 식별 실패(400) → 허용 목록 밖(415) → 디코딩 실패(400) 순서를 명시한다. 현재 코드는 순서를 지키지만(`api/main.py:37-48`, 프로브 확인) M1(크기 검사를 디코딩 뒤로)과 M2(`convert`를 format 검사 앞으로)가 모두 녹색이다. 필요한 셀: 한도 초과 비이미지 바이트 → 413, 헤더가 살아 있는 잘린 GIF(또는 BMP) → 415.
- **B2 — config 소유권과 배포 값에 잠금 없음**. `phase_7_api_demo.md:30,59`는 형식 목록·크기 한도·device를 `configs/inference.yaml`이 소유한다고 한다. 테스트는 형식 목록을 바꿔 보지 않아 하드코딩(M12)이 살아남고, `device` 무시(M14, `api/main.py:31`)도 살아남는다. 또 배포 config 값(`configs/inference.yaml:4-5`의 10485760·JPEG/PNG/WEBP, README:81의 공개 문구)을 읽는 테스트가 없어 100 MiB·GIF로 바뀌어도(M13) 녹색이다. 필요한 셀: 비기본 형식 목록(예: `['PNG']`이면 JPEG 415)으로 목록 소유 확인, `device` 전달 확인, 저장소 `configs/inference.yaml` 값 고정.
- **B3 — 계획 내부 모순(GPU)**. `phase_7_api_demo.md:57` "GPU는 설정으로 켠다" ↔ `:64` "GPU 실행은 이번 범위에서 제공하지 않는다". 후자는 구현자가 같은 커밋에서 추가했고 소유자 결정 기록이 없다. 소유자가 어느 쪽이 정본인지 정하고 다른 쪽을 고쳐야 한다.
- **B4 — "메모리에서만" 문구와 실제 동작 불일치**. `phase_7_api_demo.md:34`. 1 MiB 초과 업로드는 프레임워크가 이름 없는 디스크 임시 파일에 둔다(프로브). 영구 저장은 아니므로 문구를 "영구 저장하지 않는다(1 MiB 초과는 요청 동안 이름 없는 임시 파일)"로 고치거나, 코드에서 메모리 전용으로 바꿀지 소유자가 정해야 한다.
- **B5 — 규격 침묵·코드 강제(MPO JPEG 415)**. 다중 프레임 JPEG는 PIL format `MPO`라 `configs/inference.yaml:5` 목록 밖 → 415. CLI(`src/score.py:19`)는 같은 파일을 점수 낸다. 계획 `:53,59`는 이 경우를 다루지 않는다. `MPO`를 허용 목록에 넣을지(첫 프레임 점수, CLI와 같음), 415를 계약에 명시할지 정하고 해당 회귀 셀을 추가해야 한다.

### Hardening recommendations(비차단)

- **H1** — lock 근거 정정. `api/main.py:32` 주석과 `phase_7_api_demo.md:62`의 "검출기가 입력 크기 상태를 가진다"는 `src/anonymize.py:159`(호출마다 새 검출기)와 맞지 않는다. lock 유지 자체는 문제없으니 근거 문구를 "보수적 직렬화"로 고치는 정도.
- **H2** — `README.md:81` "잘린 파일은 400"은 허용 형식에 한정해야 정확하다(잘린 GIF는 계획 순서대로 415). 픽셀 폭탄 413·필드 누락 422도 한 줄 추가할 수 있다.
- **H3** — Content-Type이 판정에 쓰이지 않음을 잠그는 셀 추가(`tests/test_api.py:37`이 항상 `application/octet-stream`). 프로브상 동작은 맞다.
- **H4** — 413 판정 전 본문 전체를 받는다. 외부 배포는 범위 밖이지만, 배포 시 reverse proxy 본문 한도나 스트리밍 한도가 필요하다.
- **H5** — 같은 이름 `image` 필드가 둘이면 마지막 것을 쓴다(프로브: 유효 PNG + 쓰레기 → 400). 계약 침묵, 영향 작음.
- **H6** — `test_openapi_schema_matches_contract`(`tests/test_api.py:136-141`)에 필드 타입(number/integer/string) 단언 추가.

## 판정

**조건부 합격** — B1(판정 순서 회귀 셀), B2(config 소유권·배포 값 회귀 셀) 추가와 B3(GPU 모순)·B4("메모리에서만")·B5(MPO JPEG) 소유자 정리·대응 셀 추가가 조건이다.

- 응답 schema·OpenAPI enum·NaN 차단·1회 로드·기동 거부·크기 양방향 경계·바이트 기반 형식 판정은 계약대로이고 각 변이가 무는 셀이 있다.
- 실제 서버 값이 CLI와 일치한다(85.53991233735206, photographic_like, 0, `f5bf7f4d004f`).
- 남은 문제는 코드 결함이 아니라 계약이 명시한 조항의 잠금 누락(B1·B2)과 계약 문구 정합성(B3·B4·B5)이다.

## 미결 사항

- 슬라이스 표 상태는 "Implemented(독립검증 대기)"(`phase_7_api_demo.md:41`)로 남아 있다. 조건 해소 후 추적검증이 필요하다.
- P07-03은 P07-02 선행이므로 조건 해소 전 착수 여부는 소유자 판단이다.

## 재현

```bash
cd /mnt/f/devel/Tracepecter
git status --short                                   # 빈 출력
docker compose run --rm -T dev python -m pytest tests/test_api.py -q
docker compose run --rm -T dev python -m pytest -q
# mutation 예: M1
#   api/main.py 37-39의 크기 검사를 convert 뒤로 옮김 → pytest tests/test_api.py -q → 22 passed(생존)
#   git checkout -- api/main.py && git status --short
docker compose --profile api up -d api               # GET /openapi.json 200 대기
curl -F "image=@/mnt/h/tracepector/images/real/스포티/998959.jpg" localhost:8000/score
docker compose --profile api down
```

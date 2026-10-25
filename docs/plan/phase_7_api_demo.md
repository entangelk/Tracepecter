# P07 — Inference API와 Web Demo

**상태:** Waiting for Decision ([DB-08](../decision_briefs/DB-08_P07_response-contract.md)). 계획 작성 2026-10-25.

## 목표

`docs/project.md` §22·§23·§28에 따라 채택된 모델을 HTTP API와 간단한 웹 데모로 연결한다. 사용자가 패션 이미지 한 장을 올리면 원본 미리보기, 가린 얼굴 수, 0~100 Photographic Realism Score, 분류, "실제 촬영 여부를 증명하지 않는다"는 안내를 본다. 로그인·DB·사용자 관리는 구현하지 않는다(§28).

## 선행 조건

- 채택된 artifact: `checkpoints/leakage_repair/r1/best.pt` + `experiments/p09_leakage_repair/r1/calibration/calibration.json`(P09-04, [진단](../../experiments/p09_leakage_repair/r1/diagnostic/README.md)). 실행 설정 정본은 `configs/primary.yaml`이다.
- P08 추론 계약([phase_8 §추론 계약 세부](phase_8_face_anonymization.md)):
  - 모든 추론은 checkpoint에 결합된 익명화 규격으로 얼굴을 흰 원으로 가린 뒤 점수를 낸다.
  - 규격 키가 없거나 `null`인 checkpoint, YuNet 누락·불일치는 거부한다.
  - 응답에 `faces_anonymized`를 넣는다.
  - `model_version`은 checkpoint·calibration artifact·익명화 규격 sha256의 조합을 식별한다.
- 기존 `src/score.py` CLI가 같은 경로를 실제 이미지로 실행한다(2026-10-25 확인, exit 0).
- **DB-08 결정**: 응답 분류 체계·threshold 소유, `confidence` 필드, 데모 형태. 결정 전에는 구현하지 않는다.

## 계약의 소유권과 데이터 흐름

| 값 | 소유자 | API에서의 성격 |
| --- | --- | --- |
| 이미지 바이트 | 클라이언트 | 유일한 입력(`multipart/form-data`, 필드 `image`) |
| temperature·확률 threshold | calibration artifact | 서버 소유. config는 artifact 경로만 가리키고 값을 복제하지 않는다 |
| `realism_score` | `100*sigmoid(logit/T)`에서 유도 | 읽기 전용 |
| `classification` | artifact threshold에서 유도(DB-08 결정 1) | 읽기 전용, 어휘는 `photographic_like`/`synthetic_like` |
| `faces_anonymized` | 익명화기가 그린 원 개수 | 읽기 전용 |
| `model_version` | checkpoint·calibration·익명화 규격 sha256에서 유도 | 읽기 전용, 서버 시작 시 1회 계산 |
| 업로드 크기·형식 제한, device | `configs/inference.yaml`(신규, §24·§25) | 서버 설정 |

- API와 CLI는 한 추론 함수를 공유한다. 전처리·점수·분류 규칙을 두 곳에 따로 쓰지 않는다.
- 데모는 API 응답만 표시한다. 점수 경계나 분류 문구를 데모가 따로 계산하지 않는다.
- 원본 이미지는 저장하지 않는다(DB 없음). 요청 처리 후 메모리에서만 쓴다.

## 슬라이스와 통과 기준

| ID | 작업 | 선행 조건 | 완료 증거 | 상태 |
| --- | --- | --- | --- | --- |
| P07-01 | 공유 추론 코어 | DB-08 결정 1·2 | `src/inference.py`: artifact·모델·익명화기를 1회 로드하고 이미지 1장 → 응답 dict. `src/score.py`는 이 코어를 호출. `model_version` 유도·거부 경로 회귀 테스트 | Planned |
| P07-02 | `POST /score` API | P07-01 | `api/main.py`(FastAPI): 정상 응답 schema, 잘못된 이미지·형식·크기 거부, 시작 시 artifact 검증 실패면 기동 거부. TestClient 테스트와 실제 이미지 1장 호출 기록 | Planned |
| P07-03 | Web Demo·실행 경로 | P07-02, DB-08 결정 3 | 업로드 → 원본 미리보기 → 점수·분류·가린 얼굴 수·고정 안내 문구 표시. compose 서비스, README Inference 절 갱신, 실제 이미지로 화면 확인 | Planned |

### P07-01 — 공유 추론 코어

- `load_calibration` 검증(버전·방법·checkpoint hash·유한 온도·threshold 범위)과 `require_anonymization=True` 모델 로드를 그대로 쓴다. 검증을 약화하지 않는다.
- 응답 필드는 DB-08 결정 결과로 확정한다. 결정 전 초안은 `realism_score`, `classification`, `faces_anonymized`, `model_version`이다.
- `model_version`: checkpoint sha256, calibration 파일 sha256, 익명화 규격 sha256을 정해진 순서로 이어 붙인 문자열의 sha256 앞 12자리. 셋 중 하나만 바뀌어도 값이 달라져야 하고(과소 엄격 가드), 같은 입력이면 같아야 한다(과잉 엄격 가드).
- 같은 이미지는 CLI와 코어에서 같은 점수를 낸다. 기존 score CLI 출력 형식은 유지하거나, 바꾸면 README를 같은 커밋에서 고친다.

### P07-02 — `POST /score` API

- 입력: `multipart/form-data`의 `image` 하나. JPEG·PNG·WebP를 받고, 디코딩 실패는 400, 지원하지 않는 형식은 415, 크기 초과는 413으로 거부한다. 거부 시 점수를 내지 않는다.
- 응답: P07-01 dict를 그대로 직렬화한다. NaN·무한대는 직렬화 전에 거부한다.
- 모델은 프로세스 시작 시 1회 로드한다. 요청마다 다시 읽지 않는다.
- 테스트는 stub 모델 fixture로 schema·거부 경로·동일 입력 동일 출력을 확인하고, 실제 artifact 호출은 수동 실행 기록으로 남긴다.
- 실행: compose에 `api` 서비스를 추가한다. 기본 device는 CPU로 두고 GPU는 설정으로 켠다. GPU 점유 정책(HANDOFF 주의)을 따른다.

### P07-03 — Web Demo

- §23 화면: 업로드, 원본 미리보기, 점수 막대와 `NN / 100`, 분류 문구, 가린 얼굴 수, 고정 안내 문구 두 개.
  - "이 점수는 이미지가 실제 촬영처럼 보이는 정도를 평가하며, 실제 촬영 여부를 증명하지 않습니다."
  - "얼굴 영역은 점수에 반영되지 않습니다."
- 형태는 DB-08 결정 3에 따른다.
- 확인: 실제 REAL·GEN 이미지 각 1장 이상을 데모로 올려 화면과 API 응답이 일치하는지 기록한다. 화면 확인은 기능 확인이며 일반화 근거가 아니다.

## 완료 조건

- 세 슬라이스의 회귀 테스트와 전체 CPU suite 통과, 슬라이스별 독립검증 합격(소유자 표준 루프).
- `project.md` §22 출력 예시와 README Inference 절이 실제 응답과 일치한다(DB-08 결과 반영).
- 데모가 `docs/project.md` §23의 필수 문구와 가린 얼굴 수를 표시한다.
- 인포그래픽 현황 보고서(`reports/infographic/tracepecter_report.html`)에 P07 결과를 반영한다.

## 병행 작업과 제외

- 제외: 로그인·DB·사용자 관리(§28), 이미지 저장, 대량 배치 API, 외부 배포·인증, 모델 재학습·재보정.
- 제외: P08-07 얼굴이 보이는 실사 holdout, 신규 데이터 수집, 사람 평가. 기존 결정대로 P07의 관문이 아니다.
- 병행 가능: holdout 수집 설계(별도 페이즈)는 P07과 독립이다.

## 관련 결정 브리프

- [DB-08](../decision_briefs/DB-08_P07_response-contract.md) — 응답 분류 체계·`confidence`·데모 형태 (Open)
- [DB-06](../decision_briefs/DB-06_P06_face-exposure.md) — 추론 전 얼굴 익명화 (Resolved)

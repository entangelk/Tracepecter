**합격** — 차단 건 없음. 비차단 보강 후보 2건(H1: detect/칠하기의 좌표순 정렬 가드 부재, H2: legacy checkpoint + `--face-cache` 단독 거부 셀 부재)은 아래와 같다.

# P08-02 익명화 전처리 모듈 독립검증

## 대상

- 날짜: 2026-10-13(KST).
- 요청자: 소유자("작업 AI가 작업한거 독립검증해줘" — 핸드오프 P08-02 독립검증 지시).
- 검증자: 구현에 참여하지 않은 Claude Code 세션(신규, 구현자 맥락 미승계).
- 검증 대상: P08-02 슬라이스 전체 — `src/anonymize.py` 모듈, 학습·평가·calibration·score 실행 경로 연결, checkpoint 규격·해시 결합 계약, 얼굴 좌표 캐시 `experiments/p08_anonymized/face_boxes.csv`(6,000행), 회귀 테스트, 문서 갱신(README·sot·HANDOFF·인덱스·CHANGELOG·`.gitattributes`).
- 작업 출처: `main` `d667327`(HEAD), working tree clean(변이 전 pre-flight `git status --short` 빈 값 확인, 변이마다 재확인).
- 정본: `docs/plan/phase_8_face_anonymization.md` §범위·검증 2(P08-02) 및 §계약·소유권(익명화 규격·checkpoint 결합·얼굴 좌표 캐시 절), `experiments/p08_anonymized/README.md`(구현 계약 문서), `configs/anonymize.yaml`(규격 정본, k=1.2 소유자 결정 2026-10-11), `docs/sot.md:27`(규격 소유 행). 상위 사양(`project.md` v1.4 §15·§22)은 이 슬라이스에서 변경되지 않았다.
- 선행 검증: [P08-01 전체 슬라이스](p08_01_full_slice.md)(합격, 2026-10-13) — 측정 근거·k=1.2·edge_sigma=0.5·검출 설정(score 0.9·최소 크기 너비×0.04)이 이 슬라이스의 입력이다.
- 절차: `docs/guides/verification.md`.

## 범위

1. 계약-구현-테스트 스택 통합 감사: 계획 §2 P08-02 검증 목록(캐시/즉시 일치·결정성, 캐시 누락·해시 불일치 거부, 무얼굴 통과, 다중 얼굴·겹침 규칙, checkpoint 결합 양방향 5셀)과 §계약·소유권의 분기 전부를 경계 행렬로 만들어 회귀 셀에 매핑.
2. 실행 경로 연결 검사: `src/train.py`·`src/evaluate.py`·`src/calibrate.py`·`src/score.py`·`src/dataset.py`의 결합·거부 지점, 증강 전 적용 순서.
3. 규격 소유자(`configs/anonymize.yaml`) 무결성: YuNet 실측 sha256, canonical JSON 해시 규칙, 필드·범위 검증.
4. 좌표 캐시 전수 무결성 독립 재검증(6,000행 이미지 바이트 해시 재계산, `src/anonymize.py` 재사용 없이 순수 표준 라이브러리).
5. 캐시 ↔ 즉시 재검출 동등성 실측: 작업자와 **다른 seed**의 split × source_type 층화 35장에서 YuNet 직접 재검출과 좌표 float 비교.
6. 테스트 스위트 전체·집중 재실행, 변이 검증(under-strict 4 + over-strict 2, 방어 제거 포함).
7. 문서 계약: README baseline score 예시 교체, `docs/sot.md` 소유 행, metadata 무변경, `.gitattributes` LF, CHANGELOG·인덱스·HANDOFF.

재학습(P08-04)·calibration 실행(P08-05)·채택 판정(P08-06)·API(P07)은 이 슬라이스 범위 밖이다.

## 방법

### 테스트 재실행

```bash
docker compose run --rm -T dev python -m pytest -q
  # → 144 passed, 12 warnings(Pillow deprecation), 44.5s, exit 0
docker compose run --rm -T dev python -m pytest \
  tests/test_anonymize.py tests/test_baseline.py tests/test_calibration.py \
  tests/test_train_smoke.py -q
  # → 30 passed(변이 복원 후 재확인)
```

작업자 핸드오프·일지의 "전체 회귀 137개"는 중간 시점 기록이고, 같은 커밋에 이후 신규 셀(경계 커널·규격 범위·모델 로드 전 거부 등 7셀)이 포함되어 최종 수는 144다. 전부 통과했으므로 유리한 방향의 차이일 뿐이나, 핸드오프 요약의 수치는 최종 커밋 기준이 아니었다는 점을 기록한다. 집중 회귀 30개·`test_anonymize.py` 15셀 주장은 재실행으로 확인됐다.

### 캐시 전수 무결성 재검증(독립 스크립트, 순수 표준 라이브러리)

`src/anonymize.py`를 전혀 import하지 않고 표준 라이브러리(csv·hashlib·json·math)로 재계산했다. 핵심 로직: canonical JSON 해시 = `json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)`의 UTF-8 SHA256(README §규격·계보의 정의를 그대로 재구현), `parameters_sha256`은 `configs/anonymize.yaml`의 `face_detector`에서 `model`·`model_sha256`을 제외한 나머지 키의 해시.

확인 항목과 결과(전부 독립 재계산):

| 항목 | 결과 |
| --- | --- |
| 캐시 CSV SHA256 | `319d5376f71e3c65155857b33fa2e4dc653d2094a7b8f8cbef90812393d15af8` — README 주장과 동일, LF(CR 0), 6,001행(헤더+6,000) |
| `image_id` ↔ `data/metadata.csv` | 쌍방 차집합 0(누락·과잉 없음), 중복 없음 |
| 이미지 바이트 해시 전수(6,000장) | 불일치 0, 파일 부재 0(`/mnt/h/tracepector/images`) |
| `detector_sha256` | 전 행 동일 + 실측 YuNet sha256과 일치(`8f2383e4dd3c…`) — 규격 `model_sha256`과도 일치 |
| `parameters_sha256` | 전 행 동일 + 독립 재계산값과 일치(`39681cbf2f05…`) |
| `boxes` 유효성 | 전수 파싱·4원소·유한·w>0·h>0 위반 0 |
| 통계 | 얼굴 있음 1,949 / 없음 4,051 / 다중 7 / 전체 얼굴 1,957 — 작업 기록 주장과 동일 |
| 분포 | train 3,780 / val 820 / test 800 / test_unseen 600, REAL 3,000 / GEN 3,000 — 주장과 동일 |

### 캐시 ↔ 즉시 재검출 동등성(실측, 검증자 독립 seed)

작업자 표본(seed 20261013)과 겹치지 않는 seed 31102026으로 split × source_type 7개 층에서 층별 5장(총 35장, 얼굴 있음 10장 포함)을 뽑아, `cv2.FaceDetectorYN`을 계약 문서(README §얼굴 좌표 캐시의 검출 설정)로부터 직접 재구성해 비교했다.

```bash
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro \
  -v /tmp:/hosttmp:ro dev python -I /hosttmp/p08_verify_detect.py
```

결과: 35장 전부 좌표 목록이 float까지 완전 일치(불일치 0). 작업자 35장(얼굴 있음 표본 비율 더 높음)과 이번 독립 35장을 합쳐 70장 근거다. 전수 6,000장 즉시 재검출 재실행은 수행하지 않았다(작업자도 표본 검증임을 명시).

### 변이 검증

각 변이 직전 `git status --short` 빈 값 확인, 해당 셀만 실행, `git checkout --`로 HEAD 바이트 복원 후 매번 트리 clean 확인.

| 변이 | 위치·내용 | 재실패 셀 | 결과 |
| --- | --- | --- | --- |
| M1: 캐시 행 누락 시 즉시 검출 fallback (`raise` → `return self.detect(image)`) | `src/anonymize.py` `boxes()` | `test_cache_matches_live_and_rejects_missing_stale_rows` | 1 failed |
| M2: 최소 크기 경계 배제 (`>=` → `>`) | `src/anonymize.py` `detect()` 필터 | `test_all_faces_filter_and_paint_deterministically` | 1 failed |
| M3: 학습 키 필수 검사 제거 | `training_config()` 진입 검사 | `test_binding_training_and_fail_closed` | 1 failed(KeyError로 ValueError 어설션 파괴) |
| M4: score 거부 완화 (`require_anonymization=True`→`False` 두 곳) | `src/score.py` | `test_score_rejects_before_encoder_loading[missing]`·`[None]` | 2 failed |
| M5: legacy/null을 평가에서도 거부 (무조건 `raise`) | `checkpoint_anonymizer()` | `test_legacy_and_null_allowed_for_evaluation_but_not_score[config0]`·`[config1]` | 2 failed |
| M6: 좌표순 정렬 제거 (`sorted` 2곳) | `src/anonymize.py` `detect()`·`__call__` | **없음 — 15 passed** | 가드 부재(아래 H1) |

## 발견

### 1. 계약-구현 일치(경계 행렬)

계획 §2 P08-02 검증 목록과 §계약·소유권의 분기를 전수 대응시켰다. 빈 칸 없음.

- **모든 얼굴·무얼굴·결정성**: `tests/test_anonymize.py:30`(`test_all_faces…`) — 4박스(최소 크기 경계 포함/미달 혼합)에서 3개 전부 칠함·배경 보존·재호출 동일. 최소 크기 필터는 `src/anonymize.py:150-151`의 `max(f[2], f[3]) >= width * min_size_ratio`로 경계 포함(README 계약 "최소 크기 경계는 포함" 일치, M2로 잠금 확인).
- **캐시/즉시 일치·거부 계약**: `tests/test_anonymize.py:51` — 캐시↔즉시 픽셀 동일, 누락 ID·이미지 해시 불일치(Dataset 경로·`write_face_cache` 재개 경로 양쪽)·`detector_sha256`/`parameters_sha256` 위조 거부, 빈 목록 행은 원본 통과, LF 재작성 byte 동일, 기존 원이 칠해진 이미지 재적용도 같은 규칙. `Anonymizer.boxes`(`src/anonymize.py:155-163`)와 캐시 로드 검증(`src/anonymize.py:129-141`: 열 순서·중복/빈 ID·해시·JSON 좌표 검증)이 각 거부를 담당한다. 즉시 검출 fallback은 없다(fail closed).
- **무얼굴 통과**: `src/anonymize.py:166-168`(빈 목록 → 원본 그대로, count 0) + 위 셀의 빈 목록 행 확인.
- **checkpoint 결합 양방향 5셀**(계획 §2 검증 목록 그대로): ① 키 없는 legacy 평가 허용 `tests/test_anonymize.py:200-206`·`96-101`, ② 내용·sha256 변조 거부 `tests/test_anonymize.py:116-119`·`207-210`(checkpoint 저장 상태 위조 포함), ③ score legacy/null 거부 `tests/test_anonymize.py:245-260`(encoder 구성 **이전** 거부를 `build_encoder` 금지로 잠금 — 작업자 정리 주장 확인), ④ null 평가 허용 `tests/test_anonymize.py:96-101`, ⑤ 새 학습 키 필수 `tests/test_anonymize.py:113-114` + 기존 학습 fixture 전부 명시 null로 갱신(`tests/test_baseline.py`·`test_face_mask.py`·`test_face_mask_ci.py`·`test_failure_analysis.py` diff 확인).
- **YuNet 파일 sha256 불일치·부재 거부**: `tests/test_anonymize.py:126-132`(잘못된 바이트·파일 삭제 양쪽). 계약 "키가 있는데 … YuNet 파일 sha256이 다르면 모든 하류가 거부"와 일치 — `load_model`(`src/evaluate.py:100`)이 로드 시점에 `checkpoint_anonymizer(saved['config'])`로 강제 검증한다.
- **증강 전 적용**: `tests/test_anonymize.py:135-149` — detect가 원본 크기로 호출됨을 확인하고 transform이 익명화된 픽셀을 받는다. `src/dataset.py:132-133`에서 원본 RGB 익명화 후 transform 적용(계획 L48 일치).
- **같은 함수 사용**(계획 L47): train(`src/train.py:64-83`, train/val 동일 worker)·evaluate·calibrate(`checkpoint_anonymizer` 경유)·score가 모두 `Anonymizer.__call__`을 쓴다. 통합 셀 `tests/test_anonymize.py:152-210`이 학습→checkpoint 결합→평가→calibration→score를 한 경로로 검증한다(캐시 사용 시 학습·평가·calibration에서 즉시 검출 0회, 캐시/즉시 평가 지표 동일, 원본 YAML 삭제 후에도 checkpoint snapshot으로 하류 동작).
- **P08-01 측정 커널 일치**: `tests/test_anonymize.py:225-233` — 랜덤 RGB·소수 좌표 단일 원이 `scripts/p08_measure.paint_synthetic`과 byte 동일. 규격(k=1.2·fill 흰색·edge_sigma=0.5·원만)은 `configs/anonymize.yaml` 그대로이고 `validate_spec`(`src/anonymize.py:37-63`)이 필드 집합·범위를 강제한다.
- **legacy 비교 평가 override**: `tests/test_anonymize.py:213-222` — 명시 규격으로 익명화 평가, 결합 checkpoint 덮어쓰기 거부. README의 "비교용 checkpoint 사본 디렉터리" 주의(평가 CLI가 checkpoint 디렉터리에 기록)는 문서로 보존된다.

### 2. 캐시 계약(계획 §계약·소유권)

키 4종(`image_id`·`image_sha256`·`detector_sha256`·`parameters_sha256`)·값(전체 상자 JSON) 구조가 `CACHE_FIELDS`(`src/anonymize.py:21`)와 계약 그대로 일치하고, 무얼굴 빈 목록 행·거부 규칙·`data/metadata.csv` 무변경(커밋에 해당 파일 없음)을 확인했다. `write_face_cache`(`src/anonymize.py:181-207`)의 재개 논리(행 flush, 기존 행 바이트 해시 재검증, metadata 밖 잔여 행 거부)는 정상이고, 재개 재검증이 검출이 아닌 해시만 확인하는 것도 기록된 설계다.

### 3. 실측 캐시·동등성

위 방법 절의 표와 같이 전수·표본 검증 모두 주장과 동일했다. CSV SHA256 주장(`experiments/p08_anonymized/README.md:39`)도 직접 계산해 일치를 확인했다.

### 4. 문서 계약

- README "Calibrated image score" 절이 baseline(P05) artifact의 score 거부와 P08 artifact 대기 상태를 명시하고 예시를 `experiments/p08_anonymized/calibration/`로 교체했다(계획 L91 요구 이행).
- `docs/sot.md` 규격 소유 행이 "P08-02 checkpoint snapshot의 원본"으로 갱신됐고(계획 L84 요구), `configs/anonymize.yaml` 주석의 stale 표현 정리·`.gitattributes` 캐시 LF 추가·CHANGELOG·페이즈 인덱스·HANDOFF 갱신을 확인했다.
- 인계 요약의 "전체 회귀 137개"는 최종 커밋 기준 144개와 다르다(위 방법 절). 본체 일지는 중간·최종 집중 회귀를 구분해 기록하고 있다.

## 문제·위험

### 차단(계약 위반)

없음.

### 비차단 보강 후보

- **H1 — 좌표순 정렬 가드 부재(M6 변이 미검출)**: README 계약 문장 "얼굴 목록을 좌표순 정렬해 겹침 처리 순서를 고정한다"의 `sorted`(`src/anonymize.py:153`·`171`)를 제거해도 현재 어떤 셀도 실패하지 않는다(모든 stub detect가 이미 정렬된 목록을 반환). 계획 §2 검증 목록의 "겹침 규칙"은 기존 원과 겹쳐도 같은 규칙으로 칠하는 것(L49)이고 그 셀은 존재하므로 계약-요구 분기 누락은 아니다. YuNet 자체가 결정적 순서를 반환하고 캐시에도 정렬 값이 저장되어 현재 경로에서 관찰 가능한 결함은 없다. 다만 "검출기가 비정렬을 반환해도 같은 픽셀"을 잠그려면 detect stub이 역순·겹치는 원을 반환하는 셀이 필요하다(`verification.md` "mutation이 안 물 때" 사례로 기록).
- **H2 — legacy + `--face-cache` 단독 거부 셀 부재**: 결합 규격 없는 checkpoint에 캐시만 지정하면 `src/anonymize.py:89-91`이 `'face cache requires anonymization'`으로 거부하는데, 이 분기의 직접 셀이 없다(통합 셀은 결합 checkpoint만 다룬다). 구현은 fail closed라 계약 위반이 아니지만, 가드가 있는 만큼 셀로 잠그는 것이 견고하다.

## 판정

**합격.** 근거:

1. 계획 §2 P08-02 검증 목록과 §계약·소유권이 요구하는 분기 전부(경계 행렬 빈 칸 없음)가 명명된 회귀 셀로 매핑되고, 그 셀들이 실제로 물린다(M1~M5 변이 확인).
2. 캐시 6,000행의 이미지 바이트 해시를 검증자가 전수 재계산해 0 불일치, 검출기·파라미터 해시·통계·분포가 문서 주장과 동일하다.
3. 검증자 독립 seed 35장(작업자 표본과 무관)에서 캐시 ↔ 즉시 재검출 좌표가 float까지 동일하다.
4. 전체 144·집중 30 테스트 재실행 통과, checkpoint 결합 양방향·fail closed(§22)·증강 전 적용·P08-01 커널 일치가 코드와 테스트 양쪽에서 확인됐다.
5. H1·H2는 계약이 요구하지 않는 보강 후보다(위 분류 근거).

## 남은 일

- P08-02 상태를 계획·인덱스·HANDOFF에서 Complete로 갱신하고 P08-03(진단·채택 규칙 사전 고정, 재학습 결과 **전에** 커밋)에 착수한다. 본 검증의 합격 판정이 그 선행 조건이다.
- H1·H2 보강은 소유자·차기 작업자 판단. P08-03 진행을 막지 않는다.
- score CLI는 P08-05 calibration artifact가 생길 때까지 실제 사용 가능한 상태가 아니다(설계된 거부 동작).

## 재현

```bash
git status --short                                    # 빈 값이어야 함(HEAD=d667327)
# 1) 테스트
docker compose run --rm -T dev python -m pytest -q    # 144 passed
docker compose run --rm -T dev python -m pytest tests/test_anonymize.py \
  tests/test_baseline.py tests/test_calibration.py tests/test_train_smoke.py -q  # 30 passed
# 2) 캐시 전수 재검증: 순수 표준 라이브러리로 (a) metadata↔캐시 ID 쌍방 차집합,
#    (b) 6,000장 이미지 sha256 전수 재계산·비교, (c) detector_sha256==sha256(YuNet 파일),
#    (d) parameters_sha256==canonical-JSON 해시(face_detector에서 model/model_sha256 제외),
#    (e) boxes JSON 전수 파싱·유효성, (f) 통계·split/source 분포 재계산.
# 3) 독립 표본 재검출(seed 31102026, 7층×5장): cv2.FaceDetectorYN을 규격에서 직접 구성해
#    캐시 boxes와 float 비교 — docker compose run --rm -T \
#      -v /mnt/h/tracepector/images:/images:ro dev <스크립트> (불일치 0)
# 4) 변이 M1~M6: 위 표의 위치·내용대로 적용 → 해당 셀만 실행(재실패 확인) →
#    git checkout -- <path> → git status --short 빈 값 확인. M6은 15 passed(가드 부재).
sha256sum experiments/p08_anonymized/face_boxes.csv   # 319d5376f71e3c65155857b33fa2e4dc653d2094a7b8f8cbef90812393d15af8
```

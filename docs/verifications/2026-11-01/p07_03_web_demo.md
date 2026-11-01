# P07-03 Web Demo 독립검증

## 대상 메타데이터

- 날짜: 2026-11-01
- 요청자: 소유자(entangelk), 메인 세션 경유
- 검증자: Claude Opus 5.5 (독립 검증 서브에이전트, 구현에 관여하지 않음)
- 대상: P07-03 정적 웹 데모. 커밋 `6819a2b`, 비교 기준 부모 `f62b473`(P07-02 Complete).
- 정본 규격: `docs/plan/phase_7_api_demo.md`(§계약의 소유권과 데이터 흐름, 슬라이스 표, §P07-03 "구현 세부" 포함, §완료 조건), `docs/decision_briefs/DB-08_P07_response-contract.md` Resolution(결정 3), `docs/project.md` §23(DB-06 주석 포함)·§22(응답 필드 의미), `README.md` "Inference 방법".
- 작업 원천: `main` HEAD `6819a2b`, 검증 시작 시 작업 트리 clean.

## 범위

1. 계약 자체 정합성(계획 ↔ DB-08 결정 3 ↔ §23 ↔ README).
2. 구현: `demo/index.html`, `api/main.py`의 `GET /`, compose `api` 서비스(P07-02 기존). P07-01·02는 데모가 의존하는 부분만.
3. 회귀 테스트: `tests/test_api.py` 신규 2셀, `tests/test_p07_demo.cjs` 7셀과 경계 행렬 대응.
4. mutation testing(M1~M12).
5. 전체 CPU suite, 실제 CPU API 서버 + 실제 Chrome(headless) 화면 확인.

## 방법

- 계약 범위를 먼저 읽고 아래 경계 행렬을 만든 뒤 코드를 읽었다.
- Node: `node --test tests/*.cjs` → 10 pass(데모 7 + 기존 P08 3), exit 0.
- 집중: `docker compose run --rm -T dev python -m pytest tests/test_api.py -q` → 39 passed, exit 0.
- 전체: `docker compose run --rm -T dev python -m pytest -q` → 361 passed, 1 skipped, exit 0(51.7s).
- mutation: 사전 `git status --short` 빈 출력 확인 → `sed -i`로 `demo/index.html` 변이 → `node --test tests/test_p07_demo.cjs` 및/또는 `pytest tests/test_api.py -q -k demo` → `git checkout -- demo/index.html` → 마지막에 `git status --short` 빈 출력 재확인.
- 실제 화면: `docker compose --profile api up -d api` → `GET /` 200 대기 → `/tmp/p0703/run.cjs`, `/tmp/p0703/race.cjs`(playwright-core, `executablePath: '/usr/bin/google-chrome'`, `--no-sandbox`)로 `#file`에 업로드, 각 `/score` 응답 JSON과 DOM 값을 같은 실행에서 비교, 라이트·다크·390px 폭 스크린샷을 직접 확인 → `docker compose --profile api down`. GPU는 쓰지 않았다. 스크린샷·스크립트는 `/tmp/p0703`에만 두었다(데이터셋 이미지 포함, 커밋하지 않음).
- 보조 입력(`/tmp/p0703`, `tracepecter/dev` 컨테이너의 PIL로 생성): EXIF Orientation=6인 400×200 JPEG(왼쪽 빨간 띠) `exif6.jpg`, 64×64 GIF `a.gif`, 11 MiB 초과 `big.jpg`, 텍스트 `bad.txt`.

## 경계 행렬

| # | 계약 조항 | 출처 | 잠그는 셀 | 상태 |
| --- | --- | --- | --- | --- |
| C1 | `GET /`이 `demo/index.html` 제공, 같은 서버 `POST /score` 호출, 필드 `image` | 계획 :73·:76, DB-08 결정 3 | `test_demo_page_served_with_fixed_notices`, node `upload posts field image…` | 잠김 |
| C2 | 고정 안내 문구 2개 원문 그대로 | 계획 :70-72, §23 | `test_demo_page_served_with_fixed_notices`(M6·M6b 재실패) | 잠김(표시 여부는 H3) |
| C3 | 원본 미리보기 표시 | §23 DB-06 주석, 계획 :70 | node `upload posts…`(M10 재실패) | 잠김 |
| C4 | 점수 막대(원래 값) + `NN / 100` | §23, 계획 :78 | node `render shows…`(M8 재실패) | 잠김 |
| C5 | 정수 표시는 `Math.round` | 계획 :78 | node `render shows…` — 82.4·0.4만 사용 | **비어 있음**(M1 생존, B3) |
| C6 | 분류 문구 2개 매핑, 분류는 서버 값 | 계획 :77, DB-08 결정 1 | node `render shows…`(90점 synthetic_like), `test_demo_does_not_own_threshold`(M5 재실패) | 잠김 |
| C7 | 모르는 분류 값은 오류 | 계획 :77 | node `render shows…`·`network failure or unknown…`(M4 재실패) | 잠김 |
| C8 | 가린 얼굴 수 표시 | §23, 완료 조건 | node `render shows…` | 잠김(표시 여부는 H3) |
| C9 | 400·413·415별 문구, 그 밖은 HTTP 코드 포함 일반 문구 | 계획 :79 | node `rejection 400/413/415/500…`(M7 재실패) | 잠김 |
| C10 | 거부 시 점수 영역을 숨긴다 | 계획 :79 | node `rejection…` — 매 셀이 새 stub(`hidden: true` 초기값)에서 시작 | **비어 있음**(M2 생존, B2) + **실제 위반**(B1) |
| C11 | 크기 한도·허용 형식은 설정 소유, 화면에 복제하지 않음 | 계획 :79, 소유권 표 :30 | 없음 | **위반 의심**(B5) |
| C12 | 데모가 점수 경계·분류를 계산하지 않음 | 계획 :33, README :81 | `test_demo_does_not_own_threshold`, node 90점 synthetic_like | 잠김(이중 방어) |
| C13 | 미리보기에 EXIF 회전 미적용(`image-orientation: none`) | 계획 :80, README :81 | 없음 | **비어 있음**(M3 생존, B4) |
| C14 | 데모 파일은 앱 생성 시 1회 읽음 | 계획 :76 | 없음 | 클라이언트 관찰 동작 없음 → H5 |
| C15 | README Inference 절 갱신, 실제 이미지 화면 확인 | 슬라이스 표 :42 | 수동(본 기록) | 일치 |

## 발견 사항

### 1. 계약 자체 정합성

- DB-08 결정 3(정적 HTML 1개, 같은 서버 `POST /score`, 새 의존성 없음)과 계획 :73·:76이 일치한다. `requirements.txt` 변경 없음(`git show HEAD --stat`).
- §23 필수 문구는 "성격의 문구"로 되어 있고 계획 :71-72가 원문을 고정했다. 페이지(`demo/index.html:64-65`)는 계획 원문과 바이트 단위로 같다(실제 Chrome DOM 출력으로도 확인).
- §23 "업로드한 원본 이미지를 보여 준다"와 계획 :80 `image-orientation: none`: 원본 파일 바이트를 EXIF 태그만 적용하지 않고 보여 주는 것이므로 "원본"과 모순되지 않으며, P07-02에서 검증된 "EXIF 회전 미적용" 입력 규칙(계획 :61)과 같은 방향이다. README :81이 이를 밝힌다. 계약 충돌로 보지 않는다.
- 계획 :77 "모르는 분류 값은 오류"는 계획에 명시돼 있어 spec-silent가 아니다. §22·DB-08 결정 1의 2단계 어휘와 모순되지 않는다.
- 계획 :79 "크기 한도·허용 형식 숫자는 … 화면에 복제하지 않는다"는 "허용 형식 숫자"라는 표현이 모호하다(형식 목록인지 숫자 한도인지). B5와 묶어 정리가 필요하다.

### 2. 구현

- `api/main.py:21,40,43-45`: 경로를 모듈 기준으로 고정하고 `create_app` 안에서 1회 읽어 `HTMLResponse`로 돌려준다. 단순하고 계획과 일치한다.
- `demo/index.html:81-91` `render`: 분류는 `LABELS[result.classification]`, 없으면 throw(:83). 점수 비교 코드가 없다. 막대 폭은 원래 값(:86), 표시값은 `Math.round`(:87). 얼굴 0이면 "가린 얼굴 없음", 그 밖은 "얼굴 N개를 흰 원으로 가린 뒤 평가했습니다."(:89).
- `demo/index.html:93-95,115`: 400·413·415 외 상태는 `점수를 계산하지 못했습니다(HTTP n).`. 네트워크 실패·JSON 실패·모르는 분류는 catch(:122-124)에서 일반 문구.
- `demo/index.html:104-125` `submit`: 요청 순번·취소가 없다. 앞 요청의 응답이 뒤 요청보다 늦게 오면 그대로 화면에 쓴다 → B1.
- `demo/index.html:53` `accept="image/jpeg,image/png,image/webp"`: `configs/inference.yaml`의 `formats: [JPEG, MPO, PNG, WEBP]`를 페이지에 다시 선언한다 → B5.
- `demo/index.html:27` `label.pick input { display: none; }`: 파일 입력이 탭 순서에서 빠진다(실측: Tab 후 `document.activeElement`가 `BODY`) → H1.
- 외부 네트워크: 페이지에 `http`·`<link>`·`@import`·외부 `src`가 없고 글꼴은 시스템 글꼴 스택(:20). 실제 Chrome에서 localhost·blob 외 요청 0건.
- 접근성 기본: `lang="ko"`(:2), 미리보기 `alt`(:54), 오류 `role="alert"`(:55), 결과 `aria-live="polite"`(:56). 다크 모드 토큰(:12-17). 390px 폭에서 `scrollWidth` 390(가로 스크롤 없음).

### 3. 회귀 테스트

- `tests/test_api.py:275-280`: 200·`text/html`·문구 2개 포함·`fetch('/score'`·`body.append('image'`를 확인한다. 문구가 보이는지는 확인하지 않는다(M11 생존, H3).
- `tests/test_api.py:283-290`: stub artifact의 threshold 문자열, 실제 artifact 값의 접두(`23.5`·`0.235`, 실제 `threshold_probability` 0.23513…), `realism_score` 비교식 부재를 확인한다. node의 "90점이라도 synthetic_like" 셀과 함께 점수 기반 분류 변이(M5)를 두 층에서 잡는다.
- `tests/test_p07_demo.cjs:21-33`: 반올림 표본이 82.4·0.4뿐이라 `Math.floor`·`Math.trunc`와 구분되지 않는다(B3). 실제 REAL 표본 85.54처럼 소수부 ≥ .5 값이 하나 있으면 잠긴다.
- `tests/test_p07_demo.cjs:52-62`: 거부 셀마다 새 stub에서 시작하고 stub 요소의 초기값이 `hidden: true`(:10)라 "거부 시 점수 영역 숨김"이 직전 성공 결과를 실제로 숨기는지 확인하지 못한다(B2).
- `image-orientation: none`을 확인하는 셀이 없다(`grep -rn orientation tests/`에 데모 관련 결과 없음, B4).

### 4. Mutation testing

사전 `git status --short` 빈 출력 확인, 각 변이 후 `git checkout -- demo/index.html`, 종료 후 빈 출력 재확인.

| 변이 | 내용 | 결과 |
| --- | --- | --- |
| M1 | `Math.round` → `Math.floor`(:87) | **생존**(node 7/7 통과) → B3 |
| M2 | 시작 시 `$('result').hidden = true` 삭제(:106) | **생존** → B2 |
| M3 | `image-orientation: none` 삭제(:31) | **생존**(pytest demo 2셀·node 모두 통과) → B4 |
| M4 | 모르는 분류 throw 제거 | 재실패: node 1, 7 |
| M5 | `realism_score > 23.5`로 분류 | 재실패: `test_demo_does_not_own_threshold`, node |
| M6 | 첫 문구 "증명하지" → "보장하지" | 재실패: `test_demo_page_served_with_fixed_notices` |
| M6b | 둘째 문구 삭제 | 재실패: 같은 셀 |
| M7 | `ERRORS[413]` 삭제 | 재실패: node `rejection 413` |
| M8 | 막대 폭에 반올림 값 사용 | 재실패: node 1 |
| M10 | 미리보기 `hidden = false` 삭제 | 재실패: node 2 |
| M11 | `.notice`에 `hidden` 속성 추가 | **생존** → H3 |
| M12 | `#faces`에 `hidden` 속성 추가 | **생존** → H3 |

(M9 번호는 쓰지 않았다.)

### 5. 실제 화면(CPU API, 실제 Chrome)

같은 실행에서 `/score` 응답과 DOM을 비교했다(`model_version` `f5bf7f4d004f`).

| 입력 | 응답 | 화면 |
| --- | --- | --- |
| REAL `스포티/998959.jpg` | 200, 85.53991233735206, `photographic_like`, 얼굴 0 | "86 / 100", 막대 `85.5399%`, "실제 착용 촬영과 유사한 이미지입니다.", "가린 얼굴 없음", 미리보기 800×800, 문구 2개 표시(라이트·다크 동일) |
| GEN `qwen_image_21/gen_000006.png` | 200, 0.00044999…, `synthetic_like`, 얼굴 1 | "0 / 100", 막대 0px, "생성 이미지와 유사한 특성이 보입니다.", "얼굴 1개를 흰 원으로 가린 뒤 평가했습니다.", 문구 2개 표시 |
| `bad.txt` | 400 | "이미지 파일을 읽을 수 없습니다.", 결과 숨김, 미리보기 자리에 깨진 이미지 아이콘과 alt(H6) |
| `a.gif` | 415 | "지원하지 않는 이미지 형식입니다.", 결과 숨김 |
| `big.jpg`(11 MiB 초과) | 413 | "파일이 너무 큽니다.", 결과 숨김 |
| `exif6.jpg`(Orientation=6) | 200, 89.34, `photographic_like` | 스크린샷에서 빨간 띠가 왼쪽, 가로형 → EXIF 회전 미적용 렌더링 확인(`naturalWidth/Height`는 Chrome이 회전 기준 200×400으로 보고하지만 렌더링은 미회전) |
| **연속 업로드**: REAL 직후 `bad.txt` | 400이 먼저, REAL 200이 나중 도착 | **오류 "이미지 파일을 읽을 수 없습니다."와 결과 "86 / 100"이 동시에 표시, 미리보기는 `bad.txt`(깨진 이미지)** → B1 |

작업 기록의 REAL·GEN 화면 값(86, 0, 문구, 얼굴 수)은 재현됐다. 콘솔 오류는 400 응답과 `favicon` 404뿐이다(H7).

### 6. README·계획과 동작

- README :81의 서술(원본 미리보기, `NN / 100` 반올림, 분류 문구, 가린 얼굴 수, 문구 2개, 응답만 표시, EXIF 미회전)은 실제 동작과 일치한다. 단 B1 상황에서는 "응답만 표시"가 다른 이미지의 응답을 표시하는 형태로 깨진다.
- 계획 슬라이스 표 :42 상태 "Implemented(독립검증 대기)"는 현재 상태와 맞다. compose `api` 서비스는 P07-02 것을 그대로 쓰며 `.:/app` bind mount로 `demo/`가 보인다.

## 이슈 / 위험

### 차단(계약 의무)

- **B1 — 늦게 도착한 이전 응답이 거부 화면 위에 점수를 띄운다** (`demo/index.html:104-125`, 특히 :114-121). 요청 순번·취소가 없어, 이미지를 고른 뒤 결과가 오기 전에 다른 파일을 고르면 앞 응답이 나중에 화면을 덮어쓴다. 실제 Chrome에서 REAL → `bad.txt` 순으로 고르자 오류 문구와 "86 / 100"이 동시에 보였고 미리보기는 `bad.txt`였다. 계획 :79 "거부 응답은 … 점수 영역을 숨긴다"와 §23·계획 :70의 "올린 이미지의 미리보기와 그 점수" 대응을 어긴다. 정상 이미지 두 장을 연속으로 올리는 경우에도 같은 경로로 미리보기와 점수가 어긋날 수 있다. 해소: 최신 요청만 반영(순번 비교 또는 `AbortController`)하고 회귀 셀 추가.
- **B2 — "거부 시 점수 영역 숨김" 잠금 부재** (`tests/test_p07_demo.cjs:52-62`, stub 초기값 :10). M2(시작 시 결과 숨김 삭제) 생존. 직전 성공 → 거부 순서 셀이 필요하다. B1의 회귀 셀(늦은 응답 무시)도 여기 포함돼야 한다.
- **B3 — `Math.round` 잠금 부재** (`tests/test_p07_demo.cjs:24,47`). 표본 82.4·0.4는 `floor`/`trunc`와 같은 결과라 M1 생존. 계획 :78의 리터럴이 테스트로 고정되지 않았다. 소수부 ≥ .5 표본(예: 85.54 → "86") 추가로 해소.
- **B4 — `image-orientation: none` 잠금 부재** (`demo/index.html:31`, 계획 :80). M3 생존. 실제 Chrome에서 동작은 맞음을 확인했지만 계약 리터럴을 지키는 셀이 없다. HTML/CSS 문자열 확인 셀이면 충분하다.
- **B5 — 설정 소유 허용 형식을 페이지가 다시 선언** (`demo/index.html:53` `accept="image/jpeg,image/png,image/webp"` ↔ `configs/inference.yaml` `formats`, 계획 :79·소유권 표 :30). 설정에서 형식을 바꾸면 파일 선택기 필터가 어긋난다(특히 모바일 선택기). 계획 문구가 "허용 형식 숫자"로 모호해 이것이 금지 대상인지 계약이 답하지 않는다 → spec-silent-but-code-enforced. 해소: `accept`를 `image/*`로 넓히거나 빼고 그 셀을 추가하거나, 계획에 "선택기 힌트용 `accept`는 허용"을 명시(소유자 판단).

### 보강 권고(비차단)

- **H1 — 키보드로 파일 선택 불가** (`demo/index.html:27`). `display: none`인 입력은 포커스되지 않고 `label`도 포커스 대상이 아니다. 실측 Tab 후 포커스 `BODY`. 시각적으로만 숨기는 스타일(예: clip)로 바꾸면 해결.
- **H2 — 413 문구가 압축 폭탄 판정과 맞지 않음** (`demo/index.html:77`). 413은 10 MiB 초과와 픽셀 수 초과(README :85) 둘 다인데 문구는 "파일이 너무 큽니다."뿐이다. 작은 파일·거대 해상도에서 오해 소지.
- **H3 — 문구·얼굴 수가 "보이는지"는 잠기지 않음** (`tests/test_api.py:275-280`). M11(`.notice` hidden)·M12(`#faces` hidden) 생존. 문자열 포함만 확인한다.
- **H4 — `.dockerignore:9`가 `demo/`를 제외** 하는데 `api/main.py:40`이 기동 시 파일을 읽는다. 현재 compose는 bind mount라 문제없지만, mount 없이 이미지로 띄우면 데모 파일 부재로 `POST /score`까지 기동 실패한다.
- **H5 — "앱 생성 시 1회 읽음" 무잠금** (`api/main.py:40`, 계획 :76). 응답이 같아 클라이언트가 관찰할 분기가 없으므로 비차단으로 둔다.
- **H6 — 거부 시 미리보기에 깨진 이미지 아이콘** (스크린샷 확인). 이미지로 열리지 않는 파일이면 미리보기를 자리표시로 되돌리는 편이 깔끔하다.
- **H7 — `favicon` 404** 콘솔 소음.

## 판정

**불합격** — 계획 P07-03 구현 세부 "거부 응답은 … 점수 영역을 숨긴다"(:79) 위반: 연속 업로드 시 늦게 도착한 이전 응답이 거부 화면과 다른 파일의 미리보기 옆에 점수를 표시한다(B1).

- 단일 업로드 경로(REAL·GEN·400·413·415·EXIF)는 실제 Chrome에서 응답과 화면이 일치하고, 필수 문구 2개·가린 얼굴 수·원본 미리보기·서버 분류 우선·외부 의존 없음이 확인됐다.
- 그러나 B1은 실제로 재현된 계약 위반이고, B2~B4는 계약 리터럴·분기에 잠금이 없으며(M1·M2·M3 생존), B5는 설정 소유 값의 중복으로 계약 정리가 필요하다.

## 미결 사항

- 작업 트리는 검증 전후 clean(본 기록 커밋 제외). 서버 컨테이너는 내렸다.
- P07 Complete 처리는 B1~B5 해소와 추적 검증 이후로 미룬다.
- B5는 소유자 판단이 필요할 수 있다(`accept` 허용 여부).

## 재현

```bash
cd /mnt/f/devel/Tracepecter
node --test tests/*.cjs
docker compose run --rm -T dev python -m pytest tests/test_api.py -q
docker compose run --rm -T dev python -m pytest -q
# mutation (예: M1)
git status --short   # 빈 출력이어야 함
sed -i 's/Math.round(result.realism_score)/Math.floor(result.realism_score)/' demo/index.html
node --test tests/test_p07_demo.cjs   # 통과하면 B3 재현
git checkout -- demo/index.html && git status --short
# 실제 화면
docker compose --profile api up -d api
node /tmp/p0703/run.cjs "/mnt/h/tracepector/images/real/스포티/998959.jpg" \
  "/mnt/h/tracepector/images/generated/qwen_image_21/gen_000006.png" /tmp/p0703/bad.txt /tmp/p0703/exif6.jpg
node /tmp/p0703/race.cjs   # 마지막 줄 race: err와 result:true가 함께 나오면 B1 재현
docker compose --profile api down
```

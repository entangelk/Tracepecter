**합격** — 라운드 1 조건부(B1) → 보강 `8972d1e`·`526438d` → 라운드 2 추적 검증(같은 검증자, 2026-10-13)으로 조건 해소·H1~H4 반영 확인.

# P08-01 전체 슬라이스 독립검증

## 대상

- 날짜: 2026-10-13(KST).
- 요청자: 소유자("P08-01 전체 슬라이스 독립검증… 독립검증 진행해줘").
- 검증자: 구현에 참여하지 않은 Claude Code 세션(신규, 구현자 맥락 미승계).
- 검증 대상: P08-01 원 규격·YuNet 재현율 측정 전체 슬라이스 — 사전등록(`dd680af`)부터 소유자 표시·보조 크기 반영(`b7bfb63`, HEAD)까지.
- 작업 출처: `main` `dd680af..b7bfb63`, working tree clean(변이 검증 전 pre-flight `git status --short` 빈 값 확인).
- 정본: `docs/plan/phase_8_face_anonymization.md` §범위·검증 1(P08-01), `configs/anonymize_measure.yaml`(`dd680af` 사전등록, 불변 확인), `configs/anonymize.yaml`(소유자 선택 k=1.2), 소유자 결정 2026-10-11(k=1.2·사전 크기 실패 보존·P08-03 크기 단서 진단), `docs/sot.md:27`(규격 소유 행). 사양 우선순위는 `docs/sot.md`로 확인했다.
- 선행 검증: [2026-10-11 재개 slice 검증](../2026-10-11/p08_01_resume.md)(합격, 전체 완료 판정은 명시적으로 제외) — 잔여 4건(소유자 train 40장 확인, sd35 확인, 보조 크기 측정, 전체 슬라이스 재검증)의 반영 여부를 이번 범위에 포함했다.
- 절차: `docs/guides/verification.md`.

## 범위

1. 사전등록 계약 불변성(`anonymize_measure.yaml` ≡ `dd680af` blob)과 규격 연결(`anonymize.yaml` k=1.2·edge_sigma=0.5 ↔ report).
2. 최종 재현율 수치·소유자 확인 목록·Wilson 구간의 원자료(CSV)로부터의 독립 재도출(train·sd35 양쪽).
3. 보조 사람 영역 크기 측정(REAL rect 합집합·GEN 수동 표시)의 수치·표본 계보·행별 산술 재도출.
4. 전량 CPU 재실행(임시 복사본)으로 산출물 재현성 확인(measure·person_size 양쪽).
5. 블라인드 검토 페이지 누출 여부·템플릿·소유자 CSV 검증 계약.
6. 경계 행렬: 계약 요구 분기 ↔ 회귀 셀 대응(변이 10종, 양방향).
7. 기록 갱신(README·계획·index·HANDOFF·일지·sot)과 이전 검증 잔여 반영.

P08-02 이후(익명화 모듈·checkpoint 결합·재학습)와 원자료 육안 표시 자체의 재판독은 범위 밖이다(한계 참고).

## 방법

### 테스트·정적 검사

```bash
git status --short                      # pre-flight: 빈 값 확인
docker compose run --rm -T dev python -m pytest \
  tests/test_p08_person_size.py tests/test_p08_measure.py \
  tests/test_face_mask_ci.py tests/test_p06_patterns.py -q   # 54 passed
node tests/test_p08_owner_review.cjs                          # 2 passed
```

### 독립 재도출(호스트 Python 3 표준 라이브러리 전용)

- `configs/anonymize_measure.yaml` 현행 바이트 ≡ `git show dd680af:configs/anonymize_measure.yaml`(동일).
- provenance 재계산: 측정 config SHA-256 `65c19178…`, `data/metadata.csv` `039cbdd1…`, `configs/anonymize.yaml` `0831fbd2…`, YuNet onnx `8f2383e4…`(호스트 실측), 라벨 ZIP `63b9fb8a…`(호스트 실측) — `report.json`·`person_size_report.json` 기록값과 전부 일치. `person_size_report.json`의 입력 11종 해시 전수 재계산 일치.
- 재현율: `recall_labels_agent.csv` + `recall_detections.csv` + 소유자 CSV(각 pool별)를 결합해 최종 표시(소유자 우선)·양성·검출 수·재현율·Wilson 95% 구간(독립 구현) 재계산.
- 소유자 확인 목록: 불일치(에이전트 표시 ≠ 검출) 전부 + 나머지의 `random.Random(20261012).sample(rest, round(0.2·len(rest)))` 재도출, 커밋된 확인 CSV·소유자 CSV와 행 단위 비교.
- 보조 크기: 두 측정 CSV의 사분위(`statistics.quantiles`, inclusive — `np.percentile` 선형 보간과 동일), `frame_clipped` 집계, 행별 산술(지름/분모·(bottom−top)×높이) 검증. 표본 계보: 검출+최종 보임 87장을 `sorted`+`random.Random(20261011).shuffle` 한 앞 50장과 `person_sample_gen.csv` 비교. REAL은 `person_rects_real.json` 발췌로부터 rect 합집합 높이를 전행 재계산해 `person_size_real.csv`와 비교(불일치 0), 지름은 `real_disc_candidates.csv` major와 전행 비교.
- 블라인드 페이지: `reports/errors/review/p08/index.html`(40건)·`p08_sd35/index.html`(30건)의 CASES payload 키·고유 ID·JPEG 여부·정답/검출/선정 사유 문자열 부재 확인, 다운로드 파일명 확인.
- 검출 설정 parity: `configs/face_mask_ci.yaml`(P06-02c) 검출기 블록과 `anonymize_measure.yaml`·`anonymize.yaml` 리터럴 대조(전부 동일). Hough 미사용 확인(`grep -ri hough` 무매치).
- `report_before_owner_decision.json`과 현행 `report.json`의 REAL·size_match·σ 불변 확인. README 상대 링크 전수 존재 확인.

### 전량 CPU 재실행(임시 복사본, 기존 산출물 미변경)

```bash
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev python - <<'PY'
# 1) measure_stage: measure/ 전체를 tempfile로 복사해 재실행, 산출물 비교
# 2) p08_person_size.run: configs·data·measure 체계를 tempfile로 복사해 재실행, 산출물 비교
PY
```

- measure: `report.json`·`recall_owner_check_sd35.csv` **byte 동일**. `recall_detections.csv`·`recall_owner_check.csv`(train)는 raw diff·**CRLF→LF 정규화 후 동일**(내용 일치; 아래 H2).
- person_size: `person_size_real.csv`·`person_size_gen.csv`·`person_rects_real.json`·`person_size_report.json` **4종 전부 byte 동일**.

### 변이(10종, 전부 사후 `git checkout -- <path>` 복원 + `git status --short` 빈 값 확인)

| 변이(`scripts/p08_measure.py`·`p08_person_size.py`·`p08_owner_review.html`) | 방향 | 결과 |
| --- | --- | --- |
| M1 `:337` `<= tolerance_px` → `<` (±1px 닫힌 구간 배제) | 과잉 | **무저항**(p08 20셀 전부 통과) |
| M2 `:337` `chosen is None and` 제거(최소 σ→마지막 매칭 σ) | 과소 | **무저항**(20셀 통과) |
| M3 `:157` `gate_applies and not missing` → `not missing` (sd35 관문 오적용) | 과잉 | `test_owner_review_requires_every_selected_id_and_keeps_test_reporting_only`·`test_measure_report_keeps_original_failure_and_waits_for_owner` 재실패 |
| M4 `:151` 소유자 표시 무시(에이전트 표시만) | 과소 | 같은 셀(corrected case) 재실패 |
| M5 `:144` `value not in ('0','1')` 제거 | 과소 | `test_owner_labels_reject_duplicates_invalid_values_and_unknown_ids` 재실패 |
| M6 `p08_person_size.py:106` `selected['diameter_per_face']` → `1.0` | 과소 | `test_report_uses_manual_height_and_selected_k_without_changing_main_gate` 재실패 |
| M7 `p08_person_size.py:31` 합집합 → 부위 높이 합(겹침 이중 계상) | 과오 | `test_rect_height_unions_every_part_without_summing_overlap_or_clipping` 재실패 |
| M8 `p08_person_size.py:41` 표본에서 소유자 표시 무시 | 과소 | `test_sample_uses_owner_labels_and_only_detected_train_faces` 재실패 |
| M9 `:307` `use_ellipse` 부등호 반전(원형→타원) | 과오 | `test_measure_report_keeps_original_failure_and_waits_for_owner` 비거부 4 파라미터 재실패(선택 규격 불일치 ValueError) |
| M10 html 미완료 저장 거부 제거 | 과소 | `node tests/test_p08_owner_review.cjs` 2 실패 |

복원 후 combined focused suite 54 passed + node 2 passed, 트리 클린.

## 발견 사항

### 계약·사전등록

- 사전 측정 기준은 `dd680af`와 바이트 동일이며 결과 확인 후에도 바뀌지 않았다(위 방법). 소유자 선택 k=1.2는 `configs/anonymize.yaml:11`이 정본이고, 사전 크기 관문 실패(k=0.6456, [1.0,1.6] 밖)는 `report.json` `size_match.passed=false`로 보존되며 `selected_size`(k=1.2, 사분위 전부 ±15% 밖 → 실패)와 분리 기록된다. 이 구분은 `tests/test_p08_measure.py:11`(실패 보존·선택 k가 사전 실패를 통과로 바꾸지 않음)이 잠근다.
- 규격 연결: `anonymize.yaml`의 `diameter_per_face: 1.2`·`edge_sigma: 0.5`·`shape: circle`·`fill`은 `report.json` `selected_size.k`·`sigma`·`use_ellipse=false`·선택 규격 검증(`scripts/p08_measure.py:319`)과 일치한다. 검출기 블록은 P06-02c(`configs/face_mask_ci.yaml`)와 리터럴 동일(계획 "검출 설정은 P06-02c와 같다" 충족).
- 계획 ↔ config 내부 정합: ±15%(tolerance 0.15)·k 범위 [1.0,1.6]·타원 문턱 0.20·경계 ±1px(tolerance_px 1.0)·재현율 0.80/양성 80장·확대 50/최대 400·sd35 100장 보고 전용 — 계획 §P08-01과 config가 모두 일치한다. 모순 없음.

### 재현율 관문·소유자 확인

- train: 150장 중 소유자 확인 40장(보임 31·안 보임 9, 에이전트 표시와 상이 3장 = `gen_000333`·`gen_001364`·`gen_001836`) 반영 최종 양성 98·검출 87, 재현율 88.78%, Wilson 95% 81.01~93.62% — 관문(점추정 ≥0.80·양성 ≥80) 통과. 양성 98 ≥ 80이므로 표본 확대 분기는 발동하지 않는다(계약상 양성 부족 시에만).
- sd35: 100장 중 소유자 확인 30장(보임 26·안 보임 4, 상이 3장 = `gen_002559`·`gen_002761`·`gen_002997`) 반영 양성 74·검출 64, 재현율 86.49%, Wilson 76.88~92.49% — `owner_final`·`passed=null`·`gate_applies=false`(보고 전용)로 계약대로다.
- 확인 목록: train 불일치 12 + 무작위 28(=round(0.2×138)), sd35 불일치 13 + 무작위 17(=round(0.2×87)) — 커밋된 CSV와 행·사유까지 완전 일치, 소유자 CSV의 ID 집합도 확인 목록과 정확히 일치한다(일부 확인이 최종으로 오인될 여지 없음, `tests/test_p08_measure.py:30`이 잠금).
- 소유자 CSV 검증(중복·모르는 ID·0/1 외 값 거부)은 `:49` 셀이 잠근다(M5 기입증). 검출 재계산 포함 전량 재실행에서 동일 수치가 재현됐다.

### 보조 사람 영역 크기(보고 전용)

- REAL 150개 지름/의복 rect 합집합 높이 사분위 0.12406/0.14229/0.18582, GEN 50장 지름/보이는 사람 높이 사분위 0.12481/0.13501/0.20806, `frame_clipped` 29 — 표준 라이브러리 재도출과 전부 일치. 행별 산술·rect 합집합 재계산(발췌 JSON 기준, 불일치 0)·지름-후보 연결도 전행 일치.
- 표본 계보: 재현율 표본의 검출+최종 보임 87장에서 seed `20261011` 순서 앞 50장 — 재도출 일치. 수동 표시 CSV는 표본과 정확히 같은 50 ID, 범위 검증 통과.
- `gate_applies=false`이며 `report.json`(이미지 너비 대비 관문)은 수정하지 않는다(통합 셀 `tests/test_p08_person_size.py:56`이 원본 보고서 불변을 잠금). 두 분모의 의미 차이·해석 제한은 측정 README에 명시돼 있다.

### 블라인드 절차·기록

- 생성된 두 검토 페이지 payload는 `image_id`·이미지뿐이고 정답·검출·선정 사유가 없다(정적 확인 + `:61` 셀 양 pool 파라미터 + `test_p08_owner_review.cjs` 저장 로직). 미완료 저장 거부·완료 시 전수 CSV·대상별 파일명은 cjs가 잠근다(M10 기입증).
- 측정 README의 모든 수치 표(원 150개·k 사분위·타원 0/150·경계 2px·원 위 검출 0/150·누락 확인 0/50·재현율·보조 크기)는 원자료 재도출과 일치한다. 상대 링크 전수 존재. HANDOFF·계획 `:29`·`00_index.md` P08행의 상태 서술("관문 통과·보고 전용·독립검증 대기")은 사실과 일치하며 완료로 전환하지 않았다. `docs/sot.md:27` 소유 행 존재.
- 이전 검증 잔여: 소유자 train 확인·sd35 확인·보조 측정 3건 모두 슬라이스에 반영됐고, "대표 얼굴 검출을 P08-02에 재사용 금지" 경고도 README에 유지돼 있다.
- 복잡도: `owner_check_rows`는 set 차집합 단일 순회 O(n), `recall_summary`는 행 수 선형(누락 정렬 O(r log r)), `p08_person_size.run`은 입력 수 선형(라벨 ZIP 해시 1회 포함). 경계 측정은 σ grid 11×100장×72방향으로 유한. 신규 무한 retry·루프 없음.

## 문제·위험

### Blocking — 계약 의무

- **B1: 경계 질감 관문의 σ 선택 계약에 회귀 가드가 없다.** 사전 규격(`configs/anonymize_measure.yaml:43-47`)과 계획 §P08-01은 "전이 폭 중앙값이 REAL의 ±1px **안**(닫힌 구간)이 되는 **가장 작은 σ**"을 선택 규칙으로 사전 고정했다. 구현(`scripts/p08_measure.py:337`)은 옳지만, 이 리터럴을 잠그는 셀이 없다. M1(`<=`→`<`)과 M2(최소 σ 가드 제거) 모두 p08 suite 20셀 전부 통과(무저항). 실측에서 σ=0.5는 |1−2|=1.0으로 **정확히 경계값**이고 σ=1.0은 delta 0이므로, M1은 선택을 0.75로, M2는 1.0으로 조용히 바꾸고 `configs/anonymize.yaml`의 `edge_sigma` 유도가 변할 수 있다. 계약 요구 분기(±1px 포함 경계·최소 σ·매칭 없음 시 `edge_passed=false`)가 빈 칸이므로 본 가이드에 따라 차단 항목으로 한다. 해소 조건: σ 선택을 직접 잠그는 회귀 셀(예: `edge_width_by_sigma`가 `{0.25: 0.0, 0.5: 1.0, 0.75: 2.0, 1.0: 2.0}`, REAL 2px, tolerance 1.0인 stub에서 σ=0.5 선택·`edge_passed=true`, tolerance 밖 조합에서 `edge_passed=false`·σ=None)을 추가하고 양방향 변이로 검출력을 입증할 것.

### Hardening recommendations — 비차단

- H1(이전 검증 H1 잔존): `report.json` provenance에 소유자 표시 CSV(`recall_labels_owner*.csv`)의 SHA-256이 없다. `person_size_report.json`은 `recall_labels_owner.csv` 해시를 이미 기록한다. 사람이 바꾼 원자료와 보고서의 계보 강화 후보.
- H2: `measure_stage`가 쓰는 CSV는 csv 표준 dialect(CRLF)로 생성되지만 repo blob은 LF(`core.autocrlf=input`)라서, 재실행 시 `recall_detections.csv`·`recall_owner_check.csv`가 raw byte 불일치가 난다(내용은 정규화 후 완전 일치 — 이번 재실행으로 입증). `p08_person_size.write_csv`처럼 `lineterminator='\n'`을 쓰면 byte 수준 재현이 된다. 2026-10-11 검증이 byte 동일을 본 것은 당시 worktree 파일이 생성 직후 CRLF 상태였기 때문이다.
- H3: 보조 측정 GEN 표본의 모집단(검출+보임 87장)과 seed(20261011)가 사전 config가 아니라 코드·README·보고서에 사후 기록돼 있다. 관문이 없는 보고 전용이라 계약 위반은 아니나, 향후 유사 측정에서는 config에 사전 고정하는 것이 이 페이즈의 사전등록 원칙에 부합한다.
- H4: 사람 높이 수동 표시(`person_height_gen.csv`)는 에이전트 수행이며 소유자 확인을 거치지 않았다. 보고 전용이고 정밀도 한계가 명시돼 있으나, P08-03 크기 진단 설계 시 이 한계를 상기할 것.

## 판정

라운드 1(2026-10-13, 보강 전): **조건부 합격** — B1(경계 관문 σ 선택 회귀 셀 추가) 해소 시 합격. 최종 판정은 문서 첫 줄을 따른다(라운드 2에서 합격 확정).

- 수치·계보 전면 재현: 재현율 train 87/98(88.78%, Wilson 81.01~93.62) 관문 통과, sd35 64/74(86.49%) 보고 전용, 보조 크기 사분위·frame_clipped·표본 계보·행별 산술 전부 원자료 재도출과 일치.
- 재현성: 임시 복사본 전량 CPU 재실행에서 `report.json`·sd35 확인 목록·보조 산출물 4종 byte 동일, 나머지 2개 CSV는 줄바꿈만 차이(내용 동일, H2).
- 사전등록 불변·규격 연결·검출 설정 parity·블라인드 절차·기록 상태 전부 계약대로. 내부 계약 모순 없음.
- 변이 10종 중 8종 기대 셀 재실패(소유자 최종성·sd35 비적용·CSV 검증·k 사용·rect 합집합·표본 계보·ellipse 방향·미완료 저장). M1·M2만 무저항이며 이것이 B1이다.
- 소유자 육안 표시(원 확인·재현율 1차 표시의 정답 자체·사람 높이 범위 판독)는 재판독하지 않았다 — 원자료의 소유자 서술은 소유자 확인 절차(불일치+무작위 20%)와 기록으로 수용했다.

## 추적 검증 — 라운드 2 (2026-10-13)

- 대상: 보강 커밋 `8972d1e`(B1 회귀 셀·H1 provenance·H2 LF)·`526438d`(구현자 변이 자가확인 기록). 요청: 소유자. 검증자는 라운드 1과 동일하며, 구현자 설명·자가확인 표는 신뢰하지 않고 전 항목을 원자료에서 재확증했다. 변이 전 `git status --short` 빈 값 확인(트리 클린).

### B1 해소 확인

- 신규 셀 `tests/test_p08_measure.py:176` `test_edge_sigma_includes_both_tolerance_bounds_and_keeps_first_match`는 σ grid [.25,.5,.75,1.0]·REAL 전이 폭 2px stub에서 (a) 하한 경계(σ=0.5→폭 1.0, delta=1.0) 선택, (b) 상한 경계(σ=0.5→폭 3.0, delta=1.0) 선택, (c) 전 σ 매칭 없음 → `sigma=null`·`edge_passed=false`를 잠근다. `sigma` 값·`edge_width_by_sigma` 전체·`edge_passed`를 모두 단언한다. 선택 코드(`scripts/p08_measure.py:337`) 자체는 변경하지 않았다(보강은 셀 추가만 — 계약 리터럴 불변).
- 변이 3종 독립 실행(적용→guarding 셀 실행→`git checkout --` 복원→`git status --short` 빈 값 확인 each):

| 변이 | 방향 | 결과 |
| --- | --- | --- |
| M1r `:337` `<= tolerance_px` → `<` (닫힌 경계 배제) | 과잉 | exit 1 — 하한·상한 경계 2셀 재실패(무매칭 1셀은 통과) |
| M2r `:337` `chosen is None and` 제거(최소 σ→마지막 매칭 σ) | 과소 | exit 1 — 같은 2셀 재실패 |
| M3r `edge_passed=chosen is not None` → `True`(무매칭도 통과) | 과소 | exit 1 — 무매칭 셀 재실패 |

### H1~H4 반영 확인

- H1: `report.json` `provenance.owner_labels_sha256` 두 pool 값이 소유자 CSV 실측 sha256과 일치(재계산). 표시 파일 부재 시 `null` 처리도 `tests/test_p08_measure.py:151`이 잠근다.
- H2: csv writer 5곳 `lineterminator='\n'`(`scripts/p08_measure.py:178`·`:193`·`:249`·`:357`·`:362`), 측정 출력 3종 `\r` 부재 회귀 셀(`tests/test_p08_measure.py:153`), worktree sd35 확인 목록·빈 양식의 LF 정규화 확인. 재실행 산출물 4종이 HEAD blob·worktree와 모두 byte 동일(아래).
- H3/H4: 측정 README "남은 작업과 한계"에 보조 표본 선정의 사후 고정 성격, 사람 높이가 소유자 재확인 없는 에이전트 육안 표시임, P08-03에서 진단 표본·판정 규칙을 재학습 결과 전에 별도 고정한다는 명시를 확인했다.

### 수치 불변·재현

- `report.json`은 라운드 1 대비 `owner_labels_sha256` 추가 외 전 필드 동일(역직렬화 비교). `person_size_report.json` 입력 해시 11종 유효 — 보조 산출물은 본 변경의 영향이 없다.
- 집중 회귀 **57 passed**(`tests/test_p08_person_size.py`·`test_p08_measure.py`·`test_face_mask_ci.py`·`test_p06_patterns.py`) + `node tests/test_p08_owner_review.cjs` **2 passed** — 독립 재현. `git diff --check` 통과, 갱신 문서(README·계획·index·HANDOFF·일지) 링크 전수 존재.
- 임시 복사본 전량 CPU 재실행(보강 코드, 이미지 읽기 전용 mount, 산출물은 mount로 꺼내 host에서 비교): `report.json`(sha256 `9237f055…`)·`recall_detections.csv`(`dbd0eee4…`)·`recall_owner_check.csv`(`bb525ec1…`)·`recall_owner_check_sd35.csv`(`75afd38f…`) 4종 전부 **HEAD blob·worktree와 byte 동일** — 라운드 1의 EOL 차이(H2)가 해소됐다.

### 라운드 2 잔여 (비차단)

- R1: 스크립트가 다시 쓰지 않는 입력 CSV(`real_disc_candidates.csv`·`real_disc_review.csv`·`recall_labels_agent.csv`·train 빈 양식)는 worktree CRLF·blob LF 상태로 남는다(`core.autocrlf=input`). 이 머신에서는 안정적이나 신규 clone에서 체크아웃하면 worktree가 LF가 되어 `person_size_report.json`이 기록한 `recall_labels_agent.csv` 해시와 재실행 결과가 어긋날 수 있다(검증 시 불일치로 드러나는 형태라 조용한 오염은 아니다). 향후 기회에 입력 CSV도 LF로 정규화하면 blob 기준 재현이 완전해진다.

## 남은 운영 상태

1. B1 해소·H1~H4 반영 확인으로 **P08-01 슬라이스 독립검증은 합격**이다(라운드 2 확정).
2. 구현자 다음 작업: 측정 README·계획 §P08-01·`00_index.md`·HANDOFF의 "조건부 합격·추적 검증 대기" 문구를 합격으로 갱신하고 CHANGELOG에 P08-01 종결 항목을 추가한 뒤 P08-02(익명화 모듈)에 착수한다.
3. R1(입력 CSV EOL)은 비차단이며 P08-02 이후 기회에 반영할 수 있다.
4. 검증으로 슬라이스 코드·산출물은 변경하지 않았다. 본 기록의 라운드 2 갱신을 검증자가 커밋한다.

## 재현

위 "테스트·정적 검사" 명령 → "독립 재도출" 스크립트(호스트 표준 라이브러리: CSV 결합·Wilson·사분위·표본 seed·확인 목록·해시) → 임시 복사본 CPU 재실행(measure·person_size, 이미지 읽기 전용 mount) → 변이 표의 literal을 1개씩 적용·guarding 셀 실행·`git checkout --` 복원·`git status --short` 확인(매번) → combined focused suite. 실측은 GPU 미사용. 컨테이너 실행은 Docker socket 권한으로 승인된 escalation을 사용했다.

라운드 2 재현: 집중 회귀 57+2 → 소유자 CSV 해시·report 필드 차이·EOL 상태 재계산 → 변이 M1r~M3r(`tests/test_p08_measure.py::test_edge_sigma_includes_both_tolerance_bounds_and_keeps_first_match` guarding 셀) → 임시 복사본 재실행 후 산출물 4종 sha256을 `git show HEAD:<경로>` blob·worktree와 비교(컨테이너에는 git이 없으므로 산출물을 mount로 꺼내 host에서 비교).

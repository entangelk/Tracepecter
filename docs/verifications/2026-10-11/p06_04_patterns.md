# P06-04 오류 패턴 문서 + DB-03 얼굴 트리거 판정 — 독립검증

**조건부 합격** — 완료 조건 "Test B calibration 악화 분해"의 표본별 서술이 사실과 다르다(악화 12장은 "전부 sd35 GEN"이 아니라 sd35 GEN 10 + REAL FN 2). 또한 crop 민감도 해석 문장(`patterns/README.md:48`)이 같은 문서의 수치와 모순된다. 두 문장을 고치면 합격이다.

- 숫자 재계산: 오류 15, 얼굴 상태표, 생성기별 오류, Fisher p(0.00521·0.511), low_confidence 15/5, crop 분해 7/4/0(합계 11 = P06-02의 11)가 원천 자료와 독립 구현으로 모두 일치한다. 재실행 산출물도 커밋본과 바이트 단위로 같다.
- REAL 얼굴 노출 0.6%는 무작위 30장 육안 확인으로 지지된다. 미검출된 정면 얼굴은 0장이었다.
- DB-03 트리거 발동 판정은 조항의 일반문("오류가 얼굴 영역에 집중되는 패턴")에 근거하고, 예시 방향이 관측되지 않았음을 밝히고 있어 타당하다. 트리거의 효과도 "재상정"뿐이다.

## 대상 메타데이터

| 항목 | 값 |
| --- | --- |
| 일자 | 2026-10-11 |
| 요청자 | 소유자(메인 에이전트 경유) |
| 검증자 | Claude Code 독립검증 에이전트(작성자 아님) |
| 대상 | P06-04 — `experiments/p06_failure_analysis/patterns/{README.md,features.csv,patterns.json}`, `scripts/p06_patterns.py`, `tests/test_p06_patterns.py`, `docs/decision_briefs/DB-06_P06_face-exposure.md`, `docs/decision_briefs/00_index.md`, DB-03 재상정 절 |
| 출처 | `06f5254`(스크립트·테스트), `79163f6`(문서·산출물). main, 검증 시작 시 clean tree |
| 정본 계약 | `docs/plan/phase_6_failure_analysis.md:14`(P06-04 정의), 같은 문서 "완료 조건"·"제외·병행", `DB-03` Recommendation 2, `DB-05` Resolution, HANDOFF 1번 항목, `docs/guides/phase-and-decision-briefs.md` |

## 범위

1. 문서 수치 재계산(patterns/README.md, DB-06)
2. 스크립트 논리 대 주장: face_state 규칙, 오류 경계, crop 기하, YuNet sha 검사, 결정성
3. 추론 타당성: 트리거 해석, P3 인과 서술, REAL "얼굴 없음" 육안 표본 확인
4. DB-06 브리프·인덱스 정합
5. 테스트(집중·전체)와 양방향 guard 감사
6. 변이 테스트

## 방법(재현 가능한 명령)

- 결정성: 커밋 산출물을 scratch에 복사한 뒤 `docker compose --profile training run --rm -T train python -m scripts.p06_patterns`를 실행했다(4분 14초, exit 0). 이어서 `cmp`로 features.csv·patterns.json을 비교했다. 결과는 IDENTICAL이고 `git status --short`도 비어 있었다.
- 독립 재계산: 검증자가 작성한 `recompute.py`(scratch, 리포 밖)를 `docker compose --profile training run --rm -T -v <scratch>:/v train python /v/recompute.py /v/recompute.json`로 실행했다.
  - 이 스크립트는 `src.face_mask_ci.detect_face`를 쓰지 않는다. `cv2.FaceDetectorYN`을 config 값으로 직접 호출하고, 선택 규칙을 다시 구현했다.
  - sigmoid(logit/T)도 직접 계산했다.
  - crop은 `src/failure_analysis.py:72-75`과 같은 정수 기하로 수행했다. 그 뒤 crop 이미지에 YuNet을 다시 돌렸다.
  - 집계는 `analyze.py`가 했다. 양측 Fisher 검정은 `scipy.stats.fisher_exact(alternative='greater')`로 교차 확인했다.
- 오류·검토 수치: `reports/errors/{false_positive,false_negative}/manifest.csv`, `review_{set,agent,owner}.csv`를 직접 조인했다.
- REAL "얼굴 없음" 표본 확인: REAL face_state=none 619장을 seed 20261011로 섞어 앞 30장을 접촉 시트로 만들었다. 얼굴 후보 5장은 상단 45%를 원해상도로 잘라 Read 도구로 직접 봤다.
- 테스트: `docker compose run --rm -T dev python -m pytest tests/test_p06_patterns.py -q`(6 passed, exit 0), `docker compose run --rm -T dev python -m pytest -q`(102 passed, exit 0).
- 변이: 매 변이 전 `git status --short`가 비어 있음을 확인했다. 변이를 적용하고 집중 테스트를 돌린 뒤 `git checkout -- scripts/p06_patterns.py`로 복원했고, clean 상태를 다시 확인했다. 11개 변이 모두 복원 후 clean이었다.

## 발견

### 1. 수치 재계산

| 주장(위치) | 주장값 | 재계산값 | 판정 |
| --- | --- | --- | --- |
| 오류 수(`patterns/README.md:19-22`) | 15 = FP 10 + FN 5. test 12(FP 8, FN 4), val 3 | 15. manifest와 일치(FP: sd35 7 전부 test_unseen, qwen 3 = test 1·val 2) | 일치 |
| FP 부위·score | 아우터 5·상의 4·원피스 1, 72.6~99.4 | 같음 | 일치 |
| FN 부위·score | 아우터·하의·상의 1, 원피스 2. 32.5~55.2 | 같음 | 일치 |
| REAL 얼굴 상태(`:55`) | 276 / 5 / 619 | 276 / 5 / 619 | 일치 |
| GEN 얼굴 상태 | 0 / 851 / 469 | 851 / 469. GEN의 원 검출 23장은 규칙상 무시 | 일치 |
| GEN 오류 none / visible | 8/469, 2/851 | 8, 2 | 일치 |
| 한쪽 Fisher p(GEN) | 0.005 | 0.0052109(자체 구현 = scipy) | 일치 |
| 한쪽 Fisher p(REAL none > disc) | 0.51 | 0.51078 | 일치 |
| low_confidence GEN none / visible | 15 / 5 | 15 / 5(전체 24) | 일치 |
| 생성기별(`:36-42`) | sd35 1/382·6/218, qwen 1/130·2/50, 나머지 0 | 같음 | 일치 |
| crop 분해(`:45-47`) | none 336에서 7, 제거 127에서 4, 유지 482에서 0 | none은 343장(원래 오답 7 포함), 원래 정답 336 중 새 FP 7. 제거 127 중 4. 유지 482(원래 오답 1 포함) 중 새 FP 0. 새 FP 합계 11 = 전부 sd35·test_unseen. P06-02 표의 B GEN 전환 11과 같다. Test A GEN 새 FP는 0 | 수치 일치, 분모 기준 불일치(Hardening H3) |
| "crop 뒤 얼굴이 보이지 않는 GEN"(`:45`) | 11장 모두 | crop 이미지에 YuNet을 다시 돌려도 11장 모두 미검출 | 일치(독립 근거) |
| 종횡비(`:76`) | GEN 1.0 6/660, 1.46 4/660 | 같음 | 일치 |
| 학습 생성기 오류(`:30`) | playground·sdxl·z 0, qwen 3 | 같음 | 일치 |
| z_image_turbo none(`:49`) | 178/180, 오류 0 | 같음 | 일치 |
| 소유자 FP 판정(`:65`) | synthetic 9, ambiguous 1 | 같음 | 일치 |
| 불일치 16건 분류(`:84-87`) | 7/4/3/2 | 소유자 ≠ 에이전트 16건. 분류 건수는 일치. 다만 문구 세 곳이 부정확하다(H5) | 건수 일치 |
| **Test B NLL/Brier 악화(`:29`)** | "loss가 커진 12장이 **전부** logit이 양수인 sd35 GEN" | 악화 12장 = **sd35 GEN 10(logit > 0) + REAL 2(1032814 logit −0.099, 1284862 logit −0.227)**. NLL과 Brier 모두 같은 12장이다. 합계 +0.5146(GEN +1.2377, REAL −0.7231)은 주장과 일치 | **불일치(Blocking B1)** |

- 악화 표본 목록은 다음과 같다. sd35는 gen_000547·2679·2723·2727·2731·2736·2738·2759·2786·2813, REAL은 1032814·1284862다.
- 원리상 T<1은 logit 부호가 틀린 쪽에 있는 모든 표본의 loss를 키운다. 따라서 p<0.5인 REAL FN 2장(score 46.9·42.9)도 반드시 악화된다.
- 같은 문장이 `experiments/p06_failure_analysis/README.md:46`, `docs/plan/phase_6_failure_analysis.md:56`에도 있다. 처음 생긴 곳은 `d0074e9`이고, P06-04가 이 문장을 자기 산출물(P1 근거)로 그대로 가져왔다.

### 2. 스크립트 논리

- face_state(`scripts/p06_patterns.py:31-35`): REAL만 disc를 우선하고, GEN의 disc는 무시한다. P06-02b 근거("GEN 검출 37장 전부 오검출", 이 2,220장 중에는 23장)와 일치한다.
- 오류 경계(`:38-39`): `p >= threshold`이면 REAL로 판정한다. `src/failure_analysis.py:27-35`의 `case_type`과 같다. val 1247671(p = threshold)은 정답 REAL로 처리된다. 재계산의 오류 15·features.csv 불일치 0으로 확인했다.
- low_confidence(`:141`): `10 <= 100p <= 90` 대 `case_type`의 `low/100 <= p <= high/100`. 부동소수 경계 표현은 다르지만 결과 24장은 같다.
- crop 기하(`:58-64`): 스크립트는 `/2`와 위쪽 경계 포함(`<=`)을 쓴다. 실제 구현(`src/failure_analysis.py:73-75`)은 `//2`와 반열린 구간이다.
  - GEN 크기(832×1216, 정사각)에서는 차이가 0이다. 검증자가 정수 기하로 재계산해도 482/127이 같다.
  - 홀수 차이나 가로형 입력에서는 0.5px 어긋날 수 있다(H2).
  - "얼굴 중심 유지"는 근사다. crop 뒤 YuNet 재검출 기준으로 유지 판정 4장은 얼굴이 미검출이었고, 제거 판정 5장은 검출됐다. 결론(새 FP 11장 모두 crop 뒤 미검출)은 바뀌지 않는다.
- YuNet sha256 검사는 `:115-116`에 있다. 재계산에서 sha가 일치했다(True).
- 결정성: 재실행 산출물이 커밋본과 바이트 단위로 같다.
- 복잡도: 이미지당 1회 검출로 O(n)이고 집계도 O(n)이다. 문제없다.

### 3. 추론 타당성

- **트리거 해석**: DB-03 조항(`DB-03_P01_face-policy.md:29`)의 본문은 "오류가 얼굴 영역에 집중되는 패턴"이고 괄호 안은 "예"다. 관측된 것은 반대 방향(얼굴 없는 GEN → REAL 통과)의 집중이다.
  - 근거: GEN 8/469 대 2/851, p = 0.0052. 생성기 교란을 빼려고 sd35만 따로 봐도 6/218 대 1/381, p = 0.011이다.
  - P06-02c 개입 실험의 "확정"도 근거로 함께 들었다.
  - 문서가 예시 방향이 관측되지 않았음을 명시하고(`patterns/README.md:98`), 트리거의 효과는 소유자 재상정뿐이다.
  - 따라서 "발동" 판정은 타당하다. 다만 오류 절대수(8 대 2)가 작다는 점은 한계로 남는다.
- **P3 인과 서술**: 데이터 비대칭은 측정값으로 지지된다. 과장된 부분은 두 가지다.
  - (a) `:58` "학습 데이터에서 거의 완벽한 단서", `:60` "본 적이 없다"는 학습 split(REAL 2,100)이 아니라 test/val 900장을 측정한 값이다. 같은 K-Fashion 풀이라 외삽은 그럴듯하지만, 측정 범위를 밝혀야 한다(H4).
  - (b) `:48` "crop 민감도는 대부분 얼굴 노출 변화로 설명된다"는 문서 자신의 수치와 모순된다. 새 FP 11장 중 7장은 crop 전에도 얼굴이 없던 표본이어서 crop이 얼굴 노출을 바꾸지 않았다. 얼굴 노출 변화(제거)로 설명되는 것은 4장뿐이다.
    - 수치가 말해 주는 것은 "crop 뒤 얼굴이 남은 표본에서는 새 FP가 0/481"이라는 것, 즉 얼굴 노출이 보호 조건이라는 점까지다.
    - 7장의 전환은 여전히 구도·정보 손실과 분리되지 않는다(Blocking B2).
- **REAL "얼굴 없음" 육안 확인(30장)**:
  - 정면이나 온전한 얼굴이 보이는데 미검출된 사례는 **0/30**이다.
  - 프레임 상단에서 잘려 입·턱만 보이는 부분 얼굴이 2장(1241284, 531531)이다.
  - 뒷머리·뒷모습이 3장(1305174 소형 전신 측후면, 709734, 830132)이다.
  - **흰 타원 익명화가 있는데 P06-02b 원 검출기가 놓친 사례**가 1장(935906)이다.
  - 나머지 24장은 얼굴이 프레임 밖이다.
  - 결론: REAL 얼굴 노출 0.6%는 YuNet 누락 때문에 생긴 값이 아니다(지지됨). 다만 REAL "흰 원" 276은 하한이다(타원·소형 원 누락, H6).

### 4. DB-06 브리프·인덱스

- 옵션 A~D는 서로 다른 실행안이고 선택이 가능하다. D는 A의 GEN 정합을 포함하지만, REAL 수집 여부로 갈리므로 상호배타로 볼 수 있다.
- 추천은 표 아래에 있다. 추천이 "C + D의 축소판(평가 전용 holdout)"을 묶지만, holdout은 평가용이라 옵션 선택과 충돌하지 않는다.
- 인덱스 행(`00_index.md:13`)은 Open·2026-10-11·추천 C로 본문과 일치한다. "대기 중인 사항"도 갱신됐다.
- **C의 과장(Hardening H1)**:
  - `DB-06:30`의 "K-Fashion과 같은 흰 원"·"얼굴이 보이는 실사 입력도 같은 형태로 바뀌어 처음 보는 분포 문제를 피한다", `:39`의 "학습 분포 안으로 가져온다"는 YuNet이 얼굴을 검출할 때만 성립한다.
  - P06-02c가 검증한 것은 GEN 대상 40장의 정밀도(40/40)뿐이고, 재현율은 측정하지 않았다. GEN "얼굴 없음"에 측면 얼굴이 섞여 있다는 것은 보고서 자신의 한계다(`patterns/README.md:119`).
  - 미검출 GEN 측면 얼굴은 C 뒤에도 "보이는 얼굴 → GEN" 단서로 남는다.
  - B를 기각한 논리("처리 자체가 새 단서")는 C에도 적용된다. 합성 원(지름 1.2×상자, 완전 원형)과 K-Fashion 원(타원 포함, 크기·경계 처리 상이, 935906 사례)이 다르면 "합성 원 → GEN" 단서가 생길 수 있다.
  - 이 두 가지가 Cons에 없다.
- 계획서 "관련 결정 브리프"(`phase_6_failure_analysis.md:47-51`, DB-03·DB-05만 있음)에 DB-06 링크가 없다(Outstanding 참조).

### 5. 테스트·양방향 guard

6셀 모두 통과했다. 셀별 대응과 변이 결과는 다음과 같다.

| 변이 | 내용 | 결과 | 잡은 셀 |
| --- | --- | --- | --- |
| M1 | GEN disc도 'disc'로 | 실패 | `test_face_state_uses_disc_only_for_real` |
| M2 | `>=` → `>`(경계) | 실패 | `test_is_error_at_threshold_boundary` |
| M3 | crop 아래 경계 배타 | 실패 | `test_crop_keeps_face_checks_face_centre_inside_centre_square` |
| M4 | crop 위(아래쪽 끝) 경계 검사 삭제 | **통과(생존)** | — (H2) |
| M5 | Fisher 합 범위 +1 | 실패 | `test_fisher_greater_is_hypergeometric_upper_tail` |
| M6 | summarize low_confidence = 0 | **생존** | — (fixture의 low_confidence가 전부 False, H7) |
| M7 | crop 오류에 원본 error 사용 | 실패 | `test_summarize_counts_by_face_state_and_tests_concentration` |
| M8 | Wilson 중심 식 변경 | 실패 | `test_wilson_matches_known_values` |
| M9 | YuNet sha 검사 제거 | **생존** | — (`main()` 테스트 없음, H7) |
| M10 | REAL 검정 a/b 뒤바꿈 | **생존** | — (REAL 검정 미단언, H7) |
| M11 | low_confidence 정의에서 "오분류 아님" 제거 | **생존** | — (`main()` 미테스트, H7) |

- 순수 함수(face_state·is_error·wilson·fisher)는 양방향 guard가 있다.
- 생존 변이는 계획서가 테스트를 계약으로 요구하지 않는 보고 경로(`main()`·보조 집계)에 있다. 이 슬라이스의 계약 산출물은 문서·수치이고, 수치는 독립 재계산으로 검증했다. 그래서 Hardening으로 분류한다.
- 전체 suite는 102 passed, exit 0이다.

## Issues / Risks

### Blocking

- **B1** — `experiments/p06_failure_analysis/patterns/README.md:29`: "temperature 적용 후 loss가 커진 12장이 전부 logit이 양수인 sd35 GEN"은 거짓이다. 실제로는 sd35 GEN 10장과 REAL FN 2장(1032814, 1284862, logit < 0)이다.
  - 이 분해는 P06-04 완료 조건("Test B calibration 악화 분해", `phase_6_failure_analysis.md:14`·완료 조건 4번)의 산출물이다.
  - 같은 문장인 `experiments/p06_failure_analysis/README.md:46`, `docs/plan/phase_6_failure_analysis.md:56`도 함께 고쳐야 한다.
  - 결론(GEN 기여 +1.238이 순악화를 만든다)은 유지된다.
- **B2** — `patterns/README.md:48`: "crop 민감도는 대부분 얼굴 노출 변화로 설명된다"는 같은 문서 `:46`의 수치(11장 중 7장은 crop 전에도 얼굴 없음)와 모순된다. P06-02가 열어 둔 질문을 근거 없이 닫는다.
  - 수정 방향: "새 FP는 crop 뒤 얼굴이 보이지 않는 표본에서만 나왔다(얼굴 유지 0/481). 얼굴 제거로 설명되는 것은 4/11이고, 원래 얼굴이 없던 7장의 전환은 구도·정보 손실과 분리되지 않는다."

### Hardening(비차단)

- **H1** `docs/decision_briefs/DB-06_P06_face-exposure.md:30,39`: C의 Cons에 두 가지를 추가하고, "처음 보는 분포 문제를 피한다"를 "검출된 얼굴에 한해"로 한정한다.
  - (a) YuNet 재현율이 측정되지 않았고, 미검출 GEN 측면 얼굴이 GEN 단서로 남는다.
  - (b) 합성 원과 K-Fashion 원의 모양·크기·경계 차이가 새 단서가 될 위험이 있다. B 기각 논리의 대칭 적용이다.
- **H2** `scripts/p06_patterns.py:63-64`: crop 기하를 `src/failure_analysis.py:73-75`(정수 `//2`, 반열린 구간)와 맞추거나 공용 함수로 쓴다. `tests/test_p06_patterns.py:36-41`에 아래쪽 끝(중심 y = 1024 경계)과 가로형 케이스를 추가한다(M4 생존).
- **H3** `scripts/p06_patterns.py:100-106`, `patterns/README.md:46`: crop 집계에 none 그룹을 넣고, "새 FP"(원래 정답 → crop 오답)를 직접 계산한다. 336은 patterns.json에 없어 산출물에서 재현되지 않는다. 336(원래 정답만)과 482(원래 오답 1 포함)는 분모 기준도 다르다.
- **H4** `patterns/README.md:58,60`, `DB-06:20`: 얼굴 노출 비율이 test·val 2,220장 측정값이라는 점을 밝힌다. 원하면 train split도 측정해 "학습 데이터" 주장을 직접 뒷받침한다.
- **H5** `patterns/README.md:84-86`: 문구 세 곳을 고친다.
  - gen_002813은 상의(니트)인데 "미니멀 코트 컷"으로 묶였다.
  - qwen 4건 중 0736·0972는 에이전트가 `ambiguous`였다(0972는 결함까지 기록). 따라서 "에이전트가 속고"는 2건에만 해당한다.
  - z_image 1409는 score 59.5의 low_confidence다. "모델은 고확신 GEN으로 정답"은 1436·1519에만 맞는다.
- **H6** `patterns/README.md:55`, 한계 절: REAL 흰 원 276은 하한이다. 육안 30장 중 1장(935906)이 타원 익명화 미검출이었다. 이 점을 명시한다.
- **H7** `tests/test_p06_patterns.py:51-62`: summarize fixture에 low_confidence True 행과 REAL disc/none 오류를 넣어 `real: none > disc` 방향과 low_confidence 합계를 단언한다(M6·M10). `main()`의 low_confidence 정의·sha 불일치 오류를 작은 fixture로 고정한다(M9·M11).

## 판정

**조건부 합격** — B1(NLL/Brier 악화 12장의 구성 정정: sd35 GEN 10 + REAL FN 2, 세 문서)과 B2(crop 해석 문장 정정)를 닫으면 합격이다.

- 핵심 수치는 원천 자료에서 독립 재계산한 값과 모두 일치하고, 산출물은 결정적이다.
- REAL 얼굴 노출 0.6%는 육안 확인으로 지지된다(정면 얼굴 미검출 0/30).
- DB-03 트리거 발동 판정과 DB-06 상정은 조항 문언과 근거에 비추어 타당하다.
- 결함은 표본별 분해 서술 한 건(완료 조건 산출물의 사실 오류)과, 수치와 모순되는 해석 문장 한 건이다.

## Outstanding

- P06-04 기록이 아직 반영되지 않았다: HANDOFF.md(1번 항목 여전히 "P06-04 작업 예정"), `docs/plan/phase_6_failure_analysis.md`(진행 상황 마지막 줄 "다음: P06-04", 관련 결정 브리프에 DB-06 없음), work_log, CHANGELOG. 검증 뒤 반영 예정으로 보인다.
- DB-06은 Open이다(P06 완료를 막지 않음).
- DB-03 배경 사실("REAL은 대부분 얼굴이 포함된 착용컷", `DB-03:9`)은 측정값(0.6%)과 다르다. Resolved 브리프라 본문은 보존하되, 재상정 절에 이 차이를 한 줄 적는 것을 권한다.

## 재현

```bash
git status --short                                   # 비어 있어야 함
cp -r experiments/p06_failure_analysis/patterns <scratch>/patterns_committed
docker compose --profile training run --rm -T train python -m scripts.p06_patterns
cmp experiments/p06_failure_analysis/patterns/features.csv <scratch>/patterns_committed/features.csv
cmp experiments/p06_failure_analysis/patterns/patterns.json <scratch>/patterns_committed/patterns.json
docker compose --profile training run --rm -T -v <scratch>:/v train python /v/recompute.py /v/recompute.json  # 검증자 독립 재계산(YuNet 직접 호출, crop 재검출)
python3 <scratch>/analyze.py <scratch>/recompute.json experiments/p06_failure_analysis/patterns/features.csv <scratch>/real_none.json
docker compose run --rm -T dev python -m pytest tests/test_p06_patterns.py -q
docker compose run --rm -T dev python -m pytest -q
# 변이: 각 변이 전 git status --short 비어 있음 확인 → 적용 → 집중 테스트 → git checkout -- scripts/p06_patterns.py → clean 재확인
```

검증 스크립트(`recompute.py`, `analyze.py`)는 세션 scratch에 있으며 리포에 넣지 않았다. 핵심 로직은 위 "방법" 절에 적었다. Test B 악화 분해는 `nll(l,z,t) = −[l·log σ(z/t) + (1−l)·log(1−σ(z/t))]`를 t=1과 t=T에서 비교해 계산했다.

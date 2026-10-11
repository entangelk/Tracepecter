# 독립검증 — DB-06 C 확정 기록 · `project.md` §22 전처리 조항 · P08 계획

**합격** — (4차, 커밋 `08f6ecf`) R1이 닫혔다: score CLI·API는 키가 없거나 `null`인 checkpoint를 거부하고, 거부·통과 양방향 셀이 있다. 1–3차 차단 조건(C1–C3, N1–N2, R1)이 모두 닫혔고, 남은 것은 비차단 H25 하나다.

> 3차 판정(커밋 `397abf2` 대상): **조건부 합격** — (3차, 커밋 `397abf2`) N1·N2와 H17–H21은 닫혔다. 남은 조건 하나: 학습 config에 허용한 명시적 `null` 키(`phase_8_face_anonymization.md:81`)를 score CLI·API가 어떻게 처리하는지 정해지지 않았다(`:84`는 "키 없음"만 거부). "score CLI·API는 키가 `null`이어도 거부"(§22)를 계약에 넣고, P08-02 검증 셀(`:51-56`)에 추가할 것.
>
> 2차 판정(커밋 `a412f74` 대상): **조건부 합격** — (2차, 커밋 `a412f74`) 1차 C1–C3은 닫혔다. 새 조건 2개: (N1) P08 채택 실패 시 baseline 유지 규칙(`phase_8_face_anonymization.md:58-59`)이 무조건 익명화를 요구하는 `project.md:780`(§22)·P07 선행 조건(`plan/00_index.md:14`)과 충돌하므로, 비채택 분기에서 P07이 무엇을 서빙하는지 소유자 결정으로 정할 것. (N2) checkpoint 결합 계약(`phase_8:73`)의 "규격이 없으면 거부"와 "규격이 없으면 원본 경로로 동작"이 같은 조건에 두 결과를 주므로 판별 규칙을 명시할 것.
>
> 1차 판정(커밋 `6f0f383` 대상): **조건부 합격** — (C1) 결정 반영 누락 정리: `docs/sot.md` 버전 로그에 project.md §22 변경 기록, `docs/plan/00_index.md:23`·`README.md:25`·`README.md:87`의 "무처리(DB-03)" 현행 서술 갱신. (C2) P08 계획에 익명화 규격이 checkpoint에 결합되어 evaluate·calibrate·score로 전달되는 계약을 명시. (C3) P08 결과가 나쁠 때(단서 잔존·지표 하락)의 채택/중단 분기와 P07이 쓸 checkpoint를 정하는 사전 규칙 또는 소유자 결정 지점을 계획에 명시.

- 결정 자체(DB-06 C 선택·일자·근거·Resolved)와 옵션 표 보존, 상호 링크, 인덱스 상태는 맞다.
- 인용 수치(0.4%·64.5%·1.7%/0.24%·p = 0.005·7.6% [5.7, 9.5]·흰 원 25%/31%)는 원자료와 일치한다.
- 차단 사유는 문서 오류가 아니라 **반영 누락 3곳**과 **계획의 미정 분기 2개**다. 모두 P08 착수(승인) 전에 문서만으로 닫을 수 있다.

## 대상 정보

| 항목 | 내용 |
| --- | --- |
| 일자 | 2026-10-11 |
| 요청자 | 소유자("검증하고 더 필요한 것 없는지") |
| 검증자 | 독립 검증 에이전트(작성자 아님) |
| 대상 | DB-06 Resolution, `docs/project.md` §22 신설 조항, `docs/plan/phase_8_face_anonymization.md`, 인덱스·HANDOFF·CHANGELOG·work log 반영 |
| 기준 사양 | `docs/project.md`(§1·§4·§15·§22·§23·§25), `docs/sot.md` §2–§4, `docs/guides/phase-and-decision-briefs.md`, `docs/guides/data-contracts.md`, `docs/guides/verification.md` |
| 작업 출처 | 커밋 `6f0f383`(직전 P06 완료 커밋 `171d505` 참조), 작업 트리 clean |

## 범위

1. 결정 기록 완결성·문서 간 일관성(상태·링크·일자·잔존 "Open"/"무처리" 서술)
2. 사양 일관성(§22 신설 조항과 다른 절의 충돌)
3. P08 계획 품질(템플릿, 선행 산출물, 검증 가능한 완료 조건, 슬라이스 순서·누락)
4. 계획·브리프의 사실 주장
5. 기록(work log·CHANGELOG·HANDOFF)

## 방법

```bash
git show --stat 6f0f383 171d505
git show 6f0f383 -- docs/project.md docs/decision_briefs README.md HANDOFF.md CHANGELOG.md docs/plan docs/daily_logs
cat -n docs/plan/phase_8_face_anonymization.md docs/decision_briefs/DB-06_P06_face-exposure.md docs/sot.md
grep -rn -i 'DB-03\|무처리\|DB-06\|얼굴\|face' README.md HANDOFF.md docs/project.md docs/plan/*.md docs/decision_briefs/00_index.md
grep -n '^# \|^## ' docs/project.md docs/plan/phase_*.md
sed -n 400,535p docs/project.md; sed -n 740,835p docs/project.md
cat -n src/dataset.py src/score.py src/calibrate.py; grep -n 'def load_model' -A9 src/evaluate.py; grep -n 'config' src/train.py
cat configs/face_mask_ci.yaml configs/primary.yaml configs/calibration.yaml
grep -n '64.5\|0.4%\|1.7%\|0.24\|0.005\|흰 원' experiments/p06_failure_analysis/patterns/README.md
grep -n '7.6\|confirmed' experiments/p06_failure_analysis/face_mask_ci/README.md
grep -n 'Hough\|ellipse' src/face_mask.py experiments/p06_failure_analysis/face_mask/README.md
# 변경 파일의 상대 링크 존재 확인(Python 스크립트, 깨진 링크 0)
```

문서·계획 슬라이스이므로 변이 테스트는 하지 않았다(대상 코드 변경 없음).

## 발견 사항

### 1. 결정 기록 완결성·일관성

확인한 것:

- DB-06 옵션 표 A–D 보존, Resolution에 선택(C)·일자·근거·Status `Resolved`가 있다(`DB-06_P06_face-exposure.md:3`, `:56-65`). 가이드의 Resolution 요건을 충족한다.
- DB-03 재상정 절에 DB-06 대체 링크가 있다(`DB-03_P01_face-policy.md:50`). `sot.md:35`의 "supersession 링크를 건 새 결정 ID" 규칙을 충족한다.
- 브리프 인덱스 DB-06 행 Resolved(`decision_briefs/00_index.md:13`), 대기 사항 "없음"(`:17`), 페이즈 인덱스 P06·P07·P08 행(`plan/00_index.md:13-15`), P06 계획 관련 브리프(`phase_6_failure_analysis.md:52`, `:87`)가 서로 맞다. 변경 파일의 상대 링크는 모두 존재한다.

관찰한 결함:

- **`docs/sot.md` 버전 로그 미갱신(차단, C1)**. `sot.md:45`는 "요구사항·범위·기준·구조 변경"을 버전 로그에 기록하도록 한다. 이전 §10 변경은 v1.3으로 기록됐다(`sot.md:53`). §22 추론 입력 전처리 신설은 API 요구사항 변경인데 v1.4 행이 없다.
- **현행 정책으로 읽히는 "무처리" 서술 잔존(차단, C1)**.
  - `docs/plan/00_index.md:23` "얼굴 처리(DB-03: 무처리) Resolved" — 실행 상태 SoT(`sot.md:18`)의 비고가 대체된 결정을 현행처럼 말한다.
  - `README.md:25` "얼굴 영역: 무처리 정책(DB-03)", `README.md:87` Known limitations "무처리 정책(DB-03)이므로 점수에 얼굴 특성이 기여할 수 있으며". README는 precedence 5순위이지만 외부 공개 요약이고, Known limitations는 DB-06 이후 의미가 바뀐다(얼굴 영역이 점수에서 빠짐, 미검출 얼굴만 기여).
- 비차단: 브리프 인덱스 DB-03 행(`decision_briefs/00_index.md:9`)에 "DB-06으로 대체" 표시가 없다. DB-06 헤더 Related phase(`DB-06:4`)가 "재학습"으로만 되어 P08을 가리키지 않는다. `phase_1_data_pipeline.md:82`, `:88`은 당시 기록이라 그대로 둬도 되지만 "(2026-10-11 DB-06으로 대체)" 한 줄이 있으면 오독이 줄어든다.

### 2. 사양 일관성

- §22 조항(`project.md:778`)은 "학습·평가와 똑같은 전처리"라고 하지만, 학습·평가 전처리를 소유하는 §15(`project.md:503-531`)는 "기본 처리"를 RGB·Resize·Crop·Normalization으로 나열하고 "최초 baseline에서는 복잡한 preprocessing을 사용하지 않는다"고만 한다. 엄밀한 모순은 아니지만(P08 모델은 최초 baseline이 아님), 학습 전처리 계약이 API 절에만 있고 전처리 절에는 없다. 소유자 확인 사항 Q1로 올린다.
- §4 비범위 "얼굴 deepfake 탐지"(`project.md:93`)와는 충돌하지 않는다. 오히려 얼굴을 점수에서 빼는 방향과 일치한다.
- §1·§34 제품 정의("실제 착용 촬영처럼 보이는 정도")와 §23 데모(Preview 표시, `project.md:790-833`)는 "얼굴 영역은 점수에 기여하지 않음"과 "미리보기에 원본/익명화본 중 무엇을 보이는가"를 말하지 않는다. §22 출력 예의 `model_version: "v0.1"`(`project.md:772`)도 새 checkpoint·calibration·익명화 규격 조합을 식별하는 규칙이 없다. 조항이 "상세 계약은 P08에서 정한다"고 위임했으므로 P08 계획에 해당 항목이 있어야 하는데 없다(H11). 사양 측 판단은 Q2로 올린다.
- `sot.md` §2 SoT 지도(`:15-28`)에 익명화 규격 config 소유 행이 없다. P08-02 구현 시점에 추가하면 된다(비차단, H9에 포함).

### 3. P08 계획 품질

템플릿: 목표·선행 조건 / 범위·검증 / 계약·소유권 / 완료 조건 / 제외·병행 / 관련 결정 브리프가 있다(`phase_8:7-63`). P05·P06 계획과 같은 저장소 관례(결합 제목)를 따른다. 선행 조건은 산출물로 적혀 있고(`:16`), GPU 정책(`:58`)도 기존 지시와 같다.

차단:

- **C2 — 익명화 규격의 checkpoint 결합과 하류 전달 미정**. 하류 도구는 모두 checkpoint에 저장된 config로 입력 변환을 다시 만든다: `src/evaluate.py:97-105`(`load_model`이 `saved['config']` 반환), `src/calibrate.py:39-42`, `src/score.py:37-39`. 학습 config는 checkpoint에 통째로 저장된다(`src/train.py:134-139`). 계획은 "학습 config는 이를 참조만 한다"(`phase_8:42`)고만 한다. 이대로면 (a) evaluate·calibrate·failure_analysis가 익명화 없이 새 checkpoint를 평가하거나, (b) `configs/anonymize.yaml`을 경로로만 참조할 경우 학습 뒤 파일이 바뀌어도 같은 checkpoint가 다른 입력으로 평가된다. 계약 절에 "checkpoint config에 익명화 규격 내용(또는 경로+sha256)을 넣고, 하류는 checkpoint에서만 읽으며, 불일치·누락 시 거부"를 명시해야 한다(`data-contracts.md` §1·§2: 소유자·소비자·계보).
- **C3 — 실패 분기 없음**. 관문은 P08-01 재현율 하나뿐이다(`phase_8:24`). P08-03/04에서 Test A/B ROC-AUC가 §20 기준 아래로 떨어지거나, P08-05에서 단서가 남았다고 판정될 때 무엇을 하는지(baseline 유지·소유자 결정·P07 차단)가 없다. 그런데 P07 선행 조건은 이미 "새 checkpoint·calibration artifact"로 고정됐다(`plan/00_index.md:14`). 채택 규칙이 없으면 `configs/primary.yaml`(SoT, `sot.md:25`)을 언제 바꾸는지도 정해지지 않는다. 사전 규칙이나 "P08-05 판정 후 소유자 결정" 지점을 완료 조건에 넣어야 한다.

비차단(아래 Hardening H1–H16에 상세):

- 익명화를 증강보다 먼저 적용하는 것은 구현 가능하다. `MetadataDataset.__getitem__`에서 `self.transform` 앞(`src/dataset.py:128-130`)에 원본 해상도 좌표로 칠하면 Resize·crop·flip·JPEG가 뒤에 온다. 좌표 캐시가 원본 기준이라 증강과 충돌하지 않는다. `RandomJPEG`(p = 0.5)가 칠한 뒤 적용되는 점은 합성 원 경계를 REAL에 가깝게 만드는 쪽으로 작용한다. 평가·추론에는 JPEG가 없으므로 PNG GEN의 날카로운 합성 원 경계는 남는다(H1).
- P08-01 원 모양 측정 방법이 정해지지 않았다. 기존 원 검출기는 Hough 원 검출이라(`experiments/p06_failure_analysis/face_mask/README.md:68`) 타원을 놓친다(`patterns/README.md:60` "흰 원 수는 하한이다… 흰 타원 익명화가 있다"). 이 검출기로 분포를 재면 원 쪽으로 치우친다(H1).

### 4. 사실 주장

| 주장 | 위치 | 원자료 | 판정 |
| --- | --- | --- | --- |
| 얼굴 노출 REAL 학습 0.4%, GEN 학습 64.5% | `phase_8:11` | `patterns/README.md:57-58`(8/2,100, 1,084/1,680) | 일치 |
| GEN 오류율 1.7% 대 0.24%, Fisher p = 0.005 | `DB-06:10` | `patterns/README.md:35`(8/469, 2/851) | 일치 |
| 흰 원 전환율 7.6% [5.7, 9.5], 두 의존 확정 | `DB-06:11` | `face_mask_ci/README.md:42`, `:48-49` | 일치 |
| 흰 원 REAL 평가 31%, 학습 25%, GEN 65% | `DB-06:16-19` | `patterns/README.md:54-58`(30.7%, 24.5%, 64.5%) | 반올림 일치 |
| 합성 원 = 얼굴 상자 × 1.2 | `DB-06:32` | `configs/face_mask_ci.yaml:22` | 일치 |
| 학습 설정(SigLIP frozen + MLP, 10 epoch, seed 42) | `phase_8:30` | `configs/primary.yaml` | 일치. 단 `output.checkpoint_dir`도 바뀌므로 "익명화만 켠다"는 엄밀히는 아님(H8) |
| `scripts/p06_patterns.py` 존재 | `phase_8:35` | `scripts/` 목록 | 일치 |

### 5. 기록

- work log Decisions에 소유자 결정·근거·대가가 한국어로 있다(`work_log.md:157`). Next steps도 갱신됐다(`:178`). `:123`의 "Open으로 올렸다"는 당시 사실 기록이라 문제 없다.
- CHANGELOG 행(`CHANGELOG.md:33`)은 소유자 결정과 근거 링크를 담는다.
- HANDOFF 다음 작업 1번(`HANDOFF.md:20-23`)은 P08 승인 대기·artifact 비덮어쓰기·P07 의존을 정확히 적는다.
- 결정 반영 목록(`DB-06:61-65`)에 `sot.md`가 없다(C1과 같은 원인).

## Issues / Risks

### Blocking

1. **C1 결정 반영 누락** — `docs/sot.md:45-55`(버전 로그 v1.4 행 없음), `docs/plan/00_index.md:23`, `README.md:25`, `README.md:87`.
2. **C2 익명화 규격의 checkpoint 결합·하류 전달 계약 없음** — `phase_8:40-44` 대비 `src/evaluate.py:97-105`, `src/calibrate.py:39-42`, `src/score.py:37-39`.
3. **C3 실패·채택 분기 없음** — `phase_8:46-52` 대비 `plan/00_index.md:14`.

### Hardening (비차단)

- **H1 원 규격 측정·정합 기준** (`phase_8:21-22`): REAL 무작위 표본을 사람이 타원으로 주석해 재고(Hough 검출기 금지), 크기는 이미지 너비만이 아니라 K-Fashion 사람 rect 또는 머리 크기 대비로도 잰다(DB-06:47은 "얼굴 대비 크기"라 했음). "맞춘다"의 판정 기준(예: 축비·크기 분위수 허용폭, fill 값, 경계 폭)을 측정 전에 적는다. 합성 원에 경계 처리(안티에일리어싱·JPEG 재인코딩)를 할지 P08-01에서 정한다.
- **H2 재현율 관문 정의** (`phase_8:23-24`): GEN 100장이면 얼굴 보임은 약 65장이라 80% 점추정의 95% 구간 폭이 ±10%p 안팎이다. 판정을 점추정·구간 하한 중 무엇으로 할지, 라벨러(DB-05처럼 에이전트 1차 + 소유자 확인), YuNet 상자를 보지 않는 블라인드 라벨링, "보이는 얼굴" 정의(측면·부분·최소 크기), seed를 적는다. threshold(0.9)·`min_size_ratio`(0.04, `face_mask_ci.yaml:17`, `:20`)를 고정할지 조정할지도 정하고, 조정한다면 별도 표본에서 재현율을 다시 잰다. test GEN(sd35 포함)도 따로 보고한다.
- **H3 다중 얼굴**: P06-02c는 최고 score 상자 하나만 쓴다(`face_mask_ci.yaml:21`). 익명화는 threshold를 넘는 모든 얼굴을 가리는지 명시한다.
- **H4 REAL의 기존 원과 검출 겹침** (`phase_8:29`): "REAL의 기존 원은 건드리지 않음"은 추론 시 원 검출기가 없으므로 그대로는 검사할 수 없다. P08-01에서 기존 원 REAL에 대한 YuNet 검출률을 재고, 검출 상자가 기존 원과 겹칠 때의 규칙(그냥 칠함/건너뜀)을 정해 그 규칙을 테스트한다.
- **H5 2×2 평가로 원인 분리** (`phase_8:31`): baseline checkpoint를 익명화 입력으로, 새 checkpoint를 원본 입력으로도 평가해 "재학습 효과"와 "입력 변화 효과"를 나눈다(P08-05(c)는 새 모델 쪽만 다룸).
- **H6 사전 고정 순서** (`phase_8:34`): P08-05 진단 config와 C3 채택 규칙을 P08-03 학습 결과를 보기 전에 커밋한다. 현재 문구 "실행 전"은 P08-03/04 지표·오답을 본 뒤 고정하는 것을 허용한다.
- **H7 "원본 baseline 재현값"의 뜻** (`phase_8:31`): 기존 checkpoint 재평가인지 재학습인지 적는다. 재학습 결정성은 입증되지 않았다(`work_log.md:149`, V1).
- **H8 새 config·출력 경로 명명**: 학습 config(예: `configs/anonymized.yaml`, `output.checkpoint_dir: checkpoints/anonymized`), calibration config(현 `configs/calibration.yaml:3`은 `experiments/p05_calibration`에 쓰므로 그대로 쓰면 P05 artifact를 덮어씀), 실험 기록 경로(`experiments/p08_…`)를 계획에 적는다.
- **H9 config 중복 분류** (`phase_8:42`): `configs/face_mask_ci.yaml`의 `face_detector` 블록은 사전 고정된 진단 스냅샷이므로 `anonymize.yaml`과의 중복은 "필요에 의한 독립"으로 명시하고, 기존 파일은 고치지 않는다고 적는다. 구현 시 `sot.md` §2에 익명화 규격 소유 행을 추가한다.
- **H10 얼굴 좌표 CSV 계보** (`phase_8:27`, `:43`): 키(image_id + 이미지 sha256 + 검출기 sha256 + 검출 파라미터 해시), "검출 안 함"과 "얼굴 없음"의 구분(얼굴 없는 행도 명시 기록), 저장 위치·추적 여부, 행 누락 시 거부를 정한다.
- **H11 추론 계약 세부** (`project.md:772`, `:778`): YuNet 파일 누락·sha 불일치 시 익명화 없이 점수를 내지 않고 거부(fail closed), API 응답에 익명화 정보(예: 가린 얼굴 수)를 넣을지, `model_version`이 checkpoint·calibration·익명화 규격 조합을 식별하는 규칙을 P08 계약 절에 넣는다.
- **H12 DB-06 후속 고려와의 정합**: DB-06은 "P06-02c 개입 실험을 다시 돌려"(`DB-06:46`)라고 했지만 P08-05 후보(`phase_8:35-37`)에는 그대로는 없다. 대체 근거를 적거나 포함한다(예: 익명화 원을 회색으로 바꿨을 때 변화).
- **H13 인덱스 표시**: `decision_briefs/00_index.md:9` DB-03 행에 "DB-06으로 대체(2026-10-11)", `DB-06:4` Related phase에 P08.
- **H14** `plan/00_index.md:19` 상세 문서 목록에 `phase_8_face_anonymization.md` 추가.
- **H15 효과 측정의 한계 명시**: DB-06 C의 주 동기인 "얼굴이 보이는 실사의 FN"은 P08-06 holdout 없이는 측정되지 않는다(`DB-06:22`). 완료 조건에서 이 점을 한계로 적는다(게이트 여부는 Q3).
- **H16 미검출 측면 얼굴**: 익명화 후에는 "보이는 얼굴 = YuNet이 놓친 얼굴"만 남아 그것이 더 강한 GEN 단서가 될 수 있다. P08-05(a) 집계에서 "미검출이지만 얼굴 보임"(H2 표본 라벨 재사용)을 따로 본다.

### 소유자 확인이 필요한 사양 문제 (CLAUDE.md §1)

- **Q1** §15(이미지 전처리)에 학습·평가 얼굴 익명화를 넣을까?
  - A: §15에 조항을 넣고 §22와 상호 참조(추천: 학습 전처리의 정본 위치가 §15).
  - B: §22에만 두고 §15는 그대로("최초 baseline" 한정으로 읽음).
- **Q2** 제품 의미·데모 표시를 어떻게 할까?
  - A: §1·README에 "얼굴 영역은 점수에 반영하지 않음"을 명시하고, 데모 미리보기는 원본을 보이며 응답에 익명화 여부만 표시.
  - B: 데모가 익명화된 이미지를 보여 점수 입력을 그대로 공개.
  - C: P07에서 정한다(지금은 한계 문구만 갱신).
- **Q3** 얼굴이 보이는 실사 holdout(P08-06)을 게이트로 쓸까?
  - A: 게이트 아님 — P07은 P08 artifact로 진행하고 holdout 결과는 사후 보고.
  - B: P07 공개 데모는 holdout 측정 뒤로 미룬다.
- **Q4** (C3 관련) P08 결과가 baseline보다 나쁘면?
  - A: 사전 규칙(예: Test A/B ROC-AUC가 §20 기준 이상이고 P08-05 단서 판정이 "해소")을 만족할 때만 primary 교체, 아니면 baseline 유지 + 소유자 보고.
  - B: 규칙 없이 P08-05 뒤 소유자가 결정.

## Outstanding items

- 작업 트리 clean, HEAD `6f0f383`. 이 기록 파일만 추가했다(미커밋).
- P08은 소유자 승인 대기다. C1–C3은 문서 수정만으로 닫히며, P08 착수 전에 닫는 것을 권한다.

## 재현

```bash
cd /mnt/f/devel/Tracepecter
git show 6f0f383
grep -rn -i '무처리\|DB-03' README.md docs/plan/00_index.md docs/decision_briefs/00_index.md
sed -n 43,56p docs/sot.md
sed -n 40,52p docs/plan/phase_8_face_anonymization.md
sed -n 97,105p src/evaluate.py; sed -n 36,42p src/calibrate.py; sed -n 36,40p src/score.py
sed -n 53,60p experiments/p06_failure_analysis/patterns/README.md
```

## 2차 검증 (2026-10-11, 커밋 `a412f74`)

### 대상·방법

- 대상: 커밋 `a412f74`. 1차 C1–C3·H1–H16 반영과 소유자 결정 Q1–Q4(모두 추천안)의 반영. 작업 트리 clean에서 시작했다.
- 방법:

```bash
git show --stat a412f74
git show a412f74 -- docs/project.md docs/sot.md README.md docs/plan/00_index.md docs/decision_briefs HANDOFF.md CHANGELOG.md docs/daily_logs
cat -n docs/plan/phase_8_face_anonymization.md
grep -n 'checkpoint_sha256' experiments/p05_calibration/calibration.json
grep -n '얼굴 익명화\|입력 전처리' docs/project.md
grep -n '승인 대기' docs/decision_briefs/DB-06_P06_face-exposure.md docs/plan/*.md HANDOFF.md
```

### 1차 조건 재확인

| 항목 | 근거 | 판정 |
| --- | --- | --- |
| C1 sot 버전 로그 | `sot.md:3`(최종 갱신 2026-10-11), `sot.md:56`(project.md v1.4 행) | 닫힘 |
| C1 페이즈 색인 비고 | `plan/00_index.md:23`(DB-03을 DB-06 C가 대체) | 닫힘 |
| C1 README | `README.md:25`, `README.md:87`(현 baseline 무처리, P08 이후 익명화, 얼굴 영역 미반영, 미검출 얼굴 잔존) | 닫힘 |
| C2 checkpoint 결합 | `phase_8:73`(규격 전체 + sha256 저장, 하류는 checkpoint 규격만 사용, 누락·불일치·YuNet sha 불일치 시 거부) | 닫힘. 단, 같은 문장 안의 판별 문제는 N2 |
| C3 채택 규칙 | `phase_8:57-59`(§20 기준 + "단서 해소"일 때만 primary 교체), `:50`·`:87`(학습 전 커밋·git 순서 확인) | 닫힘. 단, 비채택 분기의 하류 영향은 N1 |

Hardening 반영: H1 `:29-32`, H2 `:33-37`, H3 `:40`, H4 `:38`·`:42`, H5 `:51`, H6 `:50`·`:87`, H7 `:63`, H8 `:61-64`, H9 `:70-72`, H10 `:74-77`, H11 `:78-81`, H12 `:55`, H13 `decision_briefs/00_index.md:9`·`DB-06:4`, H14 `plan/00_index.md:19`, H15 `:91`, H16 `:53`. 모두 반영됐다.

사실 확인: baseline checkpoint sha `151244…`(`phase_8:22`)는 `experiments/p05_calibration/calibration.json:5`와 일치한다. YuNet sha `8f2383e4…`는 `configs/face_mask_ci.yaml:16`과 일치한다.

소유자 결정 반영: Q1 `project.md:530`(§15), `:780`(§22 → §15 참조). Q2 `project.md:835`(§23), `README.md:87`. Q3 `phase_8:66`. Q4 `phase_8:57-59`. work log `work_log.md:170-174`에 결정과 근거가 한국어로 있고, CHANGELOG `:34`와 HANDOFF `:20-24`가 서로 맞다.

### 새 발견

**N1 (차단) — 비채택 분기와 §22·P07의 충돌**

- `phase_8:59`: 채택 규칙을 만족하지 못하면 "baseline을 유지"한다.
- `project.md:780`(§22): 추론은 조건 없이 "점수를 계산하기 전에 … 흰 원으로 가린다"이고, "학습·평가와 똑같은 전처리"를 쓴다. §15(`:530`)는 "P08 이후 모델은"으로 한정했지만 §22에는 한정이 없다.
- `plan/00_index.md:14`: P07은 "새 checkpoint·calibration artifact"를 선행 조건으로 둔다.
- 비채택이면 P07은 다음 중 하나가 되어 어느 쪽이든 사양을 어긴다.
  - baseline을 원본 입력으로 서빙하면 §22 위반.
  - baseline에 익명화 입력을 넣으면 "학습·평가와 똑같은 전처리" 위반.
  - 새 checkpoint를 쓰면 채택 규칙 위반.
- 사양 문서 사이의 모순이므로 검증자가 고르지 않는다(아래 Q5).

**N2 (차단) — fail closed와 "규격 없음 = 원본 경로"의 판별 불가**

- `phase_8:73`은 "규격이 없거나 … 거부한다"고 한 뒤, 같은 문단에서 "baseline checkpoint는 규격이 없으므로 원본 입력 경로로 동작"한다고 한다.
- 같은 관측("checkpoint config에 규격 없음")에 결과가 둘이다. 그러면 규격이 빠진 익명화 checkpoint가 조용히 원본 경로로 평가된다. C2가 막으려던 실패가 그대로 남는다.
- 판별 규칙이 필요하다. 예:
  - 하류 도구(evaluate·calibrate·failure_analysis)에서는 키가 없으면 원본 경로로 둔다(기존 checkpoint 호환). 키가 있는데 내용·sha가 틀리면 거부한다.
  - score CLI와 API는 §22에 따라 규격이 없으면 거부한다.
  - 새 학습 config에는 익명화 키를 항상 명시한다(규격 또는 명시적 `null`). `configs/anonymized.yaml`로 만든 checkpoint에 규격이 없으면 학습 단계에서 거부한다.
- 이 규칙은 P08-02 검증 목록(`phase_8:44-49`)의 "checkpoint 결합 계약 위반 시 거부" 셀에 양방향으로 넣어야 한다.
  - 거부 방향: 키는 있고 sha 불일치, score·API에서 규격 없음.
  - 통과 방향: 하류 평가에서 baseline 키 없음.

**§22 Output 예시에 `faces_anonymized`가 없는 점 — 모순 아님(비차단)**

- §22 Output(`project.md:767-776`)은 예시다. 같은 절이 "상세 계약은 P08에서 정하고 P07에서 구현"(`:780`)으로 세부를 위임했고, 계획이 필드를 확정했다(`phase_8:80`).
- §23(`:835`)의 표시 요구는 이 필드로 충족된다. 필드를 더하는 변경이라 기존 필드와 충돌하지도 않는다.
- 다만 정본이 계획에만 있는 상태다. P07에서 API를 구현하는 커밋에 §22 예시와 `README.md:65-72` 예시를 함께 갱신하고 sot 버전 로그에 남기기를 권한다. `model_version: "v0.1"` 예시도 같은 시점에 바꾼다(H17).

### 2차 Hardening (비차단)

- H17: 위 §22/README 예시 갱신 시점 명시(P07 완료 조건에 넣기).
- H18 `DB-06:63`: P08 계획 "(승인 대기)" → "(검증 합격 후 착수)" 등 현행 상태로.
- H19 `project.md:530`: 익명화 문단이 "강한 augmentation…"(`:528`)과 "특히 blur…"(`:532`) 사이에 들어가 하나의 주의 문단을 끊는다. `:532` 뒤로 옮기면 읽기가 낫다(의미 변화 없음).
- H20 `phase_8:31`: 크기 맞춤이 중앙값 하나뿐이다. 분위수(예: 25·75%)도 같은 허용폭으로 보거나, 이미지 너비 기준 외에 사람 rect 대비 크기를 보조 지표로 보고한다. 경계 폭 "같은 폭"에도 허용폭을 `anonymize_measure.yaml`에 적는다.
- H21 `phase_8:37`: 양성이 80장 미만이면 관문 미달인지 표본 추가인지를 적는다(150장이면 기대 양성 약 97장이라 드물다).

### 소유자 확인 (CLAUDE.md §1)

- **Q5** P08 채택 규칙을 통과하지 못하면 P07은?
  - A: P07을 보류하고 P08을 다시 돈다(검출 보강·원 규격 조정). §22는 그대로 둔다.
  - B: §22에 "채택된 익명화 모델에 한함"을 넣는다. 비채택이면 P07은 baseline을 원본 입력으로 서빙하고, 데모와 README에 얼굴 단서 한계를 표시한다.
  - C: 결과를 보고 그때 소유자가 정한다. 대신 §22와 P07 선행 조건에 "P08-06 판정 후 소유자 결정"을 명시한다.
  - 검증자 의견: 채택 규칙을 먼저 고정한 취지와 맞는 것은 A 또는 B다. C는 사전 고정의 의미를 약하게 한다.

### 2차 판정

**조건부 합격** — N1(소유자 결정 Q5와 그에 맞춘 §22·`plan/00_index.md:14`·`phase_8:59` 정합)과 N2(`phase_8:73` 판별 규칙과 P08-02 양방향 검증 셀)를 닫으면 합격이다. 두 조건 모두 문서 수정으로 닫히며, P08-01(이미지 측정)은 N1·N2와 무관하므로 소유자가 원하면 먼저 시작해도 된다.

## 3차 검증 (2026-10-11, 커밋 `397abf2`)

### 대상·방법

- 대상: 커밋 `397abf2`. N1·N2, H17–H21, 소유자 결정 Q5 = A의 반영. 작업 트리 clean에서 시작했다.
- 방법:

```bash
git show --stat 397abf2
git show 397abf2 -- docs/project.md docs/plan docs/decision_briefs HANDOFF.md docs/daily_logs CHANGELOG.md README.md docs/sot.md
grep -n 'null\|score CLI' docs/plan/phase_8_face_anonymization.md
sed -n 526,536p docs/project.md
```

### 2차 조건·Hardening 재확인

| 항목 | 근거 | 판정 |
| --- | --- | --- |
| N1 비채택 분기 | `phase_8:66`: primary를 교체하지 않고, P07 대기, P08 재시도, 재실패면 소유자에게 다시 묻는다. §22는 바꾸지 않는다. `plan/00_index.md:14`: P07 선행 조건이 "채택된 익명화 artifact(미채택이면 P08 재시도, Q5)"다. `project.md:780`(§22)는 변경 없음. 세 문서가 이제 같은 말을 한다. | 닫힘 |
| N1 기록 | `work_log.md:179`: Q5 결정과 근거(알려진 단서가 있는 모델을 내보내지 않음, §22 유지). HANDOFF `:23`도 맞다. | 닫힘 |
| N2 판별 규칙 | `phase_8:80-84`: 키 유무로 판별한다. 새 학습 config에 키가 없으면 거부, 키는 있는데 내용·sha가 틀리거나 YuNet sha가 다르면 모든 하류가 거부, legacy는 평가 도구에서만 원본 입력, score·API는 키가 없으면 거부. `:51-56`에 양방향 검사 셀이 있다. | 닫힘. 단, `null` 분기 문제는 R1 |
| H17 | `plan/00_index.md:14`: P07 완료 근거에 `faces_anonymized`·`model_version`, §22 예시·README 갱신, 데모 표시가 들어갔다. | 닫힘 |
| H18 | `DB-06:63` "(소유자 지시: 계획 독립검증 합격 후 착수)" | 닫힘 |
| H19 | `project.md`: 익명화 문단이 "특히 blur…" 뒤, `---` 앞으로 옮겨졌다. 의미 변화 없음. | 닫힘 |
| H20 | `phase_8:31-33`: 사분위 3점 ±15%, 사람 영역 대비, 경계 ±1px | 닫힘. 측정 가능성은 H22 |
| H21 | `phase_8:40-41`: 50장씩 최대 400장까지 늘리고, 그래도 미달이면 관문 미통과 | 닫힘 |

### 새 발견

**R1 (차단) — 명시적 `null` 키 checkpoint의 score·API 처리가 정해지지 않음**

- `phase_8:81`은 새 학습 config에 "규격, 또는 명시적 `null`"을 허용한다. 그러면 키는 있지만 값이 `null`인 checkpoint가 생긴다(예: 이후 무처리 대조 재학습).
- `:84`는 score CLI·API가 "키가 **없는**" checkpoint만 거부한다고 한다. `:82`의 거부 조건은 "내용·sha256이 맞지 않음"인데, `null`에는 비교할 sha가 없다.
- 그 결과 `null` checkpoint는 score·API를 원본 입력으로 통과할 수 있다. §22(`project.md:780`, 모든 추론은 익명화)와 충돌한다. N2와 같은 종류의 미추적 분기다.
- 수정 제안:
  - `:84`를 "score CLI·API는 키가 없거나 `null`이면 거부"로 고친다.
  - `:55`에 "`null` 키 checkpoint를 score·API가 거부" 셀을 더한다.
  - 평가 도구에서 `null`은 원본 입력으로 동작하게 하고, 그 통과 방향 셀도 둔다.

### 3차 Hardening (비차단)

- **H22** `phase_8:31-32`: "사람 영역(K-Fashion 부위 rect의 합집합 높이)" 기준은 REAL에만 rect 라벨이 있다(`project.md:235`). GEN에는 라벨이 없다. 합성 원 쪽 사람 영역을 어떻게 잴지(같은 표본 수동 표시 등)를 `anonymize_measure.yaml`에 적는다. ±15% 기준을 두 정규화 모두에 걸지, 하나에만 걸지도 함께 적는다.
- **H23**: score CLI가 키 없는 checkpoint를 거부하게 되면, HANDOFF `:26`의 baseline score 실행 명령이 P08-02 구현 시점부터 동작하지 않는다. 그 구현 커밋에서 HANDOFF·README 실행 예시를 함께 고친다.
- **H24**: Q5는 P07 일정에 영향을 주는 소유자 결정이다. CHANGELOG에는 Q1–Q4 행(`CHANGELOG.md:34`)만 있다. 다음 CHANGELOG 갱신 때 Q5를 한 줄 덧붙인다(records 가이드의 "주요 변경을 이끈 사용자 결정" 규칙).

### 3차 판정

**조건부 합격** — R1(`null` 키 분기를 score·API에서 거부하고 검증 셀 추가)만 남았다. 한 줄짜리 계약 수정과 셀 한 개로 닫힌다. P08-01은 R1과 무관하다.

## 4차 검증 (2026-10-11, 커밋 `08f6ecf`)

### 대상·방법

- 대상: 커밋 `08f6ecf`. R1과 H22–H24 반영. 작업 트리 clean에서 시작했다.
- 방법:

```bash
git show --stat 08f6ecf
git show 08f6ecf -- docs/plan CHANGELOG.md HANDOFF.md docs/daily_logs docs/project.md README.md
grep -n 'null\|HANDOFF·README\|보조 척도' docs/plan/phase_8_face_anonymization.md
```

### 재확인

| 항목 | 근거 | 판정 |
| --- | --- | --- |
| R1 계약 | `phase_8:85`: score CLI·API는 키가 없거나 `null`인 checkpoint를 거부한다(§22 근거 명시). | 닫힘 |
| R1 검증 셀 | `phase_8:55`(거부: CLI·API에서 `null`), `:56`(통과: 평가 도구에서 `null`이면 원본 입력). 기존 셀(`:53-54`, `:57`)과 합쳐 키 없음·`null`·불일치·학습 config 누락의 네 분기가 모두 셀에 대응한다. | 닫힘 |
| H22 | `phase_8:31`: 관문은 이미지 너비 척도에만 건다. 사람 영역 대비 크기는 관문 없는 보조 척도로 둔다(REAL은 rect 합집합, GEN은 측정 표본 수동 표시). 방법은 `anonymize_measure.yaml`에 적는다. 이제 측정 불가능한 기준이 관문에 들어가지 않는다. | 닫힘 |
| H23 | `phase_8:86`: 구현 커밋에서 HANDOFF·README의 baseline score 예시를 함께 고친다. | 닫힘 |
| H24 | `CHANGELOG.md:35`: Q5와 `null` 키 규칙 행이 있다(한국어). | 닫힘 |

`08f6ecf`는 계획·CHANGELOG·검증 기록만 바꿨다. `project.md`, 색인, HANDOFF, work log는 3차 상태 그대로이고, 3차에서 확인한 정합이 유지된다.

### 4차 Hardening (비차단)

- **H25** `phase_8:84`: 계약 본문은 "키 없는 legacy checkpoint는 평가 도구에서만 원본 입력"이라고만 적고, `null` 키의 평가 도구 동작은 검증 셀(`:56`)에만 있다. 구현자가 본문만 읽어도 알 수 있도록 `:84`에 "키가 `null`인 checkpoint도 같다"를 한 구절 더하면 좋다. 셀이 계약을 고정하므로 차단 사유는 아니다.

### 4차 판정

**합격** — 1차부터 4차까지의 차단 조건이 모두 닫혔다. 결정 기록(DB-06 C, Q1–Q5), 사양(project.md v1.4 §15·§22·§23), P08 계획(관문·사전 고정·채택·비채택 분기·checkpoint 결합·좌표 캐시 계보·추론 계약), 기록 문서가 서로 맞는다. P08-01부터 착수할 수 있다.

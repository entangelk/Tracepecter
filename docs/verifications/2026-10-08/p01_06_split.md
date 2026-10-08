# P01-06 Dataset Split 독립검증 기록

## Subject metadata

- 검증 일자: 2026-10-08
- 요청자: 소유자(독립검증 지시 — 반증 목표)
- 검증자: 독립 검증 서브에이전트(검증 대상 작업 미작성)
- 대상 슬라이스: P01-06 Dataset split — `scripts/split_dataset.py`(그룹 split·unseen 분리·누출 검사), `tests/test_split_dataset.py`(회귀 가드 3셀), `data/metadata.csv`(REAL 3,000 + Generated 620행 병합·split 배정 결과)
- canonical spec 참조(범위 한정 스코프):
  - `docs/project.md` v1.2 — §10(Test A/B 설계), §12(메타데이터 스키마 split 열), §14(Dataset Split). 교차참조로 §13(중복 제거·동일 그룹 동일 split) 포함
  - `docs/plan/phase_1_data_pipeline.md` — P01-06 행(산출물·완료 확인) 및 비고의 P01-03·P01-05·P01-04 결과(look_group·pHash·unseen 1종 구성의 원천)
  - 절차 SoT: `docs/guides/verification.md`
- 검증 대상 소스: `scripts/split_dataset.py`·`tests/test_split_dataset.py`는 commit `523b4c8`에서 생성, `data/metadata.csv`는 commit `71bf48d`(HEAD)에서 배정. 검증 시점 `git status --short` 빈 출력(clean tree) — mutation은 clean-tree branch(`git checkout --` 복원)로 수행
- 제약 준수: 검증자 git commit/push 없음, GPU 미사용, 원천 데이터 기록 없음(mutation 복원 후 트리 클린 확인)

## Scope

1. **계약 대비 구현** — §14 그룹 기준(동일 인물·룩 그룹·source·근사중복 클러스터·generator)·70/15/15·unseen 별도 유지, §10 unseen 생성기 training 완전 배제, §12 split 열 값 도메인이 구현과 일치하는가. 계약-구현-테스트 경계 행렬 작성
2. **데이터 무결성** — `data/metadata.csv`(3,620행)가 입력 CSV 6종(`metadata_real.csv` + `metadata_gen_{qwen_image_21,z_image_turbo,sdxl,playground_25,sd35_medium}.csv`)과 행 단위 정합인지 독립 재병합 대조. 누출 검사(`check_leakage`)를 구현 미재사용 로직으로 재검증 — 구현 자체의 오탐·미탐 가능성 점검
3. **비율·층화** — source_type×category 셀별 70/15/15 재계산(unseen 제외 기준)
4. **결정성** — 동일 seed 재실행 byte 대조, 상이 seed 대조(seed 무효성 여부)
5. **테스트 코드 감사** — 3개 가드가 계약 조항을 실제로 잠그는지(under-strict/over-strict 양방향), mutation testing 4건(양방향 각 2건)으로 입증
6. **복잡도** — 시간복잡도·무한/비결정 루프 부재
7. **계약 갭** — 계약이 침묵하지만 코드가 강제하는 동작 명시
8. 스팟 체크 — 이미지 실물 존재(`~/data/tracepector/images/`)

## Methodology

- 계약 스코프 먼저 확정 후(`verification.md` §"Verify the spec/implementation/test/fixture stack as one whole") §10·§12·§14·계획서 P01-06 행을 정독하고 경계 행렬을 먼저 작성, 이후 코드·데이터 대조.
- 데이터 무결성·누출·비율: `split_dataset.py` 코드를 전혀 재사용하지 않는 독립 스크립트(순수 표준 라이브러리, `/tmp`에 배치)로 다음을 검사:
  - 병합 정합 — 6개 입력 CSV를 순서대로 읽어 `(source_type, image_id)` 키 집합이 출력과 완전 일치하는지, 11개 비-split 필드가 입력→출력에서 불변인지, 입력의 split 열이 전부 빈 값이었는지, 헤더 12열 순서 일치.
  - 누출 — REAL은 `look_group → split 집합` 직접 그룹화(집합 크기 >1 = 누출), 빈 look_group 행 카운트, 다중 스타일에 걸친 look_group의 단일 split 여부. unseen은 ①`generator == sd35_medium` 행이 전부 `test_unseen`인지 ②`test_unseen` 행이 전부 sd35_medium인지 ③standard split(train/val/test)에 sd35_medium 부재. gen `(generator, image_id)` 전역 유일성.
  - 비율 — 전체·source_type별·(source_type, category) 8개 셀별 train/val/test 비율(test_unseen은 §14 "별도" 예산에서 제외한 standard 기준) 재계산, ±5pp 허용 기준.
  - split 값 도메인 — {train, val, test, test_unseen} 외 값 부재.
- 결정성: 스크립트를 Docker(`docker compose run --rm dev`)로 재실행(입력 6종 동일 순서)해 `--seed 42`·`--seed 7` 두 출력을 `data/metadata.csv`와 `cmp` byte 비교 후 임시 파일 삭제.
- 테스트 감사 + mutation testing: pre-flight로 `git status --short` 빈 출력 확인(클린) 후 4건의 mutation을 각각 적용→`tests/test_split_dataset.py`만 실행→어떤 셀이 재실패했는지 기록→`git checkout -- scripts/split_dataset.py` 복원→클린 확인. 완료 후 전체 스위트 `tests/` 1회 실행.
- 이미지 스팟 체크: metadata.csv에서 무작위 12행 추출(`random.seed(1)`)해 `~/data/tracepector/images/` 하위 실물 존재 확인(`data/images` 심볼릭 링크 경유).

## Findings

### 1. 계약 대비 구현 — 경계 행렬

| # | 계약 조항 (출처) | 방향 | 구현 (file:line) | 테스트 셀 | 셀 상태 |
|---|---|---|---|---|---|
| 1 | 70/15/15 (§14) | fire | `split_dataset.py:31` `SPLIT_RATIO=(0.70,0.15,0.15)`, `:74-81` 셀 결손 최대 split에 그룹 배정 | `test_group_split_no_leakage_and_ratios:57-63`(±5pp) | 채움 (M4 입증) |
| 2 | 동일 인물·룩 그룹 단위 split (§14, §13 "동일 그룹 → 동일 split") | fire | `group_key` real 분기 `:41-42`(`real:<look_group or image_id>`), `check_leakage:104-111` | `test_same_look_group_stays_together:84-93` | 채움 (M1 입증) |
| 3 | 근사중복 클러스터 단위 split (§14, §13) | fire | pHash 클러스터가 P01-05에서 `look_group`에 기입 → #2와 동일 경로 | #2 셀 + 데이터 재검증(그룹 2,929개 전수 단일 split) | 채움 (데이터로 입증) |
| 4 | generator 단위 (§14) | fire | `group_key` gen 분기 `:43`(`gen:<generator>:<image_id>`) | `test_group_split_no_leakage_and_ratios`(gen 80행 fixture) + 데이터 재검증 | 채움 |
| 5 | source 단위 (§14; 계획서 P01-06 행은 "source_domain" 명시) | fire | real/gen 접두어로 `source_type`은 그룹 키에 반영(`:41-43`) — 단 `source_domain`은 코드에 부재(grep 0건) | 전용 셀 없음 | **공석 — 아래 H5 참조(비차단 사유 기술)** |
| 6 | unseen generator 별도 유지·training 완전 배제 (§10, §14) | fire | `main:130-133` unseen 전량 `test_unseen` 배정, `check_leakage:112-114` 혼입 검사 | `test_unseen_generator_separated:66-81` | 채움 (M2 입증) |
| 7 | §12 split 열 값 train/val/test(+별도 unseen test) | literal | `test_unseen` 리터럴(`:11,106,113,133`), 나머지 `SPLITS`(`:32`) | `test_unseen_generator_separated`의 리터럴 사용 + 데이터 재검증(규격 외 값 0) | 채움 |
| 8 | 누출 검사 통과 시 정상 종료·위반 시 차단 (계획서 P01-06 완료확인) | NOT fire(정상 오탐 없음) | `check_leakage:101-115`, `main:138-141`(위반 시 exit 1) | `test_group_split_no_leakage_and_ratios:54`, `test_unseen_generator_separated:76` | 채움 (M3 입증) |
| 9 | 결정성(재현성) | — | `rnd = random.Random(seed)`(`:54`)은 **미사용** — 그리디 알고리즘 전체가 난수 없이 결정적 | `test_group_split_no_leakage_and_ratios:50-51` | 채움 (사실상 자명) |

- §10 Test A(standard test에 학습 동일 생성기 포함 허용): standard split에 train 4종(qwen_image_21 124·z_image_turbo 124·sdxl 124·playground_25 124)+REAL 3,000 배정 — 허용 조항 위반 없음.
- 행렬의 유일한 공석은 #5이며, 이는 아래 Issues-H5에서 비차단 사유와 함께 기술한다(현 데이터에서 source_domain 단일(kfashion)·그룹 키 조합원 누락의 실패 방향이 "과그룹화"(누출 안전 쪽)이므로 계약이 요구하는 방향성을 위반하지 않음).

### 2. 데이터 무결성 — 전부 통과 (독립 로직)

- 병합 정합: 출력 3,620행 == 입력 6종 합계(3,000+124×5). `(source_type, image_id)` 키 집합 완전 일치(중복·누락 0). 11개 비-split 필드 불변 위반 0건. 입력 6종의 split 열은 전부 빈 값(배정 전 상태 확인). 헤더 12열 §12 v1.2 순서 전 파일 일치. 출력 행 순서는 REAL→gen 4종→sd35_medium(unseen 후치)로 `main:135-136`(`split_rows + unseen_rows`) 구조와 부합.
- 누출 재검증(구현 미재사용): REAL `look_group` split 누출 **0** — 그룹 2,929개(크기 분포 1×2,869·2×54·3×3·4×2·6×1). 빈 look_group 행 **0**(빈 값이면 image_id 폴백 단독 그룹이 되어 누출 보호가 사라지는데, 그런 행이 없음 — P01-05 100% 커버 주장과 정합). 다중 스타일에 걸친 look_group 35개(P01-05 이중 라벨링 캡처분) 전원 단일 split. sd35_medium는 124/124 전량 `test_unseen`, `test_unseen`에 sd35_medium 외 행 0, standard split에 sd35_medium 0행, REAL의 `test_unseen` 행 0. gen `(generator, image_id)` 전역 유일(그룹 키 단독성 전제 성립).
- 구현 오탐 가능성 점검: `check_leakage`의 누출 판정은 `group_key`에 전적으로 의존하는데, real 분기가 `look_group or image_id` 폴백(`:42`)을 가지므로 "빈 look_group + 그룹 흩어짐" 조합에서는 미탐이 가능하다 — 실데이터에서는 빈 look_group 0건으로 기각. 반대로 test_unseen 행을 그룹 스캔에서 제외(`:106-107`)하므로 "REAL이 test_unseen에 배정되고 look_group이 표준 split과 겹치는" 조합도 미탐 — 실데이터 REAL test_unseen 0건으로 기각(구조적 관찰는 H2).
- 스팟 체크: 무작위 12행(REAL 8·GEN 4, split 4종 포함) 전부 실물 존재.

### 3. 비율·층화 — 통과

- REAL 3,000: train 2,100(70.0) / val 452(15.1) / test 448(14.9).
- Generated(standard 496행): train 348(70.2) / val 76(15.3) / test 72(14.5). test_unseen 124(별도).
- (source_type, category) 8개 셀별 최대 편차 **0.5pp**(real 4셀 0.1pp, generated 4셀 0.5pp) — 구현 docstring·커밋이 주장하는 셀별 층화가 실데이터에서 성립. 주: 파일 전체 기준으로는 train 67.6%처럼 보이나 이는 test_unseen 124행이 분모에 포함된 때문으로, §14는 unseen을 "별도로" 예산 밖에 두므로 standard 기준이 계약 부합 해석이다.

### 4. 결정성 — 통과(강건한 수준)

- `--seed 42` 재실행 출력이 `data/metadata.csv`와 **byte 동일**(`cmp` 통과).
- `--seed 7` 재실행 출력도 seed 42와 byte 동일 — `--seed`가 출력에 아무 영향이 없음(알고리즘에 난수 소비가 없음). 결정성은 계약 요구를 초과 충족하나, 인수가 사실상 no-op이라는 점은 H1 참조.

### 5. 테스트 코드 감사 + mutation testing — 4건 전건 재실패, 짝 성립

pre-flight `git status --short` 빈 출력 확인 후 수행. 각 mutation 후 `docker compose run --rm dev python -m pytest tests/test_split_dataset.py -q`만 실행, `git checkout -- scripts/split_dataset.py` 복원, 복원 후 클린 확인(4회 모두).

| Mutation | 방향 | 내용 | 재실패 셀 |
|---|---|---|---|
| M1 | under-strict(그룹 응집) | `group_key` real 분기에서 look_group 무시(`real:<image_id>`) | `test_same_look_group_stays_together:93` 1셀 |
| M2 | under-strict(unseen 분리, 방어 제거) | `check_leakage`의 unseen 혼입 검사 루프 제거 | `test_unseen_generator_separated:81` 1셀 |
| M3 | over-strict(정상 오탐) | 누출 판정 `len(splits) > 1` → `>= 1` | `test_group_split_no_leakage_and_ratios:54` + `test_unseen_generator_separated:76` 2셀 |
| M4 | over-strict(비율 왜곡) | `SPLIT_RATIO` (0.85, 0.10, 0.05) | `test_group_split_no_leakage_and_ratios:61` 1셀 |

- M1 관찰(`verification.md` §"When a mutation does not bite"의 층 분리 분석): M1 상태에서 test 1 fixture의 알고리즘 출력에는 실제로 18개 look_group이 복수 split에 분산했으나(독립 시뮬레이션으로 확인), `test_group_split_no_leakage_and_ratios:54`의 `check_leakage(split_rows) == []`는 **통과**로 유지되었다 — 변이된 `group_key`를 `check_leakage`도 공유해 분산 자체가 관측 불가가 되기 때문. 결함은 `test_same_look_group_stays_together`(group_key→check_leakage 경로를 직접 고정)이 잡았다. 설계상 정상이지만 test 1의 누출 어설션이 group_key와 독립적이지 않음을 보여준다(→ H7).
- 양방향 성립: under-strict 2건(M1·M2)·over-strict 2건(M3·M4) 각각 최소 1셀 재실패. over-strict 방향(정상 케이스 오탐 억제)은 M3에서 2개 셀이 나눠 잡아 "should NOT fire" 경계가 이중으로 잠겨 있다.
- 복원 후 전체 스위트: `tests/` 25 passed(5.83s).

### 6. 복잡도 — 양호

- `stratified_group_split`: 그룹화 O(n) + 정렬 O(G log G) + 배정 루프 O(G·3·t)(t=그룹이 건드리는 셀 수, 실데이터 상수) = 전체 **O(n + G log G)**, 공간 O(n). 반복 전체 스캔 없음(셀 카운트는 인덱스 조회). 재시도·폴링·재귀·입자 의존 무한 루프 부재. tie-break가 split명 사전순(`:81`)으로 결정적.
- `check_leakage`: O(n) 단일 패스 2회.

### 7. 계약 갭 관찰 (계약 침묵·코드 강제)

- **셀별 층화**: §14는 전역 70/15/15만 규정하나 구현은 (source_type, category) 셀별 결손 기준 배정을 강제한다(`:72-81`, docstring `:12`). 실데이터 0.5pp로 양호하나 계약엔 없는 동작 — H4.
- **test_unseen의 gen-only 구성**: §10의 예시 블록은 Test B의 TEST에 "Real images + Generator D only"를 함께 표기하지만, 구현은 test_unseen을 unseen 생성기 행으로만 구성한다(REAL은 standard split에만). §12의 "(+별도 unseen test)"·계획서 P01-04 비고("sd35_medium, Test B 전용")는 실물 배분을 규정하지 않는다. 평가 시점에 standard test의 REAL 448행을 Test B 음성으로 재사용하는 구성이 가능하므로 §10의 핵심 전제(해당 생성기의 training 완전 배제)는 위반되지 않았으나, Test B 평가 구성 방법 자체가 계약 미고정 — H3.

## Issues / Risks

### Blocking (contract obligations)

- 없음. 경계 행렬에서 계약이 요구하는 fire/NOT-fire 경로 중 테스트·데이터 검증으로 잠기지 않은 셀은 없고(#5 공석의 비차단 사유는 H5), 스펙 내부 모순·리터럴 불일치·누출·비율 위반 모두 기각됐다.

### Hardening recommendations (non-blocking)

- **H1 — `--seed` no-op·사용되지 않는 `rnd`**: `split_dataset.py:54`의 `rnd = random.Random(seed)`은 이후 사용되지 않고(전체 파일에서 `random`의 유일 소비), `--seed` 인수(`:122`)는 출력에 영향을 주지 않는다(seed 42/7 출력 byte 동일로 입증). 결정성에는 유리하나 호출자가 seed 교체로 다른 split을 기대하는 오해의 씨앗. 제거하거나 docstring에 "알고리즘은 결정적 그리디, seed는 예비 인수"로 명시할 것.
- **H2 — `check_leakage`의 test_unseen 면제 스코프**: `:106-107`이 test_unseen 행을 그룹 누출 스캔에서 제외하고, 반대 방향(비-unseen 행의 test_unseen 배정)도 검사하지 않는다. `main`의 구성(unseen 파티션이 generator 조건 전용, `:130-133`)이 두 사태를 봉쇄하고 실데이터에서도 0건이었으나, 함수 단독 사용 시에는 관측 사각. test_unseen을 그룹 스캔에 포함하거나 조성 불변식(REAL 미포함·unseen 전량)을 주장에 추가할 것.
- **H3 — Test B 평가 구성 계약 미고정**: test_unseen이 gen-only인데 §10 예시는 TEST에 Real images를 병기. "평가 시 standard test의 REAL을 Test B 음성으로 재사용"인지 "test_unseen에 REAL 샘플을 별도 배정"인지 소유자가 §10 또는 §14에 고정하고, 채택 시 대응하는 구성 검사를 추가할 것. 본 슬라이스는 배정 결과에 대한 계약 위반이 없으므로 차단하지 않는다.
- **H4 — 셀별 층화의 계약 부재**: source_type×category 셀별 70/15/15이 코드가 강제하는 동작인데 §14는 침묵하고 대응 회귀 셀도 없다(전역 비율 셀만 존재). 층화를 계약에 명시하고 셀별 비율 가드를 추가하거나, 구현 상세로 남길 것 명시.
- **H5 — source 기준 그룹 키의 명칭 차이**: 계획서 P01-06행은 "source_domain"을 그룹 기준으로 명시하나 `split_dataset.py`에는 `source_domain` 문자열이 없다(grep 0건). 그룹 접두어는 `source_type`(real/gen)이다. 현 데이터는 REAL 단일 출처(kfashion)라 행동 차이가 없고, 출처가 늘어나도 look_group 값 충돌 시 과그룹화(누출 안전 방향)로만 귀결된다. 다만 계획서 문구와의 정합을 위해 real 그룹 키에 source_domain을 포함하거나 계획서 문구를 source_type으로 정정할 것.
- **H6 — `main`/CLI 오케스트레이션 무셀**: unseen 파티션·병합 순서·출력 기록·exit 1 게이트(`:118-160`)를 직접 잠그는 셀이 없다(본 검증이 임시 CSV 재실행·무결성 대조로 대체 입증). 소형 fixture로 `main`을 끝까지 돌리는 스모크 셀 추가를 권장.
- **H7 — test 1 누출 어설션의 group_key 의존**: M1에서 확인했듯 `check_leakage(split_rows) == []`는 group_key가 틀어지면 알고리즘 출력의 실제 분산을 못 본다(18개 그룹 분산 상태에서 green). 결함 자체는 test 3이 잡아 슈트 수준 방어는 성립하나, test 1에서 look_group 기준 직접 재그룹화하는 독립 어설션을 추가하면 층이 분리된다.

## Verdict

**합격**

- 근거: ① 계약-구현-테스트 경계 행렬에서 계약 요구 경로의 빈 셀 없음(유일 공석 #5는 현 데이터에서 행동 차이 0·실패 방향이 안전 쪽이라 비차단, H5로 추적). ② 데이터 무결성 — 3,620행 병합 정합(키 집합 일치·비-split 필드 불변), 누출 0(독립 로직 재검증), unseen 완전 분리(sd35_medium 124/124). ③ 비율 — 셀별 최대 편차 0.5pp(§14 70/15/15 부합, unseen은 별도 예산). ④ 결정성 — 재실행 byte 재현. ⑤ mutation 4건(under/over 양방향 각 2건) 전건 재실패, 짝 기록. ⑥ 복잡도 O(n + G log G), 무한·비결정 루프 없음. ⑦ 계약 갭 2건(H3·H4)은 명시적으로 분리·비차단 분류.
- 단, `verification.md`의 "green bar ≠ 계약 검증" 구분 원칙에 따라: 위 ②-⑤는 스위트 통과가 아니라 원천(스펙·코드·데이터) 재도출로 확보한 증거이다.

## Outstanding items

- `data/metadata.csv`는 현재 씨드 규모(REAL 3,000 + GEN 620). P01-07(Generated ≥3,000·metadata 최종화)이 남아 있어 확장 시 본 스크립트 재실행이 필요하다 — 재실행 시 비율·누출 재검증이 P01-07 완료 확인에 포함되어야 한다(그룹 수 증가로 셀별 편차 재확인 권장).
- H1~H7은 소유자 판단으로 반영 여부 결정(H3·H4·H5는 계약 문구 정정을 수반하는 후보).
- 검증 종료 시점 트리 클린(검증자 생성 파일은 본 기록뿐).

## Reproduction

```bash
cd /mnt/f/devel/Tracepecter

# 0. pre-flight(mutation 전제)
git status --short          # 빈 출력이어야 함

# 1. 회귀 가드 3셀
docker compose run --rm dev python -m pytest tests/test_split_dataset.py -q   # 3 passed

# 2. 결정성 — 재실행 byte 대조(입력 순서는 metadata.csv 행 순서와 동일)
docker compose run --rm dev python scripts/split_dataset.py \
  --inputs data/metadata_real.csv data/metadata_gen_qwen_image_21.csv \
           data/metadata_gen_z_image_turbo.csv data/metadata_gen_sdxl.csv \
           data/metadata_gen_playground_25.csv data/metadata_gen_sd35_medium.csv \
  --out .tmp_rerun.csv --seed 42
cmp data/metadata.csv .tmp_rerun.csv && rm .tmp_rerun.csv    # byte 동일

# 3. 독립 무결성·누출·비율 재검증 — split_dataset.py 미재사용 로직으로:
#    (a) 6입력·출력 (source_type,image_id) 키 집합·11필드 불변 대조
#    (b) REAL look_group→split 집합 그룹화(누출 0), 빈 look_group 0,
#        sd35_medium↔test_unseen 상호 포함 관계, 셀별 70/15/15 재계산
#    (검증 시 사용한 스크립트는 /tmp에 1회성으로 배치 — 상단 Methodology의 체크 목록으로 재작성 가능)

# 4. mutation(임의 1건 예시 — M3; 매건 복원 후 git status --short 확인)
python3 - <<'EOF'
import re, pathlib
p = pathlib.Path("scripts/split_dataset.py")
s = p.read_text(encoding="utf-8").replace("if len(splits) > 1:", "if len(splits) >= 1:")
p.write_text(s, encoding="utf-8")
EOF
docker compose run --rm dev python -m pytest tests/test_split_dataset.py -q   # 2 failed 재현
git checkout -- scripts/split_dataset.py && git status --short               # 복원·클린

# 5. 전체 스위트
docker compose run --rm dev python -m pytest tests/ -q      # 25 passed
```

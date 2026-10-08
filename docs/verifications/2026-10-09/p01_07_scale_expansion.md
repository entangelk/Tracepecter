# P01-07 전체 규모 확장·완료 확인 — 독립검증 기록

## Subject metadata

- 일자: 2026-10-09
- 요청자: 소유자(독립검증 지시 — 구현자 주장을 복사하지 않고 원천에서 재도출)
- 검증자: Claude Code 서브에이전트(독립검증자 — 검증 대상 슬라이스에 기여하지 않음)
- 검증 대상: P01-07 슬라이스 — 배치 2 생성 산출물 5종, 최종 `data/metadata.csv`, §27 Phase 1 완료 처리
- 작업 원천: commit `c50547c`(qwen b2) → `fd6d301`(z b2) → `2f2bcd4`(sdxl b2) → `ea4470a`(playground b2) → `80e1c03`(sd35 b2) → `1504e23`(최종 metadata.csv) → `0d985c0`(완료 처리 docs) — `main` 브랜치, HEAD = `0d985c0`, working tree clean
- 정준 계약: `docs/project.md` §7(데이터셋 규모, :197)·§10(Test B, :319)·§12(스키마 v1.2, :403)·§14(split, :478)·§27 Phase 1 완료 조건(:970), `docs/plan/phase_1_data_pipeline.md` P01-06/P01-07 행·결과 비고(:62, :100-101), `docs/plan/00_index.md` P01 행(:8)

## Scope

1. **완료 조건 정합** — §27 Phase 1 완료 조건 7개를 `data/metadata.csv`에서 구현 미재사용 로직으로 독립 재계산
2. **데이터 무결성** — 입력 11개 CSV(REAL 1 + GEN 씨드 5 + GEN b2 5) 대비 metadata.csv 행 정합(키 집합·비split 필드 불변), 결정성(byte 재현)
3. **누출·층화 재검증** — `split_dataset.py` 구현을 재사용하지 않는 독립 로직(REAL look_group 직접 재그룹화 포함), 비율·셀별 층화 재계산
4. **배치 2 특유** — 5종 b2 CSV 476행·카테고리 119×4·gen_ID 범위·전역 유일, sd35(unseen) test_unseen 전량
5. **중복 방지 설계 실증** — `plan_jobs` 직접 재실행으로 seed 43 스트림 실증 + seed 42 재사용 반사실 재현
6. **이미지 실물** — b2 ID 범위 파일 존재·PIL 정상·전수 MD5 유일성
7. **테스트 스위트** — 28셀 통과 + mutation(가드 물림 증명)
8. **완료 보고 문서** — 계획서 비고·인덱스·HANDOFF·CHANGELOG 수치의 재계산 대조

비고: P01-07 커밋은 데이터·문서만 변경(코드 변경 0 — `git show --stat`로 확인). `split_dataset.py`·`generate_ai.py`·테스트는 P01-06 검증 이후 불변이므로, 코드 계약은 스케일 확장 후에도 가드가 물리는지의 재확인으로 검증했다.

## Methodology

독립 재계산 스크립트는 저장소 외부 `/tmp/p0107_verify/`에 두어 저장소를 오염시키지 않았다(검증기록 외 저장소 변경 없음).

```bash
# 1) 완료 조건·무결성·누출·층화·배치2 — 독립 로직 재계산 (split_dataset.py 미재사용)
python3 /tmp/p0107_verify/verify_main.py
# 2) 생성기×split 교차표 + P01-06 시점(1504e23^) 대비 재배정 분석
python3 /tmp/p0107_verify/verify_gentab.py
# 3) 결정성 — 동일 입력으로 재실행해 byte 비교
python3 scripts/split_dataset.py --inputs data/metadata_real.csv data/metadata_gen_qwen_image_21.csv \
  data/metadata_gen_qwen_image_21_b2.csv data/metadata_gen_z_image_turbo.csv data/metadata_gen_z_image_turbo_b2.csv \
  data/metadata_gen_sdxl.csv data/metadata_gen_sdxl_b2.csv data/metadata_gen_playground_25.csv \
  data/metadata_gen_playground_25_b2.csv data/metadata_gen_sd35_medium.csv data/metadata_gen_sd35_medium_b2.csv \
  --out /tmp/p0107_verify/metadata_rerun.csv
cmp data/metadata.csv /tmp/p0107_verify/metadata_rerun.csv   # → BYTE-IDENTICAL
# 4) seed 43 스트림 실증 — plan_jobs 직접 재실행·CSV 대조·스트림 교집합·반사실
python3 /tmp/p0107_verify/verify_seedstream.py
# 5) 이미지 — b2 파일 존재·PIL 샘플·전수 MD5 중복
python3 /tmp/p0107_verify/verify_images.py
cd ~/data/tracepector/images/generated && md5sum */*.png | awk '{print $1}' | sort | uniq -d | wc -l  # → 0
# 6) 테스트
docker compose run --rm dev python -m pytest -q   # → 28 passed
# 7) mutation — pre-flight git status --short 클린 확인 후 cada 복원(git checkout -- <path>)·git diff 로 복원 확인
#    MU1: scripts/split_dataset.py check_leakage unseen 검사 제거 → tests/test_split_dataset.py
#    MO1: SPLIT_RATIO (0.70,0.15,0.15)→(0.75,0.15,0.10) → tests/test_split_dataset.py
#    MU2: scripts/generate_ai.py plan_jobs rng=random.Random(seed)→전역 random → tests/test_generate_ai.py
#    M1~M4: /tmp 사본에 결함 주입(sd35→train, gen_ID 중복, look_group 분할, category 변조) → verify_main.py
```

## Findings

### 1. §27 Phase 1 완료 조건 7개 — 전부 독립 충족 확인

| # | 조항(§27) | 재계산 결과 | 판정 |
| --- | --- | --- | --- |
| 1 | 최소 6,000 이미지 | 6,000행(REAL 3,000 + GEN 3,000, source_type 제3값 0) | 충족 |
| 2 | Real ≥ 3,000 | 3,000 | 충족 |
| 3 | Generated ≥ 3,000 | 3,000(5종 × 600) | 충족 |
| 4 | 축소된 패션 category 구성 | 4부위 정확히 {상의 1,500·아우터 1,500·원피스 1,500·하의 1,500}, 결측 0 | 충족 |
| 5 | metadata.csv 생성 | 존재·컬럼 = §12 v1.2 12필드 정확 순서 | 충족 |
| 6 | train/val/test split 완료 | train 3,780 / val 812 / test 808, 결측·규격 외 값 0 | 충족 |
| 7 | unseen_generator_test 생성 | test_unseen 600 = sd35_medium 600 전량(양방향: standard split에 sd35 0행, test_unseen에 비 sd35 0행) | 충족 |

§7 최소 목표(Real 3,000+ / Generated 3,000+ / 합계 6,000+) 동시 충족. 스키마 필드 규격 전수: REAL — label 1·source_domain `kfashion`·generator 빈·style·look_group 비빈·prompt_id 빈, GEN — label 0·source_domain/style/look_group 빈·prompt_id `f[1-6]b[1-7]v[1-3]` 전량 정합, REAL parts 도메인 위반 0.

### 2. 데이터 무결성 — 정확 일치

- 입력 11개 CSV 합 6,000행 = metadata.csv 6,000행. image_id 전역 유일(입력·출력 중복 0), 키 집합 차 0.
- **비split 필드 불변**: 6,000행 × 11필드 전수 대조 불일치 0건.
- **결정성**: 동일 11입력으로 재실행한 결과가 `data/metadata.csv`와 **byte 동일**(`cmp` 통과). 최종 산출물은 결정적 알고리즘의 정확한 산출임이 입증됨.
- P01-06 시점(`1504e23^`) 대비: 기존 3,620행 중 148행(z_image 80·sdxl 68)만 split 재배정(`test->train` 72·`train->test` 40·`val->train` 32·`train->val` 4), **REAL 0행 불변**, 기존 행 비split 필드 불변. 이는 계획서 "6,000행 split 재배정" 표현과 정합(셀 총량 변화에 따른 결정적 재계산).

### 3. 누출 재검사(구현 미재사용) — 위반 0

- REAL look_group **직접 재그룹화**(빈 값 image_id 폴백 포함): 그룹 2,929개, 복수 split 걸침 0, 빈 look_group 0(P01-05 100% 커버 주장과 정합).
- GEN (generator, image_id) 전역 유일 → 개별 그룹 구조 자체 성립. REAL test_unseen 혼입 0.
- 구현 `check_leakage`(`scripts/split_dataset.py:105-126`)과 독립 로직이 동일 결론(누출 0)에 도달 — 오탐·미탐 없음.

### 4. 비율·셀별 층화 — 계획서 주장 수치 전부 재현

- REAL: train 2,100(70.0%) / val 452(15.1%) / test 448(14.9%) — 비고 "real 70.0/15.1/14.9%" 일치.
- GEN(standard 2,400): 1,680(70.0%) / 360(15.0%) / 360(15.0%) — 비고 일치.
- 셀별(source_type×category, unseen 제외) 70/15/15 최대 편차 **0.07pp**(§14 부합, P01-06 잠금 조건 유지).
- split×source_type 내 카테고리 셰어 25% 대비 최대 편차 **0.00pp** — 비고 "셀별 층화 25%±1pp" 일치.
- 종당 600×5 확인. train 3,780/val 812/test 808 + test_unseen 600 — 계획서·인덱스·HANDOFF·CHANGELOG 수치 전부 재계산과 일치.

단, 집계 비율만으로는 드러나지 않는 **생성기×split 분포**는 아래 8항 및 Hardening H1 참조.

### 5. 배치 2 산출물 — 전부 정합

- 5종 b2 CSV 각 476행, 카테고리 119×4 정확, gen_ID 연속 범위: qwen 624-1099, z_image 1100-1575, sdxl 1576-2051, playground 2052-2527, sd35 2528-3003(커밋 메시지 범위와 일치).
- 씨드분 범위(재도출): qwen 1-124, z_image 125-248, sdxl 250-373, playground 375-498, sd35 500-623 — 각 124행·카테고리 31×4.
- 전역 유일: 씨드 620 ∪ b2 2,380 = 3,000, 교집합 0, metadata.csv gen_ID 집합과 정확 일치.
- §12 Generated 행 필드 규격(path `images/generated/<gen>/<id>.png`, label 0, source_domain/style/look_group/split 빈, prompt_id 비빈, parts-카테고리 대응) 전수 정합.

### 6. 중복 방지 설계(seed 43) 실증 — 성립

`plan_jobs`(`scripts/generate_ai.py:107-133`)는 `random.Random(seed)`로 결정적이므로 이미지 재현 시드는 CSV에 없어도 스트림을 직접 재현해 실증 가능했다. 전 생성기 5종에 대해:

- **스트림 실증**: 씨드 CSV 124행·b2 CSV 476행의 (category, prompt_id) 순서가 `plan_jobs(g, 125, 42)`·`plan_jobs(g, 476, 43)` 출력과 행 단위 전수 일치 — 기록된 행이 실제 각 스트림에서 생성됐음.
- **중복 방지**: 두 스트림의 이미지 동일성 키 (prompt, seed, width, height) 교집합 **0**(이미지 시드만의 교집합도 0).
- **반사실(설계 동기 실재)**: seed 42를 count 476으로 재사용했을 경우 생성기당 **31쌍**(원피스 블록 선두 31작업)이 씨드런과 정확 중복 — 5종 합산 155장의 완전 중복량산이 실제로 발생했을 경로임.
- **경험적 확증**: 생성 이미지 3,000장 전수 MD5 중복 0.

### 7. 이미지 실물·테스트

- 5종 디렉토리 각 600파일, b2 ID 결측 0, 무작위+경계 샘플 6장/종 PIL open·load 정상, 해상도 {832×1216, 832×832} = `SIZES` 스펙. GEN path→파일 대응 3,000/3,000. REAL 스팟 10/10 정상.
- 테스트 스위트: `docker compose run --rm dev python -m pytest -q` → **28 passed**(보고 셀 수와 일치).
- Mutation(전건 pre-flight `git status --short` 빈 확인, 복원 후 `git diff` 빈·전체 스위트 재통과로 확인):
  - MU1(unseen 검사 제거, under-strict) → `test_unseen_generator_separated` + `test_unseen_scope_guards` 재실패
  - MO1(SPLIT_RATIO 0.75/0.15/0.10, over-strict) → `test_group_split_no_leakage_and_ratios` 재실패
  - MU2(plan_jobs 비결정화, under-strict) → `test_plan_jobs_stratified_and_deterministic` 재실패
  - M1~M4(/tmp 사본 결함: sd35→train / gen_ID 중복 / look_group 분할 / category 변조) → 본 검증자 로직 각각 A7 / B2·B3·C2·E / C1 / B4 재실패 — 감사 논리 자체의 물림 증명

### 8. 완료 보고 문서 — 수치 정합, 서술 2건 미세 부정확

- `docs/plan/00_index.md:8` P01 Complete 처리 — §27 조건 7개 실제 충족(1항)과 정합. HANDOFF:8·CHANGELOG 행 수치 전부 재계산과 일치. HANDOFF:16 Test B REAL 재사용 보류(P01-06 H3) 계속 명시 — 적절.
- **부정확 1**: 계획서 결과 비고(:101) "gen_ID 전역 연속 1~3,003" — 실제로는 3개 공백(249·374·499, 씨드분 125슬롯 예약 잔여). 범위(1~3,003)·유일성 주장은 정확하나 "연속"은 부정확(H2).
- **부정확 2**: work log(2026-10-08 :85) seed 42 재사용 시 "각 카테고리 블록 앞부분" 재현 서술 — 반사실 재현 결과 첫 블록(원피스) 선두 31쌍만 중복(per_category 31≠119로 이후 블록 RNG 상태 발산). 위험의 실재성은 확증되었으나 범위 서술 과대(H3).

### 검증 불가 항목(보고 수치 재검증 불가로 명시)

- "~19s/장·~33s/장·총 ~16시간·야간 무인 진행" 등 실행 시간·운영 서술 — 산출물로 재계산 불가. 검증 대상에서 제외(파일 존재·무결성·MD5 유일성으로 대체 입증).

## Issues / Risks

### Blocking (계약 의무 위반)

- **없음.** §27 완료 조건 7개 전부 독립 충족, §7·§12·§14(잠금 해석—아래 H1)·§10 Test B 분리 모두 성립. 경계 행렬(위 1~8항)에서 계약 요구 분기의 빈 셀 없음.

### Hardening recommendations (비차단)

- **H1 — 생성기×split 퇴화, P02/P03 평가 설계 확정 전 소유자 결정 권장(최우선)**. 생성기별 분포 재계산: qwen_image_21 **600 train / 0 val / 0 test**, playground_25 **600/0/0**, sdxl 280/160/160, z_image_turbo 200/200/200(sd35 600 test_unseen). 즉 **val·test의 GEN 360행은 z_image+sdxl만**으로 구성되고 train 점유율 35.7%씩인 qwen·playground는 검증·시험에서 관측 불가능. 구조적으로 결정적 알고리즘(그룹 키 사전순: playground→qwen→sdxl→z 순 셀 결손 소진)의 귀결이며 P01-06 시점(124행 규모에서 qwen·playground 전량 train)과 동일 구조로, P01-07이 도입한 회귀는 아님 — P01-06 검증이 잠근 "GEN=개별 그룹" 해석과 source_type×category 셀 층화 계약은 준수 중임. 그러나 (a) §10 Test A의 목적("일반적인 classification 성능 측정")상 test GEN이 train GEN 구성을 대표하지 못하고, (b) 집계 비율(real/generated 70/15/15)만 보고되어 어느 기록에도 이 분포가 명시되지 않았다. 권고: cell을 (source_type, category, generator)로 확장한 재배정 또는 현 구성의 명시적 수용을 P02 평가 설계 전에 소유자가 결정. 분포 자체는 본 기록의 교차표로 문서화됨.
- **H2 — 계획서 비고 문서 수정**: "gen_ID 전역 연속 1~3,003" → "범위 1~3,003·전역 유일(예약 공백 3)" 정정(데이터 결함 아님).
- **H3 — work log 반사실 서술 정정**: 중복 재현 범위는 생성기당 첫 카테고리 블록 31쌍(전 블록 아님).
- **H4 — P01-06 계승 사항 재확인**: GEN 근사중복 pHash 점검 대규모 실행 위임(`scripts/split_dataset.py:10-11` 명시, 본 검증의 MD5 전수 유일성은 정확 중복만 커버), Test B(test_unseen)의 REAL 재사용 여부 보류(HANDOFF:16) — P02 평가 설계 시 결정 필요.

## Verdict

**합격**

- §27 Phase 1 완료 조건 7개를 구현 미재사용 재계산으로 전부 충족 확인(6,000행·REAL 3,000·GEN 3,000·4부위 카테고리·§12 v1.2 metadata.csv·split·test_unseen 600).
- 무결성: 11입력 대비 키 집합·비split 필드 완전 불변, 재실행 byte 동일, 148행 GEN 재배정은 계획된 "재배정" 범위 내(REAL 불변).
- 누출 0(독립 로직), 셀별 층화 최대 편차 0.07pp, 보고 수치 전부 재현.
- seed 43 중복 방지 설계: 스트림 실증(CSV↔plan_jobs 전수 일치)·교집합 0·반사실 31쌍/gen·이미지 MD5 전수 유일.
- 이미지·테스트(28 passed)·mutation 7건(코드 3 + 데이터 4) 전건 재실패와 짝 기록 완료.
- H1(생성기×split 퇴화)은 계약 위반이 아닌 계승된 설계 속성으로 분류하되 P02 착수 전 소유자 결정을 권고 — 본 기록에 교차표로 고정.

## Outstanding items

- `main` HEAD `0d985c0`, working tree clean(본 검증의 mutation은 전건 복원·`git diff` 빈 확인). 검증 스크립트는 `/tmp/p0107_verify/`에 존재(저장소 외).
- P01 Complete 처리로 P02(Baseline) 착수 게이트 개방. **P02 평가 설계 전 H1 소유자 결정 및 HANDOFF:16 Test B REAL 재사용 결정이 선행 권장.**
- H2·H3 문서 정정은 언제든 가능(비차단).

## Reproduction

```bash
git status --short   # clean 확인
python3 /tmp/p0107_verify/verify_main.py            # §27·무결성·누출·층화·배치2 (exit 0)
python3 /tmp/p0107_verify/verify_gentab.py          # 생성기×split 교차표·재배정 분석
python3 scripts/split_dataset.py --inputs data/metadata_real.csv data/metadata_gen_qwen_image_21.csv data/metadata_gen_qwen_image_21_b2.csv data/metadata_gen_z_image_turbo.csv data/metadata_gen_z_image_turbo_b2.csv data/metadata_gen_sdxl.csv data/metadata_gen_sdxl_b2.csv data/metadata_gen_playground_25.csv data/metadata_gen_playground_25_b2.csv data/metadata_gen_sd35_medium.csv data/metadata_gen_sd35_medium_b2.csv --out /tmp/metadata_rerun.csv && cmp data/metadata.csv /tmp/metadata_rerun.csv
python3 /tmp/p0107_verify/verify_seedstream.py      # seed 43 실증·반사실
python3 /tmp/p0107_verify/verify_images.py          # b2 이미지 스팟
cd ~/data/tracepector/images/generated && md5sum */*.png | awk '{print $1}' | sort | uniq -d | wc -l   # 0
docker compose run --rm dev python -m pytest -q     # 28 passed
# mutation은 본 기록 Methodology 절의 절차(pre-flight 클린 게이트·git checkout 복원·git diff 확인) 그대로
```

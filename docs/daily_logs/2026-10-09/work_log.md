# 2026-10-09 work log

## Goals

- (세션 5 속행) P01-07 배치 2 마무리 — 잔여 생성기(sdxl·playground·sd35) 완료 확인·검증·커밋, 최종 split 재실행·재검증, §27 Phase 1 완료 처리, 독립검증(소유자 지시: 비차단 보강 포함 합격까지 반복).

## Completed work

### P01-07 배치 2 완성 — Generated 3,000장

- 야간 자동 진행(무인): sdxl b2 완료(10-08 23:54, 실측 ~19s/장 — 씨드 실행 대비 3배 빠름, 무경합·웜 캐시로 추정) → playground b2 완료(10-09 02:22, ~33s/장) → sd35 b2 완료(05:53) → `ALL_B2_DONE`. 총 소요 ~16시간(예상 30시간의 절반).
- 생성기별 검증·커밋(각 476행 · 카테고리 119×4 · gen_ID 범위 내 유니크 · 기존 전체와 교집합 0 · 샘플 20/20 PIL 정상): sdxl(1576-2051)·playground(2052-2527)·sd35(2528-3003).
- **통합 검증**: 11개 CSV + REAL = 6,000행, image_id 전역 유일(교집합 0 전수 확인). Generated 합계 3,000 = §7 최소 목표 충족.

### 최종 split 재실행·재검증 (P01-06 Outstanding 요건)

- `data/metadata.csv` 재배정: train 3,780 / val 812 / test 808 + test_unseen 600. real 70.0/15.1/14.9%, generated 70.0/15.0/15.0%, 셀별(source_type×category) 층화 25%±1pp, 그룹 누출 0.

### P01 완료 처리 — §27 Phase 1 완료 조건 전부 충족

- 충족 근거: 최소 6,000장 ✓ · Real ≥3,000 ✓ · Generated ≥3,000 ✓ · 카테고리 4부위 구성 ✓ · metadata.csv ✓ · train/val/test split ✓ · unseen generator test(test_unseen 600) ✓.
- 반영: `docs/plan/phase_1_data_pipeline.md` P01-07 완료 + 결과 비고, `docs/plan/00_index.md` P01 → Complete, HANDOFF 재작성(다음 = P02 착수), CHANGELOG 행.
- 생성 컨테이너 정지(GPU 반환 — 재사용 시 compose gpu profile).

### P01-07 독립검증·hardening (소유자 지시: 비차단 항목까지 반영·합격까지 반복)

- 독립검증([기록](../verifications/2026-10-09/p01_07_scale_expansion.md)): **합격** — blocking 0. §27 조건 7개 원천 재계산 충족, 무결성(키 집합·필드 불변·byte 동일 재실행), seed 43 실증(반사실: seed 42 재사용 시 생성기당 31쌍 정확 중복 발생 — 설계 동기 입증), mutation 7건 전건 재실패.
- hardening 4건 반영:
  - **H1(실질 결함): 생성기×split 퇴화** — 결정적 배정의 그룹키 사전순 소진으로 qwen·playground 600장이 전량 train에만 배정(§19 generator별 ROC-AUC를 val/test에서 측정 불가). §14가 generator를 층화 차원으로 명시하므로 **셀 정의를 source_type×category×generator로 확장**해 해소 — train 생성기별 420/92/88, REAL은 generator 공백이라 배정 불변(0행), 총량 동일. 가드에 generator 축 셀 비율 어설션 추가.
  - H2: 계획서 비고 gen_ID "전역 연속" 부정확 → 249·374·499 공백 3 명시로 정정.
  - H3: 10-08 work log 반사실 서술 정정(중복은 각 블록이 아닌 첫 카테고리 블록 31쌍만).
  - H4(계승): GEN pHash 위임·Test B REAL 재사용 보류 — HANDOFF 유지.
- 검증: split 재실행 누출 0, 가드 6셀·전체 28 cells passed.

## Issues found

- 없음(배치 2 전 구간 rc=0, 재기동 0회 — 재개 가드는 예비로만 존재).

## Decisions

- P01-07 검증은 데이터·split 최종 산출물에 대한 독립검증으로 진행(생성 프로세스 자체는 생성기별 검증으로 이미 잠금) — 소유자 지시 프로세스(비차단 보강 포함 합격까지 반복) 그대로 적용.

## Next steps

- P01-07 독립검증(서브에이전트) → 보강 → 합격 확정.
- P02 착수 — 페이즈 계획서 작성 후 baseline 모델 구현.
- 보류: Test B 평가 시 REAL 재사용 여부(소유자 결정, P02 평가 설계 전).

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

### P01-07 추적 검증 — 합격 재확정

- 추적 검증 판정: **합격**(신규 blocking 0) — H1 해소를 diff·데이터에서 독립 재확인(생성기별 420/92/88×4, REAL 0행 불변, 3축 셀 편차 ≤0.33pp, P01-06 잠금 의미 잔존). **MU3 역방향 mutation**으로 H1 가드 실증(generator 축 제거 시 3축 셀 어설션이 퇴화 서명에서 정확 재실패). H2·H3 정정 확인.
- HANDOFF 최종 갱신(split 수치 820/800, 검증 완료 상태) — 세션 마무리·다음 작업자 인계.

## Issues found

- 없음(배치 2 전 구간 rc=0, 재기동 0회 — 재개 가드는 예비로만 존재).

## Decisions

- P01-07 검증은 데이터·split 최종 산출물에 대한 독립검증으로 진행(생성 프로세스 자체는 생성기별 검증으로 이미 잠금) — 소유자 지시 프로세스(비차단 보강 포함 합격까지 반복) 그대로 적용.

## Next steps

- P02 착수 — 페이즈 계획서(`docs/plan/phase_2_*.md`) 작성 후 baseline 모델 구현. 게이트 개방 상태.
- 보류(소유자 결정, P02 평가 설계 전): Test B(test_unseen) 평가 시 REAL 이미지 재사용 여부 · GEN 근사중복 pHash 점검 시점(P02+ encoder 연결 권장).

## P02 착수 — 후속 세션

### 목표

- 핸드오프의 다음 작업인 frozen SigLIP baseline을 구현하고 실제 데이터 학습·Test A/B 평가까지 확인한다.

### 구현·검증

- `src/model.py`: vision-only SigLIP pooled feature, pretrained config 기반 차원 유도, frozen encoder eval/no-grad 유지. head는 train mode를 유지하며 freeze 해제도 지원한다.
- `src/dataset.py`: 원본 CSV의 split 선택과 평가용 category/generator/source projection, Docker `/images` 마운트 지원. 약한 crop/resize·brightness/contrast 추가, 평가 transform은 결정적이다.
- `src/train.py`: validation BCE 기반 `best.pt`, epoch별 `last.pt`(optimizer/RNG 포함)와 동일 config 재개, config·metadata SHA256·학습 이력의 JSON 기록. smoke는 stub/CPU로 유지한다.
- `src/evaluate.py`: Test A/B 및 category/generator/source별 metric. ROC-AUC는 동률 threshold를 묶어 계산하며 PR-AUC는 trapezoidal 면적이다. 단일 클래스 AUC는 null로 기록한다.
- `Dockerfile.training`·compose `training` profile: 기존 ComfyUI CUDA 기반 환경 재사용, 런타임 의존성 exact pin. 학습용 서비스는 ComfyUI 서버를 기동하지 않는다.
- 검증: 신규 테스트 구현 전 import 실패 확인. 기존 CPU 환경 전체 32 passed, 이후 재개/마운트 가드 추가 및 exact pin CUDA 환경 전체 **33 passed**. 기존 dedup fixture의 Pillow deprecation 경고 12건은 동작 실패가 아니다. 독립검증·mutation testing은 수행하지 않았다.

### 발견 이슈

- CPU dev 이미지에는 git 실행 파일이 없다. `GIT_COMMIT` 환경변수를 우선 읽고 git이 있을 때만 조회하도록 수정했다. smoke의 commit은 없을 수 있지만 실학습에는 명시 전달한다.
- 이 머신 Docker Compose의 기본 Bake 빌드가 panic을 낸다. `COMPOSE_BAKE=false docker compose --profile training build train`으로 빌드 확인했다.
- 실제 pretrained 가중치 다운로드·실학습 검증은 진행 중이다. 아직 P02 Complete로 판정하지 않는다.

### 소유자 결정

- [DB-04](../../decision_briefs/DB-04_P02_unseen-real.md) 옵션 A 선택: Standard test REAL 재사용. train/val REAL을 포함하지 않고 테스트 간 공유 표본 수를 기록한다. §10 및 SoT 버전 로그에 반영했다.

### 다음 단계

- 실제 pretrained encoder와 CUDA 데이터 경로 확인 후 10 epoch 학습, best checkpoint에서 Test A/B 평가 및 실험 기록 보관.
- 이후 P03 비교, GEN pHash/embedding 중복 점검은 별도 후속 범위.

- 후속 확인: 소유자가 Test B의 FAKE=`test_unseen` 600장 정의를 재확인했다. CSV 실측 REAL 448 + Generated 600 = 1,048장. 최종 평가 독립성에 대한 질문에는 개발 중 테스트 결과로 모델/설정을 선택한다면 별도 미사용 REAL/FAKE holdout을 권고한다고 설명했다. 신규 데이터 수집이나 기존 split 변경은 아직 착수하지 않는다.
- 재개 검증 추가: augmentation 포함 연속 3 epoch와 2 epoch 후 RNG를 바꿔 재개한 결과의 학습 이력·전체 모델 state가 동일함을 확인했다. 변경된 config로 재개는 거부한다.

- 공식 pretrained 가중치 로드 성공(vision 차원 768, vision 누락 key 없음; 원본의 text_model/logit key는 vision-only 로딩에서 제외). 모델 revision을 `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`로 고정했다.

- 최종 CUDA 환경 전체 **34 passed**(기존 Pillow 경고 12건), CPU exact pin 이미지 빌드도 성공. 실학습 provenance를 고정하기 위해 구현·계획·결정을 먼저 커밋한 뒤 실험을 실행한다. 이는 mutation 검증용 커밋이 아니며 mutation은 수행하지 않는다.

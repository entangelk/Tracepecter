# 페이즈 인덱스

> Tracepecter MVP 실행 상태. 페이즈 번호는 `docs/project.md` §27–§28의 Phase 정의와 1:1로 매핑한다(P07은 §28 데모 구축).

| ID | 페이즈 | 상태 | 선행 조건 | 완료 근거 | 결정 브리프 |
| --- | --- | --- | --- | --- | --- |
| P00 | 프로젝트 초기화 — repo/환경/README/config/skeleton | Planned | — | 학습 skeleton이 `python -m src.train --config configs/baseline.yaml` smoke 실행으로 정상 종료 | — |
| P01 | 데이터 파이프라인 — 수집/생성/메타데이터/dedup/split | Planned | P00: 실행 환경 + 소유자의 K-Fashion 다운로드 완료 | `metadata.csv` + train/val/test split + unseen generator test 생성, 최소 6,000장(Real ≥ 3,000, Generated ≥ 3,000)·축소된 패션 category 기준 충족 | [DB-01](../decision_briefs/DB-01_P01_real-data-domain.md) |
| P02 | Baseline 모델 — frozen encoder + MLP head | Planned | P01: 씨드 데이터(Real 500 + Generated 500) split 확보 | 1-명령 학습 + checkpoint 저장 + validation metric + test evaluation 동작 | — |
| P03 | Baseline 비교 — SigLIP vs DINO | Planned | P01: 전체 dataset 완료, P02: baseline 학습·평가 동작 | 동일 split 기준 비교 report + primary encoder 선정 기록 | — |
| P04 | LoRA (조건부) | Planned | P03 (진입 조건: `docs/project.md` §17) | LoRA vs frozen 비교 결과 문서 — 유의미하지 않으면 baseline 유지 | — |
| P05 | Score calibration | Planned | P03: primary encoder 선정 | validation 기반 calibration parameter + threshold + 0~100 score 정의 기록 | — |
| P06 | Failure analysis | Planned | P05 | `reports/errors/` 자동 저장 + failure case 100개 이상 수동 검토 + 오류 패턴 문서 | — |
| P07 | API + Demo | Planned | P05 | `POST /score` API 응답 + web demo에서 score 출력 확인 | — |

## 비고

- 상세 슬라이스 계획은 해당 페이즈 착수 직전에 작성한다. 현재 상세 문서는 P00만 존재: [`phase_0_initialization.md`](phase_0_initialization.md).
- `docs/project.md` §35의 thin-slice 원칙에 따라, P02는 P01 전체 완료 전에도 씨드 데이터(1,000장 규모)로 착수할 수 있다. P01은 병렬로 규모 확장을 계속한다.
- 페이즈 상태·선행 조건·완료 근거가 바뀌면 본 인덱스와 해당 페이즈 문서를 같은 변경에서 함께 갱신한다. 규칙: `docs/guides/phase-and-decision-briefs.md`.
- REAL 데이터는 AIHub K-Fashion으로 확정(DB-01. 승인 완료·다운로드 전 — P01 착수 전 소유자 다운로드 필요). AI 생성기(≥3종) 접근 수단은 여전히 미확인이므로 P01 상세 계획 수립 시 확인한다. 축소 카테고리 목록도 P01에서 라벨 분포 기반 확정.

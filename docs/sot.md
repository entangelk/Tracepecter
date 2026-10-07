# Tracepecter — Source of Truth (SoT)

> 최종 갱신: 2026-10-07

## 1. 프로젝트 정의

> Fashion Photo Realism Scorer는 패션 착용 이미지가 실제 착용 촬영 사진과 얼마나 유사한 시각적 특성을 가지는지 평가하는 vision model이다. 실제 촬영 여부를 증명하는 forensic detector가 아니라, 패션 이미지의 photographic realism을 연속적인 score로 평가하는 것을 목표로 한다.
> — `docs/project.md` §34

- 첫 milestone: 패션 착용 이미지 1장 입력 시 학습된 모델이 0~100 Photographic Realism Score를 반환하고, 별도 test dataset에서 baseline metric을 확인할 수 있는 상태 (`docs/project.md` §35).
- MVP 성공 기준(Standard Test ROC-AUC ≥ 0.90, Unseen Generator ROC-AUC ≥ 0.80 포함)은 `docs/project.md` §20이 소유한다. 본 문서에는 복제하지 않는다.

## 2. SoT 지도 — 어떤 문서가 무엇을 소유하는가

| 주제 | SoT | 비고 |
| --- | --- | --- |
| 제품 요구사항·범위·데이터 전략·모델 전략·페이즈 정의·성공 기준 | `docs/project.md` | governing spec |
| 실행 상태(페이즈·슬라이스 진행) | `docs/plan/00_index.md` + 개별 페이즈 문서 | |
| 소유자 결정 | `docs/decision_briefs/` | Resolved 시 관련 산출물·문서에 반영 |
| 현재 개발 상태(다음 작업자용 스냅샷) | `HANDOFF.md` | |
| 작업 기록·사용자 결정 배경 | `docs/daily_logs/` | |
| 주요 변경 이력 | `CHANGELOG.md` | |
| 데이터 메타데이터 schema | `docs/project.md` §12 | 구현 시점에 `docs/guides/data-contracts.md` 규칙 적용 |
| 학습·추론 parameter | `configs/*.yaml` | 코드에 직접 기입하지 않는다 (`docs/project.md` §25) |
| 실험 config·metric | `experiments/` | 실험마다 config와 metric을 함께 보관 (§26) |
| 시스템의 실제 동작 | 코드 자체 | 문서와 불일치 시 코드가 사실이다. 문서를 고치거나 소유자 결정을 올린다 |

## 3. Spec precedence — 사양 충돌 판정 순서

동일 주제에 대한 서술이 충돌하면 아래 순서로 판정한다.

1. 소유자의 명시적 최신 지시 — 단, 지속 효력을 위해 decision brief 또는 work log로 기록되어야 한다. 기존에 기록된 결정과 충돌하는 새 지시는 스스로 판정하지 말고 어느 쪽이 canonical인지 소유자에게 확인한다.
2. Resolved 상태의 decision brief (`docs/decision_briefs/`) — 늦게 Resolved된 것이 우선한다. 기존 결정을 바꿀 때는 supersession 링크를 건 새 결정 ID를 사용한다.
3. `docs/project.md` — 제품 사양의 기준 문서.
4. `docs/plan/*` 페이즈 문서 — project.md와 모순되지 않는 범위에서 유효하다. 모순 발견 시 project.md를 갱신하거나 decision brief로 올린다.
5. `README.md`, `reports/`, `HANDOFF.md`, `docs/daily_logs/` — 기록·요약이며 선언적 근거가 아니다. stale할 수 있다.
6. 코드 주석.

작업 방법(기록 규칙·검증 절차 등)의 충돌은 별도 축으로, `CLAUDE.md`/`AGENTS.md` → `docs/guides/*` 순으로 적용한다. 사양 문서 내부 또는 사양 문서 사이의 유의한 모순을 발견한 작업자는 임의로 한쪽을 택하지 말고 소유자에게 제기한다.

## 4. 버전 로그

의미 있는 변경(요구사항·범위·기준·구조 변경)만 기록한다. 문구 교정 등 기계적 변경은 기록하지 않는다.

| 대상 | 버전 | 날짜 | 변경 요약 | 근거 |
| --- | --- | --- | --- | --- |
| project.md | v1.0 | 2026-10-07 | 최초 기준 확정 — 프로젝트 시작 | — |
| project.md | v1.1 | 2026-10-07 | REAL 데이터를 AIHub K-Fashion으로 확정하고 Fashion Photo Realism Scorer로 재정의. 카테고리는 패션 중심 축소로 변경(목록은 P01 확정), 생성 프롬프트·split 그룹 기준 등 착용컷 도메인에 맞게 갱신 | 소유자 결정 2026-10-07, [DB-01](decision_briefs/DB-01_P01_real-data-domain.md) |
| sot.md | v1.0 | 2026-10-07 | 최초 작성 — 문서 체계·precedence 정의 | CLAUDE.md §1 (spec-precedence tree 요구) |

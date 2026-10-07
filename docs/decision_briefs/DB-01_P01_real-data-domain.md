# DB-01 — REAL 데이터 도메인을 착용컷 패션 이미지로 정의

**Status:** Resolved
**Related phase:** P01

## Decision needed

REAL 데이터를 AIHub K-Fashion 이미지(착용컷 중심)로 확정하면서, 기존 프로젝트 정의("Product Photo Realism")와 데이터 도메인이 어긋나게 되었다. REAL/AI 양측의 이미지 형태를 어느 쪽으로 맞출지, 프로젝트 정의를 유지할지 변경할지가 P01 상세 계획의 전제가 되므로 소유자 결정이 필요했다.

## Options

| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| A | 착용컷 기준으로 프로젝트를 Fashion Photo Realism Scorer로 재정의. REAL=K-Fashion 착용 이미지, AI=착용 패션 컷 생성 | 원본 데이터를 그대로 사용해 데이터 품질·단순성에 최선. 크롭 등 전처리 파이프라인 불필요 | 원 정의(상품 사진)에서 벗어남. e-commerce 상품컷 사용 사례는 Phase 2 확장으로 분리 |
| B | 정의(상품컷) 유지, K-Fashion을 폴리곤/렉트 좌표로 크롭해 의류 상품컷 유사 real 데이터 구축 | 원 정의·원 사용 목적 유지 | 크롭 전처리 파이프라인 추가. 모델이 크롭 아티팩트(잘린 배경·신체 경계)를 학습할 confound 위험 — "데이터 품질이 모델보다 중요"라는 프로젝트 원칙과 상충 |
| C | 상품컷 + 착용컷 혼합 real | 도메인 다양성 증가 | 초기 정의가 흐려지고 라벨·split 설계 복잡화(§32 초기 확장 금지 원칙과 상충) |

## Recommendation + reason

A. 데이터 품질과 단순성(§31 우선순위, §32 하지 말아야 할 것)에 부합하고, 크롭 confound 위험을 원천 제거한다.

## Follow-up considerations

- 착용컷에는 얼굴이 포함된다. 모델이 의류 realism이 아니라 얼굴 위조 artifact에 반응하지 않도록, P01 데이터 설계에서 얼굴 영역 처리 정책을 REAL/AI 양측에 동일하게 적용한다. (§4 비범위의 얼굴 deepfake 탐지와는 구분)
- 축소 카테고리 목록은 K-Fashion 라벨 분포 확인 후 P01에서 확정한다(필요 시 별도 결정).
- K-Fashion은 내국인 신청·승인 후 API 다운로드 방식이며 재배포 제한이 있다 — metadata provenance에 출처를 기록한다(§8).
- metadata schema의 `product_id` 등 상품 가정 필드는 P01에서 K-Fashion 라벨 구조에 맞게 조정한다(§12).

## Deferred / out of scope

- Phase 2 이후 e-commerce 상품컷 도메인으로의 재확장 여부는 MVP 완료 후 별도 결정.

## Resolution

- 선택: **A**
- 일자: 2026-10-07
- 근거: 소유자 결정. 패션 이미지 데이터셋 채택에 따라 착용컷 기준 재정의가 자연스럽고 데이터 품질·단순성에 최선.
- 반영: `docs/project.md` v1.1(§1·§2·§3·§7·§8·§9·§13·§14·§21·§23·§24·§27 Phase 1·§34·§35), `docs/sot.md` 버전 로그 및 정의 인용, `docs/plan/00_index.md` P01 행, `docs/decision_briefs/00_index.md`, `HANDOFF.md`, `CHANGELOG.md`, 2026-10-07 work log.

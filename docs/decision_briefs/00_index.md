# 결정 브리프 인덱스

소유자 결정이 구현을 막고 기존 문서·선행 결정에서 해결되지 않을 때만 브리프를 작성한다. 작성·해결 절차는 `docs/guides/phase-and-decision-briefs.md`를 따른다.

| ID | 페이즈 | 관련 슬라이스 | 주제 | 상태 | 결정 | 일자 |
| --- | --- | --- | --- | --- | --- | --- |
| [DB-01](DB-01_P01_real-data-domain.md) | P01 | P01 전체 | REAL 데이터 도메인 — 착용컷 패션으로 재정의 | Resolved | 옵션 A: Fashion Photo Realism Scorer로 재정의, REAL=AIHub K-Fashion | 2026-10-07 |
| [DB-02](DB-02_P01_ai-generators.md) | P01 | P01-04 | AI 생성기 접근 수단 — 로컬/API/혼합 5종 구성 | Resolved | 옵션 A(소유자 변형): 전량 로컬 오픈소스 무비용 — Qwen-Image 보유·Z-Image 추가 가능, 5종 구성은 P01-04 설계 시 확정 | 2026-10-07 |
| [DB-03](DB-03_P01_face-policy.md) | P01 | P01 데이터 설계 전체 | 얼굴 영역 처리 정책(DB-01 후속) | Resolved(DB-06으로 대체) | 옵션 A: 무처리 — 프롬프트 정합 + P06 재검 트리거로 위험 관리 | 2026-10-07 |

| [DB-04](DB-04_P02_unseen-real.md) | P02 | P02-03 | Test B REAL 구성 | Resolved | 옵션 A: Standard test REAL 재사용 | 2026-10-09 |
| [DB-05](DB-05_P06_review-set.md) | P06 | P06-03 | 100개 검토군 구성·검토 주체 | Resolved | 결정 1 A: 오류 전수+보충 ≥100(유형 구분) · 결정 2 R1: 에이전트 1차+소유자 확인 | 2026-10-09 |
| [DB-06](DB-06_P06_face-exposure.md) | P06 | P06-04 → P08·P07 | 얼굴 노출 비대칭 대응(DB-03 재상정) | Resolved | 옵션 C: 공통 흰 원 익명화(학습·평가·추론) + 얼굴 노출 실사 평가 holdout | 2026-10-11 |
| [DB-07](DB-07_P09_review-coverage.md) | P09 | P09-01~02 | 후보 검토 범위 | Resolved | A 방향: 우선순위 검토·미검토 범위 명시 | 2026-10-20 |
| [DB-08](DB-08_P07_response-contract.md) | P07 | P07-01~03 | API 응답 분류 체계·confidence·데모 형태 | Open | — | 2026-10-25 |

## 대기 중인 사항

- **DB-08**(P07): §22 예시(3단계·config threshold·confidence)와 보정 artifact의 2단계 threshold 충돌, 데모 형태. 결정 전 P07 구현 보류.

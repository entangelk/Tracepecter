# 결정 브리프 인덱스

소유자 결정이 구현을 막고 기존 문서·선행 결정에서 해결되지 않을 때만 브리프를 작성한다. 작성·해결 절차는 `docs/guides/phase-and-decision-briefs.md`를 따른다.

| ID | 페이즈 | 관련 슬라이스 | 주제 | 상태 | 결정 | 일자 |
| --- | --- | --- | --- | --- | --- | --- |
| [DB-01](DB-01_P01_real-data-domain.md) | P01 | P01 전체 | REAL 데이터 도메인 — 착용컷 패션으로 재정의 | Resolved | 옵션 A: Fashion Photo Realism Scorer로 재정의, REAL=AIHub K-Fashion | 2026-10-07 |
| [DB-02](DB-02_P01_ai-generators.md) | P01 | P01-04 | AI 생성기 접근 수단 — 로컬/API/혼합 5종 구성 | Resolved | 옵션 A(소유자 변형): 전량 로컬 오픈소스 무비용 — Qwen-Image 보유·Z-Image 추가 가능, 5종 구성은 P01-04 설계 시 확정 | 2026-10-07 |
| [DB-03](DB-03_P01_face-policy.md) | P01 | P01 데이터 설계 전체 | 얼굴 영역 처리 정책(DB-01 후속) | Resolved | 옵션 A: 무처리 — 프롬프트 정합 + P06 재검 트리거로 위험 관리 | 2026-10-07 |

## 대기 중인 사항

- 없음 — P01 계획서 승인 완료(2026-10-07, 카테고리 4부위·schema v1.2 포함). 남은 선행은 소유자의 원천 이미지 다운로드 완료뿐.

# CHANGELOG.md

주요 설계·기능 변경 이력. 사소한 수정은 기록하지 않는다. 상세는 daily_logs 참고.

| 날짜 | 변경 | 세부 |
| --- | --- | --- |
| 2026-10-07 | 프로젝트 부트스트랩 — SoT 문서, 페이즈 인덱스, P00 계획서, 결정 브리프 체계 생성 | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | [DB-01] Fashion Photo Realism Scorer로 재정의 — REAL 데이터 AIHub K-Fashion 확정, 카테고리 패션 중심 축소 방향 확정 (project.md v1.1) | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P00 구현 — git repo·Python 환경·디렉터리 골격·README·baseline config·학습 skeleton(stub encoder)·회귀 테스트 9종 | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P00 독립검증 **합격**(blocking 0건) + hardening 7건 보강 — 테스트 결정화·Normalize/BCE 잠금·smoke 실패경로 정리 등 | [검증 기록](docs/verifications/2026-10-07/p00_initialization.md) · [work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P00 재검증 **합격** — H1~H7 해소 입증, P00 Complete 처리 | [검증 기록](docs/verifications/2026-10-07/p00_initialization.md) |
| 2026-10-07 | P01 상세 계획서 작성 — K-Fashion 라벨 전수 분석(967,806장) 기반 카테고리 4부위 확정 제안, metadata schema v1.2 제안, 슬라이스 P01-01~07 정의. 결정 브리프 [DB-02](docs/decision_briefs/DB-02_P01_ai-generators.md)·[DB-03](docs/decision_briefs/DB-03_P01_face-policy.md) Open 등록 | [P01 계획서](docs/plan/phase_1_data_pipeline.md) · [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | 소유자 결정 — P01 계획 승인(카테고리 4부위·schema v1.2), [DB-02](docs/decision_briefs/DB-02_P01_ai-generators.md) 생성기=전량 로컬 오픈소스 무비용(Qwen-Image 보유·Z-Image 추가), [DB-03](docs/decision_briefs/DB-03_P01_face-policy.md) 얼굴=무처리, 실행 환경 Docker Compose 전환(venv 대체) | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P01-02 완료 — §12 metadata schema v1.2 개정(project.md v1.2: `product_id` 제거, `parts`·`style`·`look_group`·`prompt_id` 추가), `scripts/analyze_kfashion_labels.py` 등록, `Dockerfile`·`compose.yaml`·`.dockerignore` 추가 | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |

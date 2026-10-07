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
| 2026-10-07 | P01 독립검증 **재검증 합격** — 초회 조건부(B1 수치 정정) + hardening H1~H6 보강(§12 v1.2 12열 리터럴 잠금 셀 신설·fixture 규약 정합·정규식 확장 등), 가드 RV1~RV3 독립 재입증 | [검증 기록](docs/verifications/2026-10-07/p01_plan_schema_docker.md) · [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P01-01 완료 — 원천 Training 3파트 정합 검증(매핑 불일치 0.0000%, 유효 이미지 967,806장, 무결성 샘플 30/30). 산출물 조정: 전량 해제→선택적 추출 | [P01 계획서 비고](docs/plan/phase_1_data_pipeline.md) · [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P01-03 완료 — REAL 씨드 500장 선별·추출·`data/metadata_real.csv` 생성(부위별 125×4 층화, §12 v1.2). `scripts/kfashion_common.py`(규칙 공유화)·`build_metadata.py` + 회귀 가드 4셀(pytest 15 cells) | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |
| 2026-10-07 | P01-05 완료 — pHash 근사중복 클러스터링(in-repo 64-bit DCT)으로 look_group 100% 커버(129→500), 스타일 이중 라벨링 동일 룩 그룹 포착. `deduplicate.py` + 가드 3셀(pytest 18 cells). embedding 유사도 층은 P02+ 위임 | [2026-10-07 work log](docs/daily_logs/2026-10-07/work_log.md) |

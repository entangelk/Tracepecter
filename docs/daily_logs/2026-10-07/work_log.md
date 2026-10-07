# 2026-10-07 work log

## Goals

- 프로젝트 부트스트랩: `docs/project.md`를 기준으로 SoT 문서와 초기 페이즈 계획 체계를 구축한다.

## Completed work

### 프로젝트 문서 체계 구축

- 설명: CLAUDE.md §1의 spec-precedence tree 요구에 따라 SoT 문서를 작성하고, `docs/guides/phase-and-decision-briefs.md`가 정의하는 layout대로 페이즈·결정 브리프 체계를 만들었다.
- 파일 변경:
  - `docs/sot.md` (신규) — 프로젝트 정의 인용, SoT 지도(주제별 소유 문서), spec precedence 6단계 판정 순서, 버전 로그
  - `docs/README.md` (신규) — 문서 지도 허브. plan/decision 인덱스 링크
  - `docs/plan/00_index.md` (신규) — P00~P07 페이즈 인덱스(project.md §27–§28과 1:1 매핑)
  - `docs/plan/phase_0_initialization.md` (신규) — P00 상세 계획(슬라이스 P00-01~P00-03, 완료 확인 기준 포함)
  - `docs/decision_briefs/00_index.md` (신규) — 결정 인덱스(등록된 결정 없음 + P01 관련 대기 사항)
  - `HANDOFF.md` (신규) — 현재 상태 스냅샷
  - `CHANGELOG.md` (신규) — 초기 엔트리
- 주요 변경: 코드·데이터 없는 문서만의 변경. `docs/project.md`는 수정하지 않았다(v1.0으로 버전 로그에 등록만 함).
- 효과: 사양 충돌 시 판정 규칙이 생겼고, 이후 작업자가 페이즈 상태를 인덱스에서 확인할 수 있다.

### REAL 데이터 소스·도메인 결정 반영 (DB-01)

- 설명: 소유자가 REAL 데이터를 AIHub K-Fashion 이미지(dataSetSn=51)로 확정하고, 도메인을 착용컷 패션으로 재정의(옵션 A)했다. 결정을 DB-01로 등록하고 project.md와 기록 문서 전반에 반영했다.
- 파일 변경:
  - `docs/decision_briefs/DB-01_P01_real-data-domain.md` (신규) — 옵션 표(A 착용컷 재정의 / B 크롭 상품컷 / C 혼합)·권장·해결 기록
  - `docs/decision_briefs/00_index.md` — DB-01 등록, 대기 사항 갱신
  - `docs/project.md` (v1.0 → v1.1) — 제목·§1·§2·§3·§7·§8·§9·§13·§14·§21·§23·§24·§27 Phase 1·§34·§35: 착용컷 패션 도메인 문구, K-Fashion 소스 확정, 카테고리 축소(목록 P01 확정), 생성 프롬프트·배경을 착용컷 기준으로 교체, split 그룹 기준을 '동일 인물·룩'으로 교체
  - `docs/sot.md` — §1 정의 인용 갱신, 버전 로그 v1.1 추가
  - `docs/plan/00_index.md` — P01 선행 조건(다운로드 완료)·완료 근거·DB-01 링크 갱신
  - `docs/README.md`·`HANDOFF.md`·`CHANGELOG.md` — 정의 문구·상태 동기화
- 주요 변경: 코드 없는 문서 변경. K-Fashion 채택에 따른 정의 변경이 governing spec에 반영됨.
- 효과: P01 상세 계획의 전제(도메인·소스)가 확정됨.

## Issues found

- 없음.

## Decisions

- 페이즈 ID는 `docs/project.md` §27–§28 번호와 1:1 매핑(P00~P07). 이유: 매핑 테이블 없이 원문 추적이 가능하다. P07은 번호 없는 §28 "데모 구축"에 부여.
- 상세 페이즈 문서는 P00만 작성하고 P01~P07은 인덱스 등록에 그침. 이유: 데이터 소스·생성기 선정 등 미결정 사항이 있어 지금 상세를 쓰면 투기적이 된다(작성 시점: 착수 직전).
- git init을 오늘 작업에 포함하지 않고 P00-01 슬라이스로 이관. 이유: project.md Phase 0 완료조건에 속하는 작업이고, 사용자가 요청한 것은 문서 부트스트랩이며 커밋은 요청 시에만 수행하는 기본 원칙.
- 사용자 결정: "SoT 문서 + 초기 페이즈 계획서" 중심의 문서 우선 부트스트랩으로 프로젝트를 시작함(사용자 지시, 2026-10-07).
- 사용자 결정: REAL 데이터 = AIHub K-Fashion 이미지(dataSetSn=51, 약 120만 장, 부위별 rect/polygon 좌표 라벨). 이유: 패션 이미지 대량 확보 + 라벨 활용 가능. 카테고리는 패션 중심으로 축소(목록은 P01에서 확정).
- 사용자 결정(DB-01, 옵션 A): 도메인을 착용컷 패션으로 재정의. 이유: 크롭 전처리·crop artifact confound를 피하고 데이터 품질·단순성 우선. 상품컷(e-commerce) 도메인은 Phase 2 확장으로 분리.
- 데이터 접근 상태: AIHub 승인 완료·다운로드 전 → P01 착수 전 소유자 액션 필요.

## Next steps

- P00-01~P00-03 착수 (`docs/plan/phase_0_initialization.md`)
- 소유자: AIHub K-Fashion 다운로드 (P01 선행 조건)
- P01 상세 계획 수립 시: 축소 카테고리 목록 확정, AI 생성기(≥3종) 접근 수단 확인, 얼굴 영역 처리 정책(DB-01 후속 고려사항)

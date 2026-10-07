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

### P00 구현 (P00-01 ~ P00-03)

- 설명: 페이즈 초기화 슬라이스 3개를 구현했다. 소유자 지시에 따라 구현 후 독립검증(서브에이전트 1개) → 검증기록 확인 → 차단/비차단 전부 보강 → 합격까지 진행하는 흐름으로 작업한다.
- 파일 변경:
  - P00-01: `.gitignore`(data/raw·data/processed·checkpoints 비추적 정책 추가), `pyproject.toml`(신규 — 메타데이터+pytest 설정), `requirements.txt`(신규 — 의존성 canonical), git init 및 초기 커밋 2건(유저 first commit + docs 부트스트랩)
  - P00-02: §24 디렉터리 골격(configs/data/scripts/src/experiments/api/demo/checkpoints/reports/tests), `README.md`(§29 필수 항목), `configs/baseline.yaml`(§25 5개 최상위 키 준수)
  - P00-03: `src/model.py`(StubEncoder + RealismScorer §16 스택 + set_encoder_frozen), `src/dataset.py`(§12 메타데이터 Dataset + §15 transform/JPEG 증강), `src/train.py`(config 구동 학습 루프 + `--smoke`), `tests/test_model.py`·`tests/test_dataset.py`·`tests/test_train_smoke.py`(회귀 가드 9개)
- 검증: `pytest` 9 passed / `python -m src.train --config configs/baseline.yaml --smoke` 정상 종료(epoch loss 출력 + checkpoint 저장 + "smoke ok") / baseline.yaml 파싱 성공 / venv 내 전 의존성 import 성공.

### P00 독립검증 결과 반영 (hardening 7건)

- 설명: 독립검증(서브에이전트) 판정 **합격** — blocking 0건, 비차단 hardening 7건. 소유자 지시에 따라 비차단 항목까지 전부 보강했다. 기록: `docs/verifications/2026-10-07/p00_initialization.md`.
- 보강 내역 (H1~H7):
  - H1 `tests/test_model.py` — `test_output_is_probability` 를 seed 고정 + 입력 100배 스케일로 결정화(기존 55% 확률 재실패 → 확정 재실패).
  - H2 `tests/test_dataset.py` — `test_transform_resizes_and_normalizes` 에 Normalize 값 검증 추가(회색 128 → ≈0.0078, 미정규 시 ≈0.502 재실패). 기존 부등호 체인은 Normalize 제거를 흡수했음(M7).
  - H3 `src/dataset.py` docstring — §15 구현 범위를 P00 분(Resize·HFlip·JPEG·Normalize)으로 정정, 잔여 op 는 P02 위임 명시 + 페이즈 비고 반영.
  - H4 `src/train.py` — `build_loss()` 추출 + `tests/test_train_smoke.py::test_loss_is_binary_cross_entropy` 로 §16 BCE 리터럴 잠금.
  - H5 `docs/plan/phase_0_initialization.md` 비고 — §24 잎 노드의 페이즈별 위임 명시.
  - H6 `docs/plan/00_index.md` 비고 — 의존성 exact pin 재검토를 P02 과제로 등록.
  - H7 `src/train.py` — smoke 실패 경로에서 임시디렉터리 정리(`except BaseException: rmtree; raise`), `run_training` 분리.
- 효과: 검증이 지적한 셀 주장↔실제 lock 간 격차 제거. 보강 후 재검증은 동일 검증자에게 요청해 기록을 갱신한다.

### 보강 가드 self-mutation 확인 (커밋 후 실시)

절차: 커밋 후 `git status --short` clean 확인 → mutate → 해당 셀만 실행 → 재실패 확인 → `git checkout -- <path>` 복원 → clean 확인. 최종 전체 스위트 10 passed.

| mutation | 적용 위치 | 재실패한 셀 |
| --- | --- | --- |
| M1' head 스택에서 `nn.Sigmoid()` 제거 | `src/model.py` (head) | `test_output_is_probability` (확정 — H1 결정화 확인) |
| M7' `transforms.Normalize` 제거 | `src/dataset.py` (build_transform) | `test_transform_resizes_and_normalizes` (확정 — H2 잠금 확인) |
| M-BCE `build_loss()` → `nn.MSELoss()` | `src/train.py` (build_loss) | `test_loss_is_binary_cross_entropy` (확정 — H4 잠금 확인) |

## Issues found

- **BCELoss dtype 불일치 (해결)**: DataLoader 가 python float label 을 float64 로 collate해 `BCELoss` 가 `Found dtype Double but expected Float` 로 실패. `src/train.py` 학습 루프에서 `labels.to(probabilities.dtype)` 로 수정. 발견 경로: 최초 smoke 실행 실패(pytest 2 failed) → 수정 후 9 passed.
- **H7 재구성 회귀 (해결)**: `run_training` 분리 중 `smoke ok` 출력이 누락되어 CLI 계약 셀 2개(`test_train_smoke_creates_checkpoint`·`test_train_cli_command_runs_clean`) 재실패 — 보강 변경 자체의 회귀를 기존 가드가 포착한 사례. 출력 복원 커밋으로 해결, 10 passed.
- **프로세스 교훈**: `pytest | tail` 파이프로 exit code 가 가려진 채 실패 상태에서 커밋이 진행됨(직후 발견·수정). 이후 pytest 실행은 exit code 를 명시적으로 확인한다.

## Decisions

- 페이즈 ID는 `docs/project.md` §27–§28 번호와 1:1 매핑(P00~P07). 이유: 매핑 테이블 없이 원문 추적이 가능하다. P07은 번호 없는 §28 "데모 구축"에 부여.
- 상세 페이즈 문서는 P00만 작성하고 P01~P07은 인덱스 등록에 그침. 이유: 데이터 소스·생성기 선정 등 미결정 사항이 있어 지금 상세를 쓰면 투기적이 된다(작성 시점: 착수 직전).
- git init을 오늘 작업에 포함하지 않고 P00-01 슬라이스로 이관. 이유: project.md Phase 0 완료조건에 속하는 작업이고, 사용자가 요청한 것은 문서 부트스트랩이며 커밋은 요청 시에만 수행하는 기본 원칙.
- 사용자 결정: "SoT 문서 + 초기 페이즈 계획서" 중심의 문서 우선 부트스트랩으로 프로젝트를 시작함(사용자 지시, 2026-10-07).
- 사용자 결정: REAL 데이터 = AIHub K-Fashion 이미지(dataSetSn=51, 약 120만 장, 부위별 rect/polygon 좌표 라벨). 이유: 패션 이미지 대량 확보 + 라벨 활용 가능. 카테고리는 패션 중심으로 축소(목록은 P01에서 확정).
- 사용자 결정(DB-01, 옵션 A): 도메인을 착용컷 패션으로 재정의. 이유: 크롭 전처리·crop artifact confound를 피하고 데이터 품질·단순성 우선. 상품컷(e-commerce) 도메인은 Phase 2 확장으로 분리.
- 데이터 접근 상태: AIHub 승인 완료·다운로드 전 → P01 착수 전 소유자 액션 필요.
- 구현 결정: `--smoke` 플래그 — 실데이터 없이 완료 확인 명령이 동작해야 하므로 tiny synthetic dataset 으로 1 epoch 검증 경로를 만들었다. 페이즈 문서의 완료 확인 문구도 같이 정정.
- 구현 결정: `model.encoder: stub` — 실제 encoder 연결은 P02 범위(§27 Phase 2 'Vision Encoder 연결'). skeleton 은 구조·파이프라인만 검증.
- 구현 결정: venv 를 `~/.venvs/tracepecter`(ext4)에 생성하고 CPU torch wheel 로 설치 — WSL2 /mnt/d 9p I/O 병목 회피 + skeleton 단계에는 CUDA 불필요. CUDA 전환은 P02 에서 결정.

### P00 재검증 결과 및 Complete 처리

- 재검증(동일 검증자, 커밋 범위 `f787fe4..01fa039`): **합격** — H1~H7 전부 해소 확인, 신규 가드 3종 확정 재실패 입증(R1 Sigmoid 제거 10/10, R2 Normalize 제거·R3 loss 교체 단독 재실패), R4로 H7 리팩터 후에도 초회 가드 유지 확인. self-mutation 짝표는 독립 재현으로 전부 일치.
- 잔여 관찰 2건(H2 잠금이 mean 중심이라 std 리터럴 변형은 통과·`torch.manual_seed(0)` 전역 RNG)은 검증자가 조치 불필요로 판정 — 기록(`docs/verifications/2026-10-07/p00_initialization.md` §잔여 관찰)에만 유지하고 코드 변경 없음.
- P00 상태 Complete 처리(`docs/plan/00_index.md`·phase_0 비고).

## Next steps

- 소유자: AIHub K-Fashion 다운로드 (P01 선행 조건)
- P01 상세 계획 수립 시: 축소 카테고리 목록 확정, AI 생성기(≥3종) 접근 수단 확인, 얼굴 영역 처리 정책(DB-01 후속 고려사항)

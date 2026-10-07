# 2026-10-07 work log

## Goals

- 프로젝트 부트스트랩: `docs/project.md`를 기준으로 SoT 문서와 초기 페이즈 계획 체계를 구축한다.
- (세션 2) P01 상세 계획 수립 — 라벨 분포 분석 기반 카테고리 확정 제안, 생성기·얼굴 처리 결정 브리프 작성. 원천 이미지 다운로드와 독립적인 작업만 수행.
- (세션 3) P01-01 — 원천 이미지 다운로드 완료 확인·정합 검증. 이어 P01-03(REAL 선별·metadata 빌드) 착수.

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

### (세션 2) K-Fashion 라벨링데이터 전수 분석

- 설명: 원천 이미지 다운로드 진행 중(소유자 추정 5~7시간)이나 라벨링데이터.zip(Training, 1.1GB)은 수신 완료 상태였다. zip을 /tmp(ext4)로 복사해 967,806개 JSON을 전수 파싱·집계했다(소요 약 1분, 파싱 오류 0).
- 주요 결과:
  - 부위 라벨 존재: 상의 617,304(63.8%) · 하의 557,589(57.6%) · 원피스 183,572(19.0%) · 아우터 179,274(18.5%). 부위 조합 16종(최다 `상의+하의` 38.1%, 라벨 전무 0.4%).
  - 부위별 카테고리 값: 아우터 7종 · 상의 7종 · 하의 5종 · 원피스 2종(총 21종).
  - 스타일: 스트리트 46.5% 압도적 편중, `기타` 폴더(4,400장)는 스타일 라벨 부재.
  - 파일명: 쇼핑몰 출처 `PREFIX_NNN_MM.jpg` 패턴이 약 42%(약 138k 샘플 기준) — `PREFIX_NNN`을 동일 룩 그룹 키 후보로 쓸 수 있으나 나머지는 파일명 그룹핑 불가 → §13 pHash 클러스터 보완 필요.
- 분석 스크립트: 1회성으로 /tmp에서 실행(세션 종료 시 소실). P01-02에서 `scripts/analyze_kfashion_labels.py`로 repo 등록해 재현성 확보 예정.

### (세션 2) P01 상세 계획서·결정 브리프 작성

- 설명: 핸드오프의 "P01 상세 계획" 과제를 수행했다. 라벨 분포 근거로 카테고리 4부위 확정 제안, metadata schema v1.2 제안, 슬라이스 P01-01~P01-07 정의, 결정 브리프 DB-02·DB-03 작성.
- 파일 변경:
  - `docs/plan/phase_1_data_pipeline.md` (신규) — 목표·선행 조건·라벨 분포 결과·카테고리 확정 제안·schema v1.2 제안·슬라이스 인덱스·완료 기준·제외·관련 브리프·비고(GPU 정책·머신 차이 포함)
  - `docs/decision_briefs/DB-02_P01_ai-generators.md` (신규, Open) — 생성기 접근 수단 옵션 A(전량 로컬)/B(전량 API)/C(혼합, 추천)/D(수동) — 총 5종(train 4 + unseen 1), 필요량 3,600~4,000장, GPU 점유 제약 반영
  - `docs/decision_briefs/DB-03_P01_face-policy.md` (신규, Open) — 얼굴 처리 옵션 A(무처리, 추천)/B(공통 블러)/C(크롭 제거, 비권장) + P06 재검 트리거
  - `docs/plan/00_index.md` — P01 행(계획서·DB-02·DB-03 링크, 라벨 수신 완료), 비고 갱신(GPU 정책 추가)
  - `docs/decision_briefs/00_index.md` — DB-02·DB-03 등록, 대기 사항 갱신
  - `HANDOFF.md` — 다음 작업 재작성(검토 대기로 전환), 주의에 GPU 정책·venv 부재(이 머신) 추가
  - `CHANGELOG.md` — 엔트리 추가
- 효과: 소유자 결정 2건(DB-02·DB-03)과 계획 승인만으로 P01 착수 가능한 상태가 됨. 원천 다운로드와 병렬로 P01-02는 즉시 실행 가능.

### (세션 2) 소유자 결정 — P01 계획 승인·DB-02·DB-03·Docker Compose

- 사용자 결정: P01 계획서 승인(카테고리 4부위 확정 + metadata schema v1.2 포함) → P01 In Progress, P01-02 착수.
- 사용자 결정(DB-02): 생성기 접근 수단 = 전량 로컬 오픈소스 무비용. 로컬에 Qwen-Image 보유, 필요 시 Z-Image 설치. 5종(train 4 + unseen 1) 구성은 P01-04 설계 시 VRAM 적합성 보고 후 확정. 외부 AI 데이터셋 보완도 허용(라이선스·provenance 확인 조건).
- 사용자 결정(DB-03): 얼굴 처리 정책 = 옵션 A 무처리. 프롬프트 정합 + P06 재검 트리거로 위험 관리.
- 사용자 결정(환경 체계): venv 대신 Docker Compose로 전환. 계기: 이 머신에 P00 venv이 없어 재현성 문제를 직접 확인 + 소유자 제안. GPU 패스스루(`--gpus all` 컨테이너에서 3060 인식) 사전 검증 완료. `requirements.txt` 의존성 canonical 유지, Dockerfile이 이를 설치하므로 계약 변경 없음. 도중 venv 재구성을 시작했으나 완료 직후 결정으로 대체됨(설치 잔존물은 무해).

### (세션 2) P01-02 완료 — 카테고리·metadata schema 확정

- 설명: 계획 승인에 따라 P01-02 슬라이스를 수행했다.
- 파일 변경:
  - `scripts/analyze_kfashion_labels.py` (신규) — 라벨 zip 전수 분석 스크립트(stdlib만 사용, 경로 인자 방식). 대표 부위 규칙(원피스>아우터>상의>하의) 분포·look_group 후보 3단 파일명 패턴 비율 포함
  - `docs/project.md` (v1.1 → v1.2) — §12 metadata schema 개정: `product_id` 제거, `parts`·`style`·`look_group`·`prompt_id` 추가, 필드 규칙 명시
  - `src/dataset.py` — docstring의 CSV 컬럼 나열을 §12 v1.2로 갱신(동작 변경 없음)
  - `tests/test_dataset.py` — fixture 헤더·행을 v1.2 12열로 갱신 + 12열 리터럴 잠금 셀 추가(독립검증 H1 — 기존 3셀은 read_metadata가 소비하는 5열만 잠금, 나머지 7열은 미잠금이었음)
  - `docs/sot.md` — project.md v1.2 버전 로그 추가
  - `Dockerfile`·`compose.yaml`·`.dockerignore` (신규) — Docker Compose 실행 환경(dev 서비스, /data 읽기전용 마운트, DATA_DIR 오버라이드)
  - `README.md` — Training 방법 Docker 명령으로 교체, Dataset 구성에 카테고리 4부위·DB-02/DB-03 반영
  - `docs/plan/phase_1_data_pipeline.md`·`docs/plan/00_index.md`·`docs/decision_briefs/00_index.md`·DB-02·DB-03 — 결정 해결·P01-02 완료·수치 정정 반영
- 검증: 스크립트 전수 재실행(967,806 JSON, 오류 0) 결과가 계획서 수치와 일치 — 대표 부위 상의 54.4%/원피스 19.0%/아우터 17.4%/하의 8.9%/라벨없음 0.4%, 부위별 카테고리 21종. 정정 2건: 스타일 스트리트 비중 46.5%→46.4%(반올림), 파일명 3단 패턴 비율을 샘플 기준 42%(접두사 매치)에서 전수 23.1%(3단 패턴 매치)로 교체 — 재현 가능한 스크립트 기준 수치로 통일. 환경 검증: `docker compose run --rm dev` 에서 pytest 10 passed(exit 0) + smoke 정상 종료(checkpoint 저장·"smoke ok") — venv 임시 검증(10 passed) 후 컨테이너 기준 최종 확인.
- 효과: P01 데이터 설계의 전제(카테고리·스키마·생성기·얼굴 정책)가 전부 확정. 다음 슬라이스는 원천 이미지 수신 완료 후 P01-01·P01-03.

### (세션 2) P01 독립검증(초회) 결과 반영 — B1 정정 + hardening H1~H6

- 설명: 소유자 지시로 독립검증(서브에이전트 1개, 검증 대상 미작성)을 수행했다. 판정 **조건부 합격** — blocking 1건(B1), 비차단 hardening 6건(H1~H6). P00 관례에 따라 비차단 항목까지 전부 보강했다. 기록: `docs/verifications/2026-10-07/p01_plan_schema_docker.md`.
- 보강 내역:
  - B1: `docs/plan/phase_1_data_pipeline.md`:30 "스트리트 편중(46.5%)" → 46.4% 정정. 정정 커밋(28189d8)이 :20만 고치고 :30을 누락했던 것.
  - H1: `tests/test_dataset.py` — §12 v1.2 12열 리터럴 잠금 셀(`test_metadata_fixture_locks_schema_v12_columns`) 추가. 검증자 MU1이 기존 3셀은 소비 5열만 잠금(나머지 7열 미잠금)임을 입증.
  - H2: work log Next steps 스테일 3항(승인 대기·P01-02 대기·venv 재구성) 재작성.
  - H3: fixture 값을 §12 규약에 정합(REAL=kfashion/상의/스트리트/look_group, Generated=gen_a/prompt_id).
  - H4: `scripts/analyze_kfashion_labels.py` MALL_FILENAME 정규식을 jpg/jpeg/png 대소문자 무관으로 확장(현 코퍼스는 jpg/JPG뿐 — 수치 불변 확인).
  - H5: `part_attr_anomaly`(카테고리 없는 부위 항목 77,754건) stdout 요약 출력 추가.
  - H6: `docs/project.md` §3 — 카테고리 확정 결과(4부위) 역참조 추가(위임형 문구 대체).
- 검증(보강 후): 컨테이너 pytest 11 passed(신규 셀 포함) + 분석 스크립트 재실행 수치 불변(3단 패턴 224,002/23.1%, 이상 항목 하의 32,906·상의 29,857·아우터 9,550·원피스 5,441 — 검증자 수치와 일치).

### (세션 2) 보강 가드 self-mutation 확인 (커밋 2912777 후 실시)

절차: 커밋 후 `git status --short` clean 확인 → mutate → 잠금 셀만 컨테이너 실행(`docker compose run --rm dev python -m pytest tests/test_dataset.py::test_metadata_fixture_locks_schema_v12_columns -q`) → 재실패 확인 → `git checkout -- tests/test_dataset.py` 복원 → clean 확인. 최종 전체 스위트 11 passed.

| mutation | 적용 위치 | 재실패한 셀 |
| --- | --- | --- |
| MU-A' `style` 컬럼 제거(HEADER+REAL/GEN 행 — 검증자 MU1과 동일 변형) | `tests/test_dataset.py` (HEADER·row) | `test_metadata_fixture_locks_schema_v12_columns` (확정 — H1 셀이 잠금) |
| MU-B' 헤더에서 `parts`↔`source_type` 순서 교환 | `tests/test_dataset.py` (HEADER) | `test_metadata_fixture_locks_schema_v12_columns` (확정 — 순서 잠금) |

### (세션 2) P01 재검증 결과 — 최종 합격

- 재검증(동일 검증자, 커밋 범위 `b3754fb..78d27c3`): **합격** — B1·H1~H6 전건 해소 확인(계획서 잔여 46.5% 0건), 스크립트 전수 재실행 수치 불변(H4 정규식 확장에도 3단 패턴 224,002/23.1%), 컨테이너 pytest 11 passed(exit 0).
- 가드 독립 재입증: 검증자가 구현자 self-mutation과 **다른 변형** 3종을 재유도 — RV1 `prompt_id` 컬럼 제거·RV2 13열(`product_id`) 추가·RV3 REAL 행만 `split` 필드 결손 — 전부 신규 잠금 셀 단독 확정 재실패(제거·추가·행 수준 방향 각각 입증).
- 잔여 관찰(비차단): 12열 리터럴 고정은 의도된 잠금 — 스키마 v1.3 확장 시 셀·리터럴·§12를 같은 변경으로 갱신. GPU 패스스루 사전 검증 주장은 GPU 점유 정책상 검증자 재현 불가 — P01-04 GPU 서비스 추가 시점 실동작 확인.
- 기록: `docs/verifications/2026-10-07/p01_plan_schema_docker.md`(초회 조건부 합격 보존 + 재검증 최종 합격).

### (세션 2) 원격 SSH 전환·push (소유자 지시)

- 소유자가 SSH 설정 전환과 push 를 명시적으로 지시했다(2026-10-07). CLAUDE.md §6 "Never push" 는 소유자가 push 시점을 통제하기 위한 규칙이므로 명시적 지시에 의한 push 는 규칙의 의도와 충돌하지 않는다(2026-10-07 P00 세션과 동일한 해석).
- 이 머신(=P01 작업 머신)은 HTTPS 로 clone 되어 있었다. 기존 SSH 키(`~/.ssh/id_ed25519` 등)로 `ssh -T git@github.com` 인증 성공(entangelk) 확인 → origin URL 을 `git@github.com:entangelk/Tracepecter.git` 로 전환.
- push: `f3981d1..7628f56 main -> main`(fast-forward, 세션 2 커밋 6건 — P01 계획서·P01-02·독립검증 보강·재검증 기록). push 후 main 과 origin/main 동기화 확인.

### (세션 3) P01-01 완료 — 원천 데이터 수신 확인·정합 검증

- 설명: 소유자의 다운로드 완료 통보(2026-10-07 저녁)에 따라 P01-01을 수행했다. Training 원천 3파트(17.8+28+13.6GB) + Validation 수신 확인(임시파일 잔여 없음).
- 검증 결과:
  - 구조: 원천 zip은 라벨과 동일한 스타일 폴더 + 이미지 식별자(stem) 네이밍 — `기타/1070263.jpg` ↔ `기타/1070263.json`. 라벨의 `이미지 파일명`(원본 파일명)은 provenance 정보.
  - 정합: 스타일 집합 24종 일치 · 확장자 전부 `.jpg` · 라벨 stem 967,806 == 이미지 stem 967,806 · **매핑 불일치 0.0000%**(양방향 차집합 0).
  - 무결성: 각 zip 무작위 10장씩 PIL verify → 30/30 정상. 이미지 800px 기준(롱사이드).
  - zip 샤딩: _1=9개 스타일, _2=스트리트 단독(449,494), _3=14개 스타일. 스타일별 단일 zip 수용.
- 구현 결정: "zip 해제" 산출물을 **전량 해제가 아닌 선택적 추출**로 조정 — 필요량 Real ≤5,000장(§7)인데 1.2M장 60GB 전량 해제는 불필요. 완료 기준(불일치 보고·유효 수 확정)은 충족. 조정 사유는 계획서 비고에 기록.
- 파일 변경: `docs/plan/phase_1_data_pipeline.md`(P01-01 완료 처리·비고 3건), `HANDOFF.md`, `CHANGELOG.md`, 본 로그.


## Issues found

- **BCELoss dtype 불일치 (해결)**: DataLoader 가 python float label 을 float64 로 collate해 `BCELoss` 가 `Found dtype Double but expected Float` 로 실패. `src/train.py` 학습 루프에서 `labels.to(probabilities.dtype)` 로 수정. 발견 경로: 최초 smoke 실행 실패(pytest 2 failed) → 수정 후 9 passed.
- **H7 재구성 회귀 (해결)**: `run_training` 분리 중 `smoke ok` 출력이 누락되어 CLI 계약 셀 2개(`test_train_smoke_creates_checkpoint`·`test_train_cli_command_runs_clean`) 재실패 — 보강 변경 자체의 회귀를 기존 가드가 포착한 사례. 출력 복원 커밋으로 해결, 10 passed.
- **프로세스 교훈**: `pytest | tail` 파이프로 exit code 가 가려진 채 실패 상태에서 커밋이 진행됨(직후 발견·수정). 이후 pytest 실행은 exit code 를 명시적으로 확인한다.

## Decisions

- 페이즈 ID는 `docs/project.md` §27–§28 번호와 1:1 매핑(P00~P07). 이유: 매핑 테이블 없이 원문 추적이 가능하다. P07은 번호 없는 §28 "데모 구축"에 부여.
- 상세 페이즈 문서는 P00만 작성하고 P01~P07은 인덱스 등록에 그침. 이유: 데이터 소스·생성기 선정 등 미결정 사항이 있어 지금 상세를 쓰면 투기적이 된다(작성 시점: 착수 직전).
- git init을 오늘 작업에 포함하지 않고 P00-01 슬라이스로 이관. 이유: project.md Phase 0 완료조건에 속하는 작업이고, 사용자가 요청한 것은 문서 부트스트랩이며 커밋은 요청 시에만 수행하는 기본 원칙.
- 사용자 결정(세션 2): GPU(RTX 3060)는 소유자의 다른 AI 모델 작업이 점유 중. 학습·생성 등 GPU 작업은 그 작업 종료 후 남는 시간에만 수행하고, 여유 전에는 큐에 쌓지 않는다. DB-02·P01 계획서 비고에 반영.
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

### GitHub 원격 연결 및 push (소유자 지시)

- 소유자가 `https://github.com/entangelk/Tracepecter.git` 연결과 push 를 명시적으로 지시했다(2026-10-07). CLAUDE.md §6 "Never push" 는 소유자가 push 시점을 통제하기 위한 규칙이므로, 소유자의 명시적 지시에 의한 이번 push 는 규칙의 의도와 충돌하지 않는다. 향후 push 도 소유자 지시 시에만 수행한다.
- 원격은 이미 origin 으로 등록되어 있었다(HTTPS). HTTPS push 는 credential 부재 + 깨진 VS Code askpass 소켓으로 실패 → SSH key 인증(`ssh -T git@github.com` 성공)을 확인해 origin URL 을 `git@github.com:entangelk/Tracepecter.git` 로 전환 후 `git push -u origin main` 성공(HEAD 10c561d).
- push 범위: 8개 커밋 전체. `docs/guides/`, `CLAUDE.md`, `AGENTS.md` 는 .gitignore 로 제외(로컬 작업 지침).

## Next steps

- 소유자(진행 중): K-Fashion 원천 이미지 다운로드 완료 — P01-01(원천 정합 검증)·P01-03(REAL metadata 빌드) 착수 조건
- P01-04 설계(생성기 5종 구성·VRAM 12GB 적합성 보고) — 본 생성은 GPU 여유 시점에만
- 관측(이 머신, 2026-10-07): `/mnt/f/data` 다운로드 진행 중(원천데이터_1 부분 수신 상태).

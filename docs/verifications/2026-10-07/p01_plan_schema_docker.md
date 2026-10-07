# P01 계획서·라벨 전수 분석·schema v1.2·Docker 전환 독립검증 기록

## Subject metadata

- 검증 일자: 2026-10-07
- 요청자: 소유자(독립검증 지시 — 반증 목표)
- 검증자: 독립 검증 서브에이전트(검증 대상 작업 미작성)
- 대상: P01 상세 계획서 승인·P01-02 슬라이스(카테고리 4부위·metadata schema §12 v1.2 확정)·DB-02/DB-03 해결·실행 환경 venv→Docker Compose 전환
- canonical spec 참조:
  - `docs/project.md` v1.2 — §3·§8·§9·§12(스키마)·§13·§14·§27 Phase 1
  - `docs/plan/phase_1_data_pipeline.md`(승인된 P01 계획서)
  - `docs/decision_briefs/DB-01·DB-02·DB-03` + `docs/decision_briefs/00_index.md`
  - `docs/plan/00_index.md`, `docs/sot.md`(버전 로그), `HANDOFF.md`, `CHANGELOG.md`, `docs/daily_logs/2026-10-07/work_log.md`
  - 절차 SoT: `docs/guides/records-and-handoff.md`(로컬), `docs/guides/phase-and-decision-briefs.md`(로컬), `docs/guides/verification.md`(로컬)
- 검증 대상 소스: commit `d774505` → `b3754fb`(HEAD), 범위 `git log f3981d1..b3754fb` 3커밋. pre-flight `git status --short` 빈 출력(clean tree) — mutation 은 clean-tree branch(`git checkout --` 복원)로 수행.
- 제약 준수: GPU 미사용(`--gpus`·CUDA 실행·nvidia-smi 전무), `/mnt/f/data` 쓰기 없음(컨테이너 `/data` 마운트는 읽기 전용이며 미접근), 검증자 git commit/push 없음.

## Scope

1. **스크립트 재현성(핵심)** — 원본 라벨 zip↔/tmp 복사본 sha256 일치 확인 후 `scripts/analyze_kfashion_labels.py` 전수 재실행, 계획서 "라벨 분포 분석 결과" 수치와 전수 대조
2. 스크립트 자체 결함 — 정규식(확장자·대소문자)·라벨링 구조 이상 케이스 처리가 특정 셀을 왜곡하는지 실제 zip 전수 탐색
3. 스키마 일관성 — §12 v1.2 필드 12개 == `src/dataset.py` docstring == `tests/test_dataset.py` HEADER == 계획서 schema 표 교차 확인, §13·§14 모순 여부, 표기 규약(`|`·소문자) 일관
4. 가드 실효성 — fixture "스키마 호환성 가드" 주장의 mutation 검증(컬럼 제거 → 셀 재실패 짝표)
5. Docker 환경 — Dockerfile·compose.yaml·.dockerignore·requirements.txt 상호 정합 + 문서화된 검증 명령 2종 재실행(exit code 확인)
6. 브리프·인덱스 규칙 — DB-02·DB-03의 가이드 준수(옵션 표 보존·Resolution 요소·양방향 링크), DB-01 후속 반영
7. 페이즈·기록 규칙 — 인덱스/계획서 상태 일치, HANDOFF 규칙(검수 헤더 줄 수·완료 서술·머신 로컬 관측 날짜 표기), sot.md 버전 로그, CHANGELOG 링크, 마크다운 링크 전수 확인
8. 과거 기록 훼손 여부 — work log 섹션 계층·세션 2 시간순 서술 점검

## Methodology

모든 명령은 repo root `/mnt/f/devel/Tracepecter`에서 실행. 호스트 python3에는 torch 부재(venv 폐기·Docker 전환의 직접 귀결)이므로 테스트 실행은 전부 `docker compose run --rm dev`로 수행했다.

### 재현 명령(전체 흐름은 하단 Reproduction 참조)

```bash
# 1) 무결성: 원본↔복사본 sha256 (원본은 9p 읽기 수 분 소요)
sha256sum "/mnt/f/data/K-Fashion 이미지/Training/라벨링데이터.zip" /tmp/kfashion_labels.zip
# 2) 전수 재실행(약 2분)
python3 -I scripts/analyze_kfashion_labels.py /tmp/kfashion_labels.zip --out /tmp/kfashion_stats_verify.json
# 3) 엣지 케이스 전수 탐색(검증자 작성 /tmp 스크립트 — Reproduction 참조)
# 4) Docker
docker compose build && docker compose run --rm dev python -m pytest -q
docker compose run --rm dev python -m src.train --config configs/baseline.yaml --smoke
docker run --rm tracepecter/dev python -m pytest -q   # 볼륨 없는 이미지 단독 실행
# 5) mutation(pre-flight: git status --short 빈 출력 → mutate → 컨테이너 내 셀 실행 → git checkout -- <path> → status 재확인)
```

### 수치 대조 기준

계획서 수치는 텍스트 그대로 읽었고, 스크립트 출력(stdout 요약 + `--out` JSON 양쪽)과 항목별로 대조했다. 백분율은 스크립트의 버림/반올림(`{:.1%}`)과 무관하게 검증자가 원시 카운트/967,806을 독립 재계산했다.

## Findings

### 표면 1 — 스크립트 재현성(핵심)

**sha256 일치**: 원본 `/mnt/f/data/K-Fashion 이미지/Training/라벨링데이터.zip`과 작업자 복사본 `/tmp/kfashion_labels.zip` 모두 `63b9fb8a4e94b73cc696c4a595b127e86dc476894a94e5d0f720c8bece708dba`(1,100,882,640 bytes). 복사본으로 전수 재실행했다.

**전수 재실행 결과 vs 계획서 수치** — 전 항목 일치:

| 항목 | 스크립트 재실행 | 계획서(줄) | 판정 |
| --- | --- | --- | --- |
| JSON 총·파싱 성공·오류 | 967,806 · 967,806 · 0 | 967,806·오류 0(:10) | 일치 |
| 대표 부위 분포 | 상의 526,450(54.4%)·원피스 183,572(19.0%)·아우터 168,380(17.4%)·하의 85,822(8.9%)·라벨없음 3,582(0.4%) | :27 | 일치 |
| 부위 라벨 존재 | 상의 617,304(63.8%)·하의 557,589(57.6%)·원피스 183,572(19.0%)·아우터 179,274(18.5%) | :18 | 일치 |
| 부위 조합 | 16종, 최다 `상의+하의` 368,336(38.1%) | :18 | 일치 |
| 부위별 카테고리 값 | 원피스 2종·아우터 7종·상의 7종·하의 5종(합·union 모두 21종) | :19, :29 | 일치 |
| 스타일 분포 | 스트리트 449,494(46.4%)·페미닌 9.1%·리조트 8.6%·모던 8.3%·로맨틱 7.6% | :20 | 일치 |
| `기타` 폴더 | 4,400건, 스타일 라벨값 부재(`?` 버킷 4,400) | :20 | 일치 |
| 파일명 3단 패턴 | 224,002(23.1%) | :21 | 일치 |
| 스타일 폴더 종류 | 24종 | :17 | 일치 |

**단 1건 불일치 — 계획서 :30 "스트리트 편중(46.5%)"**. 재실행 값은 46.4%(449,494/967,806 = 46.45%). git 이력으로 경위 확인: `d774505`의 계획서에는 :20과 :30 양쪽에 46.5%가 있었고, 정정 커밋 `28189d8`은 :20(→46.4%)과 :21(샘플 42%→전수 23.1%)만 고치고 **:30을 누락**했다. work log :111의 "재현 가능한 스크립트 기준 수치로 통일" 주장은 계획서 내에서 완결되지 않았다 → **Blocking B1**.

### 표면 2 — 스크립트 자체 결함 탐색

검증자가 별도 전수 스캔(967,806 JSON 재주회)으로 반례를 찾았다:

- **파일명 확장자 정규식**(`scripts/analyze_kfashion_labels.py:24`): `[JjPp][PpNn][Gg]`는 .jpg/.png(대소문자 무관)만 매치하고 **.jpeg는 누락**. 그러나 실제 코퍼스 전수 확인 결과 파일명 확장자는 `jpg` 794,139 + `JPG` 173,667 = 967,806뿐(png·jpeg·기타 0건) — 현재 데이터셋에서 누락 영향 0. `.JPG` 대소문자는 정상 처리. → H4(재사용 시 확장 권장).
- **파일명 출처 필드**(:83-87): `데이터셋 정보.파일 이름` → `이미지 정보.이미지 파일명` fallback. 전수 확인 결과 967,806 전부 첫 필드로 해결(fallback 미발동, 결측 0) — 3단 패턴 23.1% 셀 왜곡 없음.
- **빈 dict 엔트리 처리**(:70): 라벨링의 4개 부위 키는 **모든 JSON에 리스트로 존재**(대체 의미론 프로브: key 존재만으로는 4부위 모두 967,806 = 100%가 되어 대표 부위 규칙 붕괴). 실제 엔트리의 상당수가 빈 dict `{}`(전수 2,333,485개)이며, 스크립트의 "비어있지 않은 dict 존재 = 부위 라벨 존재" 판정이 없으면 계획서 수치 전체가 성립하지 않는다. 처리는 정확하고 필수적.
- **카테고리 없는 항목**(:74-78): 부위 엔트리 중 `카테고리` 키 없는 것 77,754건(하의 32,906·상의 29,857·아우터 9,550·원피스 5,441 — 샘플 확인 결과 주로 `기타` 폴더의 색상·소매기장 전용 항목). 이들은 부위 존재에는 포함되되 카테고리 값 집계에서 제외 — 21종 집계의 정합한 의미론.
- **구조 이상**: `라벨링` 키 비dict 0건, 부위가 리스트 아닌 경우 0건, `.JSON` 대문자 엔트리 0건(zip 총 엔트리 967,830 = .json 967,806 + 확장자 없는 디렉터리 엔트리 24개, 정상 스킵).
- `기타` 폴더의 스타일 표기: 스타일 리스트 첫 항목이 빈 dict → `?` 버킷 4,400. 계획서 :20 "스타일 라벨 부재" 서술과 일치.
- 관찰(비차단): `part_attr_anomaly` 카운터는 `--out` JSON에만 존재하고 stdout 요약(`print_summary`, :111-133)에는 미출력 — 재현성에는 문제없으나 위 이상 케이스 가시성이 요약에 없다 → H5.
- `이미지 식별자` 필드(§12 image_id 매핑의 전제, 계획서 :38): 실제 JSON에서는 `이미지 정보.이미지 식별자`에 존재하며 샘플 3건 모두 zip 엔트리 stem과 일치(예: `기타/1070263.json` → 1070263). 매핑 전제 성립.

**결론: 스크립트 결함으로 수치가 왜곡된 셀은 없다.**

### 표면 3 — 스키마 일관성

§12 v1.2의 12필드가 4개 표면에서 문자 그대로 일치(순서 포함):

| 표면 | 위치 | 필드 수 |
| --- | --- | --- |
| `docs/project.md` §12 REAL/Generated 예시 | :409-423, :426-442 | 12/12 |
| `src/dataset.py` docstring | :3-4 | 12/12 |
| `tests/test_dataset.py` HEADER | :12-15 | 12/12 |
| 계획서 schema 표 | :36-50 | 12/12(+`product_id` 취소선 행) |

- 순서·명칭 완전 일치: `image_id,path,label,category,parts,source_type,source_domain,generator,style,look_group,prompt_id,split`.
- `product_id` 제거: §12 본문(:405)·계획서(:50 취소선)·sot.md 버전 로그(:49)에 일관. DB-01 후속(:27) 이행.
- §13·§14 모순 없음: `look_group` 필드 규칙(:449 "동일 인물·룩 그룹 키(파일명 유래 또는 pHash 클러스터). §13·§14 split 기준")은 §13(pHash+embedding 유사중복 → 동일 split 배정)·§14(group split 기준 4종 + unseen test)과 정합. 계획서 :47와도 일치.
- 표기 규약: `parts` 다중값 `|` 구분 — §12:448·계획서 :42·fixture `상의|하의`(:34) 일치. `source_type` 소문자 `real`/`generated` — §12 예시·fixture(:28, :34) 일치.
- 관찰(비차단): project.md §3(:51)은 "최종 목록은 P01에서 라벨 분포를 확인한 뒤 확정한다"는 위임형 문구로 남아, 확정 결과(4부위)는 §12 필드 규칙(:447)과 계획서에만 존재. 위임 자체는 이행된 것이라 모순은 아니나 §3에서 역참조가 없다 → H6.

### 표면 4 — 가드 실효성(fixture "스키마 호환성" 주장)

work log :106은 fixture 12열 갱신을 "스키마 호환성 가드 유지"로 기술했다. mutation으로 반증 시도(pre-flight `git status --short` 빈 출력 확인 후 수행, 컨테이너 내 셀 실행):

| Mutation | 내용 | 재실패한 셀 | 판정 |
| --- | --- | --- | --- |
| MU1 | fixture에서 `style` 컬럼 제거(HEADER+행) | **없음** — `tests/test_dataset.py` 3셀 전부 통과(3 passed) | 12열 중 7열(`parts`·`source_domain`·`generator`·`style`·`look_group`·`prompt_id`·`split`)은 아무 셀도 잠그지 않음 |
| MU2 | fixture에서 `category` 컬럼 제거 | `test_read_metadata_parses_all_rows` + `test_dataset_returns_image_and_float_label`(KeyError, 2 failed) | `read_metadata`가 읽는 5컬럼 경로는 유효 잠금 |

즉 "전체 스키마 파싱 호환성" 잠금은 실제로는 **소비하는 5컬럼에만** 성립한다. `MetadataRow`(`src/dataset.py:21-27`)는 5필드만 투영하므로 나머지 7열은 파싱 검증 대상이 아니다. P01-02 슬라이스 계약(완료 확인 = 스크립트 재실행 일치 + §12 개정 반영, 계획서 :57)이 전체 12열 잠금 셀을 요구하지는 않으므로 blocking은 아니나, work log의 가드 범위 서술은 과장이다 → **H1**. 매 mutation 후 `git checkout -- tests/test_dataset.py` 복원 + `git status --short` 빈 출력 확인, 복원 후 전체 스위트 10 passed 재확인.

### 표면 5 — Docker 환경

- 상호 정합: `Dockerfile`은 torch/torchvision CPU wheel 선행 설치(:8-9) 후 `requirements.txt`(:11-12) 설치 — requirements에 torch/torchvision이 포함되지만 이미 설치된 버전이 하한(`>=`)을 충족하므로 정합. `COPY . /app`(:14)과 `.dockerignore`(docs/·data/·checkpoints/·demo/ 등 제외) 조합이 이미지 실행에 필요한 파일을 빼지 않는지 **볼륨 마운트 없는 이미지 단독 실행**(`docker run --rm tracepecter/dev python -m pytest -q`)으로 검증 → 10 passed, exit 0.
- `docker compose build`: 전 단계 캐시 히트로 완료(exit 0) — 기존 이미지(20분 전 빌드)가 현재 clean tree 컨텍스트와 일치함을 확인.
- **문서화된 검증 명령 재실행(리다이렉트 후 `$?` 확인)**:
  - `docker compose run --rm dev python -m pytest -q` → **exit 0, 10 passed**(work log :111·HANDOFF :9 "10 cells" 주장과 일치)
  - `docker compose run --rm dev python -m src.train --config configs/baseline.yaml --smoke` → **exit 0**, `epoch 1/1 train_loss=0.697491` + checkpoint 저장 + `smoke ok`(b3754fb 커밋 주장과 일치)
- compose.yaml은 소스를 `.:/app`으로 마운트(:18)하므로 런타임은 live tree 기준. `/data` ro 마운트(:19)·GPU 서비스 미구성(:10-11, 정책과 정합). 검증 전 과정에서 GPU 점유 시도 없음.
- README(:21-33)의 Docker 명령 4종이 compose.yaml과 정합.

### 표면 6 — 브리프·인덱스 규칙

- DB-02·DB-03: `git diff d774505 28189d8`로 확인 — 옵션 표(A~D)는 변경 없이 보존되고 `Status` Open→Resolved와 `Resolution` 절(선택·일자·근거·반영 4요소, DB-02 :41-46·DB-03 :41-46)만 추가. 가이드 "After a decision" 절차 준수.
- 양방향 링크: 계획서 → 브리프(:86-88), 브리프 → 계획서·인덱스(Resolution 반영 필드), `docs/decision_briefs/00_index.md`(:8-9)·`docs/plan/00_index.md`(:8)에서 링크. 전부 실재 파일로 해결(링크 전수 검사 참조).
- 인덱스 상태 일치: `docs/plan/00_index.md` :8 P01 In Progress ↔ 계획서 슬라이스 표 :57 P01-02 "완료 (2026-10-07)"·나머지 Planned ↔ `docs/decision_briefs/00_index.md` :13 "대기 중인 사항 없음". 모순 없음.
- DB-01 후속 이행: ①얼굴 정책 → DB-03로 결정(Resolved, 무처리 — DB-01 :24 이행) ②`product_id` 조정 → §12 v1.2에서 제거(DB-01 :27 이행) ③provenance 기록 → 계획서 비고 :95("provenance는 `source_domain`·`style` 필드와 work log로 기록"). 3건 전부 반영.

### 표면 7 — 페이즈·기록 규칙

- HANDOFF.md: 검수 헤더 ":3 · 25줄" — `wc -l` = 25로 정확. 이번 세션 diff(`f3981d1..b3754fb`)는 순수 추가가 아니라 venv 항목·구 다음 작업의 삭제+재작성(스냅샷 규칙의 "diff 확인" 준수). "P01-02 완료(…)"(:8)는 페이즈 상태 bullet 내 위치 지정 서술로, 다음 작업자가 P01-02를 재수행하지 않게 하는 현재 상태 기술 — P00 Complete 줄(:7, 선행 관행)과 같은 형태라 허용 범위로 판정. 머신 로컰 관측(GPU 점유 :21, 9p 속도 :22)은 전부 날짜 표기 동반.
- `docs/sot.md` :49: project.md v1.2 행 등재(변경 요약·근거·계획서 링크) 확인.
- CHANGELOG :12-14: 3개 엔트리 추가, 링크 유효.
- **마크다운 링크 전수 검사**: 검증자 스크립트로 repo 내 .md 파일의 상대 링크 64개 전수 확인 — **전부 해결, 깨진 링크 0건**(외부 http 링크는 DB-02 :15 조사 링크 2개로 대상에서 제외, 브리프 스스로 "재확인 필요" 명시).

### 표면 8 — 과거 기록 훼손 여부(work log)

- 섹션 계층 온전: Goals(:3) / Completed work(:8) / Issues found(:115) / Decisions(:121) / Next steps(:147) 전부 존재, 파손 흔적 없음. b3754fb의 1줄 수정도 P01-02 검증 서술 내용 추가가 원위치 반영(섹션 구조 무관).
- 세션 2 시간순: 라벨 전수 분석(:69) → 계획서·브리프 작성(:79) → 소유자 결정(:92) → P01-02 완료(:99) → (재검증 계열 Decisions·push 기록은 그보다 앞선 시점 사항으로 Decisions 내 위치) — 자연스럽다.
- **단, Next steps 섹션(:147-152) 4개 중 3개가 스테일**: ":149 소유자: P01 계획서 검토·승인 + DB-02·DB-03 결정"(같은 로그 :92-97에서 완료로 기록됨), ":151 작업자(승인 후): P01-02 즉시 착수 가능"(:99-112에서 완료), ":152 P00 venv 부재 — venv 재구성 필요"(Docker 전환으로 대체됨, :97). 로그 말미만 읽는 독자에게 대기 중인 소유자 결정이 있는 것처럼 보인다. 갱신된 다음 단계는 같은 로그 :112(효과 필드)과 HANDOFF에 존재하므로 실질 정보 상실은 없다 → **H2**(기록 위생, 비차단).

## Issues / Risks

### Blocking (계약 위반)

- **B1 — 계획서 수치 잔여 불일치**: `docs/plan/phase_1_data_pipeline.md:30` "스트리트 편중(46.5%)"이 전수 재실행 값 46.4%(449,494/967,806)와 불일치. 정정 커밋(`28189d8`)이 :20·:21은 고치고 :30을 누락했다. 동일 문서 내 동일 통계의 내부 모순으로, work log :111의 "스크립트 기준 수치로 통일" 주장을 계획서가 배반한다. 수정은 1글자("46.5"→"46.4").

### Hardening recommendations (비차단)

1. **fixture 12열 잠금 실질화**(MU1 입증): `tests/test_dataset.py`의 "스키마 호환성 가드"는 `read_metadata`가 읽는 5컬럼에만 성립. §12 v1.2 12열 리터럴(헤더 문자열 또는 컬럼 집합)을 직접 검증하는 셀 추가를 권장 — P01-03 `build_metadata.py`가 12열을 생성하는 시점에 특히 필요. work log :106의 가드 범위 서술도 함께 정정할 것.
2. **work log Next steps 갱신**(:147-152): 스테일 3항(승인 대기·P01-02 착수 대기·venv 재구성)을 현재 상태(원천 수신 대기 → P01-01/P01-03, P01-04 설계)로 재작성. HANDOFF는 이미 정확하다.
3. **fixture 값의 §12 규약 정합**: fixture가 `source_domain="src"`(§12: real=`kfashion`, generated=`null`), `category="smoke"`(§12: 4부위 중 1)를 사용 — 구조 잠금에는 무결하나 값-도메인 규약을 같이 잡을 기회.
4. **MALL_FILENAME 확장자 화이트리스트 확장**(`scripts/analyze_kfashion_labels.py:24`): .jpeg 미커버. 현재 코퍼스엔 부재(전수 확인)라 수치 영향 0이나, P01-03 look_group 키 생성에서 같은 패턴을 재사용할 경우 `.jpe?g|\.png` 등으로 확장 권장.
5. **`part_attr_anomaly` 요약 출력**: 카테고리 없는 부위 항목 77,754건이 stdout 요약에 보이지 않고 `--out` JSON에만 존재. 요약에 한 줄 추가하면 이상 케이스 가시성이 올라간다.
6. **project.md §3 확정 결과 역참조**(:51): "최종 목록은 P01에서 확정한다" 위임형 문구에 확정 결과(4부위) 링크/명시 추가 — 모순은 아니나 §12·계획서만 뒤져야 결과가 나온다.

## Verdict

**조건부 합격** — 조건: 계획서 `docs/plan/phase_1_data_pipeline.md:30`의 "46.5%"를 스크립트 재현 값 "46.4%"로 정정(B1).

- 하중 요인:
  1. 핵심 주장인 라벨 전수 분석 재현성이 완전히 성립했다 — sha256 일치 원본 복사본으로 재실행한 결과, 계획서 수치 9개 항목(총량·대표 부위 5값·부위 존재 4값·조합 16종/최다값·카테고리 21종·스타일 상위·기타 4,400·파일명 패턴 224,002/23.1%·폴더 24종)이 전수 일치. 유일한 예외가 B1(같은 문서 :20의 정정본과 모순되는 잔여 1건).
  2. 스크립트 결함 탐색에서 왜곡 반례를 찾지 못했다 — 확장자는 jpg/JPG뿐(.jpeg 부재 전수 확인), 파일명 필드 단일 경로 전수 수렴, 빈 dict 제외 처리가 없으면 부위 존재가 100%가 되어 규칙 자체가 붕괴한다는 점에서 그 처리는 필수적이고 정확하다.
  3. §12 v1.2의 12필드가 4개 표면에서 문자 그대로 일치하고 §13·§14·표기 규약과 모순이 없다.
  4. Docker 전환 검증 명령 2종이 exit 0으로 재현됐고(10 passed·smoke ok), 이미지 단독 실행까지 통과해 .dockerignore 결함이 없다. 브리프·인덱스·기록 규칙(옵션 표 보존·Resolution 요소·양방향 링크·HANDOFF 25줄·sot v1.2·링크 64개 전부 해결)도 준수했다.
- H1(fixture 잠금 범위 과장)·H2(work log Next steps 스테일)는 기록 정합성 보강 사항이며 판정을 좌우하지 않는다.

## Outstanding items

- 본 검증 기록은 미커밋 상태로 남긴다(검증자는 commit 금지). 구현자가 B1 정정과 함께 커밋할 것.
- work log :97 "GPU 패스스루(`--gpus all`) 사전 검증 완료" 주장은 GPU 점유 정책(소유자 타 AI 작업)상 검증자가 재현하지 않았다 — 기록으로만 존재. P01-04 GPU 서비스 추가 시점에 실동작 확인 필요.
- 소유자의 K-Fashion 원천 이미지 다운로드 진행 중 — P01-01/P01-03은 수신 완료 후 착수(HANDOFF :14-15와 동일).
- 검증 산출물(/tmp): `kfashion_stats_verify.json`(전체 통계), 엣지 스캔·대체 의미론 프로브 결과, docker 실행 로그 4종. 세션 종료 시 소실 무방.

## Reproduction

```bash
cd /mnt/f/devel/Tracepecter
git status --short                # 빈 출력(clean) 확인
git rev-parse HEAD                # b3754fb8910da...

# 1) 무결성 — 원본 해시(수 분 소요) 후 복사본으로 재실행
sha256sum "/mnt/f/data/K-Fashion 이미지/Training/라벨링데이터.zip"   # 63b9fb8a4e94b73cc696c4a595b127e86dc476894a94e5d0f720c8bece708dba
sha256sum /tmp/kfashion_labels.zip                                  # 동일해야 함
python3 -I scripts/analyze_kfashion_labels.py /tmp/kfashion_labels.zip --out /tmp/stats.json
# → 상의 526450(54.4%)·원피스 183572(19.0%)·아우터 168380(17.4%)·하의 85822(8.9%)·<라벨없음> 3582(0.4%)
# → 상의 617304(63.8%)·하의 557589(57.6%)·원피스 183572(19.0%)·아우터 179274(18.5%)
# → 조합 16종·상의+하의 368336(38.1%) / 카테고리 2+7+7+5=21종 / mall 224002(23.1%) / 스트리트 449494(46.4%)
# B1 확인: docs/plan/phase_1_data_pipeline.md:30 은 46.5% (불일치)

# 2) Docker
docker compose build                                              # 캐시 히트로 exit 0
docker compose run --rm dev python -m pytest -q; echo $?          # exit 0, 10 passed
docker compose run --rm dev python -m src.train --config configs/baseline.yaml --smoke; echo $?   # exit 0, "smoke ok"
docker run --rm tracepecter/dev python -m pytest -q; echo $?      # exit 0, 10 passed (이미지 단독)

# 3) mutation (각 단계 후 git checkout -- tests/test_dataset.py && git status --short 는 빈 출력이어야 함)
# MU1: tests/test_dataset.py HEADER·행에서 style 컬럼 제거 → docker compose run --rm dev python -m pytest tests/test_dataset.py -q
#      → 3 passed (재실패 셀 없음 — H1 근거)
# MU2: 같은 방식으로 category 컬럼 제거 → 2 failed(test_read_metadata_parses_all_rows·
#      test_dataset_returns_image_and_float_label, KeyError) → git checkout 복원
docker compose run --rm dev python -m pytest -q                   # 복원 후 10 passed

# 4) 마크다운 링크 전수 검사(상대 링크 추출 → 파일 존재 확인 스크립트) → 64개 전부 해결
```

---

# 재검증 (보강 후) — 2026-10-07, HEAD 78d27c3

초회 판정 **조건부 합격**(B1 1건)의 조건과 hardening H1~H6을 구현자가 보강(`2912777`)하고 work log에 self-mutation 짝표를 반영(`78d27c3`)한 최종 상태에 대한 재검증이다. 초회 판정·수치 대조표·mutation 짝표는 위에 보존되어 있다. 재검증은 P00 관례에 따라 동일 검증자가 본 기록을 갱신한다.

## Subject metadata (재검증)

- 검증 일자: 2026-10-07 (재검증)
- 검증자: 초회 검증과 동일한 독립 검증 서브에이전트
- 검증 대상 소스: commit `78d27c3` (HEAD, 범위 `b3754fb..78d27c3`: `2912777` B1+H1~H6 보강, `78d27c3` work log 기록)
- pre-flight: `git status --short` 빈 출력 — clean tree. mutation 복원에 `git checkout -- <path>` 사용, 복원마다 status 재확인.
- 제약 준수(재검증 구간): GPU 미사용, `/mnt/f/data` 쓰기 없음, commit/push 없음(본 기록 갱신만).

## B1·H1~H6 해소 확인

| 항 | 확인 방법 | 결과 |
|---|---|---|
| B1 계획서 :30 46.5%→46.4% | `git diff b3754fb HEAD -- docs/plan/phase_1_data_pipeline.md` — :30 "스트리트 편중(46.4%)"로 정정, 문서 내 46.5% 잔여 0건(grep 확인) | **해소** |
| H1 §12 v1.2 12열 리터럴 잠금 셀 | `tests/test_dataset.py:59-72` 신규 셀 `test_metadata_fixture_locks_schema_v12_columns` — `SCHEMA_V1_2_COLUMNS` 리터럴(:18-21, §12 순서 그대로 12열)과 헤더 행 완전 일치 + 데이터 행 필드 수 == 12 검증. 모듈 docstring(:7-9)에 schema 가드 방향 등재. RV1~RV3 mutation(하단)으로 실효성 입증 | **해소** |
| H2 work log Next steps 재작성 | `docs/daily_logs/2026-10-07/work_log.md` — 스테일 3항(승인 대기·P01-02 착수 대기·venv 재구성) 삭제, 현재 상태 3항(원천 수신 대기·P01-04 설계·다운로드 관측)으로 교체. 머신 로컬 관측 날짜 표기 유지 | **해소** |
| H3 fixture 값 §12 규약 정합 | `tests/test_dataset.py:43-52` — REAL 행 `1,상의,상의|하의,real,kfashion,,스트리트,look_N,,train`, Generated 행 `0,원피스,원피스,generated,,gen_a,,,p01,train` — §12 예시의 값 규약(label 1/0, source_domain kfashion/공백, generator/스타일/look_group/prompt_id 배치)과 정합. `test_read_metadata_parses_all_rows`(:75-83)의 label 0/1·real/generated 단언도 새 fixture 값과 일치 | **해소** |
| H4 MALL_FILENAME 확장 | `scripts/analyze_kfashion_labels.py:26` → `^[A-Za-z0-9]+_\d+_\d+\.(?:[Jj][Pp][Ee]?[Gg]|[Pp][Nn][Gg])$` — jpg/jpeg/png 대소문자 무관. 기존 jng/ppg 허위 매치도 소멸. 전수 재실행으로 수치 불변 확인(하단) | **해소** |
| H5 이상 항목 요약 출력 | `scripts/analyze_kfashion_labels.py:133-136` `[부위 엔트리 이상]` 출력 — 재실행 결과 하의 32,906·상의 29,857·아우터 9,550·원피스 5,441(총 77,754)로 초회 검증자 전수 스캔 수치와 정확히 일치 | **해소** |
| H6 project.md §3 확정 역참조 | `docs/project.md:51` — 위임형 문구를 "4개 부위(상의·하의·아우터·원피스)로 확정(2026-10-07 승인)" + §12 필드 규칙·계획서 역참조로 대체. §3↔§12↔계획서 체인 완결 | **해소** |

기록 위생: 구현자의 self-mutation 짝표(work log 신규 섹션)는 mutation↔셀 짝을 행 단위로 기록 — records-and-handoff.md의 짝표 규칙 준수.

## Mutation 짝표 (재검증 — 검증자 재유도)

요청대로 구현자 self-mutation(MU-A' `style` 제거·MU-B' `parts`↔`source_type` 헤더 교환)과 **다른 변형**으로 재유도했다. 각 mutation 후 신규 셀만 컨테이너 실행, `git checkout -- tests/test_dataset.py` 복원, `git status --short` 빈 출력 확인.

| Mutation | 방향 | 내용 | 재실패한 셀 | 판정 |
|---|---|---|---|---|
| RV1 | under-strict | `prompt_id` 컬럼 제거(HEADER+양 행 템플릿 — 초회 MU1의 `style`과 다른 열) | `test_metadata_fixture_locks_schema_v12_columns`(확정, 단독) | H1 셀이 초회 미잠금 7열 영역을 실제로 잠금 |
| RV2 | over-strict | 13열 추가(`product_id` 부활 — HEADER+양 행) | `test_metadata_fixture_locks_schema_v12_columns`(확정, 단독) | 열 추가도 거부 — §12 12열 고정 잠금 |
| RV3 | 행 수준 | 헤더 12열 유지, REAL 행에서만 `split` 필드 제거(행 11필드) | `test_metadata_fixture_locks_schema_v12_columns`(확정, 단독) | 헤더 비교와 무관하게 행 필드 수 검증이 독립 작동 |

## 재실행 수치 (재검증)

- 무결성 재확인: 원본 `/mnt/f/data/K-Fashion 이미지/Training/라벨링데이터.zip` 재해시 = /tmp 복사본 = `63b9fb8a4e94b73cc696c4a595b127e86dc476894a94e5d0f720c8bece708dba`(초회와 동일).
- 스크립트 전수 재실행(H4 정규식 반영본): **수치 전항목 불변** — JSON 총 967,806·오류 0, 대표 부위 상의 526,450(54.4%)·원피스 183,572(19.0%)·아우터 168,380(17.4%)·하의 85,822(8.9%)·라벨없음 3,582(0.4%), 부위 존재 617,304/557,589/183,572/179,274, 조합 16종·최다 상의+하의 368,336(38.1%), 3단 패턴 **224,002(23.1%) — H4 확장에도 불변(코퍼스에 jpeg/png 부재 재확인)**, 스트리트 449,494(46.4%). 신규 `[부위 엔트리 이상]` 출력 4값(32,906·29,857·9,550·5,441)은 초회 검증자 독립 스캔과 일치.
- `docker compose run --rm dev python -m pytest -q` → **11 passed, exit 0**(신규 셀 포함, 10→11).
- 최종 전체 스위트(RV1~RV3 복원 후) 11 passed·exit 0, 트리 clean 재확인.

## Verdict (재검증 최종)

**합격**

- 이유(하중 요인):
  1. 초회 조건(B1 — 계획서 :30 46.5%)이 정정됐고, 계획서 전체에서 스크립트 재현 수치와 불일치하는 수치는 더 이상 존재하지 않다(전수 재실행 재확인).
  2. H1~H6이 전부 반영됐고, 신규 스키마 잠금 셀은 검증자가 구현자 self-mutation과 다른 3변형(RV1 컬럼 제거·RV2 13열 추가·RV3 행 수준 필드 결손)으로 재유도해 전부 확정 재실패 — §12 v1.2 12열의 제거·추가·순서·행 불일치 방향이 실제로 잠겼다.
  3. H4 정규식 확장이 기존 수치를 전혀 흔들지 않음(224,002/23.1% 불변)을 전수 재실행으로 입증했고, H5 이상 항목 출력값이 검증자 독립 스캔과 정확히 일치한다.
  4. 전체 스위트 11 passed·exit 0, 모든 mutation 복원 후 트리 clean.
- 잔여 관찰(비차단): RV2가 입증하듯 12열은 리터럴로 고정되어 있어 스키마 v1.3 확장 시 셀·리터럴·§12를 같은 변경으로 갱신해야 한다 — 이는 의도된 잠금 동작이며 조치 불필요.

## Outstanding items (재검증 시점)

- 본 기록의 재검증 섹션 갱신분은 미커밋 상태다(검증자는 커밋 금지). 구현자 검토 후 커밋할 것.
- 초회 Outstanding과 동일: GPU 패스스루 사전 검증 주장(work log)은 GPU 점유 정책상 검증자 재현 불가 — P01-04 GPU 서비스 추가 시점 실동작 확인. 원천 이미지 다운로드 진행 중(P01-01/P01-03 대기).
- 검증 산출물(/tmp): 재실행 stdout 로그, RV1~RV3 mutation 실행 로그. 세션 종료 시 소실 무방.

## Reproduction (재검증)

```bash
cd /mnt/f/devel/Tracepecter
git status --short                # 빈 출력(clean) 확인
git rev-parse HEAD                # 78d27c301764...

# B1·H 해소 확인
grep -n "46.5" docs/plan/phase_1_data_pipeline.md        # 무출력(46.4%로 정정됨)
docker compose run --rm dev python -m pytest -q; echo $?  # exit 0, 11 passed
python3 -I scripts/analyze_kfashion_labels.py /tmp/kfashion_labels.zip \
  | grep -E "3단 패턴|부위 엔트리" -A5                     # 224002(23.1%) 불변 + 이상 4값 출력

# mutation(각 case: git status --short 빈 출력 확인 → edit → 신규 셀만 실행 → git checkout 복원 → clean 확인)
# RV1: tests/test_dataset.py에서 prompt_id 컬럼 제거(HEADER+양 행) 후
docker compose run --rm dev python -m pytest tests/test_dataset.py::test_metadata_fixture_locks_schema_v12_columns -q  # 1 failed
git checkout -- tests/test_dataset.py
# RV2: HEADER+양 행에 13열(product_id) 추가 후 → 동일 셀 1 failed → 복원
# RV3: HEADER 유지, REAL 행의 split 필드만 제거(11필드) 후 → 동일 셀 1 failed → 복원
docker compose run --rm dev python -m pytest -q           # 복원 후 11 passed
```

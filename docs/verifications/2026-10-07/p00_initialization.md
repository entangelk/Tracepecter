# P00 — 프로젝트 초기화 독립검증 기록

## Subject metadata

- 검증 일자: 2026-10-07
- 요청자: 소유자(구현자 경유 지시 — "P00 독립검증")
- 검증자: 독립 검증 서브에이전트(구현물 미작성, 반박 목표로 검증)
- 대상 슬라이스: P00 — 프로젝트 초기화 (P00-01 git/환경, P00-02 골격/README/config, P00-03 학습 skeleton + 회귀 테스트)
- canonical spec 참조:
  - `docs/plan/phase_0_initialization.md` (슬라이스 계약 — 산출물·완료 확인·비고)
  - `docs/project.md` v1.1 §12(메타데이터 스키마)·§15(전처리/augmentation)·§16(baseline 모델)·§24(권장 repo 구조)·§25(config 관리)·§27 Phase 0(완료 조건)·§29(deliverables/README 필수 항목)
  - 절차 SoT: `docs/guides/verification.md`
- 검증 대상 소스: commit `f7362e6` ("P00: 프로젝트 초기화 — 환경·골격·config·학습 skeleton·회귀 테스트")
  - 단, working tree 가 clean 하지 않았음: `git status --short` → ` M HANDOFF.md` (미커밋 1줄 메타데이터 수정, "21줄"→"22줄"). 아래 Methodology·Outstanding items 참고.
- 재검증: 동일 검증자가 2026-10-07 hardening 7건 보강 후 재검증 수행 — 커밋 범위 `f787fe4` → `01fa039` (HEAD). 결과는 하단 "재검증(보강 후)" 절. 최종 판정은 해당 절의 Verdict.

## Scope

1. 슬라이스 계약(산출물·완료 확인 기준) 대비 산출물 존재·정합성 — P00-01/02/03 전 산출물
2. 스펙↔구현 리터럴 정합성 — §16 구조·freeze·sigmoid·loss·label, §12 CSV 스키마, §15 전처리, §25 config 키, §24 디렉터리, §29 README 항목, .gitignore 정책
3. 회귀 테스트 코드 자체 감사 — 셀별 계약 lock 여부, under-strict/over-strict 방향
4. Mutation testing — under-strict 4종 + over-strict 1종 + 방어제거 1종(지시된 6종) + 탐색 1종(M7), mutation↔재실패 셀 짝표
5. CLI 완료 확인 재실행 — smoke 명령·pytest 전체·의존성 import·YAML 파싱·git check-ignore
6. 복잡도·테스트 수행 시간 검토

## Methodology

공통: 모든 명령은 repo root `/mnt/d/devel/에베베/Tracepecter` 에서 venv `~/.venvs/tracepecter/bin/python`(CPU torch 2.14.1+cpu)로 실행.

### pre-flight

```bash
git status --short          # → " M HANDOFF.md" (clean 아님)
git rev-parse HEAD          # → f7362e61c... (검증 기준 커밋 일치)
git diff HANDOFF.md         # → 1줄 메타데이터 수정뿐(코드 무관)
```

**dirty tree 에 대한 절차 분기**: 지시문은 "clean 이 아니면 mutation testing 을 시작하지 말고 보고만 한다"고 기술했으나, 절차 SoT인 `docs/guides/verification.md` §"Mutation testing" restore-rule 표는 정확히 이 상황(verifier·커밋 금지·타인의 미커밋 작업 존재)에 **Branch 3: cp backup + 복원 + diff byte 비교** 절차를 규정한다.dirty 파일(HANDOFF.md)은 문서 1줄이며 mutation 대상(src/ 3파일, 모두 HEAD 와 clean 일치)과 분리되어 있으므로 가이드 Branch 3 으로 진행했다. 안전장치: mutation 전 3파일 cp backup → mutation → 해당 셀만 실행 → cp 복원 → `cmp` byte 동일 확인 → `git status --short` 가 매번 " M HANDOFF.md" 만 출력함을 확인. HANDOFF.md sha256 을 검증 전후로 비교해 동일함을 확인(`cc26fc98…`). 본 검증은 어떠한 git 상태 변경(commit·stash·checkout)도 하지 않았다.

### boundary matrix (코드를 열기 전 스펙 조항에서 추출)

| # | 계약 분기·리터럴 (출처) | 방향 | 잠금 수단 | 상태 |
|---|---|---|---|---|
| 1 | §16 head 스택 순서 Linear→GELU→Dropout→Linear(1)→Sigmoid | NOT fire(순서 변경 거부) | `tests/test_model.py::test_head_structure_matches_spec` | 잠김(M5·M1 확정 재실패) |
| 2 | §16 Sigmoid → 출력 범위 [0,1] | fire | `tests/test_model.py::test_output_is_probability` | 잠김*(M1 에 55%로만 재실패 — 아래 Findings) |
| 3 | §16/§17 encoder freeze·head 학습 대상 | fire/반전 거부 | `tests/test_model.py::test_encoder_grad_flags` | 잠김(M2) |
| 4 | §16 Loss = Binary Cross Entropy | 리터럴 | 코드 검증 `src/train.py:92` | 리터럴 존재 확인(전용 셀 없음 — Hardening) |
| 5 | §16 label REAL=1 / GENERATED=0 | 리터럴 | fixtures 일관(`tests/test_dataset.py:30`, `src/train.py:40`) + `test_read_metadata_parses_all_rows` | 잠김(파싱 수준. 데이터 계약 최종 lock 은 P01 metadata) |
| 6 | §12 CSV 8열 스키마 파싱 | fire | `test_read_metadata_parses_all_rows`(8열 헤더 fixture) | 잠김 |
| 7 | §12 path = CSV 기준 상대경로 해석 | fire | `test_dataset_returns_image_and_float_label` | 잠김 |
| 8 | §15 Resize·Normalization | fire | `test_transform_resizes_and_normalizes` | 부분 잠김(shape 확정·Normalize 는 흡수 — Findings) |
| 9 | §15 augmentation: Horizontal Flip·JPEG(config §25 키 게이트) | fire | `build_transform` 구성 로직 + smoke 전체 경로 | 잠김(§15 잔여 op 는 Findings) |
| 10 | §25 config 키 구조 5개 최상위 + 리터럴 값 | fire | `configs/baseline.yaml` 직접 검증 + smoke 테스트(키 누락 시 main() KeyError) | 잠김 |
| 11 | P00 방어: unknown encoder → ValueError | fire | `test_unknown_encoder_rejected` | 잠김(M6) |
| 12 | stub encoder 수용 | NOT fire | 전 model 셀이 stub 사용 | 잠김 |
| 13 | float64 collate ↔ float32 logits 정렬 | fire | 두 smoke 셀 | 잠김(M4) |
| 14 | checkpoint 저장 | fire | `test_train_smoke_creates_checkpoint` | 잠김(M3) |
| 15 | CLI 완료 확인 명령 무결 종료 | fire | `test_train_cli_command_runs_clean` + 검증자 재실행 | 잠김 |
| 16 | §24 디렉터리 구조 + `tests/` | 리터럴 | 검증자 직접 검사 | 확인(Findings 참고) |
| 17 | §29 README 필수 7항목 | 리터럴 | 검증자 직접 검사 7/7 | 확인 |
| 18 | .gitignore 대량 데이터 비추적 정책 | fire | `git check-ignore` 재실행 | 잠김 |
| 19 | P00-01 의존성 7종 import | fire | 검증자 재실행 | 확인 |

빈 셀(계약 요구 lock 부재) 없음. ※ 표의 "fire/NOT fire"는 verification.md §"boundary matrix" 용어.

### 재현 명령

```bash
~/.venvs/tracepecter/bin/python -m pytest                                   # 전체 스위트
~/.venvs/tracepecter/bin/python -m src.train --config configs/baseline.yaml --smoke
~/.venvs/tracepecter/bin/python -c "import torch, torchvision, transformers, yaml, numpy, PIL, pytest; print(torch.__version__)"
~/.venvs/tracepecter/bin/python -c "import yaml; print(yaml.safe_load(open('configs/baseline.yaml', encoding='utf-8')))"
git check-ignore -v data/raw/x.jpg data/processed/x.jpg data/smoke/x.jpg checkpoints/baseline/baseline.pt
git check-ignore -v data/metadata.csv   # exit 1 = 추적 대상(의도)
```

mutation: 각 case마다 `cp src/<파일> /tmp/backup/` → 소스 edit → `~/.venvs/tracepecter/bin/python -m pytest tests/<해당 파일>::<해당 셀> -q` → `cp /tmp/backup/<파일> src/<파일>` → `cmp` 로 byte 동일 확인.

## Findings

### 표면 1 — P00-01 (git/환경)

- 초기 커밋 존재: `git log` → `9e85de6`(first commit, 사용자) → `f77833f`(docs 부트스트랩) → `f7362e6`(P00). 요구 충족.
- `pyproject.toml`·`requirements.txt` 존재. requirements(`requirements.txt:6-12`)는 페이즈 문서의 핵심 의존성 가이드(torch, torchvision, transformers, pyyaml, numpy, pillow, pytest) 7종 전부 명시. 검증자가 venv 에서 7종 import 재실행 → 전부 성공 (torch 2.14.1+cpu / torchvision 0.29.1 / transformers 5.19.0 / pyyaml 6.0.3 / numpy 2.5.2 / pillow 12.3.0 / pytest 9.1.1).
- .gitignore 정책: P00 커밋은 `.gitignore:57-62` 에 정책 7줄(주석 2줄 + `data/raw/`, `data/processed/`, `data/smoke/`, `checkpoints/`)만 추가. `git check-ignore` 재실행으로 4경로 ignoring·`data/metadata.csv` 는 추적 대상임을 확인 — work log 의 "텍스트 산출물은 추적" 정책과 일치.
- 관찰(비차단): `.gitignore` 전반에 타 프로젝트 잔여 엔트일(`frontend/openapi.json`, `node_modules/`, `artifacts/` 및 "W0 analysis"·"생성 동영상" 주석, `docs/research/research_reference_data/` 등, `.gitignore:40-73`)이 존재하나 이는 first commit(사용자 템플릿)부터 있던 것이고 P00 커밋이 도입한 것이 아님(`git show f7362e6 -- .gitignore` 로 확인). 본 슬라이스 범위 밖이므로 지적만 한다.
- 관찰(비차단): 의존성이 하한선만(`>=`) 고정. "버전 고정은 슬라이스 수행 시 결정"이라는 계약 문구상 하나의 결정이므로 위반은 아니나, P02 실학습 시 재현성을 위해 exact pin 검토 권장.

### 표면 2 — P00-02 (골격/README/config)

- §24 디렉터리: 최상위 12 엔트리(README.md·requirements.txt·pyproject.toml·configs/·data/·scripts/·src/·experiments/·api/·demo/·checkpoints/·reports/) 전부 존재 + 계약 추가 요구 `tests/` 존재. `data/raw/`·`data/processed/`도 디스크에 존재(비추적·빈 디렉터리 — 런타임 생성 정책과 정합).
- §24 잎(leaf) 중 위상 소유 파일은 미생성: `scripts/*.py`(P01 데이터 파이프라인), `src/evaluate.py` 등 3파일(P02+), `configs/lora.yaml`(P04)·`inference.yaml`, `experiments/` 하위 3디렉터리(P02+ 런 디렉터리), `api/main.py`·`demo/app.py`(P07), `reports/` 3파일, `data/metadata.csv`(P01). 페이즈 계획의 제외 목록과 §24 의 "권장" 성격에 비추어 골격 단계 해석으로 수용 가능하나, 슬라이스 비고에 이 위임이 명시되어 있지는 않음(아래 Hardening).
- §29 README 필수 7항목: `README.md` 의 섹션 헤더로 Project purpose(:5)·Dataset 구성(:9)·Training 방법(:16)·Evaluation 방법(:36)·Inference 방법(:40)·Metric(:53)·Known limitations(:62) 전부 문자 그대로 존재. 7/7 충족.
- §25 config: `configs/baseline.yaml` 이 예시 스키마의 5개 최상위 키(model/training/data/augmentation/output)와 전부 일치. 스펙 리터럴 대비: `freeze_encoder: true`(:8), `epochs: 10`(:11), `batch_size: 32`(:12), `learning_rate: 0.0001`(:13), `train_csv/val_csv`(:16-17), `horizontal_flip/jpeg_aug: true`(:20-21), `checkpoint_dir: checkpoints/baseline`(:24). 차이 2건은 모두 문서화된 정당 편차: (a) `encoder: siglip` → `stub`(페이즈 비고·config 주석:2-3·README 에 명시, P02 위임), (b) 추가 키 `embedding_dim`·`image_size`(stub skeleton 운용에 필요, §25 는 예시이므로 추가 금지 조항 없음).
- YAML 파싱: 재실행 성공(5개 최상위 키 확인).

### 표면 3 — P00-03 (skeleton + 회귀 테스트)

스펙↔구현 리터럴 정합성(패러프레이즈 불인정 기준):

- §16 구조: `src/model.py:45-51` head 스택이 `Linear(embedding_dim, embedding_dim)`→`GELU()`→`Dropout(dropout)`→`Linear(embedding_dim, 1)`→`Sigmoid()` — §16 다이어그램과 동일 순서·동일 리터럴. encoder(StubEncoder)가 Embedding 을 출력(:23).
- §16 freeze: `src/model.py:58-61` `set_encoder_frozen` — `requires_grad_(not frozen)`. `src/train.py:86` 이 config 로 구동, `src/train.py:88-91` optimizer 는 `requires_grad` 파라미터만 받음(freeze 정책과 이중 정합).
- §16 sigmoid 범위: `src/model.py:53-55` forward 가 `[B]` 확률 반환.
- §16 loss: `src/train.py:92` `nn.BCELoss()` — "Binary Cross Entropy" 리터럴 존재.
- §16 label: `src/dataset.py:78` docstring "label: REAL=1, GENERATED=0 (§16)". fixtures 일관 — `tests/test_dataset.py:30`(홀수 i→label 1·`real`), `src/train.py:40`(동일 규칙).
- §12 스키마: `src/dataset.py:3-4` docstring 에 8열 전부 명시, `read_metadata`(:29-43)가 DictReader 로 파싱(8열 헤더 fixture 로 검증). 관찰: `MetadataRow`(:20-24)는 학습에 필요한 5필드만 투영(source_domain·generator·product_id·split 제외) — CSV 원본은 8열을 유지하므로 §12 "반드시 유지" 요건은 데이터 저장소 수준(P01 metadata.csv)에서 담보. 테스트 fixture 가 8열 헤더를 쓰므로 전체 스키마 파싱 호환성은 잠김.
- §15 전처리: RGB 변환(:97 `.convert("RGB")`), Resize(:65), Normalization(mean/std 0.5, :72) 구현. augmentation 중 Horizontal Flip(:67)·JPEG 재압축(`RandomJPEG` :46-60, §15 의 "JPEG compression augmentation") 구현, 모두 §25 config 키로 게이트. §15 가 열거한 나머지 op(Center/Random Crop — 기본 처리, Minor Crop·Minor Resize·Brightness/Contrast variation — 증강)은 미구현. §25 예시 config 의 augmentation 키도 2종(hor horizontal_flip·jpeg_aug)뿐이므로 config 스키마와는 정합이나, `src/dataset.py:64` docstring 이 §15 전체 준수처럼 서술 — 아래 Hardening.
- §27 Phase 0 완료 조건 5항 전부 대응 산출물 존재.

회귀 테스트 감라(테스트가 계약을 실제로 잠그는지):

- `test_head_structure_matches_spec`(`tests/test_model.py:48-53`): head 자녀 모듈 타입 리스트를 §16 순서 그대로 정합 비교 + 마지막 Linear 의 `out_features == 1`. under/over-strict 양방향으로 확정 작동(M1·M5).
- `test_encoder_grad_flags`(:31-39): freeze 시 encoder 전 파라미터 `requires_grad=False`·head 는 `True`, 해제 시 반전까지 — §16/§17 의 should-fire + should-NOT-fire 양방향(M2).
- `test_unknown_encoder_rejected`(:42-45): 방어 조항 ValueError(M6).
- `test_read_metadata_parses_all_rows`·`test_dataset_returns_image_and_float_label`(`tests/test_dataset.py:37-57`): 8열 스키마 파싱·label 0/1·경로 해석·float label·출력 shape.
- `test_transform_resizes_and_normalizes`(:60-66): shape 은 확정 잠금. 다만 값 검증이 부등호 체인 `-1 <= min <= max <= 1` 이라 Normalize 제거를 흡수(M7 실험으로 확인 — 아래). docstring 의 "정규화를 내면 재실패" 주장은 경험적으로 거짓.
- `test_train_smoke_creates_checkpoint`·`test_train_cli_command_runs_clean`(`tests/test_train_smoke.py`): in-process·subprocess 양 진입로로 CLI 완료 확인을 잠금(M3·M4). try/finally 로 임시디렉터리 정리(:23-25).
- 주장 재확인: 구현자 "pytest 9 passed" — 검증자 재실행 9 passed in 9.03s 로 일치. "CLI smoke 정상 종료" — 재실행 exit 0, `epoch 1/1 train_loss=0.697445` + checkpoint 저장 + `smoke ok` 출력 확인.

### 표면 4 — Mutation testing 짝표

모든 mutation 을 가한 뒤 해당 guarding 셀만 실행하고, 복원 후 `cmp` byte 동일·`git status --short` = " M HANDOFF.md" 만(초기 상태와 동일)을 매번 확인했다. 최종 전체 스위트 9 passed 재확인.

| Mutation | 방향 | 내용 | 재실패한 셀 | 판정 |
|---|---|---|---|---|
| M1 | under-strict | head 스택에서 `nn.Sigmoid()` 제거 | `test_head_structure_matches_spec`(확정). `test_output_is_probability` 는 **20회 중 11회만 실패(55%)** | 스위트 수준 잠김. 단일 셀 비결정성은 Findings |
| M2 | under-strict | freeze 극성 반전(`requires_grad_(frozen)`) | `test_encoder_grad_flags`(확정, 단독) | 가드 작동 |
| M3 | under-strict | `torch.save` 체크포인트 저장 제거 | `test_train_smoke_creates_checkpoint`(확정, 단독) | 가드 작동 |
| M4 | under-strict | dtype 정렬 되돌림(`labels.to(...)` 제거) — 원본 버그 재현 | `test_train_smoke_creates_checkpoint` + `test_train_cli_command_runs_clean`(양쪽, `RuntimeError: Found dtype Double but expected Float`) | 가드 작동. work_log 의 버그 보고와 동일 에러 재현 |
| M5 | over-strict | GELU↔Dropout 순서 교환(그럴듯한 과수정) | `test_head_structure_matches_spec`(확정, 단독) | 가드 작동 |
| M6 | 방어제거 | `build_encoder`의 unknown-encoder `ValueError` 제거(무조건 stub 낙하) | `test_unknown_encoder_rejected`(확정, 단독, "DID NOT RAISE") | 가드 작동 |
| M7(탐색) | 방어제거 | `transforms.Normalize` 제거 | **재실패한 셀 없음**(dataset 3셀 전부 통과) | 흡수 계층 규명 — Findings |

- M1 비결정성 규명(가이드 §"When a mutation does not bite" 절차): `test_output_is_probability` 는 시드 미지정 `torch.randn` 입력+랜덤 초기화에 의존해, Sigmoid 없이도 로짓 4개가 우연히 [0,1] 안에 머무르면 통과한다. 20회 반복으로 11회 실패(55%)임을 측정. 동일 결함을 `test_head_structure_matches_spec` 이 100% 잡으므로 **스위트 수준의 lock 은 유지**되나, 해당 셀의 docstring 주장("Sigmoid 제거 시 재실패", `tests/test_model.py:4`)은 보장이 아님.
- M7 흡수 규명: 부등호 체인 `-1 <= min <= max <= 1` 은 ToTensor 출력 [0,1] 미정규 텐서도 수용한다(회색 128 픽셀 → 미정규 0.502 ∈ [-1,1]). 즉 이 셀은 shape(Resize)만 확정 잠그고 Normalize 리터럴(mean=0.5/std=0.5)은 잠그지 않는다. §15 "Normalization" 리터럴은 코드에 존재하지만 이를 확정적으로 잠는 셀은 현재 없다.

### 표면 5 — 복잡도·테스트 수행 시간

- `read_metadata` O(n) 단일 패스(`src/dataset.py:29-43`), `__getitem__` O(1), `RandomJPEG` 확률 게이트 1회 왕복 O(HW), 학습 루프 유한 epoch×배치, 재시도·폴링·그래프 탐색 없음. 무한 루프 위험 없음. skeleton 범위 과잉 복잡도 없음(총 279줄 src).
- 스위트 7.5~9.0s, 최대 기여는 subprocess CLI 셀. 현재 규모에서 분할 불필요. mutation 시 셀 단위 실행으로 검증 비용 최소화함.

## Issues / Risks

### Blocking (계약 위반)

- 없음. boundary matrix 19개 셀 모두 채워졌고, 스펙 리터럴은 코드에 변경 없이 존재하며, 완료 확인 명령·전 스위트가 재실행으로 통과했다.

### Hardening recommendations (비차단 — 계약이 P00 에 요구하지 않는 보강)

1. **`test_output_is_probability` 결정화**: `torch.manual_seed` 지정 또는 로짓이 [0,1] 을 벗어나는 고정 입력 사용. 현재 under-strict 방향이 55% 확률로만 작동(`tests/test_model.py:20-28`, docstring `:4`의 주장 과장). 스위트는 구조 셀이 보완하나, 셀 이름이 약속하는 lock 을 셀 스스로 확정적으로 물어야 한다.
2. **Normalize 잠금 보강(M7)**: `test_transform_resizes_and_normalizes`(`tests/test_dataset.py:60-66`)에 정확 정규화 효과 검증 추가(예: 균일 회색 입력의 기댓값 ≈ 0.008 검사) 또는 docstring 주장을 shape 로 한정해 정정. §15 Normalization 리터럴의 확정 셀이 현재 없음.
3. **§15 잔여 op 의 P02 정합 처리**: Center/Random Crop(기본 처리)·Minor Crop·Minor Resize·Brightness/Contrast variation 미구현. `src/dataset.py:64` docstring 이 §15 전체 준수처럼 서술되므로, P02 에서 구현하거나 config 스키마(`§25 augmentation` 키 확장)·문구를 정정할 것. 슬라이스 계약 문구(dataset.py = "§12 메타데이터 기반 Dataset")상 P00 위반은 아니다.
4. **BCE loss 식별 잠금**: `src/train.py:92` 리터럴은 확인됐으나 loss 교체(예: MSE)를 잡는 전용 셀 없음(smoke 는 crash 만 잡음). P02 실학습 시 loss 함수 식별·수치 가드 추가 권장.
5. **§24 잎 위임의 문서화**: scripts/·configs/lora·inference.yaml·experiments/ 하위 등 위상 소유 잎의 미생성을 페이즈 비고에 한 줄로 명시하면 "§24 와 일치" 완료 확인의 해석 여지가 사라진다.
6. **의존성 exact pin**: P02 재현성 검토 시 `>=` 하한만의 고정을 재검토.
7. **실패 경로 임시디렉터리 누수(경미)**: main() 이 학습 루프에서 예외로 죽으면 `mkdtemp` 디렉터리가 남는다(`src/train.py:67`, M4 실행 흔적으로 관찰). /tmp 의 사소한 위생 문제로 우선순위 낮음.

## Verdict — 초회 검증(2026-10-07, f7362e6 · 보존)

**합격**

- 이유(하중 요인):
  1. 슬라이스 계약의 산출물·완료 확인 기준(P00-01/02/03, §27 Phase 0)이 전부 충족됐음을 1차 자료에서 재유도했다 — 초기 커밋 존재, 의존성 7종 import 재실행 성공, §24 골격+tests/, §29 README 7/7, §25 config 파싱·리터럴 정합, CLI smoke exit 0, pytest 9 passed.
  2. boundary matrix 19개 셀에 빈 셀이 없고, 지시된 6개 mutation 전부가 예상 셀에서 재실패했다(M3·M4 처럼 셀이 예상대로 편차를 보인 짝표 포함).
  3. 스펙 리터럴(§16 스택·freeze·sigmoid·BCE·REAL=1, §12 8열, §25 키·값, §29 항목, .gitignore 정책)이 코드·산출물에 변경 없이 존재한다.
- Hardening 7건은 모두 현 스펙이 P00 에 요구하지 않는 보강 사항이며 합격을 좌우하지 않는다. 다만 1·2번(비결정적 범위 셀·Normalize 흡수)은 테스트 docstring 의 주장과 실제 lock 간 격차이므로 P02 착수 전 수정을 권장한다.
- 유의: dirty tree(HANDOFF.md 미커밋 1줄) 상태로 mutation testing 을 수행했다. 절차 SoT(verification.md)의 Branch 3(cp backup·byte 비교·git 상태 불변)를 그대로 따랐고 모든 복원을 `cmp`·`git status`·sha256 으로 검증했다. 커밋·checkout·stash 등 git 상태 변경은 일절 없었다.

## Outstanding items

- **HANDOFF.md 미커밋 수정 존재**(` M HANDOFF.md`, "마지막 자가 검수 21줄→22줄" 1줄): 구현자가 커밋 f7362e6 이후 자가 검수 갱신분을 커밋하지 않았다. 검증 기준 커밋의 코드 내용과는 무관하나, 구현자가 본 기록과 함께 정리할 것.
- 본 검증 기록(`docs/verifications/2026-10-07/p00_initialization.md`)은 미커밋 상태로 남긴다(검증자는 커밋 금지). 구현자 검토 후 커밋할 것 — 경로는 git 무시 대상이 아님을 확인함(`git check-ignore` exit 1).
- 검증 중 mutation 실패 경로가 남긴 /tmp/tracepecter_smoke_* 임시디렉터리 일부가 /tmp 에 남아 있다(권한 제약으로 일괄 삭제가 거부됨; repo 외부, 무해).
- 페이즈 Complete 처리는 본 기록 합격 확인 후 `docs/plan/00_index.md` 갱신으로 이어진다(HANDOFF 다음 작업 1번).

## Reproduction

```bash
cd /mnt/d/devel/에베베/Tracepecter
git status --short                # " M HANDOFF.md" (검증 시작 시점과 동일해야 함)
git rev-parse HEAD                # f7362e61cdbf...

# 완료 확인 재실행
~/.venvs/tracepecter/bin/python -m pytest                                   # 9 passed
~/.venvs/tracepecter/bin/python -m src.train --config configs/baseline.yaml --smoke   # exit 0, "smoke ok"

# 스펙 리터럴·정책 확인
~/.venvs/tracepecter/bin/python -c "import yaml; print(yaml.safe_load(open('configs/baseline.yaml', encoding='utf-8')))"
git check-ignore -v data/raw/x.jpg checkpoints/baseline/baseline.pt        # ignoring 확인

# mutation(각 case: backup → edit → 셀 실행 → cp 복원 → cmp)
cp src/model.py /tmp/bak_model.py
# (예: M6) build_encoder 의 raise ValueError 문단을 return StubEncoder(embedding_dim) 로 치환
~/.venvs/tracepecter/bin/python -m pytest tests/test_model.py::test_unknown_encoder_rejected -q   # FAILED(DID NOT RAISE)
cp /tmp/bak_model.py src/model.py && cmp src/model.py /tmp/bak_model.py     # byte 동일
git status --short                # " M HANDOFF.md" 만

---

# 재검증(보강 후) — 2026-10-07, HEAD 01fa039

초회 검증의 Hardening 7건(H1~H7)을 구현자가 보강(`73b66a2`)하고, 보강 중 발생한 H7 회귀를 복원(`8c336b7`)하였으며 기록을 문서 반영(`01fa039`)한 최종 상태에 대한 재검증이다. 초회 판정·mutation 짝표는 위에 보존되어 있다.

## Subject metadata (재검증)

- 검증 일자: 2026-10-07 (재검증)
- 검증자: 초회 검증과 동일한 독립 검증 서브에이전트
- 검증 대상 소스: commit `01fa039` (범위 `f787fe4..01fa039`: `73b66a2` H1~H7 보강, `8c336b7` H7 회귀 복원, `01fa039` 기록)
- pre-flight: `git status --short` 빈 출력 — **clean tree**. 가이드 clean-tree branch 로 mutation 복원에 `git checkout -- <path>` 사용, 복원마다 status 재확인.
- 변경 표면: `src/dataset.py`(docstring H3), `src/train.py`(build_loss H4·run_training/main 분리 및 실패경로 정리 H7), `tests/test_model.py`(H1), `tests/test_dataset.py`(H2), `tests/test_train_smoke.py`(H4 셀), `docs/plan/phase_0_initialization.md`(H3·H5), `docs/plan/00_index.md`(H6), work log·CHANGELOG(기록).

## H1~H7 해소 확인

| 항 | 확인 방법 | 결과 |
|---|---|---|
| H1 `test_output_is_probability` 결정화 | 코드 확인(`tests/test_model.py:24-28` — `torch.manual_seed(0)` + `randn(8,3,64,64)*100`, shape (8,)) + R1 mutation 10회 반복 | **해소** — 초회 55%(11/20) → 10/10 확정 재실패 |
| H2 Normalize 값 잠금 | 코드 확인(`tests/test_dataset.py:60-71` — 회색 128 기대값 `abs(mean) < 0.05`, Normalize 시 ≈0.0078) + R2 mutation | **해소** — 미정규 0.502 로 확정 재실패(단독 셀) |
| H3 §15 문구 정정 + 페이즈 비고 | `src/dataset.py:63-67` docstring 이 "§15 전처리 중 P00 구현분(Resize·HFlip·JPEG·Normalization)"으로 정정, 잔여 op P02 위임 명시. `docs/plan/phase_0_initialization.md` 비고 §15 행 추가 | **해소** |
| H4 BCE 리터럴 잠금 | `src/train.py:32-35` `build_loss()`(`nn.BCELoss()`) 추출, `run_training` 이 사용(`src/train.py:76`). `tests/test_train_smoke.py:17-19` 신규 셀 + R3 mutation | **해소** — MSELoss 교체 시 확정 재실패(단독 셀) |
| H5 §24 잎 위임 명시 | `docs/plan/phase_0_initialization.md` 비고 — scripts→P01, src/evaluate·experiments 하위→P02, lora.yaml→P04, inference.yaml·api·demo→P07, metadata.csv→P01, reports→P02/P06 | **해소** |
| H6 exact pin P02 등록 | `docs/plan/00_index.md` 비고 — "의존성 exact pin 재검토는 P02 실학습 환경 확정 시 수행"(현재 `>=` 명시) | **해소** |
| H7 run_training/main 분리 + 실패경로 정리 | 구조 확인(`src/train.py:54-100` 분리, `src/train.py:104-116` smoke 경로 `except BaseException: rmtree; raise`) + R4 mutation 중 /tmp 임시디렉터리 수 관찰 | **해소** — 실패 실행 후에도 잔여 0(17→17), 가드 2셀 재실패 유지 |

H7 회귀 이력 검증: work log 기록대로 분리 과정에서 `print("smoke ok")` 가 누락되어 CLI 계약 셀 2개가 재실패했고 `8c336b7` 로 복원되었다. 최종 상태에서 재실행: `python -m src.train --config configs/baseline.yaml --smoke` exit 0, `epoch 1/1 train_loss=0.697475` + checkpoint 저장 + `smoke ok` 출력 확인 — 회귀 해소 확인. 기존 가드가 보강 변경 자체의 회귀를 잡은 사례로, 가드 체인이 의도대로 작동했다.

## Mutation 짝표 (재검증)

각 mutation 후 해당 셀만 실행, `git checkout -- <path>` 복원, `git status --short` 빈 출력 확인. 최종 전체 스위트 10 passed.

| Mutation | 내용 | 재실패한 셀 | 판정 |
|---|---|---|---|
| R1 | head 스택에서 `nn.Sigmoid()` 제거 | `test_output_is_probability` — 10회 실행 10/10 실패(확정) + `test_head_structure_matches_spec`(확정) | H1 결정화 입증 |
| R2 | `transforms.Normalize` 제거 | `test_transform_resizes_and_normalizes`(확정, 단독 — dataset 나머지 2셀 통과) | H2 잠금 입증 |
| R3 | `build_loss()` → `nn.MSELoss()` | `test_loss_is_binary_cross_entropy`(확정, 단독 — smoke 2셀은 통과: MSE 는 수치상 계산되므로 이 셀만 loss 식별을 잠금) | H4 잠금 입증 |
| R4 | dtype 정렬 되돌림(`labels.to(...)` 제거) | `test_train_smoke_creates_checkpoint` + `test_train_cli_command_runs_clean`(양쪽, dtype RuntimeError) | H7 리팩터 후에도 초회 가드 유지 + 실패경로 임시디렉터리 정리 실증(/tmp 17→17) |

구현자가 work log 에 자체 수행해 기록한 self-mutation 짝표(M1'·M7'·M-BCE)는 본 재검증의 독립 재현 결과와 전부 일치했다(주장만으로 채택하지 않고 재실행으로 확인).

## 재실행 수치 (재검증)

- `~/.venvs/tracepecter/bin/python -m pytest`: **10 passed**, exit 0. 측정 10.82s(안정)·17.37s / 일시적 부하 시 72~78s 관측 — `torch` import 자체가 6.2s(9p 콜드), 최대 기여 셀은 subprocess CLI 셀(부하 시 25.9s). 가이드 §"Test execution time" 에 따라 측정값·원인을 기록하며, 현재 규모에서 분할 불필요.
- CLI smoke: exit 0 + `smoke ok`(위 H7 항목).
- 테스트 수: 9 → 10(H4 셀 추가).

## 잔여 관찰 (재검증, 비차단)

- H2 의 잠금은 mean 중심이다: `abs(mean) < 0.05` 는 Normalize 의 mean=0.5 를 ±0.025 로 잠그지만, std 리터럴만 바꾸는 변형(예: std=1.0 → 0.00196)은 통과한다. "Normalize 제거 재실패"라는 H2 요건 자체는 확정 충족이므로 잔여 기록만 남긴다(초회 M7 흡수 사항의 재발 아님).
- `torch.manual_seed(0)` 가 프로세스 전역 RNG 를 설정한다(test 순서 의존 가능성 이론상 존재). 현재 스위트는 전 셀이 결정적·안정적으로 통과하므로 조치 불필요.

## Verdict (재검증 최종)

**합격**

- 이유(하중 요인):
  1. 초회 Hardening 7건(H1~H7)이 전부 해소되었음을 코드·문서 대조와 mutation 재실행으로 입증했다. 계약상 요구된 lock 의 부재·공백은 없다(초회 blocking 0건 상태 유지).
  2. 신규·강화된 가드 셀 3종이 전부 확정적(확률 아님)으로 재실패함을 R1(10/10)·R2·R3 mutation 으로 확인했다.
  3. H7 재구성 이후에도 초회 mutation 의 전 가드(R4 양 셀)가 유지되며, 보강 중 회귀('smoke ok' 누락)는 기존 CLI 계약 셀이 포착·복원되었다. 전체 스위트 10 passed·CLI smoke exit 0 재확인.
- 잔여 관찰 2건은 모두 현 계약이 요구하지 않는 사항이며 판정에 영향 없음.

## Outstanding items (재검증 시점)

- 본 기록의 재검증 섹션 갱신분은 미커밋 상태다(검증자는 커밋 금지). 구현자 검토 후 커밋할 것.
- 초회 Outstanding 의 HANDOFF.md 미커밋 수정은 `f787fe4` 에서 정리되었음을 확인(현재 tree clean).
- P00 Complete 처리(`docs/plan/00_index.md` 갱신)는 본 재검증 합격을 조건으로 수행 가능한 상태다.
- 검증 세션 중 /tmp 에 남아 있던 tracepecter_smoke_* 잔여(초회 실패 경로 흔적)는 그대로다(repo 외부·무해). R4 검증으로 신규 잔여는 발생하지 않았다.

## Reproduction (재검증)

```bash
cd /mnt/d/devel/에베베/Tracepecter
git status --short                # 빈 출력(clean) 확인
git rev-parse HEAD                # 01fa03935b62...

# 최종 상태 재실행
~/.venvs/tracepecter/bin/python -m pytest                                   # 10 passed
~/.venvs/tracepecter/bin/python -m src.train --config configs/baseline.yaml --smoke   # exit 0, "smoke ok"

# R1: src/model.py head 스택에서 nn.Sigmoid() 줄 제거 후
~/.venvs/tracepecter/bin/python -m pytest tests/test_model.py -q            # 2 failed(범위 셀 포함)
git checkout -- src/model.py
# R2: src/dataset.py 에서 transforms.Normalize 줄 제거 후
~/.venvs/tracepecter/bin/python -m pytest tests/test_dataset.py::test_transform_resizes_and_normalizes -q   # 1 failed
git checkout -- src/dataset.py
# R3: src/train.py build_loss 의 nn.BCELoss() 를 nn.MSELoss() 로 변경 후
~/.venvs/tracepecter/bin/python -m pytest tests/test_train_smoke.py::test_loss_is_binary_cross_entropy -q  # 1 failed
git checkout -- src/train.py
# R4: src/train.py 의 labels.to(probabilities.dtype) 를 labels 로 되돌린 후
~/.venvs/tracepecter/bin/python -m pytest tests/test_train_smoke.py -q      # 2 failed (dtype)
git checkout -- src/train.py
git status --short                # 빈 출력
```
```

# P00 — 프로젝트 초기화

## 목표

`docs/project.md` §27 Phase 0: 학습 파이프라인을 구동할 수 있는 repository, Python 환경, 기본 문서, config 구조, training skeleton을 확보한다.

## 선행 조건

- 없음. (2026-10-07에 문서 부트스트랩 — SoT·페이즈 체계 — 이 완료되어 있다. `docs/sot.md` 참고.)

## 범위

### 슬라이스 인덱스

| ID | 슬라이스 | 선행 | 산출물 | 완료 확인 | 상태 |
| --- | --- | --- | --- | --- | --- |
| P00-01 | Git repository + Python 환경 | — | `git init` 및 초기 커밋, `pyproject.toml`, `requirements.txt`, venv, 대량 이미지 데이터의 Git 추적 제외 정책(`.gitignore` 반영) | 초기 커밋 존재, `pip install -r requirements.txt` 후 핵심 의존성(torch, torchvision, transformers 등) import 성공 | 완료 (2026-10-07) |
| P00-02 | Repository 골격 + README + config | P00-01 | `docs/project.md` §24의 디렉터리 구조(+ `tests/` — CLAUDE.md §4 회귀 테스트 요건), `README.md`(§29 필수 항목), `configs/baseline.yaml`(§25 스펙 준수) | 디렉터리 구조가 §24와 일치, `configs/baseline.yaml`이 YAML로 파싱 성공 | 완료 (2026-10-07) |
| P00-03 | Training skeleton | P00-02 | `src/model.py`(§16 구조: frozen encoder + MLP head + sigmoid), `src/dataset.py`(§12 메타데이터 기반 Dataset), `src/train.py`(`--config`·`--smoke` 인자), `tests/`(회귀 가드) | `python -m src.train --config configs/baseline.yaml --smoke` 가 에러 없이 종료 + `pytest` 전체 통과 | 완료 (2026-10-07) |

핵심 의존성 가이드: `torch`, `torchvision`, `transformers`(SigLIP/DINO encoder), `pyyaml`, `numpy`, `pillow`, 개발용 `pytest`. 버전 고정은 슬라이스 수행 시 결정한다.

## 완료 기준

`docs/project.md` §27 Phase 0의 완료 조건을 그대로 적용한다.

```text
Repository 생성
Python environment 구성
기본 README 작성
Config 구조 생성
Training skeleton 생성
```

## 병렬 작업 및 제외

- P00-02와 P00-03은 산출물 파일이 분리되어 있어 부분 병행 가능하다.
- 제외: 실제 데이터 수집·생성·split(P01), 실제 학습과 성능 확보(P02), `src/evaluate.py` 전체 구현(P02), LoRA(P04), API·demo(P07), §32의 금지 항목 전체(SAM, full fine-tuning 등).

## 관련 결정 브리프

- 없음.

## 비고 (2026-10-07 구현)

- `--smoke` 플래그: 실데이터 부재 시에도 완료 확인 명령이 동작하도록, tiny synthetic dataset(8장)을 생성해 1 epoch 실행한다(§35 thin-slice 원칙). 원래 완료 확인 문구에서 `--smoke` 없이 적었던 것은 실데이터 경로가 존재해야 성립하는 조건이라 정정했다.
- `model.encoder: stub`: P00 skeleton 은 임시 경량 encoder. 실제 SigLIP/DINO encoder 연결은 P02(§27 Phase 2).
- venv 는 WSL2 의 /mnt/d(9p) I/O 병목을 피해 ext4 경로 `~/.venvs/tracepecter` 에 생성했다. P00 은 CPU torch wheel 사용 — CUDA 빌드 전환 여부는 P02 에서 GPU 학습 시점에 결정한다.
- 구현 완료 상태(2026-10-07): pytest 9 passed, CLI smoke 정상 종료, `configs/baseline.yaml` 파싱 성공. 페이즈 Complete 처리는 독립검증(`docs/verifications/`) 합격 후 한다.

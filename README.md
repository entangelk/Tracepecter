# Tracepecter — Fashion Photo Realism Scorer

> Fashion Photo Realism Scorer는 패션 착용 이미지가 실제 착용 촬영 사진과 얼마나 유사한 시각적 특성을 가지는지 평가하는 vision model이다. 실제 촬영 여부를 증명하는 forensic detector가 아니라, 패션 이미지의 photographic realism을 연속적인 score로 평가하는 것을 목표로 한다. (`docs/project.md` §34)

## Project purpose

패션 착용 이미지(룩북·스트릿 패션 등)를 입력받아 **0~100 Photographic Realism Score**를 출력한다. 모델은 frozen vision encoder + MLP head 구조(§5/§16)로 시작하며, 학습 데이터는 실제 착용 사진과 AI 생성 패션 사진의 대비로 구성한다.

## Dataset 구성

- **REAL**: AIHub K-Fashion 이미지 데이터셋(dataSetSn=51, 약 120만 장, 부위별 rect/polygon 라벨 포함) — 소유자 결정 2026-10-07, [DB-01](docs/decision_briefs/DB-01_P01_real-data-domain.md)
- **Generated**: 3종 이상의 서로 다른 생성기로 착용 패션 컷 생성 (§9)
- 카테고리는 패션 의류 중심으로 축소하며, 목록은 P01에서 K-Fashion 라벨 분포 확인 후 확정한다.
- 데이터 파이프라인 구축은 P01 — 아직 데이터·metadata.csv 는 repo 에 없다.

## Training 방법

```bash
# 환경 (P00: CPU wheel 기준, GPU CUDA 빌드 여부는 P02 에서 결정)
python3 -m venv ~/.venvs/tracepecter
~/.venvs/tracepecter/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
~/.venvs/tracepecter/bin/pip install -r requirements.txt

# 학습 (P01 데이터 구축 후; §25 config 구동)
~/.venvs/tracepecter/bin/python -m src.train --config configs/baseline.yaml

# 실데이터 없이 skeleton 검증 (tiny synthetic 데이터로 1 epoch)
~/.venvs/tracepecter/bin/python -m src.train --config configs/baseline.yaml --smoke

# 회귀 테스트
~/.venvs/tracepecter/bin/python -m pytest
```

학습 parameter는 코드에 직접 쓰지 않고 `configs/*.yaml`로 관리한다(§25).

## Evaluation 방법

P02에서 구현 예정(`src/evaluate.py`). Standard Test와 **Unseen Generator Test**(§10)를 별도 구성하며, checkpoint 를 받아 metric 을 출력한다.

## Inference 방법

Score calibration은 P05, `POST /score` API와 웹 데모는 P07에서 제공한다. inference 출력 예(§22):

```json
{
  "realism_score": 82.4,
  "classification": "photographic_like",
  "confidence": 0.87,
  "model_version": "v0.1"
}
```

## Metric

핵심 지표는 두 ROC-AUC 이다(§19):

- Standard Test ROC-AUC (MVP 목표 ≥ 0.90, §20)
- **Unseen Generator ROC-AUC** (MVP 목표 ≥ 0.80) — 학습에 없는 생성기에서의 일반화

부수 지표: Accuracy, PR-AUC, Precision, Recall, F1, category/generator/source별 ROC-AUC.

## Known limitations

- 실제 촬영 여부의 forensic 증명이 아니다 — "실제 촬영처럼 *보이는* 정도"를 평가한다(§4).
- 특정 생성 모델 탐지·EXIF/워터마크 판별·영상·얼굴 deepfake 탐지·artifact 영역 segmentation 은 범위 외(§4).
- 착용컷에는 얼굴이 포함되므로, 얼굴 영역 처리 정책을 REAL/AI 양측에 동일 적용해야 한다(DB-01 후속).
- 모든 종류의 사진으로의 일반화는 보장하지 않는다(§4).

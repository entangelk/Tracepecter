# Tracepecter — Fashion Photo Realism Scorer

> Fashion Photo Realism Scorer는 패션 착용 이미지가 실제 착용 촬영 사진과 얼마나 유사한 시각적 특성을 가지는지 평가하는 vision model이다. 실제 촬영 여부를 증명하는 forensic detector가 아니라, 패션 이미지의 photographic realism을 연속적인 score로 평가하는 것을 목표로 한다. (`docs/project.md` §34)

## Why — 이 프로젝트를 시작한 이유

옷을 인터넷으로 주문하는 시대가 되었다. 실물을 보지 못하고 이미지로만 상품을 고르는데, 어느 순간부터 그 이미지가 **실제로 찍은 착용 사진인지, AI가 만들어낸 이미지인지** 구분이 되지 않는다. 쇼핑 중에 직접 겪은 일이다 — 상품 페이지의 옷 사진을 한참 들여다보며 "이게 실제 상품 컷인가, 아니면 AI로 만든 이미지인가"를 판단하느라 시간을 쓰고 있었다. 실물 확인 없이 이미지를 믿고 사야 하는 시대에, 그 이미지 자체를 의심하게 되는 시간이 생겨버린 것이다.

Tracepecter는 이 판단의 부담을 이미지 쪽으로 되돌리는 도구다.

- **소비자의 가드**: 이미지가 얼마나 "실제 찍힌 것처럼 보이는지"를 점수로 보여준다. 육안으로 들여다보며 의심하는 수고를 모델이 대신한다.
- **이미지 퀄리티를 올리는 가드**: 이런 소비자가 존재한다는 것을 기업도 알고 있다. realism 검출이 좋아질수록 "AI 이미지를 실사처럼 내놓는 일"은 통하지 않게 되고, 기업은 역으로 이미지의 품질과 정직성을 올릴 유인을 얻는다. 이 프로젝트는 그 기준을 끌어올리는 반대편 가드로 기능한다.

단, forensic 증명 도구는 아니다 — 이 점은 [Known limitations](#known-limitations) 참고.

## Project purpose

패션 착용 이미지(룩북·스트릿 패션 등)를 입력받아 **0~100 Photographic Realism Score**를 출력한다. 모델은 frozen vision encoder + MLP head 구조(§5/§16)로 시작하며, 학습 데이터는 실제 착용 사진과 AI 생성 패션 사진의 대비로 구성한다.

## Dataset 구성

- **REAL**: AIHub K-Fashion 이미지 데이터셋(dataSetSn=51, 약 120만 장, 부위별 rect/polygon 라벨 포함) — 소유자 결정 2026-10-07, [DB-01](docs/decision_briefs/DB-01_P01_real-data-domain.md)
- **Generated**: 로컬 오픈소스 생성기 5종으로 착용 패션 컷 생성(§9, [DB-02](docs/decision_briefs/DB-02_P01_ai-generators.md)) — train 4종(qwen_image_21·z_image_turbo·sdxl·playground_25) + unseen 1종(sd35_medium, Test B 전용). ComfyUI GPU 컨테이너(`Dockerfile.comfyui`) 경유 생성.
- 카테고리: K-Fashion 부위 라벨 기반 4종 — 상의·하의·아우터·원피스(P01 확정, 대표 부위 우선순위 원피스 > 아우터 > 상의 > 하의)
- 얼굴 영역: 무처리 정책(DB-03) — 프롬프트 정합 + P06 failure analysis 재검 트리거로 위험 관리
- 규모(§7 최소 목표): REAL ≥3,000 + Generated ≥3,000. P01 파이프라인(선별·생성·dedup·group split)으로 구축하며, 이미지 실물은 저장소 밖(ext4)에 적재하고 `data/metadata.csv`(§12 v1.2)가 행 단위로 추적한다. 현재 진행 상태는 `HANDOFF.md`.

## Training 방법

실행 환경은 Docker Compose(소유자 결정 2026-10-07). 의존성 목록은 `requirements.txt`가 canonical이다.

```bash
# CPU 검증 이미지 빌드
docker compose build dev

# 회귀 테스트
docker compose run --rm dev python -m pytest

# 실데이터 없이 skeleton 검증 (tiny synthetic 데이터로 1 epoch)
docker compose run --rm dev python -m src.train --config configs/baseline.yaml --smoke

# CUDA 학습 이미지 (기존 ComfyUI CUDA 기반 재사용)
docker compose --profile gpu build comfyui
docker compose --profile training build train

# 실학습 — GPU에 다른 연산 작업이 없을 때만 실행
GIT_COMMIT=$(git rev-parse HEAD) docker compose --profile training run --rm train
```

학습 이미지 경로는 `IMAGE_DIR`로 지정(기본 `$HOME/data/tracepector/images`, 컨테이너 `/images` 읽기 전용). `data/metadata.csv`의 split을 직접 선택하며 REAL=1, Generated=0으로 학습한다. 매 epoch validation BCE가 개선되면 `checkpoints/baseline/best.pt`를 원자적으로 교체하고 `experiment.json`에 config·metric·dataset hash를 보관한다. 매 epoch `last.pt`에 optimizer·RNG·진행 상태도 저장한다. 전원 단절 후에는 동일 config로 `docker compose --profile training run --rm train python -m src.train --config configs/baseline.yaml --resume`을 실행한다. 학습 parameter는 코드에 직접 쓰지 않고 `configs/*.yaml`로 관리한다(§25).

## Evaluation 방법

```bash
docker compose --profile training run --rm train python -m src.evaluate \
  --checkpoint checkpoints/baseline/best.pt --device cuda
```

`test_metrics.json`에 Accuracy·ROC-AUC·PR-AUC(사다리꼴 면적)·Precision·Recall·F1 및 category/generator/source별 지표를 저장한다. Test B는 `test_unseen`의 생성 이미지와 Standard test의 REAL 이미지를 함께 사용한다([DB-04](docs/decision_briefs/DB-04_P02_unseen-real.md)). 두 테스트는 REAL 표본을 공유하며, 단일 클래스 그룹의 AUC는 `null`이다. generator별 AUC는 해당 생성기+REAL, source별 AUC는 해당 REAL source+Generated를 비교한다.

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
- 착용컷에는 얼굴이 포함된다 — 무처리 정책(DB-03)이므로 점수에 얼굴 특성이 기여할 수 있으며, 얼굴 deepfake 판별이나 얼굴만의 위변조 증명은 범위 외다.
- 모든 종류의 사진으로의 일반화는 보장하지 않는다(§4).

## Primary encoder

P03 비교에서 SigLIP을 primary로 선정했다. 실행 설정은 `configs/primary.yaml`, 현재 checkpoint는 `checkpoints/baseline/best.pt`다. 동일 split의 DINO baseline은 `configs/dino.yaml`로 학습하며 checkpoint를 `checkpoints/dino/`에 분리한다. [비교 report](experiments/p03_comparison/README.md)에 validation/Test A/B·category 성능·GPU latency·모델 크기와 선정 규칙을 보관한다.

```bash
docker compose --profile training run --rm train python -m scripts.compare_baselines \
  --checkpoints checkpoints/baseline/best.pt checkpoints/dino/best.pt \
  --output experiments/p03_comparison/comparison.json --device cuda
```

## Calibrated image score

```bash
docker compose --profile training run --rm train python -m src.score \
  --image /images/<image-path> \
  --calibration experiments/p05_calibration/calibration.json --device cuda
```

`realism_score`(0~100)와 `classification`(`photographic_like`/`synthetic_like`)을 출력한다. temperature와 threshold는 validation에서만 선택했으며 artifact의 checkpoint hash를 검증한다. [P05 보고서](experiments/p05_calibration/README.md)에 전후 지표와 한계를 기록했다. Test B의 NLL/Brier는 소폭 악화돼 추가 검증이 필요하다. 사람 체감 score 일치는 아직 별도 평가하지 않았다.

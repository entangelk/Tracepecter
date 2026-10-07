
# Product Photo Realism Scorer

## MVP 개발 작업 계획서

### 1. 프로젝트 개요

본 프로젝트의 목적은 상품 이미지를 입력받아 해당 이미지가 **실제 제품을 카메라로 촬영한 사진처럼 얼마나 자연스럽게 보이는지**를 점수화하는 비전 모델을 개발하는 것이다.

모델은 이미지가 실제 촬영인지 AI 생성인지 절대적인 사실을 판정하는 forensic detector로 정의하지 않는다. 대신 시각적 사실성에 초점을 맞춰 `Photographic Realism Score`를 출력한다.

최종 MVP 출력 예시는 다음과 같다.

```text
Photographic Realism Score: 82 / 100

판정:
실제 촬영 이미지와 상당히 유사함

Confidence: 0.87
```

MVP에서는 우선 단일 점수만 제공하며, 이후 필요하면 Texture, Lighting, Geometry, Reflection, Typography 등의 세부 점수로 확장한다.

---

# 2. 목표

MVP의 핵심 목표는 다음과 같다.

1. 실제 상품 사진과 AI 생성 상품 사진으로 학습 데이터셋 구축
2. Pretrained Vision Encoder 기반 baseline 모델 구축
3. 이미지 입력 → 0~100 Realism Score 출력
4. 학습에 포함되지 않은 AI 생성 방식에 대한 일반화 성능 측정
5. 실제 사진과 AI 사진의 중간 영역을 표현할 수 있도록 score calibration 수행
6. 간단한 API 및 테스트 UI 제공
7. 향후 생성 이미지 품질 평가 모델로 사용할 수 있도록 구조 설계

MVP에서는 SAM 계열 모델을 사용하지 않는다.

SAM은 객체 영역 분석이나 지역별 artifact 분석을 추가할 때 Phase 2 이후 도입한다.

---

# 3. 프로젝트 범위

## 대상 이미지

초기에는 상품 이미지만 대상으로 한다.

권장 카테고리는 다음 5개다.

- Shoes
- Bags
- Cosmetics
- Electronics
- Furniture

카테고리를 제한하는 이유는 일반적인 AI 이미지 탐지보다 문제 범위를 좁혀 빠르게 의미 있는 baseline을 확보하기 위함이다.

## MVP 대상

```text
Real Product Photo
        vs
AI-generated Product Photo
```

모델 출력은 binary label 자체보다는 다음 값을 중심으로 사용한다.

```text
0                                  100
│                                   │
Synthetic-looking         Photographic-looking
```

예:

```text
0~39     AI 생성 이미지 특징이 강함
40~69    불확실 / 혼합 영역
70~100   실제 촬영 이미지와 유사함
```

해당 구간은 고정 규칙이 아니라 validation 결과를 통해 조정한다.

---

# 4. 비범위

MVP에서는 다음 기능을 구현하지 않는다.

- AI 생성 여부에 대한 법적/forensic 증명
- 특정 생성 모델 탐지
- 모든 종류의 사진에 대한 일반화
- EXIF metadata 기반 판별
- 워터마크 기반 판별
- 영상 판별
- 얼굴 deepfake 탐지
- 이미지 내부 AI artifact 위치 segmentation
- SAM 기반 region 분석

즉 모델은 다음 질문에 답하는 것을 목표로 한다.

```text
"이 상품 사진은 실제 제품 촬영처럼 보이는가?"
```

다음 질문에 답한다고 주장해서는 안 된다.

```text
"이 이미지는 실제로 카메라로 촬영된 이미지인가?"
```

---

# 5. 전체 시스템 구조

초기 구조는 최대한 단순하게 구성한다.

```text
             Product Image
                    │
                    ▼
             Preprocessing
                    │
                    ▼
          Pretrained Vision Encoder
              (initially frozen)
                    │
                    ▼
             Image Embedding
                    │
                    ▼
                MLP Head
                    │
                    ▼
                Sigmoid
                    │
                    ▼
          Photographic Realism
                0.0 ~ 1.0
                    │
                    ▼
                0 ~ 100
```

MVP에서는 Vision Encoder 전체를 처음부터 학습하지 않는다.

첫 번째 실험은 encoder를 freeze한 상태에서 classification head만 학습한다.

Baseline 성능이 부족한 경우에만 LoRA를 추가한다.

```text
Stage 1

Frozen Vision Encoder
        +
Trainable MLP Head


Stage 2

Vision Encoder
   + LoRA
        +
Trainable MLP Head
```

---

# 6. 모델 후보

첫 번째 baseline은 SigLIP/CLIP 계열의 Vision Encoder를 권장한다.

이유는 실제 촬영 이미지와 생성 이미지의 semantic 및 visual style 차이를 embedding 공간에서 구분하기에 적합하기 때문이다.

대안으로 DINO 계열 encoder를 동일한 방식으로 비교한다.

MVP에서는 아래 순서로 실험한다.

```text
Experiment A
SigLIP 계열 Encoder
Frozen + Linear/MLP Head

Experiment B
DINO 계열 Encoder
Frozen + Linear/MLP Head

Experiment C
A/B 중 우수한 Encoder
+ LoRA

Experiment D
필요 시 encoder 마지막 일부 block fine-tuning
```

처음부터 Full Fine-tuning을 수행하지 않는다.

---

# 7. 데이터셋 설계

데이터 품질이 모델 구조보다 중요한 프로젝트이므로 가장 많은 주의를 기울여야 한다.

최소 목표 데이터량:

```text
Real Images        3,000+
Generated Images   3,000+

Minimum Total      6,000
```

권장 목표:

```text
Real Images        5,000
Generated Images   5,000

Total             10,000
```

카테고리별 데이터가 지나치게 편향되지 않게 구성한다.

예:

| Category    |  Real | Generated |
| ----------- | ----: | --------: |
| Shoes       | 1,000 |     1,000 |
| Bags        | 1,000 |     1,000 |
| Cosmetics   | 1,000 |     1,000 |
| Electronics | 1,000 |     1,000 |
| Furniture   | 1,000 |     1,000 |

---

# 8. Real 데이터 수집

실제 상품 이미지는 가능한 한 여러 출처를 섞는다.

중요한 것은 특정 쇼핑몰의 디자인을 모델이 학습하지 않게 하는 것이다.

잘못된 데이터 구성:

```text
REAL → 쇼핑몰 A
AI   → 생성 모델 B
```

이 경우 모델이 실제성과 AI artifact가 아니라 쇼핑몰 A의 이미지 스타일을 학습할 수 있다.

가능하면 다음과 같이 구성한다.

```text
REAL

Source A
Source B
Source C
Source D
Public Dataset
직접 촬영 / 허용된 이미지
```

동일한 상품의 거의 같은 이미지는 train과 test에 동시에 들어가면 안 된다.

데이터 수집 시 반드시 원본 출처, 라이선스 또는 사용 가능 범위를 기록한다.

공개 배포 또는 상업적 사용을 고려한다면 무단 수집 데이터가 모델 배포를 막을 수 있으므로, MVP 단계에서도 데이터 provenance를 저장한다.

---

# 9. AI Generated 데이터 생성

AI 데이터는 반드시 복수의 생성 모델 또는 복수의 생성 방식으로 구성한다.

가장 피해야 할 구성은 다음이다.

```text
AI images = 단일 생성 모델 100%
```

이 경우 모델이 AI 이미지의 일반적인 특성 대신 특정 생성기의 artifact를 탐지할 가능성이 높다.

Generated 데이터는 최소 3개 이상의 서로 다른 generation source를 사용한다.

예:

```text
Generator A
Generator B
Generator C
Generator D
```

프롬프트도 한 형태로 고정하지 않는다.

예:

```text
studio product photography
commercial product photo
white background catalog photography
luxury advertising photography
natural daylight product photography
e-commerce listing photography
```

배경 역시 다양화한다.

```text
white studio
gray studio
indoor
outdoor
lifestyle
high-gloss advertising
minimal product shot
```

---

# 10. 가장 중요한 평가 데이터 설계

일반적인 random split만 사용하지 않는다.

모델의 실제 일반화 성능을 확인하기 위해 두 종류의 테스트셋을 구축한다.

## Test A — Standard Test

학습 데이터와 동일한 생성기 종류가 일부 포함될 수 있다.

목적은 일반적인 classification 성능 측정이다.

## Test B — Unseen Generator Test

특정 생성기를 training에서 완전히 제외한다.

예:

```text
TRAIN

Real images

Generator A
Generator B
Generator C


TEST

Real images

Generator D only
```

Generator D 이미지를 제대로 판별한다면 특정 생성기의 artifact를 외운 것이 아니라 좀 더 일반적인 visual realism feature를 학습했을 가능성이 높다.

이 Test B 결과를 프로젝트의 핵심 성능 지표로 사용한다.

---

# 11. Hard Negative 데이터

모델 성능을 실제 사용 수준으로 끌어올리려면 단순한 Real vs 저품질 AI 데이터만 사용해서는 안 된다.

다음 데이터를 반드시 포함하거나 별도 평가한다.

```text
Real but difficult

과도하게 보정된 실제 사진
배경 제거 상품 사진
스튜디오 합성 사진
HDR
극도로 매끈한 제품 표면
과도한 sharpening
강한 노이즈 제거


Synthetic but difficult

고품질 생성 이미지
실제 이미지 + AI background
실제 제품 + AI retouch
3D render
CGI product render
AI image + Photoshop retouch
```

특히 CGI/3D Render는 별도의 label을 고려한다.

최종적으로는 다음처럼 확장할 수 있다.

```text
REAL_PHOTO
CG_RENDER
AI_GENERATED
HYBRID
```

하지만 MVP 학습은 우선 binary로 진행한다.

---

# 12. 데이터 메타데이터

각 이미지마다 최소 다음 정보를 저장한다.

```json
{
  "image_id": "img_000001",
  "path": "images/shoes/real/img_000001.jpg",
  "label": 1,
  "category": "shoes",
  "source_type": "real",
  "source_domain": "source_a",
  "generator": null,
  "product_id": "shoe_028",
  "split": "train"
}
```

AI 이미지:

```json
{
  "image_id": "img_005821",
  "path": "images/shoes/generated/img_005821.png",
  "label": 0,
  "category": "shoes",
  "source_type": "generated",
  "source_domain": null,
  "generator": "generator_b",
  "product_id": null,
  "split": "train"
}
```

이 metadata를 반드시 유지한다.

향후 generator별 성능, category별 성능, source별 bias를 분석할 때 필요하다.

---

# 13. 중복 제거

인터넷 상품 사진은 동일 이미지 또는 resize/crop 버전이 매우 많다.

따라서 train/test leakage 방지를 위해 이미지 중복 제거를 수행한다.

최소 구현:

```text
pHash
+
embedding similarity
```

유사 이미지가 발견되면 동일 그룹으로 묶고 동일 split에 배정한다.

동일 제품의 여러 각도 이미지도 가능하면 동일 split으로 배정한다.

---

# 14. Dataset Split

권장 구조:

```text
Train       70%
Validation  15%
Test        15%
```

단순 random split 대신 다음 기준으로 group split한다.

```text
product_id
source
near-duplicate cluster
generator
```

별도로 unseen-generator test set을 유지한다.

---

# 15. 이미지 전처리

최초 baseline에서는 복잡한 preprocessing을 사용하지 않는다.

기본 처리:

```text
RGB conversion
Resize
Center / Random Crop
Normalization
```

Training augmentation:

```text
Horizontal Flip
Minor Crop
Minor Resize
Small Brightness/Contrast variation
JPEG compression augmentation
```

주의:

강한 augmentation은 AI artifact 자체를 제거할 수 있으므로 사용하지 않는다.

특히 blur, heavy noise, heavy compression은 초기에는 제한한다.

---

# 16. Baseline 모델

첫 실험은 encoder freeze 방식으로 구현한다.

구조:

```text
Vision Encoder
      │
      ▼
Embedding
      │
      ▼
Linear
      │
     GELU
      │
   Dropout
      │
      ▼
Linear(1)
      │
   Sigmoid
```

Loss:

```text
Binary Cross Entropy
```

Label:

```text
REAL      = 1
GENERATED = 0
```

Inference:

```text
sigmoid output = realism probability

realism_score = probability × 100
```

---

# 17. LoRA 적용 조건

Baseline 결과가 충분하면 LoRA를 추가하지 않는다.

LoRA는 다음 상황에서 진행한다.

```text
Frozen Encoder 성능이 낮음

또는

Train 성능은 낮지 않지만
Unseen Generator 성능이 크게 떨어짐

또는

특정 subtle artifact를 embedding이 구분하지 못함
```

LoRA는 vision transformer의 Attention projection 일부에 적용한다.

처음에는 전체 block 대신 뒤쪽 transformer block을 중심으로 적용한다.

학습 대상:

```text
LoRA parameters
+
MLP classification head
```

기존 encoder weight는 freeze한다.

---

# 18. Score Calibration

Binary classifier의 sigmoid 값을 그대로 사용자에게 보여주지 않는다.

Validation dataset을 사용하여 probability calibration을 수행한다.

목적은 다음과 같다.

```text
score 0.9

=

단순 모델 logit 값

이 아니라

높은 photographic realism을 의미하는
상대적으로 일관된 점수
```

최종 UI에서는 `AI probability`보다는 다음 표현을 우선 사용한다.

```text
Photographic Realism
82 / 100
```

보조 정보로 다음을 추가할 수 있다.

```text
Synthetic-like
████░░░░░░

Photographic-like
████████░░
```

---

# 19. 평가 Metric

최소 다음 metric을 기록한다.

```text
Accuracy
ROC-AUC
PR-AUC
Precision
Recall
F1

Category-wise ROC-AUC
Generator-wise ROC-AUC
Source-wise ROC-AUC

Unseen Generator ROC-AUC
```

특히 중요한 것은 다음 두 지표다.

```text
Standard Test ROC-AUC

Unseen Generator ROC-AUC
```

두 값의 차이가 크면 특정 생성 모델에 overfit되었을 가능성이 높다.

---

# 20. MVP 성공 기준

최소 성공 조건은 다음으로 정의한다.

```text
Standard Test ROC-AUC
>= 0.90

Unseen Generator ROC-AUC
>= 0.80
```

단, 수치 자체보다 다음 조건을 더 중요하게 본다.

```text
실제 상품 카테고리별 성능 편차가 과도하지 않음

특정 source만 보고 판단하지 않음

새로운 generator에서도 일정 수준 이상의 일반화

score가 실제 사람의 체감과 크게 어긋나지 않음
```

---

# 21. 사람 평가 데이터

MVP 1차 완료 후 200~500쌍 정도의 pairwise dataset을 추가한다.

사용자 또는 annotator에게 다음 질문을 한다.

```text
A와 B 중 어느 이미지가
실제 상품 촬영처럼 더 자연스러운가?
```

데이터:

```text
image_a
image_b
preferred
```

예:

```csv
image_a,image_b,preferred
img_001,img_882,A
img_723,img_112,B
img_008,img_651,A
```

향후 Ranking Loss를 이용해 realism score를 사람의 시각적 평가와 더 잘 맞출 수 있다.

이 단계는 MVP 필수 작업은 아니다.

---

# 22. API

Inference API는 FastAPI 등의 경량 HTTP API로 구성한다.

Endpoint:

```text
POST /score
```

Input:

```text
multipart/form-data
image=<file>
```

Output:

```json
{
  "realism_score": 82.4,
  "classification": "photographic_like",
  "confidence": 0.87,
  "model_version": "v0.1"
}
```

Threshold는 config에서 관리한다.

예:

```yaml
thresholds:
  synthetic_like: 40
  uncertain: 70
```

---

# 23. Demo UI

MVP는 간단한 웹 UI를 제공한다.

기능:

```text
이미지 업로드
        ↓
Preview
        ↓
Model inference
        ↓
Realism Score 출력
```

UI 예:

```text
┌──────────────────────────────┐
│                              │
│        PRODUCT IMAGE         │
│                              │
└──────────────────────────────┘


Photographic Realism

████████████████░░░░

82 / 100


실제 상품 촬영과 유사한 이미지입니다.
```

UI에는 반드시 다음 성격의 문구를 표시한다.

```text
이 점수는 이미지가 실제 촬영처럼 보이는 정도를 평가하며,
실제 촬영 여부를 증명하지 않습니다.
```

---

# 24. 권장 Repository 구조

```text
product-photo-realism/

├── README.md
├── requirements.txt
├── pyproject.toml
│
├── configs/
│   ├── baseline.yaml
│   ├── lora.yaml
│   └── inference.yaml
│
├── data/
│   ├── raw/
│   │   ├── real/
│   │   └── generated/
│   │
│   ├── processed/
│   └── metadata.csv
│
├── scripts/
│   ├── collect_real.py
│   ├── generate_ai.py
│   ├── deduplicate.py
│   ├── build_metadata.py
│   └── split_dataset.py
│
├── src/
│   ├── dataset.py
│   ├── model.py
│   ├── train.py
│   ├── evaluate.py
│   ├── inference.py
│   └── calibration.py
│
├── experiments/
│   ├── baseline_siglip/
│   ├── baseline_dino/
│   └── lora/
│
├── api/
│   └── main.py
│
├── demo/
│   └── app.py
│
├── checkpoints/
│
└── reports/
    ├── evaluation.md
    ├── category_metrics.csv
    └── generator_metrics.csv
```

---

# 25. Config 관리

학습 parameter는 코드에 직접 작성하지 않고 config 파일로 관리한다.

예:

```yaml
model:
  encoder: siglip
  freeze_encoder: true

training:
  epochs: 10
  batch_size: 32
  learning_rate: 0.0001

data:
  train_csv: data/train.csv
  val_csv: data/val.csv

augmentation:
  horizontal_flip: true
  jpeg_aug: true

output:
  checkpoint_dir: checkpoints/baseline
```

실험마다 config와 metric을 반드시 저장한다.

---

# 26. Experiment Tracking

각 실험에서 최소 다음 정보를 기록한다.

```text
experiment name
git commit
model
dataset version
train sample count
validation sample count
test sample count
hyperparameters
metrics
checkpoint
```

초기에는 CSV 또는 JSON으로도 충분하다.

필요하면 이후 experiment tracking tool을 추가한다.

---

# 27. 작업 단계

## Phase 0 — 프로젝트 초기화

완료 조건:

```text
Repository 생성
Python environment 구성
기본 README 작성
Config 구조 생성
Training skeleton 생성
```

예상 산출물:

```text
git repository
requirements
src/train.py
src/model.py
src/dataset.py
```

---

## Phase 1 — 데이터 파이프라인 구축

작업:

```text
Real image 수집
Generated image 생성
Metadata 생성
Duplicate 제거
Dataset split
```

완료 조건:

```text
최소 6,000 이미지

Real >= 3,000
Generated >= 3,000

5개 category 포함

metadata.csv 생성

train / val / test split 완료

unseen_generator_test 생성
```

---

## Phase 2 — Baseline 모델

작업:

```text
Vision Encoder 연결
Encoder freeze
MLP Head 구현
Training loop 구현
Evaluation 구현
```

완료 조건:

```text
한 번의 명령으로 학습 가능

Checkpoint 저장

Validation metric 출력

Test evaluation 가능
```

실행 형태:

```bash
python -m src.train --config configs/baseline.yaml
```

평가:

```bash
python -m src.evaluate \
  --checkpoint checkpoints/baseline/best.pt
```

---

## Phase 3 — Baseline 비교

다음 모델을 비교한다.

```text
SigLIP 계열

vs

DINO 계열
```

동일 데이터 split을 사용한다.

비교 기준:

```text
Standard ROC-AUC
Unseen Generator ROC-AUC
Category별 편차
Inference latency
Model size
```

최종적으로 하나를 primary encoder로 선정한다.

---

## Phase 4 — LoRA

Baseline 성능이 충분하지 않은 경우 진행한다.

작업:

```text
Vision Transformer attention LoRA 적용

Head + LoRA 학습

Frozen baseline과 성능 비교
```

비교 결과가 유의미하지 않으면 baseline 모델을 유지한다.

---

## Phase 5 — Calibration

작업:

```text
Validation prediction 저장

Score calibration

Threshold 선정

0~100 Realism Score 정의
```

완료 조건:

동일한 이미지 특성에서 score가 비교적 일관되게 움직이고, threshold가 validation 기준으로 결정되어 있어야 한다.

---

## Phase 6 — Failure Analysis

잘못 분류한 이미지를 자동으로 저장한다.

구조:

```text
reports/errors/

false_positive/
false_negative/
low_confidence/
```

각 이미지에 다음 metadata를 함께 기록한다.

```text
score
label
category
source
generator
```

Failure case를 최소 100개 이상 수동 검토한다.

주요 오류 패턴을 문서화한다.

예:

```text
1. 흰 배경 스튜디오 사진을 AI로 판단
2. CGI 전자제품 이미지를 실제 사진으로 판단
3. 고품질 AI 가구 이미지를 real로 판단
4. 강하게 retouch된 화장품 사진을 generated로 판단
```

이 문서가 다음 데이터 수집 방향을 결정한다.

---

# 28. 데모 구축

최종 모델을 API에 연결한다.

권장 흐름:

```text
User Image
    ↓
Web Demo
    ↓
Inference API
    ↓
Vision Model
    ↓
Realism Score
```

MVP에서는 로그인, DB, 사용자 관리 등은 구현하지 않는다.

---

# 29. 최종 Deliverables

MVP 완료 시 다음 결과물이 존재해야 한다.

```text
1. 학습 가능한 repository

2. Dataset metadata

3. Dataset generation / preprocessing scripts

4. Baseline checkpoint

5. Best model checkpoint

6. Evaluation script

7. Standard test report

8. Unseen-generator test report

9. Failure analysis report

10. Inference API

11. 간단한 Web Demo

12. README
```

README에는 반드시 다음 내용이 포함되어야 한다.

```text
Project purpose

Dataset 구성

Training 방법

Evaluation 방법

Inference 방법

Metric

Known limitations
```

---

# 30. 권장 작업 일정

1명이 토이 프로젝트 형태로 진행하는 것을 기준으로 한다.

### Day 1

```text
Repository 초기화
Dataset schema 설계
Model skeleton 작성
```

### Day 2~4

```text
Real 데이터 확보
AI 이미지 생성
Metadata 구축
```

### Day 5

```text
Deduplication
Dataset split
DataLoader 구현
```

### Day 6

```text
SigLIP 계열 baseline 학습
평가
```

### Day 7

```text
DINO 계열 baseline 학습
비교
```

### Day 8

```text
Unseen generator evaluation
Failure analysis
```

### Day 9

```text
LoRA 실험
Calibration
```

### Day 10

```text
API
Demo UI
README
최종 report
```

MVP 예상 범위는 약 2주 내외의 개인 프로젝트 규모로 잡는다.

---

# 31. 작업 우선순위

우선순위는 다음 순서를 지킨다.

```text
Data
 ↓
Baseline
 ↓
Evaluation
 ↓
Failure Analysis
 ↓
Data 개선
 ↓
LoRA
 ↓
Demo
```

LoRA 또는 복잡한 모델링을 먼저 하지 않는다.

본 프로젝트에서 가장 중요한 부분은 모델 구조보다 데이터 구성과 evaluation methodology다.

---

# 32. 하지 말아야 할 것

초기 작업자가 다음 방향으로 프로젝트를 과도하게 확장하지 않도록 한다.

```text
SAM부터 붙이기

Full Fine-tuning부터 진행

수십 개 quality label 생성

LLM/VLM을 함께 학습

모든 종류 이미지 지원

실제/AI를 100% 판별한다고 주장

Training accuracy만 보고 모델 선정

Random split만 사용

단일 AI generator만 사용
```

MVP에서는 단순한 구조로 일반화 가능성을 검증하는 것이 가장 중요하다.

---

# 33. Phase 2 확장 아이디어

MVP가 성공한 뒤 다음 단계로 확장한다.

```text
Overall Realism
        │
        ├── Texture Realism
        ├── Lighting Realism
        ├── Reflection Realism
        ├── Geometry Realism
        ├── Typography Quality
        └── Background Realism
```

이후 SAM 또는 object detector를 이용하여 영역 단위 분석을 추가할 수 있다.

```text
Product Image
       │
       ├── Global Realism Model
       │
       └── Region Detector / SAM
                │
                ├── Product
                ├── Logo
                ├── Text
                └── Background
                      │
                      ▼
               Region Realism
```

최종적으로 생성 이미지 시스템의 evaluator로 활용할 수 있다.

```text
Image Generator
       │
       ▼
Generated Product Photo
       │
       ▼
Realism Scorer
       │
       ├── score >= threshold → Accept
       │
       └── score < threshold → Regenerate
```

---

# 34. 최종 프로젝트 정의

이 프로젝트를 외부에 설명할 때는 `AI Image Detector`보다는 다음과 같이 정의한다.

> Product Photo Realism Scorer는 상품 이미지가 실제 제품 촬영 사진과 얼마나 유사한 시각적 특성을 가지는지 평가하는 vision model이다. 실제 촬영 여부를 증명하는 forensic detector가 아니라, 상품 이미지의 photographic realism을 연속적인 score로 평가하는 것을 목표로 한다.

이 정의를 README, Demo, Portfolio 설명에 동일하게 사용한다.

---

# 35. 착수 시 첫 작업

작업자는 프로젝트 시작 후 가장 먼저 다음 상태를 만드는 것을 목표로 한다.

```text
repo 생성
    ↓
metadata schema 확정
    ↓
Real 500장
Generated 500장
    ↓
Frozen encoder baseline
    ↓
첫 ROC-AUC 확인
```

처음부터 10,000장을 모두 확보한 뒤 모델을 만드는 방식보다, **1,000장 규모의 작은 데이터로 전체 pipeline을 먼저 관통시킨 뒤 데이터 규모를 늘리는 방식**을 권장한다.

첫 번째 milestone은 다음 한 문장으로 정의한다.

> 상품 이미지 1장을 넣으면 학습된 모델이 0~100 Photographic Realism Score를 반환하고, 별도의 test dataset에서 baseline metric을 확인할 수 있다.

이 상태가 만들어지면 이후 작업은 데이터 품질과 일반화 성능을 개선하는 반복 과정으로 진행한다.

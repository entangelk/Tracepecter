# P03 — SigLIP vs DINO baseline 비교

**상태:** Complete (2026-10-09)

## 목표·선행 조건

P01 전체 metadata와 P02의 학습·평가 코드 및 [SigLIP 실험](../../experiments/p02_siglip_baseline/README.md)을 사용하여 §27 Phase 3 비교를 수행하고 primary encoder를 선정한다. 사양 우선순위는 `docs/sot.md`를 따른다.

## 범위·완료 조건

1. DINOv2-base vision adapter·정규화 config 구현 → 작은 무다운로드 모델·기존 SigLIP 호환 가드.
2. 동일 split의 DINO 실학습·평가 → 10 epoch, validation BCE 기반 best checkpoint, Test A/B와 그룹별 metric.
3. 두 모델의 parameter 수·checkpoint 크기·GPU batch-1 forward latency 비교 → 동일 머신·동일 224 입력, warmup 10회·측정 100회·각 측정 CUDA 동기화.
4. 비교 report·primary config·선정 근거 기록 → 페이즈 인덱스와 HANDOFF 갱신.

## 비교·선정 방법(실험 전 고정)

- 동일 metadata SHA256, split, seed 42, epoch 10, batch 32, Adam lr 0.0001, frozen encoder와 768차원 MLP head, augmentation과 square 224 geometry를 유지한다.
- DINO는 `facebook/dinov2-base`의 CLS pooled feature, SigLIP은 기존 attention pooled feature를 사용한다. 각 pretrained 모델의 정규화가 필요하므로 DINO만 mean/std를 달리한다. 공식 DINO processor의 shortest-edge resize/center crop 대신 공통 square resize를 사용하며, 이것은 동일 pixel budget 비교이고 모든 native processor의 비교는 아니다.
- 각 모델의 checkpoint는 validation BCE로 선택한다. primary는 선택된 checkpoint의 validation ROC-AUC 차이가 0.001 이상이면 높은 모델, 미만이면 낮은 GPU batch-1 median forward latency를 우선한다. latency도 같으면 parameter 수가 작은 모델을 사용한다. 0.001은 실무 선택 기준이며 통계적 동등성 판정이 아니다.
- Standard/Unseen ROC-AUC·category 편차·모델 크기도 report에 함께 기록한다. Test 결과로 추가 튜닝하거나 선정 규칙을 바꾸지 않는다.
- latency는 float32, 이미 전처리된 동일 tensor shape, encoder+head forward만 포함한다. 이미지 decode·resize·HTTP overhead는 포함하지 않는다.

## 계약·소유권

`model.normalization`의 mean/std는 configs가 소유한다. Dataset은 이를 소비하고 checkpoint config와 실험 config는 실행 시점 스냅샷이다. 기존 SigLIP checkpoint에서 필드가 없으면 기존 mean/std 0.5를 그대로 사용한다. 차원은 pretrained config에서 유도한다.

## 제외·운영

LoRA는 P04 조건부, calibration은 P05. GEN 근사중복 및 독립 최종 holdout은 별도 후속 항목이다. GPU에 소유자 작업이 있으면 학습을 중단하고 큐잉하지 않는다. `last.pt`로 동일 config 재개하며 디스크 로그를 보관한다.

## 관련 결정·참조

Test B 구성은 [DB-04](../decision_briefs/DB-04_P02_unseen-real.md) 유지. 신규 소유자 결정은 없다.

DINO의 [공식 processor 설정](https://huggingface.co/facebook/dinov2-base/blob/f9e44c814b77203eaa57a6bdbbd535f21ede1415/preprocessor_config.json) 및 [Transformers 문서](https://huggingface.co/docs/transformers/model_doc/dinov2)를 확인했다.

## 완료 근거

- DINO 10 epoch CUDA 학습·validation 기반 best 저장·Test A/B 평가. P02와 metadata hash 및 공통 학습 설정 동일.
- [비교 report](../../experiments/p03_comparison/README.md)와 원시 benchmark JSON에 Standard/Unseen·category별 AUC·GPU latency·parameter 수·checkpoint 크기를 보관한다.
- 사전 기준으로 primary **SigLIP** 선정: validation AUC 차이 0.000102 <0.001, median forward latency 9.633ms vs DINO 12.407ms. 실행 설정은 `configs/primary.yaml`, checkpoint는 기존 `checkpoints/baseline/best.pt`.
- CPU 전체 38 passed, CUDA 집중 4 passed, 실제 DINO checkpoint의 config/epoch 및 encoder 전체 tensor가 pretrained 값과 동일함 확인. 독립검증·mutation은 미수행.
- §17의 LoRA 진입 근거가 현재 지표에는 없으므로 다음 실행 대상은 P05 calibration이다. GEN 근사중복·독립 최종 holdout은 후속 항목이다.

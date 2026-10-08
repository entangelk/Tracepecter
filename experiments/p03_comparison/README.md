# P03 — SigLIP vs DINOv2 비교·primary 선정

2026-10-09, 동일 split의 frozen encoder + 동일 768차원 MLP head 비교. **primary는 SigLIP**으로 선정한다.

## 비교 조건

- train 3,780 / val 820 / Test A 800 / Test B 1,048(REAL 448 공유 + unseen FAKE 600). metadata SHA256은 두 실험에서 동일하다.
- seed 42, 10 epoch, batch 32, Adam lr 0.0001, 동일 augmentation과 square 224 geometry. DINO 정규화만 native mean/std로 설정했다.
- DINO native shortest-edge resize/center crop 또는 518 고해상도 비교가 아니라, 동일 pixel budget의 현재 구현 비교다.
- 각 checkpoint는 validation BCE로 선택했다. primary는 사전 [P03 계획](../../docs/plan/phase_3_baseline_comparison.md)의 규칙으로 선정했다. validation ROC-AUC 차이 ≥0.001이면 높은 모델, 미만이면 GPU median latency, latency도 같으면 parameter 수 순이다. 이는 통계적 동등성 판정이 아니다.
- Test 지표는 진단용으로 기록하며 추가 튜닝 또는 선정 규칙 변경에 사용하지 않았다.
- benchmark: 이 머신 RTX 3060 12GB, torch 2.9.0+cu128, float32 batch 1, warmup 10 / 측정 100회, 매 측정 전후 CUDA synchronize. decode·preprocessing·HTTP를 제외한 encoder+head forward 시간이다. synthetic 입력 tensor shape은 두 모델 모두 1×3×224×224다.

## 결과

| 모델 | Validation ROC-AUC | Test A ROC-AUC | Test B ROC-AUC | GPU median ms | Parameter 수 | Checkpoint MiB |
| --- | --- | --- | --- | --- | --- | --- |
| siglip | 0.999874 | 0.999937 | 0.999766 | 9.633 | 93,475,585 | 356.65 |
| dino | 0.999772 | 0.999937 | 0.998618 | 12.407 | 87,171,841 | 332.61 |

validation ROC-AUC 차이 0.000102는 0.001 미만이다. SigLIP의 낮은 latency에 따라 선정했으며, DINO가 더 작은 checkpoint라는 tradeoff도 함께 기록한다.
두 모델의 Test A ROC-AUC는 같고, 현재 Test B에서는 SigLIP이 더 높다. Test 지표로 사전 선택 규칙을 바꾸지는 않았다.

| 카테고리 | SigLIP Test B ROC-AUC | DINO Test B ROC-AUC |
| --- | --- | --- |
| 상의 | 0.999881 | 0.999226 |
| 아우터 | 0.999405 | 0.994464 |
| 원피스 | 1.000000 | 0.999405 |
| 하의 | 1.000000 | 0.999821 |

## 산출물·검증

- [원시 comparison JSON](comparison.json): latency 100회 전체 값·parameter/파일 크기·config·선정 결과.
- [SigLIP 실험](../p02_siglip_baseline/README.md), [DINO config](../p03_dino_baseline/config.yaml), [DINO experiment JSON](../p03_dino_baseline/experiment.json). 원본 pretrained revision 및 checkpoint/metadata hash를 보관한다.
- 구현/benchmark 코드 commit: `c6ab048`(전체 hash는 DINO experiment JSON). P02 snapshot과 바이너리는 보존했다.
- [primary config](../../configs/primary.yaml) = SigLIP 실행 설정, checkpoint `checkpoints/baseline/best.pt`. DINO는 `checkpoints/dino/best.pt`, 재개용 `last.pt`와 로그를 별도 경로에 둔다. 바이너리는 Git 비추적이다.
- CPU 전체 회귀 38 passed, CUDA 집중 4 passed. DINO pooling·freeze/해제·정규화 기본값/거부·train/val/evaluate 전달·primary 규칙을 확인했다. 독립검증·mutation testing은 수행하지 않았다.

## 한계·다음 작업

- 현재 개발 데이터의 비교 결과이며 전체 encoder 계열의 일반적 우월성이나 독립적인 최종 제품 성능을 판정하지 않는다. 단일 REAL source, GEN 근사중복 미점검, 미사용 최종 REAL/FAKE holdout 확보가 남는다.
- 현재 frozen baseline이 수치 목표를 충족하고 unseen 성능 저하도 작으므로 §17에 따라 LoRA에 진입하지 않는다. 추가 데이터/실패 분석에서 근거가 생기면 조건을 재검토한다.
- 다음은 P05 calibration 계획·구현. 최종 독립 holdout과 GEN 근사중복은 별도 후속 항목으로 유지한다.

# P02 — frozen SigLIP baseline 실험

2026-10-09 기준 첫 실데이터 baseline. P02 실행 조건을 확인하는 개발 평가이며, 독립적인 최종 제품 검증과 구분한다.

## 구성·재현

- 구현 commit: `37ba16a42e47d0a70f2f84be8309fe6a338669c6`. pretrained vision revision은 `config.yaml`에 고정했다.
- 모델: SigLIP vision pooled feature(768) → Linear(768) → GELU → Dropout(0.1) → Linear(1) → Sigmoid. REAL=1, Generated=0.
- encoder는 frozen/eval/no-grad, head만 Adam으로 학습한다. 10 epoch, seed 42. config 및 전체 metric은 [`experiment.json`](experiment.json), config 스냅샷은 [`config.yaml`](config.yaml).
- 환경: Docker Compose training profile, torch 2.9.0+cu128 / torchvision 0.24.0+cu128 / transformers 5.19.0. 이 머신의 GPU는 RTX 3060 12GB.
- metadata SHA256: `039cbdd11407e5571b75681d64ae832b04c2f9439e94e94abf46d16f6e2d5781`. 기존 split은 변경하지 않았다.
- train 3,780(REAL 2,100 + GEN 1,680), val 820(REAL 452 + GEN 368). 선택 기준은 validation BCE이며 Test A/B 결과는 checkpoint 선택에 사용하지 않았다.
- Test A: REAL 448 + 학습에 포함된 생성기들의 GEN 352 = 800.
- Test B: Test A REAL 448 재사용 + `test_unseen`의 sd35_medium GEN 600 = 1,048([DB-04](../../docs/decision_briefs/DB-04_P02_unseen-real.md)). train/val REAL은 제외했다.
- augmentation은 학습에만 적용한다. 평가에서는 RGB·224 square bicubic resize·mean/std 0.5 정규화만 사용한다.

## 결과

| 집합 | Accuracy | ROC-AUC | PR-AUC | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| Test A | 0.995000 | 0.999937 | 0.999950 | 0.995536 | 0.995536 | 0.995536 |
| Test B | 0.988550 | 0.999766 | 0.999688 | 0.978070 | 0.995536 | 0.986726 |

best checkpoint: epoch 10, validation BCE 0.013387, validation ROC-AUC 0.999874.
PR-AUC는 PR 곡선의 사다리꼴 면적이다(average precision과 구분). 고정 threshold 0.5이며 calibration은 P05 범위다.

| 카테고리 | Test A ROC-AUC | Test B ROC-AUC |
| --- | --- | --- |
| 상의 | 0.999899 | 0.999881 |
| 아우터 | 1.000000 | 0.999405 |
| 원피스 | 1.000000 | 1.000000 |
| 하의 | 1.000000 | 1.000000 |

생성기별 AUC는 해당 GEN + 전체 REAL, source별 AUC는 해당 REAL source + 전체 GEN으로 계산한다. 세부 지표는 JSON에 보관한다.

## 검증·한계

- 실제 best checkpoint의 encoder 전체 tensor가 원본 pretrained 값과 같고 config/epoch가 실행 기록과 일치함을 확인했다.
- 최종 CPU 회귀 테스트 35 passed. CUDA 환경 전체 34 passed 이후 worker/crop 보강은 집중 테스트로 확인했다. 재개는 2-worker·augmentation을 포함한 연속 실행과 중단 후 실행의 state/이력 일치로 검증했다. 독립검증·mutation testing은 수행하지 않았다.
- Standard ≥0.90 / Unseen ≥0.80 수치 기준은 충족하지만, 단일 REAL source(K-Fashion)와 현재 생성 환경에서의 결과다. 사람의 체감·실환경 일반화·최종 제품 성공을 판정하지 않는다.
- 두 테스트의 REAL 표본은 공유되므로 서로 독립적인 표본 평가가 아니다. 개발 중 테스트 결과로 모델/설정을 선택하면 최종 검증에는 그 선택에 사용하지 않은 새 REAL/FAKE holdout을 준비하는 것이 권장된다. 현재 신규 수집이나 split 변경은 수행하지 않았다.
- GEN pHash/embedding 근사중복 점검은 미수행 후속 항목이다.
- checkpoint 바이너리는 Git 비추적이며 로컬 `checkpoints/baseline/best.pt`, 재개용 `last.pt`, 로그 `training.log`·`evaluation.log`에 남는다. checkpoint SHA256은 JSON에 기록했다.

## 다음 작업

P03 계획을 작성하고 동일 split에서 DINO baseline을 비교한다. 최종 독립 holdout 설계와 GEN 근사중복 점검은 별도 후속 작업으로 관리한다.

# P08-05 익명화 checkpoint 재calibration

상태: **구현·실행·자가 확인 완료, 독립검증 대기 (2026-10-19)**. [P08 계획](../../../docs/plan/phase_8_face_anonymization.md) §P08-05가 범위를 소유한다. 절차는 [P05](../../p05_calibration/README.md)와 같고, 익명화 checkpoint `checkpoints/anonymized/best.pt`([학습 기록](../training/README.md))를 validation 820장에서만 fitting했다. P05 artifact와 `configs/calibration.yaml`은 바꾸지 않았다.

## 설정·산출물

- [configs/calibration_anonymized.yaml](../../../configs/calibration_anonymized.yaml)은 P05 설정과 `fit`·`metrics`·`device`가 같다. 다른 것은 checkpoint·`face_cache`·출력 경로 세 개뿐이다. 익명화 규격은 override 없이 checkpoint에 결합된 규격(snapshot hash `e171cec2…`)만 쓴다. 이 차이는 `tests/test_p08_calibration_config.py`가 고정한다.
- 결과: temperature **0.96874725**, calibrated probability threshold **0.38315014**(score threshold **38.32**). score 정의는 P05와 같다: `100 * sigmoid(logit / temperature)`.
- [calibration artifact](calibration.json): checkpoint sha256 `091ac454…`(P08-04 best와 일치), metadata sha256 `039cbdd1…`(실행 전후 불변), 구현 commit `3106aee`.
- [validation predictions](validation_predictions.csv) 820행이 metadata의 val ID 집합과 정확히 같다. [metrics](metrics.json)·[config snapshot](config.yaml)도 함께 둔다.
- 모든 입력은 익명화 입력이다. val·Test A·Test B 모두 검증된 얼굴 좌표 캐시를 사용했다.

## calibration 지표 (새 모델, 익명화 입력)

| 집합 | NLL raw → calibrated | Brier raw → calibrated | ECE raw → calibrated |
| --- | --- | --- | --- |
| Validation | 0.021585 → 0.021562 | 0.006313 → 0.006338 | 0.005811 → 0.005940 |
| Test A | 0.015554 → 0.015425 | 0.004465 → 0.004459 | 0.003536 → 0.003283 |
| Test B | 0.035558 → 0.035444 | 0.010302 → 0.010300 | 0.015112 → 0.014896 |

- temperature가 1에 가까워(0.969) 확률 보정 효과는 작다. fitting 목적함수인 validation NLL은 조금 개선됐지만, **validation Brier·ECE는 조금 악화**됐다. Test A/B는 세 지표 모두 근소하게 개선됐다. 이 결과로 temperature를 다시 고르지 않았다.
- fitting 집합이 checkpoint 선택에 쓴 validation과 같다는 P05의 한계는 그대로 남는다.

| 집합 | Accuracy: raw 0.5 | Accuracy: validation 선정 threshold | ROC-AUC |
| --- | --- | --- | --- |
| Validation | 0.991463 | 0.993902 | 0.999796 |
| Test A | 0.993750 | 0.993750 | 0.999867 |
| Test B | 0.987595 | **0.983779** | 0.999647 |

- validation threshold가 0.383으로 낮아졌다. 그 결과 Test B에서 REAL로 판정된 sd35 GEN이 12장에서 16장으로 4장 늘었다(precision 0.973856 → 0.965443). REAL recall은 0.997768로 같다. unseen 생성기에 대한 threshold 일반화 한계로 기록하며, Test 결과로 threshold를 조정하지 않는다.
- 이 표는 새 모델을 익명화 입력에서 평가한 것이다. baseline(원본 입력)인 P05 값과 직접 비교하면 모델 효과와 입력 효과가 섞인다. 고정된 2×2 비교, §20 기준, '단서 해소' 판정은 P08-06이 [사전등록 계약](../diagnostic/README.md)대로 수행한다. 이 문서는 채택 여부를 판정하지 않는다.

## 재현·확인

```bash
GIT_COMMIT=$(git rev-parse HEAD) docker compose --profile training run --rm -T train \
  python -u -m src.calibrate --config configs/calibration_anonymized.yaml
docker compose --profile training run --rm -T train python -m src.score \
  --image /images/real/<image>.jpg --calibration experiments/p08_anonymized/calibration/calibration.json --device cuda
```

- 2026-10-19 이 머신(RTX 3060, H: checkpoint mount)에서 daemon이 관리하는 detached 컨테이너로 실행했다. exit 0, 약 2분 21초 걸렸다. 같은 commit으로 다시 실행했을 때 `calibration.json`·`metrics.json`·`validation_predictions.csv` 세 파일이 byte 단위로 같았다.
- score CLI는 캐시 없이 YuNet으로 직접 검출한다. val REAL `998959`의 score는 92.676153(`photographic_like`)이었고, 두 번 실행해도 같았다. val GEN `gen_000676`의 score는 0.000238(`synthetic_like`)이었다. 두 값 모두 캐시 기반 예측 logit(2.458660, -12.542751)에 temperature를 적용한 값과 일치한다. 표본 두 장으로 일반화하지 않는다.
- 회귀 가드:
  - `tests/test_p08_calibration_config.py`는 config 변이 4종(iterations 변경, P05 출력 경로 재사용, `face_cache` 삭제, baseline checkpoint 지정)에서 모두 실패하고, 원래 config에서는 통과한다.
  - P05 회귀 가드(`tests/test_calibration.py`)와 익명화 calibrate/score 연결 테스트(`tests/test_anonymize.py`)는 코드 변경 없이 그대로 유지된다.
  - 전체 CPU suite: 182 passed, 1 skipped(실제 YuNet opt-in).

## 한계

- REAL/Generated 라벨의 calibrated probability proxy라는 P05의 한계를 그대로 가진다. 얼굴이 보이는 실사에서의 calibration은 P08-07 holdout 없이 측정할 수 없다.
- 이 artifact는 P08-06에서 채택될 때까지 서빙 primary가 아니다. `configs/primary.yaml`은 바꾸지 않았다.

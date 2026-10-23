# P09 r1 val-only 보정과 고정 평가

새 checkpoint `checkpoints/leakage_repair/r1/best.pt`에 새 val820장만 사용했다. 설정은 [configs/p09_r1_calibration.yaml](../../../../configs/p09_r1_calibration.yaml), 학습 근거는 [training](../training/README.md)다. 학습/보정 metadata SHA-256은 `5a323684dbf157a1db38201f8fe8007185a7809f2ab1ab9564f225faed682161`, checkpoint SHA-256은 `8fcd4859cd13fe2c2636565f4cc40bcfeff6447923dbc04d2c99450fefca0731`이다.

## 실행과 검증

2026-10-23 이 머신에서 GPU 점유를 확인한 후, 사전 커밋 `8e01af3764ca6d86cde2fb0a3002a35c9bbe6a3f`의 설정으로 `python -m src.calibrate --config configs/p09_r1_calibration.yaml`을 CUDA에서 실행했다. [execution.json](execution.json)은 시작/종료 시각과 종료 코드0을 기록한다. 별도 경로에 [calibration.json](calibration.json)·[metrics.json](metrics.json)·[validation_predictions.csv](validation_predictions.csv)를 저장했고 작업 컨테이너는 종료 후 제거했다.

temperature는 **0.7770388872932664**, 확률 threshold는 **0.23513432654393307**이다. 새 val ID만으로 fitting했으며 기존 P08 parameter를 복사하지 않았다. `verify.py`가 val ID의 정확한 집합·중복 부재·유한 logit·label 결합을 확인하고 temperature·threshold·val 지표를 재계산해 정확히 재현했다. [verification.json](verification.json)은 입력/출력 hash와 기존11개 artifact 불변 검증을 고정한다.

```bash
docker compose run --rm -T dev \
  python -m experiments.p09_leakage_repair.r1.calibration.verify
```

## 결과

| 평가 | 표본 | AUC | 보정 accuracy | raw → 보정 NLL | raw → 보정 Brier | raw → 보정 ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| val | 820 | 0.9999158330 | 0.9975609756 | 0.01114555 → 0.01036569 | 0.00311132 → 0.00317642 | 0.00451925 → 0.00280434 |
| Test A | 800 | 0.9996131798 | 0.9925000000 | 0.02485318 → 0.02564035 | 0.00733952 → 0.00757262 | 0.00789345 → 0.00886355 |
| Test B | 1,048 | 0.9994940476 | 0.9837786260 | 0.03248728 → 0.03169555 | 0.00979875 → 0.01004842 | 0.00974557 → 0.00695806 |

보정은 val NLL을 낮췄지만 모든 지표를 개선하지 않았다. 세 cohort의 Brier와 Test A NLL/ECE가 악화됐고 Test B accuracy는 raw0.9847328244에서 낮아졌다. 이를 숨기거나 test 결과로 parameter를 다시 선택하지 않는다. 전체 PR-AUC·precision·recall·F1은 `metrics.json`에 있다.

Test B는 **새 Test A REAL448장 + test_unseen GEN600장**이다. [evaluation_ids.csv](evaluation_ids.csv)가 두 cohort ID를 명시하고 검증기가 공유448장 전부 새 test REAL이며 train/val REAL이 없음을 확인한다. 테스트 지표는 보정 실행이 산출한 값이다. 테스트 logit은 저장하지 않았으므로 검증기가 테스트 지표 자체를 독립 재계산했다고 주장하지 않는다. 최종 주석 커밋 후 진단 실행에서 고정 평가를 다시 계산한다.

## 해석과 후속

현재 값은 익명화 입력의 개발 평가다. 이전 split과 표본이 다르고 기존 데이터가 개발에 노출됐으므로 대응표본 성능 개선이나 독립 일반화 복구의 증거로 해석하지 않는다. 원본 입력·baseline 비교·얼굴 상태별 결과·다섯 단서 관문은 소유자 확인과 최종 주석 커밋 후 [P09 진단](../diagnostic/README.md)에서 수행한다. P09-04는 진행 중이며 현 primary를 변경하지 않았다.

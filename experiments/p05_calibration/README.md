# P05 — validation temperature scaling·0~100 score

2026-10-09, primary SigLIP checkpoint의 validation 820장으로 fitting했다. 원본 checkpoint와 P02/P03 스냅샷은 보존한다.

## 정의·산출물

- temperature **0.79847842**, calibrated probability threshold **0.69669911**(score threshold **69.67**).
- `realism_score = 100 * sigmoid(logit / temperature)`. 확률이 threshold 이상이면 `photographic_like`, 미만이면 `synthetic_like`. 0 logit의 score는 50이며 classification 경계와 같다는 뜻은 아니다.
- sigmoid 출력의 역변환 대신 원래 logit을 사용한다. 양수 temperature는 logit 순서를 보존하며, finite precision에서 극단 확률의 동률은 생길 수 있다.
- temperature는 validation NLL 최소, threshold는 validation balanced accuracy 최대(후보 0/1·관측 probability·0.5, 동점은 0.5 근접 후 작은 값). Test는 fitting 또는 parameter 재조정에 사용하지 않았다.
- [calibration artifact](calibration.json) = method/version·temperature·확률 threshold·checkpoint/metadata SHA256·실행 config·구현 commit. score threshold는 유도하며 중복 저장하지 않는다.
- [validation predictions](validation_predictions.csv) = `image_id,logit` 820행. label/split은 canonical `data/metadata.csv`에서 읽는다. [metrics](metrics.json), [config snapshot](config.yaml).
- fitting 데이터는 checkpoint 선택에 쓰인 기존 validation과 같다. fitting 집합에서의 지표 개선은 독립적인 calibration 검증이 아니다.

## calibration 지표

| 집합 | NLL raw → calibrated | Brier raw → calibrated | ECE raw → calibrated |
| --- | --- | --- | --- |
| Validation | 0.013387 → 0.012745 | 0.003519 → 0.003457 | 0.004870 → 0.004565 |
| Test A | 0.010695 → 0.010163 | 0.003038 → 0.003036 | 0.003365 → 0.003129 |
| Test B | 0.027139 → 0.027630 | 0.007783 → 0.007925 | 0.011638 → 0.010769 |

validation은 세 지표 모두 개선됐고 Test A에서도 개선됐다. **Test B NLL/Brier는 조금 악화**됐다. ECE는 개선됐지만 이것만으로 unseen calibration 개선을 주장하지 않는다. 이 결과로 temperature를 다시 선택하지 않았다.
ECE는 10개 equal-width bin의 REAL class probability와 관측 REAL 비율 차이의 표본수 가중합이다.

| 집합 | Accuracy: raw threshold 0.5 | Accuracy: validation 선정 threshold |
| --- | --- | --- |
| Validation | 0.995122 | 0.996341 |
| Test A | 0.995000 | 0.993750 |
| Test B | 0.988550 | 0.989504 |

Test A 정확도는 한 건 낮아졌고 Test B는 한 건 높아졌다. 이는 temperature와 validation threshold를 함께 적용한 결과이며 순수 calibration 효과와 구분한다. ROC/PR 및 Precision/Recall/F1은 JSON에 보관한다.

## scoring·재현

```bash
GIT_COMMIT=$(git rev-parse HEAD) docker compose --profile training run --rm train python -m src.calibrate --config configs/calibration.yaml
docker compose --profile training run --rm train python -m src.score --image /images/real/<image>.jpg --calibration experiments/p05_calibration/calibration.json --device cuda
```

- CLI 출력은 `realism_score`와 `classification` 두 필드다. hash가 다른 checkpoint 또는 유효하지 않은 temperature/threshold artifact는 거부한다.
- 실제 validation REAL 이미지 score 96.89161(`photographic_like`), Generated 이미지 0.00000508(`synthetic_like`). 같은 REAL을 두 번 scoring한 결과가 동일함을 확인했다. 샘플 둘로 전체 일반화를 판정하지 않는다.
- CPU 전체 43 passed, CUDA 집중 10 passed. test 이미지 변경으로 fitting 값이 바뀌지 않는 가드·val-only ID 검증·checkpoint hash 거부·단일 클래스 지표 허용/단일 클래스 fitting 거부·logit/확률 호환을 확인했다.
- 실제 validation ID 집합과 prediction CSV가 정확히 같고 metadata hash가 불변이며 checkpoint SHA256이 P02 원본과 같음을 확인했다. 독립검증·mutation testing은 미수행이다.

## 한계·다음 작업

- REAL/Generated 라벨의 calibrated probability proxy다. 사람 체감 photographic realism·중간 품질 영역·실환경 calibration은 사람 평가 및 별도 미사용 REAL/FAKE holdout으로 확인해야 한다.
- 단일 REAL source·GEN 근사중복 미점검·Test A/B REAL 공유는 유지된다. 최종 독립 holdout·GEN 점검은 후속 항목이다.
- 다음은 P06 failure analysis 계획·사례 분석. Test B의 NLL/Brier 악화도 분석 대상으로 남긴다.
- 방법: [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html).

# P06 — 오류 자동 저장·편향 통제 진단 (P06-01·P06-02)

2026-10-09, 구현 commit `35db1fb` + 사본 파일명 수정 `eb246ea`. 두 번 실행한 predictions.csv가 바이트 단위로 같다. 고정 [P05 artifact](../p05_calibration/calibration.json)(T 0.79847842, 확률 threshold 0.69669911)와 primary SigLIP checkpoint를 사용했다. 모델·threshold·split은 변경하지 않았다. 설정은 [`configs/failure_analysis.yaml`](../../configs/failure_analysis.yaml), 산출물은 [predictions.csv](predictions.csv)(`image_id,condition,logit`)와 [diagnostics.json](diagnostics.json)이다.

## P06-01 오류 저장

`reports/errors/{false_positive,false_negative,low_confidence}/manifest.csv`에 기록했다. 이미지 사본은 같은 폴더에 있으며 Git에서 추적하지 않는다. REAL=1이고, low_confidence는 오분류가 아닌 score 10~90 표본이다.

| 유형 | Test A | Test B | val | 고유 |
| --- | --- | --- | --- | --- |
| false_positive(GEN→photographic) | 1 | 7 | 2 | 10 |
| false_negative(REAL→synthetic) | 4 | 4 | 1 | 5 |
| low_confidence | 3 | 14 | 7 | 24 |

- 오분류 수가 P05와 같다(A 5, B 11). 공유 REAL을 한 번만 세면 test 고유 오분류는 **12장**이고, val을 포함하면 15장이다. C0의 AUC·정확도는 P05 `metrics.json`과 정확히 같다.
- test FP 8장 중 7장이 sd35_medium(unseen), 1장이 qwen_image_21이다. FP 10장 중 5장이 아우터다. FN 5장은 모두 score 32~55로, 강한 확신의 REAL 오판은 없다.
- val의 `1247671`은 score가 threshold와 정확히 같다. threshold를 정의한 관측 확률이므로 photographic으로 판정된다.

## P06-02 통제 진단

양 클래스에 같은 변환을 적용했다. `gen_jpeg_real_quality`만 GEN에 적용하고 REAL은 원본 logit을 사용했다. REAL test JPEG의 luminance 양자화 table로 추정한 대표 품질(median)은 **75**다. 그 결과 이 조건의 GEN 입력은 `jpeg_q75`와 같다.

| 조건 | A AUC | B AUC | B 정확도 | B GEN 평균 score 변화 | B 판정 전환(REAL/GEN) |
| --- | --- | --- | --- | --- | --- |
| 원본 | 0.999937 | 0.999766 | 0.9895 | — | — |
| JPEG q90 | 0.99992 | 0.99974 | 0.9885 | +0.33 | 1 / 2 |
| JPEG q75 | 0.99984 | 0.99966 | 0.9857 | +0.60 | 0 / 4 |
| 긴 변 512 다운스케일 | 0.99993 | 0.99980 | 0.9905 | +0.07 | 2 / 1 |
| 중앙 정사각 crop | 0.99994 | 0.99945 | 0.9819 | +2.77 | 3 / 11 |
| GEN만 JPEG(q75) | 0.99984 | 0.99966 | 0.9857 | +0.60 | 0 / 4 |

원본 정사각(h/w=1) 표본만 보면 A AUC 1.0(333장), B 0.99987(457장)이다. 전체 집합과 거의 같다.

### 해석

- **JPEG 흔적 의존의 근거는 약하다.** GEN에 REAL과 같은 수준의 JPEG 압축을 가해도 GEN 평균 score는 0.3~0.6점만 오르고, Test B에서 판정이 바뀐 GEN은 4/600장이다. JPEG 흔적이 판별의 주된 단서였다면 GEN score가 크게 올라야 한다. 다만 "JPEG가 전혀 쓰이지 않는다"는 입증은 아니다. 압축 경로가 서로 다르고(REAL은 이중 압축, GEN은 단일 압축) 정량적 기여도도 측정하지 않았다.
- **원본 해상도·리샘플링 차이**: 512 다운스케일로 AUC가 바뀌지 않았다. 고주파 리샘플링 흔적에 대한 의존 근거는 관측되지 않았다.
- **종횡비**: 정사각 표본만 따로 봐도 AUC가 유지되므로, REAL에만 있는 종횡비가 주된 단서라는 근거는 없다.
- **구도·크롭에는 민감하다.** 중앙 정사각 crop에서 unseen GEN의 score가 평균 +2.77 올랐고 11장이 모두 FP로 바뀌었다. 같은 조건에서 REAL FN 3장은 정답으로 돌아왔다. Test B 오류는 11장에서 19장으로 늘었고, 정확도는 0.9895에서 0.9819로 떨어졌다. 정사각 원본은 이 변환에서 그대로이므로, 변화는 세로형 GEN(832×1216, 전신 구도)에 crop을 적용했을 때 나온다. 전신 → 부분 프레임 변화가 GEN을 REAL처럼 보이게 한다는 가설과 일치한다. 그러나 crop은 정보 손실(머리·발 제거)도 동반하므로 원인을 구도로 확정하지 않는다. P06-03에서 판정이 바뀐 사례를 직접 검토한다.
- 모든 조건에서 AUC가 0.9994 이상이다. 따라서 이 진단은 현재 데이터 안에서의 견고성을 보여 줄 뿐이며, 다른 REAL 출처나 촬영 조건에 대한 일반화를 말해 주지 않는다.

## Test B NLL/Brier 악화 분해(P06-04 일부)

Test B 1,048장의 표본별 loss를 raw(T=1)와 calibrated로 비교했다.

- 1,036장은 개선됐고 12장은 악화됐다. 악화된 12장은 전부 **logit이 양수인 sd35_medium GEN**이다(오답 쪽으로 확신하던 표본). NLL 총 변화 +0.515 중 GEN의 기여가 +1.238, REAL의 기여가 −0.723이다.
- 원인: T<1은 logit의 크기를 키운다. 그 결과 unseen 생성기에서 이미 틀린 소수 표본의 loss가 커져 다수 표본의 개선분을 넘어선다. 악화는 표본 전반이 아니라 FP 집중 현상에서 나온다. 이는 unseen 생성기의 확신 오답이 calibration의 주요 위험이라는 뜻이다.

## 한계

- 단일 checkpoint·단일 실행이며 신뢰구간은 계산하지 않았다. 공유 REAL 때문에 A/B는 독립 표본 집합이 아니다.
- 모든 진단은 같은 K-Fashion REAL과 같은 생성 파이프라인 안에서 이루어졌다. 새 REAL 출처·저장 조건에서의 holdout 평가를 대체하지 않는다.

## 재현

```bash
docker compose --profile training run --rm -T train python -m src.failure_analysis --config configs/failure_analysis.yaml
```

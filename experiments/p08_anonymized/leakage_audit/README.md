# P08 테스트 누출 적대적 감사 (2026-10-20)

**판정: 평가 데이터 독립성 불합격.** 완전 동일 파일/픽셀이나 현재 학습 코드의 test 직접 혼입은 확인하지 못했지만, 같은 옷·촬영 배경/소품의 다른 컷이 train과 val/test에 나뉜 사례를 확인했다. 기존 0.9996 수준 AUC를 독립 일반화 성능으로 확정하면 안 된다. 기존 사전등록 통계 관문이 통과했다는 사실과 이번 데이터 독립성 실패는 서로 다른 검증 범위다.

## 범위와 원자료

- metadata 6,000행, 원본 6,000개 전수 SHA-256·decoded RGB SHA-256·pHash·해상도·형식·224px 픽셀 통계를 계산했다. 모든 원본 SHA는 학습 전에 고정된 `face_boxes.csv`와 일치한다.
- 현재 frozen SigLIP이 보는 익명화 입력에서 6,000개 embedding을 추출하고, val/test/test_unseen 2,220장 각각에 대해 train 3,780장의 최대 cosine 최근접을 계산했다. cosine은 후보 순위이며 동일 룩의 판정 기준을 임의의 숫자로 확정하지 않았다.
- GEN PNG 3,000장의 embedded ComfyUI `prompt` graph에서 실제 전체 positive prompt와 noise seed를 읽었다. metadata의 짧은 `prompt_id`는 full prompt가 아니고 style 값도 비어 있어 정확한 렌더 계보의 정본으로 사용하지 않았다.
- 기존 모델·metadata·split·checkpoint·calibration은 변경하지 않았다. 감사 도구 `scripts/p08_leakage_audit.py`와 `scripts/p08_leakage_probe.py`는 별도 artifact만 쓴다. `probe_result.json.identity`가 실행 코드·checkpoint·calibration·metadata·face cache를 고정한다.
- 이 감사는 P08-06 구현에 참여했던 Codex(root)의 추가 점검이다. 별도 에이전트의 독립검증으로 표현하지 않는다.

## 1. 직접 혼입·완전 중복

| 검사 | 결과 |
| --- | --- |
| ID·이미지 경로의 split 교차 | 0 |
| 선언된 REAL look_group의 split 교차 | 0 |
| 전체 파일 SHA-256 중복 | 0 |
| decoded RGB bytes SHA-256 중복 | 0 |
| sd35_medium의 train/val 혼입 | 0 |
| 실제 학습 config의 metadata 분리 | train 3,780 / val 820 |

실학습 commit `6ace79b`와 현재의 `src/train.py`·`src/dataset.py`·`src/model.py`는 동일하다. 실 checkpoint config는 `data.metadata_csv`를 지정하므로 학습 Dataset은 `split='train'`, validation Dataset은 `split='val'`로 필터한다. best checkpoint는 validation loss에서 선택하고 calibration fitting은 val ID만 사용한다. forward에는 이미지 tensor만 들어가며 파일명·label·source 필드를 모델에 전달하는 경로는 없다.

이는 실행 코드·저장 기록·현 원본의 일치 근거다. 과거 학습 과정 전체의 암호학적 sample ledger가 존재하는 것은 아니므로, 일치 증거를 과거 실행의 절대 증명으로 확대하지 않는다. 사전학습 encoder 원자료와의 중복도 이 감사로 배제하지 못한다.

## 2. 확인된 같은 룩 교차 — 최소 8쌍

REAL 최근접 상위 후보 중 14쌍을 원본으로 시각 점검해 8쌍에서 같은 옷과 촬영 세트의 다른 컷을 확인했다. 나머지 6쌍은 동일 룩으로 확정하지 않았다. 이는 전체 누출 수 추정이 아닌 **발견된 하한**이다. `visual_review.csv`에 ID·split·그룹·cosine·pHash 거리·판정 이유를 보존한다.

| 평가 이미지 | train 이미지 | split | pHash 거리 |
| --- | --- | --- | --- |
| 1325559 | 1331504 | test | 16 |
| 767339 | 767324 | test | 26 |
| 1283747 | 646833 | val | 18 |
| 705886 | 1335623 | val | 12 |
| 801545 | 802855 | test | 14 |
| 898255 | 1005884 | val | 16 |
| 1231839 | 205220 | test | 16 |
| 1346304 | 1346302 | val | 20 |

예: 1325559/1331504는 파란 상의·크림색 바지·목걸이와 원탁·꽃·컵·의자가 일치하고 포즈/프레이밍이 다르다. 767339/767324는 흰 블라우스·청바지·가방·구두와 바닥·의자·걸친 옷이 일치하는 다른 컷이다. 양쪽의 look_group은 서로 다른 phash ID라 기존 그룹 검사에서 잡히지 않았다.

여덟 쌍 모두 pHash 거리 10을 넘는다. 따라서 pHash만으로는 놓친다. `scripts/deduplicate.py`의 embedding 층은 P02+로 미뤄졌고 현재까지 split에 반영되지 않았다. `docs/project.md` §8·§13·§14가 요구하는 같은 룩/유사 이미지 그룹 독립성을 현재 그룹 ID 검사만으로 입증할 수 없다.

한편 pHash≤10인 cross-split 후보는 145쌍(REAL/REAL 1, GEN/GEN 105, 서로 다른 클래스 39)이다. 이 숫자는 확인된 중복 수가 아니다. REAL 후보 469348/231863은 시각적으로 다른 옷이고, 최저거리 GEN 1286/165도 회색 코트 구도는 비슷하지만 옷 질감·신발이 다르다. 낮은 pHash 거리만으로 합치는 것도 오탐 위험이 있다.

## 3. unseen generator도 새로운 생성 시나리오는 아니다

embedded graph로 확인한 train 대비 positive prompt+seed 중복:

| GEN split | 이미지 | 동일 prompt+seed | 동일 positive prompt |
| --- | --- | --- | --- |
| val | 368 | 0 | 108 |
| test | 352 | 0 | 132 |
| test_unseen | 600 | 420 | 480 |

sd35_medium은 학습하지 않은 생성기이지만 70%(420/600)는 train의 다른 생성기와 같은 positive prompt·seed를 쓴다. 따라서 ‘새 생성기’ 검사는 맞아도 ‘새 프롬프트/촬영 시나리오까지 독립’이라고 부를 수 없다. 현재 명세는 generator holdout이며 prompt-family holdout은 아니다. 이를 동일 파일의 직접 누출과 혼동하지 않는다.

`posthoc_sensitivity.json`에서 새로운 prompt+seed의 GEN 180장만 쓰면 Test B AUC 0.999330, 새로운 positive prompt의 GEN 120장만 쓰면 0.999330이다(각각 기존 REAL 448장 재사용). 단순 렌더 계보 반복만으로 높은 AUC 전체가 설명되지는 않는다.

## 4. 출처 단서 대조

REAL은 전부 JPEG 3,000장, GEN은 전부 PNG 3,000장이다. GEN의 원본 크기는 832×1216 또는 832×832이고 REAL은 다른 크기 분포다. train 통계만으로 표준화·fit한 선형 ridge 대조 결과:

| 입력 단서 | Test A AUC / accuracy | Test B AUC / accuracy |
| --- | --- | --- |
| 원본 width·height·log(bytes) 3개 | 1.000000 / 1.000000 | 1.000000 / 1.000000 |
| 원본 RGB를 224px로 줄인 색상·gradient 통계 10개 | 0.831422 / 0.777500 | 0.712563 / 0.643130 |
| 위 픽셀 통계, train labels만 셔플 | 0.528891 / 0.573750 | 0.488739 / 0.431298 |

header 단서는 현재 vision model에 직접 입력되지 않는다. 이 100% 결과는 모델이 파일명/해상도 값을 읽었다는 증명이 아니라 **class와 수집/저장 파이프라인이 완전히 교란돼 있다**는 증거다. 픽셀 통계 대조는 원본 RGB 조건이며 현재 익명화 모델의 정확도를 대체하지 않는다. 이 대조에서도 평가 labels·평가 통계는 fit에 쓰지 않았다.

같은 익명화 입력을 224×224로 맞춘 뒤 양 클래스 모두 같은 JPEG 설정으로 재압축했다. model·temperature·threshold는 고정했다.

| 조건 | Test A AUC / accuracy | Test B AUC / accuracy |
| --- | --- | --- |
| 현재 입력 | 0.999867 / 0.993750 | 0.999647 / 0.983779 |
| JPEG quality95, subsampling2 | 0.999531 / 0.988750 | 0.999368 / 0.976145 |
| JPEG quality70, subsampling2 | 0.999829 / 0.991250 | 0.999487 / 0.971374 |

재압축에도 ranking은 높다. 따라서 PNG/JPEG 형식 차이 하나가 원인이라고 결론 내릴 수 없다. 재압축은 원래 압축 이력·배경·촬영 출처·리사이즈 흔적을 완전히 제거하지 않는다. REAL이 K-Fashion 한 출처뿐인 source/label 교란은 남는다.

## 5. 음성 대조와 영향 범위

- 상수 logit 대조는 두 테스트 ROC-AUC 0.5다. 실제 상수 tensor 4장을 모델에 넣은 logit도 모두 0.0995634794로 같았다. `probe_result.json.constant_input`은 0-logit 상수 대조이며 실제 상수 tensor의 원자료는 `constant_tensor_logits`다.
- 평가 labels를 100회 무작위 셔플한 평균 AUC는 A 0.501104 / B 0.497820이다. metric이 label 또는 행 순서 때문에 자동으로 1을 내는 징후는 없다.
- 확인된 test REAL 4장만 사후 제외하면 AUC A 0.999866 / B 0.999643으로 여전히 높다. pHash 근접 후보를 제외해도 A 0.999868 / B 0.999633이다. 이것은 **확인한 몇 장만으로 전체 고성능이 설명되지는 않는다**는 민감도 검사이며, 이미 val/model 개발에 사용된 데이터의 독립성을 복구한 새 시험은 아니다.
- Test A/B는 REAL 448장을 공유한다. P06 오류 분석과 P08 채택 결정에도 같은 테스트가 사용됐으므로 최종 미접촉 holdout이 아닌 개발 평가다. 반복 개발 선택에 따른 낙관 편향을 이 데이터 안에서 정량적으로 배제하지 못한다.

## 결론과 권고

현재 점수 계산이 틀렸다는 증거는 없다. 그러나 데이터 독립성에는 실제 반례가 있고, 출처 차이만으로 class가 분리되는 설계다. 이전 사전등록 관문 통과를 취소해서 숫자를 바꾸거나, 알려진 몇 장만 빼고 ‘누출 해결’로 표시하지 않는다.

다음 수리는 REAL 촬영 시퀀스/동일 룩의 group 보강 → GEN prompt·seed 렌더 family 관리 → 재분할·재학습·재calibration → 출처/해상도/압축을 맞춘 미접촉 REAL/GEN holdout 순서가 적절하다. 현재 primary와 데이터는 감사 요청 범위에서 보존했으며 수리를 실행하지 않았다. 기존 ‘외부 holdout은 P07 관문 아님’ 결정도 이 감사가 변경하지 않는다.

## 재현

```bash
# 원본 전수 지문·픽셀 통계와 실제 PNG 계보, train-only 대조
OPENBLAS_NUM_THREADS=1 docker compose run --rm -T \
  -v /mnt/h/tracepector/images:/images:ro dev python -m scripts.p08_leakage_audit
# GPU 여유를 확인한 뒤 frozen embedding·재압축·음성 대조
# 청크: reports/errors/review/p08_leakage_probe (비추적, 재개 가능)
docker compose --profile training run --rm -T -e HF_HUB_OFFLINE=1 train \
  python -u -m scripts.p08_leakage_probe
# 감사 도구 및 실제 loader 선택 대조
docker compose run --rm -T dev python -m pytest tests/test_p08_leakage_audit.py tests/test_split_dataset.py -q
```

시각 확인은 `visual_review.csv`의 ID를 metadata 경로로 열어 같은 옷과 촬영 세트의 다른 컷인지 확인한다. cosine threshold만으로 자동 확정하지 않는다. 감사 원자료와 요약은 이 디렉터리에 보존한다. 생산 코드 변이와 최종 검사 결과는 별도 검증 기록에 갱신한다.

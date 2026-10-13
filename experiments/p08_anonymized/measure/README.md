# P08-01 — 원 규격·YuNet 재현율 측정

**상태: Complete (2026-10-13).** 학습 GEN·sd35 소유자 확인과 보조 크기 측정을 반영했고, 전체 슬라이스 독립검증 라운드 2에서 합격했다. 모델 score와 재학습 결과는 사용하지 않았다.

[전체 슬라이스 독립검증](../../../docs/verifications/2026-10-13/p08_01_full_slice.md)에서 B1(경계 포함·최소 σ·매칭 없음 회귀 가드) 해소와 H1~H4 반영을 확인해 **합격**으로 확정했다. 관련 Python 57개·브라우저 저장 2개 회귀와 독립 변이 3종을 통과했다. [이전 재개 검증](../../../docs/verifications/2026-10-11/p08_01_resume.md)은 부분 슬라이스 기록으로 보존한다.

## 기준과 소유자 결정

- 사전 기준: `configs/anonymize_measure.yaml`, 커밋 `dd680af`. 이 파일은 결과 확인 후에도 변경하지 않았다.
- 기존 작업자의 블라인드 표시·원 확인 산출물을 이어받았다. 해당 육안 표시를 이번 작업에서 독립적으로 재검증한 것은 아니다.
- [최초 보고서](report_before_owner_decision.json): REAL 원 너비 대비 크기에 맞는 k는 0.6456이며, 허용 범위 [1.0, 1.6] 밖이라 크기 관문은 실패했다.
- 소유자 선택(2026-10-11, 첨부된 이전 대화의 답변): k=1.2를 사용하고 P08-03에 원 크기 단서를 추가 진단한다. 얼굴보다 작은 원으로 분포를 맞추지 않는다. 규격의 정본은 `configs/anonymize.yaml`이다.
- 사전 실패를 사후 통과로 바꾸지 않는다. [현재 보고서](report.json)의 `size_match`는 원래 기준의 실패, `selected_size`는 선택한 k의 분포 검사다. 둘은 경계 재측정에 쓸 원의 크기 선택과 구별한다.

## 측정 결과

| 항목 | 결과 | 해석 |
| --- | --- | --- |
| REAL 확인 원 | 150개 | 이전 작업자의 후보 육안 확인 |
| 장축/너비 1사분위·중앙값·3사분위 | 0.07267 / 0.08778 / 0.10421 | 측정 표본의 분포 |
| 타원 비율 | 0/150 | 측정 표본에서 원형 선택 |
| REAL 경계 전이 폭 중앙값 | 2px | 150개에서 측정 |
| REAL 원 근처 YuNet 검출 | 0/150 | 사전 중심 거리 규칙; 관문 아님 |
| 후보 없는 이미지의 누락 확인 | 0/50 | 200px 썸네일 확인이므로 불확실 사례가 남음([기록](real_disc_missed_sample.json)) |
| 학습 GEN YuNet 검출 이미지 | 1,084장 | P06-02c와 같은 설정; 대표 얼굴 하나로 크기 측정 |
| k=1.2 원 지름/너비 사분위 | 0.12471 / 0.16316 / 0.21141 | REAL보다 큼; 사전 ±15% 분포 기준 실패 |
| k=1.2 경계 σ·전이 폭 중앙값 | σ=0.5 / 1px | 100장 표본, REAL 2px의 허용 ±1px 경계에서 통과 |
| 학습 GEN 재현율 | 87/98 = 88.78%, Wilson 95% 81.01~93.62% | 150장 중 소유자 확인 40장 반영, 재현율 관문 통과 |
| sd35 GEN 재현율 | 64/74 = 86.49%, Wilson 95% 76.88~92.49% | 100장 중 소유자 확인 30장 반영, 보고 전용(관문 없음) |

경계 σ와 실제 재계산 결과는 `report.json`이 소유한다. k=1.2 재측정의 σ=0.5는 `configs/anonymize.yaml`과 같다. 경계 관문 통과가 원 크기 단서 해소를 의미하지는 않는다.

## 사람 영역 대비 보조 크기 (보고 전용)

[보조 보고서](person_size_report.json)는 사전 규격의 보조 척도를 계산한다. 기존 이미지 너비 대비 관문과 별개이며 `report.json`의 크기 관문 실패를 바꾸지 않는다.

| 측정군 | 표본 | 분모 | 지름/높이 1사분위·중앙값·3사분위 |
| --- | --- | --- | --- |
| REAL | 확인 원 150개 | K-Fashion 의복 부위 rect 합집합 높이 | 0.12406 / 0.14229 / 0.18582 |
| GEN | 50장 | 수동 표시한 보이는 사람 영역 높이 | 0.12481 / 0.13501 / 0.20806 |

- REAL은 원래 확인한 원을 그대로 사용한다. 부위 4종의 유효 rect에서 최소 Y와 최대 Y+높이의 차이를 잰다. 좌표를 이미지 경계로 잘라내거나 의복 밖 신체 영역을 추정하지 않는다. [부위 rect 발췌](person_rects_real.json)는 외부 라벨의 파생 자료이며, 원 ZIP의 SHA256은 보고서에 기록했다. [REAL별 측정값](person_size_real.csv)도 보관한다.
- GEN은 학습 재현율 표본 중 소유자 판정 반영 후 얼굴이 보이고 YuNet이 검출한 87장에서, 기존 REAL 측정 seed `20261011`의 정렬·shuffle 순서로 앞 50장을 고정했다([표본](person_sample_gen.csv)). GEN 전체 검출 1,084장의 대표 표본이라고 해석하지 않는다.
- [GEN 수동 표시](person_height_gen.csv)가 사람 높이의 정본이다. 에이전트가 원본을 320×480 표시 크기로 변환한 시트에서 머리카락·모자부터 최하단 신체·의복·신발까지의 세로 범위를 읽고, 이미지 높이 대비 `top_fraction,bottom_fraction`으로 기록했다. 배경 인물·소품은 제외했다. 원본 높이에 비율을 곱해 픽셀 높이를 복원한다. 시트 눈금은 40px, 육안 경계의 오차는 표시 크기에서 수 px 수준이며 정밀한 분할 마스크가 아니다.
- 프레임 밖으로 잘린 인물은 보이는 높이만 잰다. 29/50장의 표시가 위 또는 아래 경계에 닿았다. GEN 원 지름은 기존 대표 얼굴 검출의 긴 변 × 선택 k=1.2다([GEN별 측정값](person_size_gen.csv)). 이 대표 얼굴 측정은 P08-02의 모든 얼굴 익명화 구현을 대신하지 않는다.
- 두 분모의 의미·표본 구성·수동 표시 정밀도가 다르므로 비슷한 중앙값만으로 원 크기 단서 해소를 판정하지 않는다. P08-03의 사전 고정 진단은 여전히 필요하다.

## 소유자 확인

**학습 GEN 40장 소유자 확인을 반영했다(2026-10-13).** 눈·코·입 중 둘 이상이 보이면 1, 하나만 보이면 0이라는 사전 기준을 사용했다. [최종 표시](recall_labels_owner.csv)는 40장 중 보임 31장·안 보임 9장이며, 에이전트 표시와 다른 3장을 교체했다. 전체 150장 기준 양성 98장·검출 87장으로 재현율 관문을 통과했다. 아래는 검토·재현 절차다.

### sd35 소유자 확인

**sd35 30장 소유자 확인을 반영했다(2026-10-13).** [최종 표시](recall_labels_owner_sd35.csv)는 보임 26장·안 보임 4장으로, 기존 표시와 다른 3장을 교체했다. 전체 100장 기준 양성 74장·검출 64장, `owner_final`이며 `passed=null`이다. 아래는 검토·재현 절차다.

보고용 sd35 표본 100장 중 에이전트 표시와 YuNet이 다른 **13장** + 나머지 87장 중 사전 seed로 뽑은 **17장**, 총 **30장**이다. seed와 무작위 20% 기준은 `configs/anonymize_measure.yaml`을 그대로 사용했다. [확인 목록](recall_owner_check_sd35.csv)은 파생 자료이며 검토 페이지에는 선정 사유·검출 결과·에이전트 표시를 넣지 않는다.

1. `reports/errors/review/p08_sd35/index.html`을 브라우저에서 연다. Windows 경로는 `F:\devel\Tracepecter\reports\errors\review\p08_sd35\index.html`이다.
2. 눈·코·입 중 둘 이상이 보이면 보임(1), 아니면 안 보임(0)으로 표시한다. 측면·부분 포함, 뒷모습·프레임 밖 제외. 사진을 누르면 확대된다. 페이지를 닫거나 새로고침하면 선택이 초기화된다.
3. 30장 전부 표시한 뒤 **CSV 저장**을 누른다. 내려받은 `recall_labels_owner_sd35.csv`를 `experiments/p08_anonymized/measure/recall_labels_owner_sd35.csv`에 둔다. CSV 열은 기존과 같은 `image_id,owner_face_visible`이다. 빈 [양식](recall_labels_owner_template_sd35.csv)을 최종 표시로 사용하지 않는다.
4. 아래 `measure` 명령으로 재계산한다. 일부 확인은 `owner_partial`, 30장 전부 확인하면 `owner_final`로 기록한다. sd35에는 학습 재현율 관문을 적용하지 않으며 `passed=null`을 유지한다. 중복 ID·다른 pool의 ID·0/1 이외 값은 거부한다.

학습 GEN과 sd35의 소유자 표시는 각각 별도 파일이 정본이다. 기존 `recall_labels_owner.csv`는 학습 GEN 결과로 보존한다. 검토 목록·빈 양식·페이지는 표시 및 검출 CSV로부터 생성하고, `report.json`은 두 소유자 표시를 반영한 파생 보고서다.

## 재현 명령

```bash
# CPU 전용: 다른 작업의 GPU를 점유하지 않는다.
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p08_measure measure --anonymization-config configs/anonymize.yaml

# 보조 크기 재계산: 고정 표본·수동 표시 CSV를 사용한다.
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p08_person_size --label-zip '/data/K-Fashion 이미지/Training/라벨링데이터.zip'

# sd35 블라인드 검토 페이지 재생성(이미지 포함 생성물은 review/ 비추적 경로에 둔다).
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p08_measure owner --pool test_gen_sd35 --sheets reports/errors/review/p08_sd35

docker compose run --rm -T dev python -m pytest \
  tests/test_p08_person_size.py tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q

# 호스트 Node.js에서 브라우저 저장 로직 회귀 확인
node tests/test_p08_owner_review.cjs
```

이미지 경로는 이 머신의 Compose 기본값이다. 다른 머신에서는 `IMAGE_DIR`에 맞춰 읽기 전용 mount를 변경한다. 보고서는 측정 config·metadata·YuNet sha256과 선택 규격 내용을 기록한다. `provenance.owner_labels_sha256`은 `train_gen`·`test_gen_sd35`별 소유자 CSV 원본 바이트 해시이며, 표시 파일이 없으면 null이다. 측정 CSV는 LF로 저장한다. 후보·표시 CSV는 원 측정과 재현율의 원자료이며, 보고서는 이들로부터 파생된다.

## 후속 작업과 한계

- 학습 GEN은 소유자 확인 후 양성 98장으로 최소 80장을 충족해 추가 표본이 필요하지 않다.
- 라운드 2 잔여 R1은 입력 CSV를 LF로 통일하고 보조 보고서의 입력 해시를 갱신해 보강했다. `.gitattributes`는 P08 측정 CSV의 LF와 기존 실험 해시에 연결된 `data/metadata.csv`의 CRLF를 체크아웃 시 보장한다. 기존 측정 수치·소유자 표시·사전 규격은 그대로다.
- H3·H4: 보조 GEN 표본 선정 방식은 사후 코드·기록에 고정한 것이며 사전 config 등록으로 소급하지 않는다. 사람 높이 표시는 에이전트의 육안 표시이고 소유자 재확인은 없었다. P08-03은 이 보조 지표로 크기 단서 해소를 결론내리지 않으며, 진단 표본·판정 규칙을 재학습 결과 전에 별도로 고정한다.
- P08-02는 모든 얼굴 검출을 처리해야 한다. 이 측정 스크립트의 P06 대표 얼굴 검출을 그대로 재사용해 여러 얼굴 익명화를 구현하지 않는다.
- P08-03 크기 진단의 표본·확대 규칙·구간 판정은 학습 결과 전에 고정한다. 원이 커졌을 때 REAL score가 바뀌는지 확인하며, 기존 익명화 원 밑의 얼굴은 복원할 수 없다.

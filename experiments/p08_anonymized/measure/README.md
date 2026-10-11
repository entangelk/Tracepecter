# P08-01 — 원 규격·YuNet 재현율 측정

**상태: 진행 중.** 소유자 표시 확인·사람 영역 대비 보조 크기 측정·독립검증이 남았다. 모델 score와 재학습 결과는 사용하지 않았다.

이번 재개 변경의 [독립검증](../../../docs/verifications/2026-10-11/p08_01_resume.md)은 합격했다(47개 회귀 테스트, 7종 변이, CPU 재측정 산출물 byte 동일). 이 판정은 P08-01 전체 완료나 소유자 표시의 최종 판정을 뜻하지 않는다.

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
| 학습 GEN 재현율 | 86/97 = 88.66%, Wilson 95% 80.83~93.55% | 150장 1차 표시 기준 잠정값 |
| sd35 GEN 재현율 | 61/71 = 85.92%, Wilson 95% 75.98~92.17% | 100장 보고 전용; 양성 80장 관문을 적용하지 않음 |

경계 σ와 실제 재계산 결과는 `report.json`이 소유한다. k=1.2 재측정의 σ=0.5는 `configs/anonymize.yaml`과 같다. 경계 관문 통과가 원 크기 단서 해소를 의미하지는 않는다.

## 소유자 확인

**다음 세션의 첫 작업은 소유자가 아래 40장을 직접 확인하는 것이다**(2026-10-11 소유자 지시). 확인 후 재현율 재계산과 후속 작업을 진행한다.

학습 GEN에서 에이전트 표시와 YuNet이 다른 12장 + 나머지의 무작위 28장, 총 40장이다. 표시는 눈·코·입 중 둘 이상이 보이면 1, 아니면 0이다(측면·부분 포함, 뒷모습·프레임 밖 제외).

1. 저장소 루트의 `reports/errors/review/p08/index.html`을 브라우저에서 연다. Windows 경로는 `F:\devel\Tracepecter\reports\errors\review\p08\index.html`이다.
2. 검출 결과·에이전트 표시·선정 사유를 보지 않고 40장을 표시한다. 사진을 누르면 확대된다. 모든 표시를 끝낸 뒤 **CSV 저장**을 누른다. 페이지를 닫거나 새로고침하면 선택이 초기화된다.
3. 내려받은 파일을 `experiments/p08_anonymized/measure/recall_labels_owner.csv`에 둔다. CSV 열은 `image_id,owner_face_visible`이다. 빈 [양식](recall_labels_owner_template.csv)도 제공한다. 빈 양식을 최종 파일로 사용하지 않는다.
4. 아래 명령으로 재계산한다. 선정된 40장의 표시가 모두 있어야 `owner_final`과 최종 관문 판정을 낸다. 일부만 있으면 `passed=null`, `owner_partial`로 남는다. 중복 ID·표본 밖 ID·0/1 이외 값은 거부한다.

## 재현 명령

```bash
# CPU 전용: 다른 작업의 GPU를 점유하지 않는다.
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p08_measure measure --anonymization-config configs/anonymize.yaml

# 블라인드 검토 페이지 재생성(이미지 포함 생성물은 기존 review/ 비추적 경로에 둔다).
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p08_measure owner --sheets reports/errors/review/p08

docker compose run --rm -T dev python -m pytest \
  tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q
```

이미지 경로는 이 머신의 Compose 기본값이다. 다른 머신에서는 `IMAGE_DIR`에 맞춰 읽기 전용 mount를 변경한다. 보고서는 측정 config·metadata·YuNet sha256과 선택 규격 내용을 기록한다. 후보·표시 CSV는 원 측정과 재현율의 원자료이며, 보고서는 이들로부터 파생된다.

## 남은 작업과 한계

- 소유자 최종 확인과 재현율 재계산. 양성이 80장 미만이면 사전 seed 순서로 50장씩 추가 표시한다(최대 400장).
- sd35 보고용 100장도 계획의 "같은 방식"에 따라 소유자 확인이 필요하다. 현재 페이지는 학습 GEN 40장만 다루므로, 그 확인 후 sd35 불일치·무작위 확인 자료를 별도로 준비한다. sd35에는 학습 재현율 관문을 적용하지 않는다.
- 사람 영역 대비 보조 크기: REAL의 K-Fashion 부위 rect 합집합 높이, GEN 측정 표본 50장의 수동 사람 영역 높이. **아직 측정하지 않았다.** 관문 없이 보고할 보조 지표다.
- P08-01 독립검증. 이번 테스트·재측정은 구현자 자가 확인이며 독립검증 합격 기록을 대체하지 않는다.
- P08-02는 모든 얼굴 검출을 처리해야 한다. 이 측정 스크립트의 P06 대표 얼굴 검출을 그대로 재사용해 여러 얼굴 익명화를 구현하지 않는다.
- P08-03 크기 진단의 표본·확대 규칙·구간 판정은 학습 결과 전에 고정한다. 원이 커졌을 때 REAL score가 바뀌는지 확인하며, 기존 익명화 원 밑의 얼굴은 복원할 수 없다.

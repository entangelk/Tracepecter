# P08-01 — 원 규격·YuNet 재현율 측정

**상태: 진행 중.** 학습 GEN·sd35 소유자 확인은 반영했으며, 사람 영역 대비 보조 크기 측정·전체 슬라이스 독립검증이 남았다. 모델 score와 재학습 결과는 사용하지 않았다.

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
| 학습 GEN 재현율 | 87/98 = 88.78%, Wilson 95% 81.01~93.62% | 150장 중 소유자 확인 40장 반영, 재현율 관문 통과 |
| sd35 GEN 재현율 | 64/74 = 86.49%, Wilson 95% 76.88~92.49% | 100장 중 소유자 확인 30장 반영, 보고 전용(관문 없음) |

경계 σ와 실제 재계산 결과는 `report.json`이 소유한다. k=1.2 재측정의 σ=0.5는 `configs/anonymize.yaml`과 같다. 경계 관문 통과가 원 크기 단서 해소를 의미하지는 않는다.

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

# sd35 블라인드 검토 페이지 재생성(이미지 포함 생성물은 review/ 비추적 경로에 둔다).
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m scripts.p08_measure owner --pool test_gen_sd35 --sheets reports/errors/review/p08_sd35

docker compose run --rm -T dev python -m pytest \
  tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q

# 호스트 Node.js에서 브라우저 저장 로직 회귀 확인
node tests/test_p08_owner_review.cjs
```

이미지 경로는 이 머신의 Compose 기본값이다. 다른 머신에서는 `IMAGE_DIR`에 맞춰 읽기 전용 mount를 변경한다. 보고서는 측정 config·metadata·YuNet sha256과 선택 규격 내용을 기록한다. 후보·표시 CSV는 원 측정과 재현율의 원자료이며, 보고서는 이들로부터 파생된다.

## 남은 작업과 한계

- 학습 GEN은 소유자 확인 후 양성 98장으로 최소 80장을 충족해 추가 표본이 필요하지 않다.
- 사람 영역 대비 보조 크기: REAL의 K-Fashion 부위 rect 합집합 높이, GEN 측정 표본 50장의 수동 사람 영역 높이. **아직 측정하지 않았다.** 관문 없이 보고할 보조 지표다.
- P08-01 독립검증. 이번 테스트·재측정은 구현자 자가 확인이며 독립검증 합격 기록을 대체하지 않는다.
- P08-02는 모든 얼굴 검출을 처리해야 한다. 이 측정 스크립트의 P06 대표 얼굴 검출을 그대로 재사용해 여러 얼굴 익명화를 구현하지 않는다.
- P08-03 크기 진단의 표본·확대 규칙·구간 판정은 학습 결과 전에 고정한다. 원이 커졌을 때 REAL score가 바뀌는지 확인하며, 기존 익명화 원 밑의 얼굴은 복원할 수 없다.

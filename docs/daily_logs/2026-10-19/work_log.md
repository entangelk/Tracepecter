# 2026-10-19 작업 기록

## 목표

- P08-05: 익명화 checkpoint를 P05와 같은 절차로 재calibration하고 artifact를 `experiments/p08_anonymized/calibration/`에 분리한다.

## 수행 내용

- `src.calibrate`는 P08-02에서 이미 checkpoint 결합 규격·`face_cache`를 지원하므로 코드는 바꾸지 않았다(기존 연결 테스트 `tests/test_anonymize.py`).
- `tests/test_p08_calibration_config.py`를 먼저 작성해 config 부재로 실패하는 것을 확인했다. 그다음 `configs/calibration_anonymized.yaml`을 추가했다. P05 설정과 비교해 checkpoint·`face_cache`·출력 경로만 다를 수 있다. 변이 4종(iterations·P05 출력 재사용·캐시 삭제·baseline checkpoint)에서 모두 실패하고 복원 후 통과했다. 변이는 scratchpad 사본으로 byte 복원했다.
- config·테스트를 커밋(`3106aee`)한 뒤 GPU 점유 25%·986MiB를 확인하고 detached 컨테이너로 실행했다. exit 0, 2분 21초. 같은 commit으로 재실행한 결과 산출물 세 파일이 byte 동일했다.
- 결과: T 0.968747, threshold 0.383150. checkpoint sha256이 P08-04 best와 일치했고, metadata hash가 불변이며, prediction ID가 val 820장과 정확히 일치했다.
- validation NLL은 개선됐지만 Brier·ECE는 근소하게 악화됐다. Test A/B 지표는 개선됐다. Test B threshold 정확도는 0.987595에서 0.983779로 떨어졌다(sd35 FP 12→16). 사후 조정하지 않았다.
- score CLI의 직접 YuNet 경로 결과가 캐시 기반 logit과 logit 차 약 4e-6 이내로 일치했다(REAL 92.676153 두 번 동일, 캐시 경로와 score 차 2.5e-5; GEN 0.000238).
- 전체 CPU suite는 182 passed, 1 skipped.

## 독립검증

- 서브에이전트 독립검증 합격(`a937278`, [기록](../../verifications/2026-10-19/p08_05_anonymized_calibration.md)). 차단 0건. GPU 재실행 byte 동일, CPU 재계산 T/threshold 비트 일치, 다른 축의 변이 6종 재실패를 확인했다.
- 비차단 H1: score CLI와 캐시 경로가 '일치'한다는 표현을 실제 오차(logit 약 4e-6)로 정정했다.

- 같은 검증자가 H1 보강(`0b1c6d4`)을 추적검증해 라운드 2 합격을 확정했다(`3e9cd63`). 남은 지적은 없다. P08-05를 Complete로 종결한다.

## P08-06 선행: GEN 얼굴 상태 주석

- `scripts/p08_face_review.py`(sheets/owner/merge)와 블라인드 소유자 페이지 `scripts/p08_face_review.html`을 추가했다. 선택 규칙(flagged 전부 + 나머지 seed shuffle `ceil(0.2n)`)·병합 검증 회귀 테스트와 node 저장 테스트를 커밋했고, 변이 3종(ceil→round, 남은 얼굴 flag 제거, 소유자 우선 제거)에서 재실패를 확인했다. 첫 변이 시도에서 미추적 파일에 `git checkout` 복원을 시도한 실수가 있었으나 즉시 수동 복원했고, 커밋 후 변이를 다시 수행했다.
- 952장 에이전트 주석(모델 점수 미사용): anonymized 607·no_visible_face 207·missed_visible_face 138. 세 상태 모두 최소 20장 충족. 확인 목록 301장(flagged 138 + random 163). 커밋 `8592952`.
- 후반부는 토큰 절감을 위해 2×2 contact sheet로 주석했다. 코·입 아랫부분만 보이는 하관은 '둘 이상'으로 보고 남은 얼굴로 표시해 소유자 확인 대상에 넣었다.

## 다음 작업

- 소유자: 확인 페이지 301장 표시 후 `face_review_owner.csv` 전달(절차는 HANDOFF).
- 작업자: merge → `face_review.csv` 커밋 → 진단 실행기 구현·실행·채택 판정 → 독립검증.

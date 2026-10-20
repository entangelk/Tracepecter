# 2026-10-20 작업 기록

## 목표

- P08-06 소유자 확인 CSV를 수령하고 예측 전에 최종 얼굴 상태를 고정한다.

## 완료한 작업

- 다운로드 `face_review_owner.csv` 301행의 열·ID·정수 범위를 기존 merge 도구로 검증했다.
- 소유자는 눈·코·입의 개수를 셌다고 확인했다. 원본 바이트는 진단 디렉터리의 `face_review_owner_features.csv`로 보존했다(sha256 `c1d2478b81c16a8dbb7831bb46d830b0618a1f37329e43c67ca7cccfdfac3cab`).
- 같은 기준(눈·코·입 중 둘 이상)으로 요소 0~1 → 얼굴 0, 요소 2~4 → 얼굴 1로 변환했다. 요소 2개 20장을 비교 이미지로 확인했고, 기존 에이전트 다중 얼굴 주석 2건(gen_001311·gen_002236)은 원본 크기로 확인했다. 배경 인물의 불명확한 이목구비를 얼굴로 세는 기존 값보다 소유자 표시를 우선했다. 이 변환은 이번 대상 인물의 요소 표시 해석이며 여러 사람의 합산 요소를 변환하는 일반 규칙이 아니다.
- `docker compose run --rm -T dev python -m scripts.p08_face_review merge`: 952행·소유자 301행·에이전트 대비 45행 변경. 최종 상태는 익명화 607 / 얼굴 없음 237 / 남은 얼굴 있음 108.
- `face_review_lock.json`에 원본·변환본·최종본·선행 입력의 SHA-256과 확인한 ID를 고정했다. HANDOFF와 페이즈 상태를 수령 상태로 갱신했다.

- 검증: `docker compose run --rm -T dev python -m pytest tests/test_p08_face_review.py -q` → 3 passed. 별도 데이터 검사로 원본 바이트 동일성, 변환식, 301개 확인 ID, 952개 최종 ID, confirmed·정수 범위, 소유자 우선 병합, SHA-256·LF를 확인했다. `git diff --check` 통과. 진단 모델 예측은 아직 실행하지 않았다.

- P08-06 실행기를 구현했다. 사전등록 config/입력/manifest, 최종 주석·HEAD, calibration/checkpoint/snapshot/YuNet/cache 이미지 hash를 선행 검증한다. 2×2 평가와 REAL shape/size·GEN gray/restore 조건만 별도 구성한다. 원본 bypass는 offline 진단에만 둔다.
- 판정 수식은 `src/diagnostic.py`에 두고, 이미지 개입은 기존 `src/anonymize.py`의 같은 rasterization/Gaussian 커널을 공유한다. 모델별 temperature·threshold는 양 입력에 고정하며 재fitting하지 않는다.
- 예측은 배치마다 fsync하는 조건별 LF CSV로 보존한다. 실행 identity가 다르면 재개를 거부하고, 중단된 마지막 CSV 행만 제거한다. 보고서는 logit에서 파생하며 코드·주석·모델 hash로 계보를 기록한다.
- 진단·개입·재개·해시·커밋 검증·고정 calibration의 양방향 가드를 추가했다. 최초 수치 테스트는 구현 전 `ModuleNotFoundError`로 실패한 뒤 구현 후 집중 38 passed를 확인했다. 전체 CPU `docker compose run --rm -T dev python -m pytest -q`는 206 passed / 1 skipped(실제 YuNet opt-in), 45.69초.

## 발견한 문제

- 최초 병합은 구조상 유효했으나 얼굴 수와 이목구비 수의 의미가 달랐다. candidate 진단 예측을 실행하기 전에 발견했고, 소유자 의미 확인 후 변환하여 잘못된 수를 최종 주석으로 고정하지 않았다.

## 결정

- 얼굴 수를 셌다는 첫 답변 후 구체적인 4/4 사례를 제시했으며, 소유자는 눈·코·입 각각을 센 것이라고 명확히 했다. 사전등록의 얼굴 기준·표본·판정 허용폭은 유지한다.

## 다음 작업

- 최종 얼굴 상태를 커밋한 뒤 P08-06 진단 실행기 구현·stub 검증·GPU 실행·채택 판정·독립검증.

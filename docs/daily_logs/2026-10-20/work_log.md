# 2026-10-20 작업 기록

## 목표

- P08-06 소유자 확인 CSV를 수령하고 예측 전에 최종 얼굴 상태를 고정한다.
- 사전등록 진단·채택 규칙을 구현·실행하고, 채택 결과와 독립검증을 반영한다.

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

- GPU 진단: 구현 `1102343`, 주석 고정 `0c4eb6e`. 2,369개 입력 이미지 hash 확인 후 8개 조건별 CSV에 총 9,651개 logit을 저장했다. candidate 익명화 Test A AUC 0.9998668324 / Test B 0.9996465774. 얼굴 상태 집중·real_shape·real_size·gen_gray·gen_restore 전부 통과했다.
- 개입 평균 절대 변화의 95% 상한은 순서대로 0.151751 / 1.946554 / 0.932232 / 1.853471점으로 5점 이하다. 맞음→틀림은 모두 0건, Wilson 상한은 REAL 2.5134% / GEN 2.3163%로 5% 이하다. 얼굴 상태별 FP는 익명화 10/607, 없음 5/237, 남음 5/108이며 세 차이 구간이 ±10%p 안이다. 차이 0 또는 모든 단서의 인과적 제거를 주장하지 않는다.
- 저장된 CSV의 고유 ID·cohort·SHA-256을 확인하고, 별도 NumPy PCG64 bootstrap·Wilson 수식으로 네 개입 구간을 재계산했다(일치). 상태별 FP를 재집계했고 P08-05 Test A/B AUC·accuracy가 동일했다. NLL 차이는 최대 4.3e-12다.
- 재개 실행은 기존 CSV를 사용하며 Python CLI exit 0(`cli_exit_code.txt`), `result.json` 최초 실행과 byte 동일을 확인했다. score CLI 실이미지 확인(`src.score --image /images/real/스포티/998959.jpg --calibration experiments/p08_anonymized/calibration/calibration.json --device cuda`)은 exit 0, score 92.676153346304·photographic_like였다.
- 사전 채택 규칙에 따라 `configs/primary.yaml`을 `configs/anonymized.yaml`과 같은 설정으로 전환했다. README·SoT의 현재 checkpoint/calibration 소유 경로를 갱신하고 P05 baseline artifact는 보존했다. 이전 학습 비교 테스트는 이동하는 primary 대신 원래 비교 정본인 `configs/baseline.yaml`을 사용하도록 바꿨다.
- 경계 자가 검토로 80장/79장·오답 구간 상한 동등 경계, 회색 조건의 두 얼굴, 기존 큰 원 축소 금지·clipping·기존 가림 보존을 추가했다. 새 primary 연결 테스트는 변경 전 실패를 확인한 뒤 설정 변경 후 통과했다. 집중 테스트는 25 passed / 1 skipped. primary 전환 후 최종 전체 CPU suite는 208 passed / 1 skipped, 51.02초. `git diff --check` 통과.

## 발견한 문제

- 첫 detached 실행의 `setsid`가 곧바로 종료되어 `--wait`로 재시작했다. 두 번째는 결과 저장까지 수행했으나 래퍼가 `setsid: wait: Success`·exit 1을 반환했다. Docker daemon 직접 관리 detached 컨테이너로 재개하여 CLI 자체 exit 0과 결과 재현성을 확인했다. 컨테이너 감독과 디스크 재개 상태로 터미널/전원 단절을 대비한다.

- 최초 병합은 구조상 유효했으나 얼굴 수와 이목구비 수의 의미가 달랐다. candidate 진단 예측을 실행하기 전에 발견했고, 소유자 의미 확인 후 변환하여 잘못된 수를 최종 주석으로 고정하지 않았다.

## 결정

- 소유자가 이번 구현도 서브에이전트 한 명의 독립검증까지 진행하도록 명시적으로 승인했다. 지적은 차단·비차단 모두 보강하고 추적검증한다.

- 얼굴 수를 셌다는 첫 답변 후 구체적인 4/4 사례를 제시했으며, 소유자는 눈·코·입 각각을 센 것이라고 명확히 했다. 사전등록의 얼굴 기준·표본·판정 허용폭은 유지한다.

## 다음 작업

- 결과·채택 설정을 커밋한 뒤 독립검증·지적 보강·추적검증. P08은 그 전까지 In Progress, P07은 대기한다.

# 2026-10-25 작업 기록

## 목표

- P09-04 소유자 얼굴 확인 180장을 수령하고, 단서 진단 예측 전에 최종 얼굴 주석을 고정한다.

## 완료한 작업

- 다운로드 `face_review_owner (1).csv` 180행이 확인 대기 ID 집합과 정확히 일치하고 중복이 없으며 0≤남은≤보임을 만족함을 확인했다.
- 값 분포(에이전트 1/0 → 소유자 4/0이 100장)가 얼굴 수가 아니라 눈·코·입 개수임을 보여 merge 전에 소유자에게 물었다. 소유자는 P08과 같은 요소 단위로 입력했다고 확인했다(페이지 선택지가 0~4의 5개).
- 원본 바이트를 `face_review_owner_new_features.csv`로 보존했다(sha256 `91a371dae0326107287f4f0260df65dca0bfc23be3160c0f6ca19e6101b86724`). P08과 같은 변환(요소 0~1 → 얼굴 0, 2~4 → 얼굴 1)으로 만든 얼굴 수를 `scripts.p09_face_review merge` 입력으로 사용했다. 임시 변환 파일은 merge가 `face_review_owner_new.csv`로 복사한 뒤 삭제했다.
- 예측 전 시각 확인 21장: 요소 2개 또는 에이전트와 불일치한 19장(에이전트 얼굴 없음 → 소유자 남은 얼굴 1인 12장 포함)은 측면·프레임 경계에서 잘린 얼굴로 코·입이 보여 얼굴 1개 기준과 맞았다. 에이전트 다중 얼굴 2장(gen_000006·gen_000064)은 배경 인물이 작고 불명확해 소유자의 주 인물 1개 표시를 우선했다.
- merge 결과: 952행·소유자 291행(재사용 111 + 신규 180)·에이전트 대비 14행 변경, 전부 confirmed. 보임 0 224 / 전부 가림 601 / 남은 얼굴 있음 127.
- `face_review_lock.json`에 입력 의미·변환 규칙·시각 확인 ID와 요소 원본 hash를 추가했고 모든 lock hash를 재대조했다.
- 검증: `docker compose run --rm -T dev python -m pytest tests/test_p09_face_review.py -q` → 9 passed. `git diff --check` 통과. 단서 진단 예측은 아직 실행하지 않았다.
- GPU 단계 전 CPU 전용 preflight(`CUDA_VISIBLE_DEVICES=` 지정, `scripts.p09_diagnostic.preflight`)를 실행했다. 사전등록·manifest·주석 lock hash, 주석 커밋 `beb2be2`, baseline/candidate 계보, 입력 이미지 2,327장 hash를 모두 통과했다(exit 0, 1분33초). 출력 디렉터리에 이전 예측 CSV는 없다. 소유자 GPU 작업(사용률 100%, 8.9GiB)이 끝날 때까지 예측은 보류한다.

## 발견한 문제

- 검토 페이지 본문은 얼굴 수 입력을 요구했지만 선택지가 0~4여서 소유자는 P08과 같은 요소 단위로 입력했다. merge의 형식 검증은 이 의미 차이를 잡지 못한다. 이후 소유자 검토 페이지는 입력 단위와 선택지를 일치시켜야 한다.

## 다음 작업

- 최종 주석 커밋 후 GPU 점유를 확인하고 `scripts.p09_diagnostic --config configs/p09_r1_diagnostic.yaml --device cuda`를 디스크 재개 가능 상태로 실행한다.

# P08-04 익명화 재학습

상태: 실행 준비. [P08-03 사전등록](../diagnostic/README.md)은 결과 전에 고정·독립검증 합격이다. [학습 config](../../../configs/anonymized.yaml)는 primary와 모델·seed·10 epoch·batch32·lr·증강·split이 같고 익명화 규격/좌표 캐시·별도 checkpoint 경로만 다르다.

Compose가 `checkpoints/`와 `HF_HOME=/app/checkpoints/hf_cache`를 같은 checkpoint bind mount에 연결한다. 이 머신의 2026-10-13 실제 연결은 `/mnt/h/tracepector/checkpoints`(H:)이며 새 artifact는 `anonymized/` 아래다. baseline은 덮어쓰지 않는다. 학습 로그 `training.log`는 작은 텍스트이고 Git 비추적이다.

실행은 setsid로 터미널과 분리하고 디스크 로그·epoch마다 best/last/experiment.json으로 보존한다. 전원 단절 후 완료 epoch는 `last.pt`를 같은 config로 재개하며 진행 중 epoch는 다시 수행한다. 재개에서도 config·익명화 snapshot·캐시 image hash를 검증한다.

```bash
# 최초 실행
GIT_COMMIT=$(git rev-parse HEAD) CHECKPOINT_DIR=/mnt/h/tracepector/checkpoints \
  docker compose --profile training run --rm -T train \
  python -u -m src.train --config configs/anonymized.yaml
# 전원 단절 후 같은 학습 commit/config로 재개: 위 명령에 --resume 추가
```

기존 `src.train --smoke`는 32px toy 원본에서 실제 YuNet이 비정상 상자를 내는 경우가 있어, smoke CLI의 합성 원본은 모델 설정 해상도로 생성하도록 보강했다. 직접 `build_smoke_dataset`을 호출하는 기존 기본 32px 동작은 유지한다. 실학습은 검증된 전체 얼굴 좌표 캐시를 사용한다.

학습 완료 후 검증 loss 최소의 best checkpoint·10 epoch history·규격 결합·입력/기존 artifact 무결성을 확인한다. 성능 비교 재평가는 P08-06의 고정 2×2에서 수행하고 baseline을 재학습하지 않는다. calibration은 P08-05, 최종 채택은 P08-06 범위다.

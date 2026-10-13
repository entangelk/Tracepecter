# P08-04 익명화 재학습

상태: **10 epoch 재학습·artifact 자가 확인, 독립검증 대기**. [P08-03 사전등록](../diagnostic/README.md)은 결과 전에 고정·독립검증 합격이다. [학습 config](../../../configs/anonymized.yaml)는 primary와 모델·seed·10 epoch·batch32·lr·증강·split이 같고 익명화 규격/좌표 캐시·별도 checkpoint 경로만 다르다.

Compose가 `checkpoints/`와 `HF_HOME=/app/checkpoints/hf_cache`를 같은 checkpoint bind mount에 연결한다. 이 머신의 2026-10-13 실제 연결은 `/mnt/h/tracepector/checkpoints`(H:)이며 새 artifact는 `anonymized/` 아래다. baseline은 덮어쓰지 않는다. 학습 로그 `training.log`는 작은 텍스트이고 Git 비추적이다.

실행은 Docker daemon이 관리하는 detached 컨테이너 내부의 `setsid --wait`로 터미널과 분리하고 디스크 로그·epoch마다 best/last/experiment.json으로 보존한다. 호스트의 도구 셸에서 분리한 supervisor는 도구 종료 시 정리돼 실제 실행은 daemon 관리 컨테이너로 전환했다. 전원 단절 후 완료 epoch는 `last.pt`를 같은 config로 재개하며 진행 중 epoch는 다시 수행한다. 재개에서도 config·익명화 snapshot·캐시 image hash를 검증한다.

```bash
# 최초 실행
GIT_COMMIT=$(git rev-parse HEAD) CHECKPOINT_DIR=/mnt/h/tracepector/checkpoints \
  docker compose --profile training run --rm -T train \
  python -u -m src.train --config configs/anonymized.yaml
# 전원 단절 후 같은 학습 commit/config로 재개: 위 명령에 --resume 추가
```

기존 `src.train --smoke`는 32px toy 원본에서 실제 YuNet이 비정상 상자를 내는 경우가 있어, smoke CLI의 합성 원본은 모델 설정 해상도로 생성하도록 보강했다. 직접 `build_smoke_dataset`을 호출하는 기존 기본 32px 동작은 유지한다. 실학습은 검증된 전체 얼굴 좌표 캐시를 사용한다.

검증 loss 최소의 best checkpoint·10 epoch history·규격 결합·입력/기존 artifact 무결성을 확인했다. 성능 비교 재평가는 P08-06의 고정 2×2에서 수행하고 baseline을 재학습하지 않는다. calibration은 P08-05, 최종 채택은 P08-06 범위다.

## 학습 결과·실행 확인

[결과 기록](result.json)은 실제 checkpoint·history에서 도출했다. train3,780/val820·10epoch 완료, best는 epoch10이고 validation loss **0.0215848964**, ROC-AUC **0.9997955945**, accuracy **0.9914634146**이다. 이는 val 결과이며 Test A/B 성능·단서 해소·채택 판정은 아직 없다.

| artifact | 이 머신의 실제 위치 | SHA256 |
| --- | --- | --- |
| best | `/mnt/h/tracepector/checkpoints/anonymized/best.pt` | `091ac45424099c41bf50bb0adf7932d4b0b1ace3ceba9b9a27e25af99732c54b` |
| last | `/mnt/h/tracepector/checkpoints/anonymized/last.pt` | `0cab54c38c08ee7574a46cec09894905d809892f4de695d1ef8d8c2ce5c63f98` |
| history/config | `/mnt/h/tracepector/checkpoints/anonymized/experiment.json` | `217644661c3f03409addf91583bab9485e48968319304a7d0ba2dc7995aebd40` |

학습 출처 commit은 `6ace79b968adba3515462938916ca08f0e3d57f7`, 익명화 snapshot hash는 `e171cec26c6f5e3ca26f5ffcdd2b00b6621e5e5980ba5fa909111950cf32075c`다. best/last/experiment config는 현재 학습 YAML의 결합 규격과 동일하다. last10epoch·history1~10·best loss 최소·best metric/history 대응·모든 best tensor 유한성을 확인했다. encoder tensor 전부가 baseline과 같고 head는 달라 frozen encoder/head 학습을 확인했다. baseline과 사전등록 입력 해시도 불변이다.

[실행 기록](execution.json)은 이 머신의 Docker mount·시작/종료·dependency 관측이다. 본 학습 wrapper의 `setsid --wait`는 `setsid: wait: Success`와 exit1을 남겨 Python 원 실행의 exit code를 포착하지 못했다. 로그는 10epoch 및 checkpoint saved까지 남았고 best/last/history는 완결됐다. 아래 완료 checkpoint 재개 검증은 추가 epoch 없이 **exit0**, artifact byte 불변으로 정상 CLI/재개 상태를 확인했다. wrapper 종료 코드1을 학습 exit0으로 바꿔 기록하지 않는다. 향후 이 머신의 긴 작업은 Docker daemon의 detached Python PID1·disk log/epoch checkpoint로 운영하고 이 `setsid --wait` wrapper를 재사용하지 않는다.

```bash
GIT_COMMIT=6ace79b968adba3515462938916ca08f0e3d57f7 \
CHECKPOINT_DIR=/mnt/h/tracepector/checkpoints \
  docker compose --profile training run --rm -T train \
  python -u -m src.train --config configs/anonymized.yaml --resume
```

Python CPU `torch.load(..., weights_only=True)`로 실제 best/last를 읽어 위 config·epoch·loss·history·tensor 검사를 수행했다. 바이너리는 Git 비추적이고 이 결과/실행 JSON·README만 추적한다. smoke 원본 해상도 회귀와 config 차이 회귀, 기존 학습/재개 관련 테스트31개가 통과했다. 독립검증은 별도 후속이며 모델 자체의 byte 결정성은 주장하지 않는다.

## 실제 YuNet opt-in 회귀

일반 CI는 모델 파일에 의존하지 않고 해당 셀을 skip한다. 실제 YuNet이 준비된 환경에서는 아래 명령으로 CPU smoke를 실행한다. opt-in 상태의 모델 부재·hash 불일치는 skip하지 않고 거부한다. 실제 검출 함수를 wrapping해 224px 원본의 train/val16회 호출을 확인하며 검출을 fake 반환으로 대체하지 않는다. CPU/stub encoder·1epoch·규격 결합·8개 validation·checkpoint 완료를 검증하고 임시 smoke 디렉터리를 지운다.

```bash
docker compose run --rm -T -e TRACEPECTER_REAL_YUNET_SMOKE=1 dev \
  python -m pytest tests/test_p08_training_config.py -q
```

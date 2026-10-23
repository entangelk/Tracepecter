# P09-03 익명화 SigLIP 재학습

새 metadata에서 기존 frozen SigLIP encoder의 head를 새로 초기화해10epoch 학습한다. [P09 계획](../../../../docs/plan/phase_9_leakage_repair.md), [사전등록](../diagnostic/README.md), [학습 설정](../../../../configs/p09_r1_train.yaml)이 범위를 소유한다. 모델 revision·seed42·batch32·lr0.0001·증강·익명화 규격은 P08과 같다. metadata와 checkpoint 출력 경로만 바꿨다.

`sample_ids.csv`는 새 metadata에서 기존 `MetadataDataset`과 동일한 train/val 조건으로 선택한3,780/820개 ID·경로·label의 근거다. metadata raw-byte hash와 학습 소스를 `input_lock.json`으로 결합한다. 기존 loader는 명시적 `image_root: /images`를 사용한다. 실제 학습의 experiment.json에서 sample 수와 dataset hash를 다시 확인한다.

## 실행과 복구

먼저 `python -m experiments.p09_leakage_repair.r1.training.prepare`로 입력·표본을 고정하고 준비/사전등록 commit을 만든다. GPU 여유와 mount·용량·쓰기 경로를 확인한다. 신규 경로 `checkpoints/leakage_repair/r1/`에는 기존 학습 checkpoint가 없어야 하며 최초 실행은 `--resume` 없이 수행한다. `src.train`은 지정한 pretrained encoder를 생성하고 `RealismScorer` head를 새로 초기화한다. 기존 best의 head를 읽는 경로는 최초 실행에 없다.

```bash
GIT_COMMIT=<사전등록_커밋> docker compose --profile training run -d \
  --name tracepecter-p09-r1 train bash -c \
  'exec python -u -m src.train --config configs/p09_r1_train.yaml > experiments/p09_leakage_repair/r1/training/training.log 2>&1'
```

Docker daemon이 관리하는 detached 컨테이너에서 exec된 Python이 PID1로 실행돼 도구 셸 종료와 분리된다. P08에서 종료 코드가 잘못 수집된 `setsid --wait` wrapper를 재사용하지 않는다. 디스크 로그와 epoch마다 atomic best/last/experiment 저장으로 전원 단절에 대비한다. 미완료 epoch는 재실행한다. 같은 source/config/input hash에서만 `--resume`으로 last.pt를 재개하며 기존 완료 checkpoint를 무심코 새 실행으로 덮어쓰지 않는다. 소유자의 다른 GPU 작업이 크게 점유하면 큐에 넣지 않고 중단한다.

최종 best 선택은 validation loss 최솟값만 사용한다. 학습 뒤10epoch history·best/last/config/metadata·익명화 결합·tensor 유한성·encoder 불변·head 변화·기존 artifact 불변을 확인하고 결과를 기록한다. 새 Test A/B 평가·재보정·채택은 P09-04이며 현 primary는 유지한다.

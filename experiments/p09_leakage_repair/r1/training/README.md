# P09-03 익명화 SigLIP 재학습

새 metadata에서 기존 frozen SigLIP encoder의 head를 새로 초기화해10epoch 학습한다. [P09 계획](../../../../docs/plan/phase_9_leakage_repair.md), [사전등록](../diagnostic/README.md), [학습 설정](../../../../configs/p09_r1_train.yaml)이 범위를 소유한다. 모델 revision·seed42·batch32·lr0.0001·증강·익명화 규격은 P08과 같다. metadata와 checkpoint 출력 경로만 바꿨다.

`sample_ids.csv`는 새 metadata에서 기존 `MetadataDataset`과 동일한 train/val 조건으로 선택한3,780/820개 ID·경로·label의 근거다. metadata raw-byte hash와 학습 소스를 `input_lock.json`으로 결합한다. 기존 loader는 명시적 `image_root: /images`를 사용한다. 실제 학습의 experiment.json에서 sample 수와 dataset hash를 다시 확인한다.

## 실행과 복구

먼저 `python -m experiments.p09_leakage_repair.r1.training.prepare`로 입력·표본을 고정하고 준비/사전등록 commit을 만든다. GPU 여유와 mount·용량·쓰기 경로를 확인한다. 신규 경로 `checkpoints/leakage_repair/r1/`에는 기존 학습 checkpoint가 없어야 하며 최초 실행은 `--resume` 없이 수행한다. `src.train`은 지정한 pretrained encoder를 생성하고 `RealismScorer` head를 새로 초기화한다. 기존 best의 head를 읽는 경로는 최초 실행에 없다.

```bash
GIT_COMMIT=cd9bafc7e2161d634a6dc39d0ff17c368bd9ef5b docker compose --profile training run -d \
  --name tracepecter-p09-r1 train bash -c \
  'exec python -u -m src.train --config configs/p09_r1_train.yaml > experiments/p09_leakage_repair/r1/training/training.log 2>&1'
```

Docker daemon이 관리하는 detached 컨테이너에서 exec된 Python이 PID1로 실행돼 도구 셸 종료와 분리된다. P08에서 종료 코드가 잘못 수집된 `setsid --wait` wrapper를 재사용하지 않는다. 디스크 로그와 epoch마다 atomic best/last/experiment 저장으로 전원 단절에 대비한다. 미완료 epoch는 재실행한다. 같은 source/config/input hash에서만 `--resume`으로 last.pt를 재개하며 기존 완료 checkpoint를 무심코 새 실행으로 덮어쓰지 않는다. 소유자의 다른 GPU 작업이 크게 점유하면 큐에 넣지 않고 중단한다.

최종 best 선택은 validation loss 최솟값만 사용한다. 학습 뒤10epoch history·best/last/config/metadata·익명화 결합·tensor 유한성·encoder 불변·head 변화·기존 artifact 불변을 확인하고 결과를 기록한다. 새 Test A/B 평가·재보정·채택은 P09-04이며 현 primary는 유지한다.

## 완료 결과와 검증

**상태: Complete (2026-10-23), 자가 검증이며 독립검증은 별도다.** 학습 출처는 사전등록 commit `cd9bafc7e2161d634a6dc39d0ff17c368bd9ef5b`다. [execution.json](execution.json)의 실제 컨테이너 시작/종료는 이 머신에서 10:50:57~11:06:51 KST이며953.67초, Python 종료 코드는0이다. 학습 중 다른 GPU 연산 프로세스는 없었다.

train3,780 / val820으로10epoch를 완료했고 validation loss 최솟값으로 **epoch10**을 선택했다. 최종 [result.json](result.json)은 실제 best/last/experiment와 원본 입력에서 도출했다.

| validation 지표 | 값 |
| --- | --- |
| loss | 0.0111455508 |
| ROC-AUC | 0.9999158330 |
| PR-AUC | 0.9999311564 |
| accuracy | 0.9963414634 |
| precision / recall | 0.9955849890 / 0.9977876106 |
| F1 | 0.9966850829 |

이 값은 새 validation 결과다. 이전 P08과 평가 ID가 다르므로 대응표본 성능 개선으로 해석하지 않는다. Test A/B·calibration·단서 해소·채택 판정은 아직 수행하지 않았다. 미검토946,311쌍·GEN 계보 공유·개발 표본 노출 한계도 유지한다.

| artifact | SHA-256 |
| --- | --- |
| `checkpoints/leakage_repair/r1/best.pt` | `8fcd4859cd13fe2c2636565f4cc40bcfeff6447923dbc04d2c99450fefca0731` |
| `checkpoints/leakage_repair/r1/last.pt` | `bc814499012d025b3f7883d58951100ddba96003c9362acdea542fba9da728ed` |
| `checkpoints/leakage_repair/r1/experiment.json` | `71a449734c35458ebbc3c56f9afbb34ef115e6ad0705f171d1ef99337b249ddd` |

Compose의 checkpoint mount 아래 `leakage_repair/r1/`에 저장된다. 이 머신의 실제 root는 `/mnt/h/tracepector/checkpoints`다. 바이너리는 Git 비추적이며 hash·history·config/ID 근거만 추적한다. 디스크 로그는 `training.log`에 남는다.

[검증 도구](verify.py)를 CPU에서 실행해 다음을 확인했다.

- best/last/experiment의 config가 YAML+익명화 snapshot과 같고 metadata hash·sample 수가 일치한다. 기존 loader의 실제 split 선택 ID·경로·label을 sample manifest와 대조했다.
- last10epoch, history1~10, best loss 최소와 metrics/history가 일치한다. optimizer·Torch/Python/CUDA RNG 재개 상태가 존재하며 모든 best/last model tensor가 유한하다.
- best와 last의 encoder tensor 전부가 보존한 P08 encoder와 같다. best head는 P08과 다르다. 최초 실행은 빈 새 checkpoint 경로와 `--resume` 없는 명령으로 수행했으며 기존 head 로딩 경로는 실행하지 않았다.
- 사전등록/주석 계보/input lock은 학습 전 commit과 바이트 일치한다. `preserved_artifacts.json`의 기존 best/last6개·metadata·primary·보정2개·주석 lock, 총11개 hash가 불변이다.
- 준비 단계 집중37 passed / 1 skipped(3.56초), 전체 CPU267 passed / 1 skipped(51.20초). skip은 기존 YuNet opt-in smoke이며 기존 Pillow 경고12개 외 실패는 없다. 학습 후에는 새 artifact를 직접 검증했고 문서 변경만으로 전체 suite를 재실행하지 않았다.

```bash
docker compose run --rm -T dev \
  python -m experiments.p09_leakage_repair.r1.training.verify
```

다음은 P09-04의 새 val-only 재보정·새 cohort 최종 주석·고정 진단/채택 검토다. 기존 primary는 유지한다.

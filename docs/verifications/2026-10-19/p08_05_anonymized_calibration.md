# P08-05 익명화 checkpoint 재calibration 독립검증

**합격** — 차단 지적 없음. 비차단 1건(H1, README 표현 정밀도)을 남긴다. P08-05 필수 계약(P05 절차 동일, validation-only fitting, 별도 출력, P05 artifact 불변, checkpoint 결합 규격만 사용)을 충족한다.

## 대상·정본·범위

- 날짜: 2026-10-19. 요청자: 소유자의 독립검증 요청(root 경유). 검증자: 구현에 참여하지 않은 Claude 단일 subagent.
- 대상: `main` HEAD `a958894`. 구현 commit `3106aee`(config·회귀 가드), 기록 commit `a958894`(artifact·기록). 검증 시작 및 변이 전 working tree clean.
- 정본: `docs/plan/phase_8_face_anonymization.md:79` §P08-05("P05 절차를 `configs/calibration_anonymized.yaml`로 실행, 출력은 `experiments/p08_anonymized/calibration/`, `configs/calibration.yaml`은 쓰지 않음, 검증은 P05와 같은 회귀 가드"), 같은 문서 §계약·소유권의 checkpoint 결합 규격, P08-06 사전등록 `configs/anonymized_diagnostic.yaml:14`의 `candidate_calibration` 경로. 이 범위에서 모순은 발견하지 않았다.
- 실제 H: checkpoint를 읽어 hash를 재계산했고, GPU 사용률을 확인한 뒤(2%·1003MiB, ai_writte_system 컨테이너만 가동) GPU 재실행 1회와 score CLI 1회를 수행했다. 출력 디렉터리는 사전 백업했다.

## 방법·실행 결과

1. `git status --short`(빈 출력), `git show --stat 3106aee a958894`, 정본 scoped reading.
2. config 비교: `diff configs/calibration.yaml configs/calibration_anonymized.yaml` → 차이는 주석·`checkpoint`·`face_cache`(추가)·`output_dir`뿐. `device`·`fit`·`metrics` 동일, `anonymize` 키 없음. `experiments/p08_anonymized/calibration/config.yaml`은 config와 byte 동일.
3. hash: `sha256sum /mnt/h/tracepector/checkpoints/anonymized/best.pt` → `091ac45424099c41bf50bb0adf7932d4b0b1ace3ceba9b9a27e25af99732c54b`, `data/metadata.csv` → `039cbdd11407e5571b75681d64ae832b04c2f9439e94e94abf46d16f6e2d5781`. 둘 다 `calibration.json`과 일치. `git_commit`은 `3106aeea…`, `fit_split=val`, `validation_count=820`.
4. CPU 재계산(`docker compose run --rm -T dev python -`, 아래 스크립트): prediction 820행·중복 없음·metadata val ID 집합 및 순서와 동일(REAL 452/GEN 368). `src/calibration.py`의 `fit_temperature`·`choose_threshold`로 재계산한 T=`0.9687472487772221`, threshold=`0.383150136171922`가 artifact와 **float 완전 일치**. validation `raw`/`calibrated`/`raw_classification`/`calibrated_classification` 재계산 dict가 `metrics.json["validation"]`과 완전 일치.
5. GPU 재실행: 출력 디렉터리를 scratchpad에 백업 → `GIT_COMMIT=3106aeea823059859f965956b5c140218dfa5fe8 docker compose --profile training run --rm -T train python -u -m src.calibrate --config configs/calibration_anonymized.yaml` → exit0, 1분27초, `temperature=0.968747 probability_threshold=0.383150`. `calibration.json`·`metrics.json`·`validation_predictions.csv` 세 파일이 백업과 `cmp` byte 동일, 이후 `git status --short` 빈 출력. 따라서 Test A/B 지표도 독립 재생성으로 확인됐다. (로그의 `text_model.* UNEXPECTED`는 vision 전용 로드의 기존 경고.)
6. Test 지표 대조: Test A count 800, Test B count 1048(= Test A REAL 448 + sd35_medium 600, `src/evaluate.py:53` 정의와 일치). Test B REAL recall 0.9977678 = 447/448, precision 0.9738562 = 447/459, 0.9654428 = 447/463 → FP 12→16. Test B GEN은 metadata상 전부 `sd35_medium`이므로 "sd35 FP 12→16" 정확. README 두 표(NLL/Brier/ECE, Accuracy/ROC-AUC)의 모든 값이 `metrics.json`과 반올림 일치. "validation Brier·ECE 근소 악화, NLL 개선, Test A/B 세 지표 근소 개선"도 수치와 일치.
7. score CLI: `src.score --image /images/real/스포티/998959.jpg ...` → `92.676153346304`, `photographic_like`(README 값 재현). 캐시 기반 logit 2.458660364에 T를 적용하면 92.676176 → H1.
8. 불변: `git diff 3106aee~1 HEAD --stat -- experiments/p05_calibration configs/calibration.yaml configs/primary.yaml src tests/test_calibration.py tests/test_anonymize.py` 빈 출력.
9. 기록: HANDOFF·`docs/plan/00_index.md`·phase_8 계획·CHANGELOG·work log·calibration README의 상대 링크 전수 존재 확인(깨진 링크 0). 모두 "독립검증 대기"로 표시하고 채택 판정은 P08-06에 남겨 과잉 주장 없음. `configs/primary.yaml` 미변경 명시.
10. 전체 suite: `docker compose run --rm -T dev python -m pytest -q > log; echo exit=$?` → **exit=0, 182 passed, 1 skipped**(실제 YuNet opt-in), 56.94s.

## 경계 행렬

| 정본 경계 | 구현/artifact | 회귀 또는 실행 증거 | 결과 |
| --- | --- | --- | --- |
| P05와 같은 fit/metric/device, checkpoint·캐시·출력만 다름 | `configs/calibration_anonymized.yaml:2-11` | `test_anonymized_calibration_matches_p05_except_checkpoint_cache_and_output`; M2·M3·M6 | 동일성 확인, drift 양쪽(후보·baseline) 거부 |
| 익명화 규격은 checkpoint 결합본만, override 금지 | config에 `anonymize` 없음; `src/calibrate.py:41`, `src/anonymize.py:94-95` | 같은 셀 :15; M1 | override 추가 시 실패 |
| checkpoint는 P08-04 best, 캐시는 학습과 같은 것 | `configs/anonymized.yaml` 참조 비교(테스트 :12-13) | M4; 실제 hash 091ac454… | 일치 |
| 출력 분리, P05 경로 재사용 금지 | `output_dir: experiments/p08_anonymized/calibration` | 테스트 :14; M5 | 다른 경로 거부 |
| validation에서만 fitting | `src/calibrate.py:45`, :57-58 | `tests/test_calibration.py:49`(P05 가드, 변경 없음), 실제 ID 집합·순서 비교 | 820 = metadata val |
| T/threshold 재현 | `calibration.json` | CPU 재계산 float 완전 일치, GPU 재실행 byte 동일 | 통과 |
| P05 artifact·primary 불변 | `experiments/p05_calibration/`, `configs/calibration.yaml`, `configs/primary.yaml` | scoped git diff 빈 출력 | 통과 |
| P08-06 소비 경로 | `configs/anonymized_diagnostic.yaml:14` | 파일 존재 | 일치 |

## 변이표·복원

`git status --short` 빈 출력 확인 후 시작했다(감사 대상이 커밋된 상태이므로 clean-tree 분기). 각 변이 뒤 `docker compose run --rm -T dev python -m pytest -q tests/test_p08_calibration_config.py`를 실행하고 `git checkout -- configs/calibration_anonymized.yaml configs/calibration.yaml`로 복원한 뒤 status 빈 출력을 매회 확인했다. 원본(M0)은 1 passed.

| 변이 | diff | 실패 위치 | 관측 |
| --- | --- | --- | --- |
| M1 | 후보에 `anonymize: configs/anonymize.yaml` 추가 | 테스트 :15 | `'anonymize' not in ...` 실패 |
| M2 | 후보 `ece_bins: 10→15` | :17 | dict 불일치 실패 |
| M3 | 후보 `device: cuda→cpu` | :17 | dict 불일치 실패 |
| M4 | 후보 `face_cache` → `.../other.csv` | :13 | 경로 불일치 실패 |
| M5 | 후보 `output_dir` → `.../calibration2` | :14 | 경로 불일치 실패 |
| M6 | baseline `temperature_max: 20.0→10.0`(P05 쪽 drift) | :17 | dict 불일치 실패 |

구현자가 보고한 변이 4종(iterations·P05 출력 재사용·캐시 삭제·baseline checkpoint)과 겹치지 않는 축으로 골라 셀이 각 조항을 개별로 잠그는 것을 확인했다. 정상 config는 통과하므로 과잉 엄격 방향도 확인됐다.

## 지적

### 차단

없음.

### 비차단

- **H1 — README의 score CLI "일치" 표현 정밀도** (`experiments/p08_anonymized/calibration/README.md:43`, 같은 취지 `docs/daily_logs/2026-10-19/work_log.md:14`). 직접 YuNet 경로 score 92.676153과 캐시 기반 logit 2.458660364에 T를 적용한 값 92.676176은 2.3e-5 차이다(역산 logit 2.4586567, 차 3.7e-6). 배치 크기·float 연산 차이로 보이는 수치 잡음이며 결론에는 영향이 없지만, "일치"만 쓰면 bit 단위 일치로 읽힌다. 권장 보강: "score 차 2.3e-5(logit 차 약 4e-6) 이내로 일치" 처럼 허용오차를 명시.

### 관찰(지적 아님)

- `validation_predictions.csv`는 `csv.writer` 기본 종결자로 CRLF가 생성되고, `core.autocrlf=input`으로 index에는 LF로 저장된다. P05 파일과 같은 상태다. 이 파일의 hash를 결합하는 소비자가 없고(`grep` 결과 `src/calibrate.py:49`·`tests/test_calibration.py:71`만 참조), CSV 판독은 두 종결자 모두 동일하므로 영향 없음. 단 fresh clone에서 재실행 byte 비교를 하면 종결자 차이로 다르게 보일 수 있다는 점만 남긴다.
- `config.yaml` snapshot은 `src.calibrate`가 쓰지 않는 수동 사본이다(P05와 같은 관례). 현재 config와 byte 동일.

## 최소 재현

```bash
diff configs/calibration.yaml configs/calibration_anonymized.yaml
sha256sum /mnt/h/tracepector/checkpoints/anonymized/best.pt data/metadata.csv
docker compose run --rm -T dev python - < recompute.py
docker compose run --rm -T dev python -m pytest -q > /tmp/pytest.log 2>&1; echo exit=$?
git diff 3106aee~1 HEAD --stat -- experiments/p05_calibration configs/calibration.yaml configs/primary.yaml src
```

```python
# recompute.py — repo root에서 dev 컨테이너로 실행
import csv, json
import numpy as np
from src.calibration import fit_temperature, choose_threshold, apply_temperature, calibration_metrics
from src.evaluate import binary_metrics
meta = {r['image_id']: r for r in csv.DictReader(open('data/metadata.csv', encoding='utf-8', newline=''))}
rows = list(csv.DictReader(open('experiments/p08_anonymized/calibration/validation_predictions.csv', newline='')))
ids = [r['image_id'] for r in rows]
assert ids == [k for k, r in meta.items() if r['split'] == 'val']
logits = np.array([float(r['logit']) for r in rows]); labels = np.array([int(meta[i]['label']) for i in ids])
cal = json.load(open('experiments/p08_anonymized/calibration/calibration.json')); f = cal['config']['fit']
T = fit_temperature(logits, labels, f['temperature_min'], f['temperature_max'], f['iterations'])
th = choose_threshold(labels, apply_temperature(logits, T))
assert (T, th) == (cal['temperature'], cal['threshold_probability'])
m = json.load(open('experiments/p08_anonymized/calibration/metrics.json'))['validation']
assert m == dict(raw=calibration_metrics(logits, labels, 1, 10), calibrated=calibration_metrics(logits, labels, T, 10),
                 raw_classification=binary_metrics(labels, apply_temperature(logits, 1)),
                 calibrated_classification=binary_metrics(labels, apply_temperature(logits, T), th))
print('ok', T, th)
```

GPU 재실행은 출력 디렉터리를 먼저 백업하고, 실행 후 세 산출물을 `cmp`로 비교한다.

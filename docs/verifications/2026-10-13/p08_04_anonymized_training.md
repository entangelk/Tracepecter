**합격** — P08-04의 설정·실제 10 epoch 산출물·checkpoint 결합·기존 산출물 보존·회귀 양방향 경계를 확인했다. 비차단 H1은 실제 YuNet smoke 자동 회귀의 추가 후보다.

## 대상·정본·범위

- 날짜: 2026-10-13. 요청자: 소유자의 지속 독립검증 요청. 검증자: 구현에 참여하지 않은 Codex 단일 subagent `p08_04_verify`.
- 대상: `main` HEAD `51afcdb`; 실제 학습 출처 `6ace79b968adba3515462938916ca08f0e3d57f7`. 검증 시작 및 변이 전 working tree clean.
- 정본 범위는 코드 열람 전에 정의했다: `docs/sot.md:32` 우선순위 → Resolved DB-06 → `docs/project.md` v1.4 §15·16·25 → `docs/plan/phase_8_face_anonymization.md:74` P08-04와 :88 checkpoint 결합·:107 사전등록 순서 → `configs/primary.yaml`, `configs/anonymized.yaml`, `configs/anonymize.yaml`. 사전등록 불변은 `configs/anonymized_diagnostic.yaml`과 `experiments/p08_anonymized/diagnostic/README.md:7` 및 manifest가 소유한다. 이 범위에서 모순은 발견하지 않았다.
- 구현/테스트: `src/train.py`의 smoke 합성 원본 해상도 변경, 신규 config 및 `tests/test_p08_training_config.py`, 기존 학습/재개·checkpoint 결합 회귀. 결과/실행 JSON·README·상태 기록도 감사했다.
- 실제 H: best/last/experiment, baseline, metadata·사전등록 입력, train/val 원본 이미지4,600개의 캐시 hash를 읽었다. H: 모델 binary를 변경하지 않았다. 실제 모델의 새 평가·추론·calibration·GPU 학습은 수행하지 않았다. 전체 suite의 tiny fixture 평가/학습은 기존 CPU 회귀 범위다.

## 방법·실행 결과

1. `git status --short`, `git log -8 --oneline`, 정본 scoped reading 및 diff 확인.
2. CPU artifact 검사: 아래 재현 Python을 `docker compose run --rm -T dev python -`에 전달. 실제 `torch.load(..., map_location='cpu', weights_only=True)`로 best/last/baseline을 읽고 JSON/규격/텐서/hash를 독립 비교했다.
3. 실제 train/val 이미지 hash 4,600개를 host Python으로 재계산해 face cache와 비교했다. test/test_unseen 원본 이미지는 새 학습 대상이 아니므로 별도 image hash 전수 검사를 하지 않았다.
4. `docker compose run --rm -T dev python -m pytest tests/test_p08_training_config.py tests/test_train_smoke.py tests/test_baseline.py -q` → **12 passed, 33.95s**. 처음 시도에서 존재하지 않는 `tests/test_training.py`, `tests/test_train_resume.py`를 지정한 명령은 수집 오류였고, 실제 `test_baseline.py`의 재개 셀로 바로잡았다.
5. 실제 YuNet CPU smoke: 아래 `main` 호출 → **exit0**, epoch1/1·`smoke ok`·best 존재 확인, 해당 smoke 임시 디렉터리 삭제. 검출기 파일 sha256 검증도 실제 초기화 경로를 통과했다.
6. clean preflight → M1~M3 source/config 변이 → exact cell exit1 → HEAD 복원 및 원래 바이트 비교 → 매회 clean 확인. 변이표 참조.
7. 복원 뒤 `docker compose run --rm -T dev python -m pytest -q --durations=5` → **181 passed, 12 warnings, 45.79s**. 경고는 기존 `tests/test_deduplicate.py:35` Pillow mode deprecation이다. 가장 느린 셀은 `test_resume_matches_uninterrupted_training` 37.61s(기존 multiprocessing 재개 시험); 변경 smoke CLI 2.17s이며 새 규모/시간 회귀가 필요할 근거는 없다.
8. 복원 뒤 변경 경계 combined focused suite와 `git diff --check`도 확인했다. **5 passed, 4.64s**, `git diff --check` 통과.

## 경계 행렬

| 정본 경계 | 구현/실제 artifact | 명명된 회귀 또는 실행 증거 | 결과 |
| --- | --- | --- | --- |
| primary와 같은 모델·freeze·10 epoch·seed42·증강·split; 익명화/캐시/출력 차이는 허용 | `configs/anonymized.yaml:2`, :9, :17, :22, :28, :32 | `test_anonymized_training_matches_primary_except_preprocessing_and_output`; M3 | 동일성 확인, 정상 허용/seed drift 거부 |
| CLI smoke 원본은 model 해상도; 직접 fixture의 기본32는 유지 | `src/train.py:45`, :53, :188 | `test_smoke_uses_model_resolution_and_preserves_default_fixture`; M1/M2 | 224 원본8개 및 default32 양방향 잠금 |
| 정상 실제 YuNet smoke 완료 | `src/train.py:65`, :188 | 실제 `main(['--config','configs/anonymized.yaml','--smoke'])` | exit0, CPU1 epoch, best 존재 |
| 새 config의 익명화 누락 거부/명시 null 허용/정상 snapshot 허용/변조 및 detector hash 불일치 거부 | `src/anonymize.py:68`, :82; `src/train.py:65` | `test_binding_training_and_fail_closed` | 전체 suite 통과 |
| 학습은 원본에서 증강 전 처리, cache 사용 및 checkpoint snapshot 보존 | `src/train.py:66`, :71; `src/dataset.py` | `test_dataset_anonymizes_before_transform`, `test_anonymized_training_evaluation_calibration_and_score` 및 실제 image hash4,600개 | 통과 |
| train/val만 학습/검증; 다른 split은 제외 | `src/train.py:70`, :79 | `test_split_and_test_b_real_reuse`; 실제 metadata split 수·experiment count | train3780/val820, test800/test_unseen600 불변 |
| frozen encoder + 새 head | `src/train.py:91`; 실제 best/last/baseline | `test_siglip_pooling_and_freeze`; 실제 tensor 비교 | encoder208 전부 baseline 동일, head4 중 변화, best/last 모든 tensor 동일/유한 |
| validation loss 최소 best, last10·history1~10 및 metric 대응 | `src/train.py:130`, :134, :141, :151 | `test_training_validation_checkpoint_and_evaluation`; 실제 CPU 비교 | best epoch10·loss0.021584896370768547, metrics/history 일치 |
| 동일 config 재개 허용/다른 config 거부, 완료 epoch·RNG/optimizer 보존 | `src/train.py:104` | `test_resume_matches_uninterrupted_training`, `test_training_validation_checkpoint_and_evaluation` | 통과; 실제 completed GPU resume는 재실행하지 않음 |
| legacy/null offline 평가 허용; score는 거부 | `src/anonymize.py:82` | `test_legacy_and_null_allowed_for_evaluation_but_not_score` | 기존 결합 계약 유지 |
| 사전등록은 결과 전 commit; 규칙·입력·baseline/P05/P06 산출물 불변 | P08-03 commit77da668/b0b1b84 → 0190959 → 학습6ace79b → 결과51afcdb | ancestor·scoped git diff·config/7 input/3 CSV SHA256 및 baseline 실파일 | 모두 일치 |
| 별도 H: anonymized 저장, atomic temp 잔여 없음 | `src/train.py:136`, :140, :156; `compose.yaml:22` | 실제 host/컨테이너 artifact SHA256 일치, `/proc/self/mountinfo` | H: bind mount·tmp 없음 |

## 확인 사항

### 설정·코드·회귀

`tests/test_p08_training_config.py:7`은 허용된 세 차이를 먼저 정확히 검사한 뒤 전체 config 동등성을 비교한다. :18은 `run_training`을 mock하되 **실제 원본 파일**의 크기를 읽어 resize 뒤 크기만 검사하는 허점을 피한다. :25~27은 기존 기본32를 보호한다. `src/train.py:45`·:53·:188의 세 변경은 해당 계약에 직접 대응하고, 입력 크기에 따른 일반화나 추가 abstraction은 없다. 생성은 `SMOKE_NUM_IMAGES=8`로 고정되어 있으며 불필요한 반복/무한 재시도는 없다.

### 실제 checkpoint·history·출처

`experiments/p08_anonymized/training/result.json:2`의 학습 commit은 실제 experiment의 `git_commit`과 같다. `git diff --exit-code 6ace79b HEAD -- src configs tests`는 빈 diff여서 감사한 source/config/test가 학습 출처 commit과 동일하다. 이것은 source 계보 일치의 증거이며, 과거 프로세스의 runtime source attestation을 독립 재구성했다는 주장은 아니다.

best/last/experiment config는 current YAML을 canonical JSON snapshot으로 결합한 결과와 완전히 같았다. 재계산 snapshot hash는 `e171cec26c6f5e3ca26f5ffcdd2b00b6621e5e5980ba5fa909111950cf32075c`. 실파일 hash/bytes는 README:27~29 및 result.json의 세 값과 동일하다. baseline 실파일 hash는 `151244676027e88bc170d88daaa334a0b2eac4a4c205a85447fda9af99a995fe`로 고정값과 같다. metadata raw-byte hash는 `039cbdd11407e5571b75681d64ae832b04c2f9439e94e94abf46d16f6e2d5781`이며 experiment와 사전등록 둘 다 일치한다.

원본 train/val 이미지4,600개가 모두 face cache의 `image_sha256`과 같았다. snapshot의 detector/parameter 계약은 실제 smoke 초기화와 기존 fail-closed 회귀에서도 검사됐다. 사전등록 config·7 입력·3 표본 CSV SHA256을 모두 raw bytes로 다시 계산해 `preregistration.json`과 비교했다. P05/P06·primary·metadata·규격·cache·diagnostic의 `0190959..HEAD` diff는 없다.

### 저장·실행 예외·상태

이 머신 2026-10-13 dev `/proc/self/mountinfo`는 `/app/checkpoints`가 H: 9p의 `/tracepector/checkpoints`로 연결됐음을 보였다. host `/mnt/h/tracepector/checkpoints/anonymized/`와 dev mount에서 읽은 hash가 같다. `*.tmp`가 없다. `compose.yaml:39`은 train의 동일 checkpoint bind mount, :40은 이미지 read-only mount, :35는 HF_HOME을 선언한다.

`experiments/p08_anonymized/training/README.md:33`와 `execution.json:23~27`은 supervisor exit1·`setsid: wait: Success`·원 Python exit 미포착과 completed resume exit0를 분리해서 기록했다. 원 학습 exit0를 허위로 주장하지 않는다. 현지 비추적 `training.log`에 epoch1~10 및 checkpoint saved가 존재하며 history의 반올림된 수치와 일치한다(검증 시 log SHA256 `690e619e48c2ad73fd00fc7ce2aeaea56a3aa92dc3c70e5686f827be7e4907af`). 별도의 3개 실파일 완결·서로 대응하는 epoch/history/tensor·atomic temp 부재로 **10epoch 결과 완료**는 충분히 지지된다.

실행 당시의 GPU/dependency·시작/종료 시각과 원 프로세스 exit는 과거 관측이므로 이번 CPU 검사로 재생하지 않았다. completed checkpoint resume exit0는 구현자의 실행 기록으로 남아 있고, 실제 GPU resume를 추가 실행해야 결과 완료를 증명할 필요는 없다고 판단했다. 전체 suite의 재개 계약은 별도로 검증했다. 이 구분을 유지하면 supervisor 예외가 학습 결과 완료 주장과 모순되지 않는다.

`HANDOFF.md:22`, phase plan:75, index:15는 독립검증 대기 상태로 일치한다. README:23은 val 결과만 주장하며 Test A/B·단서 해소·채택을 주장하지 않는다. P08-05 calibration 및 P08-06 사전 규칙 판정은 후속 경계다.

## 변이표

변이 직전 `git status --short`가 비었고 각 변이 후 `git checkout -- <path>`로 HEAD 복원했다. 원래 파일 bytes와 복원 bytes가 같고 매회 status가 비었음을 assertion으로 확인했다. 실제 H: binary는 변이하지 않았다.

| 변이 | 적용 diff/위치 | exact 재실패 셀 | 관측 |
| --- | --- | --- | --- |
| M1 under-strict | `src/train.py:188` `image_size=config['model']['image_size']`의 실제 double-quote 표현 → `image_size=32` | `test_smoke_uses_model_resolution_and_preserves_default_fixture` | exit1, :33 `(32,32)!=(224,224)` |
| M2 over-strict | `src/train.py:45` default `32` → `224` | 같은 셀 | exit1, :27 legacy fixture `(224,224)!=(32,32)` |
| M3 설정 drift | `configs/anonymized.yaml:15` seed42 →43 | `test_anonymized_training_matches_primary_except_preprocessing_and_output` | exit1, :15 config 동등성 실패 |

복원 source SHA256 `c88ef9a4ba7004f4cdc0d9f41bb38292649ecbad3be9e3cf571a487eb25d94de`, config SHA256 `db4fd75dacc03eaefd0232cfd356fddfa4ed2d8061974781d0038eb6e3622d22`.

## 지적·위험

### 차단 사항

없음. 현 슬라이스의 필수 branch와 정상 허용 branch는 위 행렬의 명명된 셀/실파일 증거로 채웠다.

### 비차단 보강 후보

**H1 — 실제 YuNet smoke 자동 회귀.** `tests/test_p08_training_config.py:35`는 `run_training`을 mock하므로 실제 YuNet의 호출/완료를 suite에서 직접 확인하지 않는다. 이번 독립 실행은 실제 모델로 성공했고 해상도 계약 양방향은 M1/M2로 잠겨 있으므로 현 계약 누락은 아니다. 모델이 있는 환경에서만 실행하는 opt-in CPU smoke 셀을 추가하면 OpenCV·YuNet 버전 변화 등으로 올바른 원본 해상도에서도 실패하는 경우를 자동으로 검출할 수 있다. 모델이 없는 일반 CPU 환경에는 명시적으로 skip하도록 범위를 정할 수 있다.

## 미해결 운영 항목

원 Python 종료 코드는 복구할 수 없으며 이를 exit0로 정정하면 안 된다. H1의 채택/보강 및 동일 검증자의 추적검증은 소유자 지속 지시에 따라 구현자가 진행할 항목이다. P08-04 상태 승격과 P08-05/06 실행은 root가 기록을 반영한 뒤 진행한다. 이번 검증자는 보고서만 커밋하며 모델/구현/상태를 직접 수정하지 않는다.

## 재현

repo root에서 아래 CPU artifact 검사 Python을 `/tmp/p08_audit.py`에 저장하고 `docker compose run --rm -T dev python - < /tmp/p08_audit.py`로 실행한다. H: mount 및 기록된 artifact가 전제다. 이 코드는 새 학습/평가를 실행하지 않는다.

```python
import csv,hashlib,json,pathlib,subprocess,torch,yaml
P=pathlib.Path
h=lambda p:hashlib.sha256(P(p).read_bytes()).hexdigest()
r=json.loads(P('experiments/p08_anonymized/training/result.json').read_text())
e=json.loads(P('checkpoints/anonymized/experiment.json').read_text())
b=torch.load('checkpoints/anonymized/best.pt',map_location='cpu',weights_only=True)
l=torch.load('checkpoints/anonymized/last.pt',map_location='cpu',weights_only=True)
a=torch.load('checkpoints/baseline/best.pt',map_location='cpu',weights_only=True)
c=yaml.safe_load(P('configs/anonymized.yaml').read_text()); spec=yaml.safe_load(P('configs/anonymize.yaml').read_text()); sh=hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(); c['anonymization']={'spec':spec,'sha256':sh}
assert b['config']==l['config']==e['config']==c
assert r['anonymization_sha256']==sh
assert b['epochs_done']==l['epochs_done']==10
assert l['history']==e['history']==r['history']
assert [x['epoch'] for x in l['history']]==list(range(1,11))
best=min(l['history'],key=lambda x:x['val_loss'])
assert b['epochs_done']==best['epoch']==r['best_epoch']
assert b['val_loss']==l['best_loss']==best['val_loss']==r['best_validation_loss']
assert b['validation_metrics']==best['validation_metrics']==r['best_validation_metrics']
assert all(torch.isfinite(v).all() for v in b['model_state'].values())
enc=[k for k in b['model_state'] if k.startswith('encoder.')]; head=[k for k in b['model_state'] if not k.startswith('encoder.')]
assert enc and head and all(torch.equal(b['model_state'][k],a['model_state'][k]) for k in enc)
assert any(not torch.equal(b['model_state'][k],a['model_state'][k]) for k in head)
assert all(torch.equal(b['model_state'][k],l['model_state'][k]) for k in b['model_state'])
for name,v in r['artifacts'].items():
 p=P('checkpoints/anonymized')/name; assert h(p)==v['sha256'] and p.stat().st_size==v['bytes']
assert h('checkpoints/baseline/best.pt')=='151244676027e88bc170d88daaa334a0b2eac4a4c205a85447fda9af99a995fe'
assert not list(P('checkpoints/anonymized').glob('*.tmp'))
rows=list(csv.DictReader(P('data/metadata.csv').open())); counts={s:sum(x['split']==s for x in rows) for s in set(x['split'] for x in rows)}
assert counts['train']==e['train_sample_count']==r['train_images']==3780 and counts['val']==e['validation_sample_count']==r['validation_images']==820
assert e['dataset_version']==h('data/metadata.csv') and e['git_commit']==r['training_git_commit']
f='configs/anonymized_diagnostic.yaml'; d=yaml.safe_load(P(f).read_text()); pre=json.loads(P('experiments/p08_anonymized/diagnostic/preregistration.json').read_text());assert h(f)==pre['config_sha256']
for k,p in d['inputs'].items():assert h(p)==pre['inputs_sha256'][k]
for k,v in pre['manifests_sha256'].items(): assert h(P('experiments/p08_anonymized/diagnostic')/k)==v
print(json.dumps(dict(encoder_tensors=len(enc),head_tensors=len(head),snapshot=sh,counts=counts,best=best,hashes=r['artifacts']),indent=2))
```

실제 train/val image hash 재현:

```bash
python3 - <<'PY'
import csv,hashlib,pathlib
P=pathlib.Path
cache={r['image_id']:r for r in csv.DictReader(P('experiments/p08_anonymized/face_boxes.csv').open())}
count=0
for row in csv.DictReader(P('data/metadata.csv').open()):
    if row['split'] not in ('train','val'): continue
    path=P('/mnt/h/tracepector/images')/P(row['path']).relative_to('images')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==cache[row['image_id']]['image_sha256']
    count+=1
assert count==4600
print(count)
PY
```

실제 YuNet CPU smoke·회귀·계보/불변 재현:

```bash
docker compose run --rm -T dev python - <<'PY'
import shutil
from src.train import main
p=main(['--config','configs/anonymized.yaml','--smoke'])
assert p.exists()
shutil.rmtree(p.parent.parent)
PY
docker compose run --rm -T dev python -m pytest tests/test_p08_training_config.py tests/test_train_smoke.py tests/test_baseline.py -q
docker compose run --rm -T dev python -m pytest -q --durations=5
git merge-base --is-ancestor b0b1b84 6ace79b
git diff --exit-code 6ace79b 51afcdb -- src configs tests
git diff --exit-code 0190959 51afcdb -- configs/primary.yaml configs/anonymized_diagnostic.yaml experiments/p05_calibration experiments/p06_failure_analysis data/metadata.csv experiments/p08_anonymized/diagnostic experiments/p08_anonymized/face_boxes.csv configs/anonymize.yaml
git diff --check
```

변이 재현은 **clean tree에서만**, 아래 Python을 `/tmp/p08_mutate.py`에 저장하고 host `python3 /tmp/p08_mutate.py`로 실행한다. 보고서를 커밋한 후의 clean preflight도 유효하다.

```python
from pathlib import Path
import subprocess,hashlib
assert subprocess.check_output(['git','status','--short'])==b''
cases=[('M1','src/train.py','image_size=config["model"]["image_size"]','image_size=32','test_smoke_uses_model_resolution_and_preserves_default_fixture'),('M2','src/train.py','image_size: int = 32','image_size: int = 224','test_smoke_uses_model_resolution_and_preserves_default_fixture'),('M3','configs/anonymized.yaml','seed: 42','seed: 43','test_anonymized_training_matches_primary_except_preprocessing_and_output')]
for name,file,old,new,cell in cases:
 p=Path(file); before=p.read_bytes(); assert old in p.read_text()
 try:
  p.write_text(p.read_text().replace(old,new))
  r=subprocess.run(['docker','compose','run','--rm','-T','dev','python','-m','pytest',f'tests/test_p08_training_config.py::{cell}','-q'],capture_output=True,text=True)
  print(name,'exit',r.returncode, r.stdout, r.stderr,flush=True)
  assert r.returncode==1
 finally:
  subprocess.run(['git','checkout','--',file],check=True)
  assert p.read_bytes()==before
  assert subprocess.check_output(['git','status','--short'])==b''
  print(name,'byte-identical clean restore',hashlib.sha256(before).hexdigest(),flush=True)

```

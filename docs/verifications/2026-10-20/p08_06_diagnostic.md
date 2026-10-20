# P08-06 진단·채택 독립검증

## 대상 메타데이터

- 날짜: 2026-10-20(KST).
- 요청자: 소유자. 이번 턴에서 서브에이전트 한 명의 독립검증까지 명시적으로 승인했다.
- 검증자: `/root/p08_independent_review`(구현하지 않은 별도 Codex 에이전트).
- 대상: HEAD `c2ba42d`, 구현 `1102343`, 최종 주석 `0c4eb6e`.
- 정본 범위: `docs/sot.md:32`의 우선순위; `docs/plan/phase_8_face_anonymization.md:63`의 P08-03 고정 계약, P08-06·계약·완료조건; `configs/anonymized_diagnostic.yaml` 전체; `experiments/p08_anonymized/diagnostic/README.md:7`~`:66` 사전 계약 및 실행 결과; `docs/project.md` §20.
- 연동 계약: `src/anonymize.py` checkpoint binding·공통 커널·cache identity, `src/calibration.py` 확률/지표, `src/evaluate.py` REAL 재사용·ROC/PR, `src/score.py` artifact 검증·필수 익명화.
- 방법 정본: `docs/guides/verification.md`를 독립검증 전에 직접 읽었다. 구현·테스트는 수정하지 않았고 커밋하지 않았다.

## 범위와 방법

정본 범위를 먼저 구성한 뒤 각 범위를 끝까지 읽고 경계표를 만들었다. 이후 실행기·새 테스트·기존 전처리/평가 테스트를 대조했다. 수치 검산은 진단 구현 함수를 호출하지 않고 CSV와 JSON의 원자료 및 별도 수식으로 수행했다. GPU 추론은 다시 하지 않았다. 현재 source 해시·입력 이미지·checkpoint·고정 calibration과 예측 파일의 계보를 직접 검증했다.

실행 명령:

```bash
git status --short
docker compose run --rm -T dev python -m pytest -q tests/test_p08_diagnostic.py tests/test_p08_diagnostic_runner.py tests/test_p08_adoption.py tests/test_p08_training_config.py
python3 /tmp/p08_independent_audit.py
python3 /tmp/p08_image_audit.py
python3 /tmp/p08_mutation_audit.py
python3 /tmp/p08_temperature_mutation.py
python3 /tmp/p08_more_mutations.py
docker compose run --rm -T dev python -m pytest -q
git diff 0c4eb6e HEAD -- configs/baseline.yaml configs/calibration.yaml experiments/p05_calibration experiments/p06_failure_analysis
git diff --check
```

검산·변이 스크립트의 핵심 재현 코드는 아래 부록에 보존한다. Docker는 sandbox 기본 제한 때문에 승인된 독립검증 범위로 escalated 실행했다. 컨테이너의 orphan 경고는 기존 진단 컨테이너 두 개를 열거했으며 삭제 작업을 하지 않았다.

## 계약/구현/테스트/fixture 경계표

| 정본 경계 | 구현 | 회귀 셀·fixture | 관측 |
| --- | --- | --- | --- |
| 예측 전 사전등록 raw hash·주석 952개 unique/confirmed·HEAD 동일 바이트 고정 | `scripts/p08_diagnostic.py:49`~`:85` | `test_preflight_rejects_tampering_before_predictions`, `test_committed_annotation_check_rejects_dirty_bytes_and_accepts_head`; 임시 실제 CSV/lock 및 Git subprocess fixture | 정상 허용·오염 거부; 최종 lock 전체 SHA 일치 |
| 각 checkpoint·metadata·snapshot·YuNet·이미지/cache identity 검증, 원본 bypass에서도 생략 금지 | `scripts/p08_diagnostic.py:86`~`:128`, `src/anonymize.py:120` | 위 tampering 셀 및 기존 `tests/test_anonymize.py` binding/cache 셀 | 2,369개 이미지 SHA, 두 checkpoint SHA, YuNet SHA, 6,000 cache parameter identity 독립 일치 |
| 모델 2개×입력 2개×val/Test A/Test B; Test B는 Standard REAL만 재사용 | `scripts/p08_diagnostic.py:233`~`:254` | `test_stub_end_to_end_fixed_calibration_and_resume`, 기존 `evaluation_indices` 회귀; REAL/GEN 각 1개 cohort fixture | 실제 val 820/Test A 800/Test B 1,048, REAL 448 공유 확인 |
| artifact별 고정 temperature·threshold를 실제 계산에 동일 적용 | `scripts/p08_diagnostic.py:241`~`:243`, `:291`~`:295` | 위 end-to-end 셀은 메타데이터·키 존재만 확인; 실제 수치 oracle 부재 | **B1: M7/M8/M9 생존**. 구현·실제 산출물은 맞지만 필수 회귀 경계 미충족 |
| ROC/PR·분류·NLL/Brier/ECE10 및 generator/category/source 분해 | `scripts/p08_diagnostic.py:238`~`:252`, `src/evaluate.py:18`, `src/calibration.py:65` | end-to-end 키 존재·기존 evaluate/calibration 수식 회귀; 실제 raw 별도 전수 검산 | 전체 cohort/세부군 모든 수치 일치; 실행기→수치 연결은 B1 보강 대상 |
| REAL 정상 익명화 위 모든 원 공동 overlay, GEN gray/restore 원본 기반·재익명화 금지 | `scripts/p08_diagnostic.py:154`~`:178` | `test_variants_preserve_other_masks_all_discs_and_no_second_anonymization`; 두 얼굴·두 원·다른 위치 mask fixture | 정상/gray/restore 픽셀 확인, M4 실패 |
| shape major/2+guard, size max(shape,target), 무축소·clipping·개별 확장비 | `scripts/p08_diagnostic.py:131`~`:151` | 같은 variant 셀의 거대 원·음수 중심 fixture | 300개 기하 행 독립 재계산·clipping 일치, size 무확장 이미지 8 |
| 절댓값 paired bootstrap·PCG64·복원추출·20,000·linear percentile·5점 닫힌 상한 | `src/diagnostic.py:26`~`:60` | `test_intervention_bootstrap_is_paired_absolute_with_replacement`; 상쇄·분산·정확한 경계 fixture | M1/M2 실패; 실제 네 조건 CI 일치 |
| harmful 오류/전체 이미지·reverse 비상쇄·Wilson95·5% 포함, 최소80·누락/중복/NaN/inf 미확정 | `src/diagnostic.py:30`~`:55` | `test_error_gate_uses_all_images_and_does_not_cancel_reverse_flips`, `test_intervention_minimum_and_error_interval_are_inclusive`, `test_invalid_interventions_are_indeterminate_not_partial_pass` | 0건에도 양의 Wilson 상한, 79 거부/80 허용; 실제 네 조건 harmful0 일치 |
| 세 얼굴 상태 우선순위·generator 보고·최소20·세 Newcombe CI ±.10 포함·누락 미확정 | `src/diagnostic.py:63`~`:91` | `test_concentration_counts_all_states_and_generators`, `test_concentration_minimum_interval_boundaries_and_bad_predictions`; 얼굴없음/일부남음·19/20 fixture | 607/237/108 및 FP10/5/5, 세 구간 일치; M6 실패 |
| candidate 익명화 AUC .90/.80 포함+전 관문 pass만 채택; fail/indeterminate 미채택 | `src/diagnostic.py:94`~`:103` | `test_adoption_requires_both_aucs_and_every_cue_gate`, `test_primary_uses_adopted_anonymized_artifacts_and_preserves_baseline` | 경계 포함·전 관문 요구, M3 실패; primary=anonymized config |
| 재개는 불완전 마지막 행만 제거, 중복/타 cohort/nonfinite 거부; identity 다르면 혼합 금지 | `scripts/p08_diagnostic.py:189`~`:230`, `:258`~`:264` | `test_resume_rejects_duplicate_and_foreign_rows_and_repairs_only_torn_tail`, end-to-end resume·artifact변경 셀 | 재예측 없음·입력 변경 거부; M5 실패 |
| baseline/P05/P06 불변·새 artifact 별도 보존 | `configs/primary.yaml:1`, `scripts/p08_diagnostic.py:260` | 채택 연결 셀 및 Git 원본 바이트 비교 | 해당 경로 diff 없음, baseline checkpoint 해시 `151244…` 유지 |

## 표면별 발견 사항

### 계약 자체와 채택 연결

`configs/anonymized_diagnostic.yaml:124`의 두 AUC projection은 `docs/project.md` §20의 .90/.80과 일치한다. 사전 고정 파일과 P05 artifact는 `0c4eb6e`와 바이트 동일하다. 사전등록 마지막 수정 커밋은 `b0b1b84`로 P08-04 결과보다 선행한다. `configs/primary.yaml`은 `configs/anonymized.yaml`과 구조적으로 동일하며 candidate calibration checkpoint 경로는 `checkpoints/anonymized/best.pt`다. 관련 계약 내부 모순은 발견하지 못했다.

### 구현과 수치 산출물

`result.json.prediction_sha256`의 8개 CSV 모두 직접 SHA-256·고유 ID·finite logit·정확한 cohort 집합을 확인했다. 예측 합계는 9,651개이고 고유 입력은 평가 2,220+REAL 149=2,369개다. `execution.json.source_sha256` 전부와 현재 source 바이트가 일치하며 `/app/scripts/p08_diagnostic.py`는 repository 상대 경로로 해석했다. `face_review_lock.json`의 원본·변환본·agent·owner 목록·최종본 해시가 모두 일치했다.

별도 구현에서 pairwise rank AUC, threshold 분류, PR trapezoid, 안정적인 logistic/NLL, Brier, equal-width10 ECE를 계산했다. 2×2×세 cohort와 모든 generator/category/source 세부군이 허용오차 `rtol=1e-10, atol=1e-11` 안에서 일치했다. candidate의 Test A AUC 0.9998668323863635 및 Test B 0.9996465773809524는 기준을 통과한다. 네 개입은 동일 PCG64 표본 인덱스를 별도 생성하여 bootstrap을 검산했고, harmful0과 Wilson 상한도 일치했다. 얼굴 상태별 FP와 Newcombe 세 구간도 일치했다. 이 근거로 현재 데이터의 채택 판정 자체를 반박할 수 없었다.

`src/diagnostic.py:43`의 bootstrap은 명세대로 O(Bn) 시간·공간이며 B=20,000, n≤162다. `src/evaluate.py:41`의 순위 지표는 O(n log n)이고, 보고 세부군 수는 현재 metadata로 제한된다. 무한 retry/polling/traversal은 없다. 구현은 고정 예측과 통계 연산을 분리하고 기존 공통 mask 커널을 재사용한다.

### 테스트와 fixture

최초 집중 suite는 **25 passed, 1 skipped (4.99s)**다. opt-in 실제 YuNet CPU 학습 smoke는 이번 기본 CPU 실행에서 skipped이며, 실제 YuNet 파일 해시와 2,369개 원본 cache 이미지는 별도 직접 검증했다. 스킵된 학습 smoke를 실행한 것으로 간주하지 않는다. 모든 변이 복원 후 전체 CPU suite는 **208 passed, 1 skipped, 12 warnings (49.60s)**였다. warning 12개는 기존 `tests/test_deduplicate.py:35`의 Pillow mode deprecation이며 이 변경의 실패가 아니다. `git diff --check`도 통과했다.

고정 calibration의 실제 계산을 깨는 세 변이를 전체 새 진단 suite가 잡지 못했다. 계산 구현이 정확한 현재 결과를 독립 확인한 사실과 회귀 guard가 없는 사실을 구분한다.

## 변이 증거

최초 변이 직전에 실행한 `git status --short` 출력은 비어 있었다. M1~M9 각각 실행 전에도 clean을 확인했고, `try/finally`에서 `git checkout -- <path>` 뒤 사전 백업과 byte 동일 및 `git status --short`가 빈 것을 모두 확인했다. 모든 변이는 커밋된 HEAD 위에서만 수행했다.

| 변이 | 실제 변경 | 정확한 guarding cell/실행 범위 | 결과 |
| --- | --- | --- | --- |
| M1 완화 | `absolute = np.abs(signed)` → `absolute = signed` | `tests/test_p08_diagnostic.py::test_intervention_bootstrap_is_paired_absolute_with_replacement` | exit1, 평균 절댓값 2 assertion 실패 |
| M2 과잉 | score CI 상한 `<=` → `<` | 위 동일 셀 | exit1, 정확한 경계 pass assertion 실패 |
| M3 완화 | 채택 cue `all` → `any` | `tests/test_p08_diagnostic.py::test_adoption_requires_both_aucs_and_every_cue_gate` | exit1, 한 관문 fail/indeterminate 미채택 assertion 실패 |
| M4 방어 제거 | REAL overlay 기반 `normal` → `original` | `tests/test_p08_diagnostic_runner.py::test_variants_preserve_other_masks_all_discs_and_no_second_anonymization` | exit1, 다른 위치 YuNet mask 보존 assertion 실패 |
| M5 방어 제거 | execution candidate calibration SHA → 상수 | `tests/test_p08_diagnostic_runner.py::test_stub_end_to_end_fixed_calibration_and_resume` | exit1, artifact 변경 시 ValueError가 발생하지 않음 |
| M6 과잉 | Newcombe 허용 경계 `>=`/`<=` → `>`/`<` | `tests/test_p08_diagnostic.py::test_concentration_minimum_interval_boundaries_and_bad_predictions` | exit1, 정확한 허용 경계 pass assertion 실패 |
| M7 방어 제거 | `evaluation_report`의 확률 temperature → 1.0 | 새 diagnostic/runner/adoption 3개 파일 전체 | **exit0, 23 passed (4.76s)** |
| M8 방어 제거 | candidate 단서 관문 확률 temperature → 1.0 | 위 3개 파일 전체 | **exit0, 23 passed (4.61s)** |
| M9 방어 제거 | `evaluation_report`의 실제 분류 threshold → 0.5 | 위 3개 파일 전체 | **exit0, 23 passed (4.53s)** |

## 이슈와 위험

### 차단 B1 — 실제 calibration 적용 회귀 경계 누락

정본 `experiments/p08_anonymized/diagnostic/README.md:21`, `:23`, `:47`은 모델별 temperature/threshold가 실제 평가·단서 계산에 적용될 것을 요구한다. 구현 위치는 `scripts/p08_diagnostic.py:241`~`:243`, `:291`~`:295`이며 현재 구현은 올바르다. 그러나 `tests/test_p08_diagnostic_runner.py:78`~`:86`은 threshold 보고값·count·키 존재만 검사하고 `:91`~`:96`은 raw logit 관계만 검사한다. M7/M8/M9 생존으로 실제 계산 연결의 guard가 빠졌음을 확인했다. 이것은 사양 필수 경계의 빈 칸으로, `docs/guides/verification.md`의 판정 규칙상 차단이다.

보강 제안: fixture에서 T=1과 모델별 T=2/3의 확률이 threshold 양쪽으로 나뉘는 사례와 artifact threshold/0.5의 분류 차이를 확보한다. 저장된 logit에서 독립 수식으로 확률·분류·NLL/Brier/ECE를 계산해 2×2 각 조건의 cohort별 보고값 및 candidate 개입/얼굴 상태·generator projection을 검증한다. 정상 artifact 적용은 허용하고 T=1·공통 threshold를 강제하는 과잉 단순화도 재실패시켜야 한다.

### 비차단 보강 권고

별도로 추가할 권고 없음. B1은 비차단으로 재분류할 수 없다. 얼굴이 보이는 외부 REAL holdout 미평가, REAL train 개입, z_image_turbo 2장 및 얼굴 상태/generator 교란은 `experiments/p08_anonymized/diagnostic/README.md:64`의 기존 한계이며 새 결함으로 취급하지 않았다.

## 판정

**조건부 합격** — B1의 모델별 고정 calibration 실제 계산 경계에 수치 회귀 assertion을 추가하고 M7/M8/M9 재실패를 확인해야 한다.

현재 구현·입력·예측·통계·채택 연결은 독립 재계산과 일치한다. 구현 결과의 오류는 발견하지 못했지만, 사양이 요구하는 계산 경계의 회귀 보호가 누락되어 독립검증 완료로 표시할 수 없다.

## 남은 작업과 최종 상태

- 모든 변이를 복원했다. 검증자는 구현/테스트를 수정하지 않았다.
- B1 보강과 추적 독립검증은 root가 진행한다. 새 GPU 예측은 현재 발견으로 요구되지 않는다.
- 이 검증 기록은 root에게 전달하는 미커밋 파일이며 검증자가 커밋하지 않는다.

## 재현 부록

다음 Python 코드를 `/tmp/p08_independent_audit.py`로 저장하고 repository root에서 `python3 /tmp/p08_independent_audit.py`로 실행하면 전체 원자료 수치 검산을 재현한다. 호스트 checkpoint 경로는 Compose 기본 mount에 맞춰 `/mnt/h/tracepector/checkpoints`를 사용한다.

```python
import csv,json,hashlib,math,statistics,subprocess
from pathlib import Path
import numpy as np,yaml
root=Path.cwd(); out=root/'experiments/p08_anonymized/diagnostic'
def read(p): return list(csv.DictReader(open(p)))
def digest(p): return hashlib.sha256((Path('/mnt/h/tracepector')/p if str(p).startswith('checkpoints/') else Path(p)).read_bytes()).hexdigest()
def close(a,b): assert np.allclose(a,b,rtol=1e-10,atol=1e-11),(a,b)
cfg=yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text()); result=json.loads((out/'result.json').read_text()); ex=json.loads((out/'execution.json').read_text()); reg=json.loads((out/'preregistration.json').read_text()); lock=json.loads((out/'face_review_lock.json').read_text())
for p,h in lock['sha256'].items(): assert digest(out/p)==h
for p,h in reg['inputs_sha256'].items(): assert digest(cfg['inputs'][p])==h
for p,h in reg['manifests_sha256'].items(): assert digest(out/p)==h
assert digest('configs/anonymized_diagnostic.yaml')==reg['config_sha256']==ex['config_sha256']
assert digest(out/'preregistration.json')==ex['registration_sha256']
assert digest(out/'face_review_lock.json')==ex['annotation_lock_sha256']
for p,h in ex['source_sha256'].items(): assert digest(p.removeprefix('/app/'))==h
assert digest(cfg['candidate_calibration'])==ex['candidate_calibration_sha256']
meta=read('data/metadata.csv'); rows={r['image_id']:r for r in meta}; real=read(out/'real_interventions.csv'); gen=read(out/'gen_interventions.csv'); anns=read(out/'face_review.csv'); realids={r['image_id'] for r in real}; genids={r['image_id'] for r in gen}; evalids={i for i,r in rows.items() if r['split'] in ('val','test','test_unseen')}
raw={}
for p,h in result['prediction_sha256'].items():
 assert digest(out/p)==h
 values=read(out/p); raw[p[:-4]]={r['image_id']:float(r['logit']) for r in values}
 assert len(values)==len(raw[p[:-4]]) and all(math.isfinite(float(r['logit'])) for r in values)
 expected=realids if '_real_' in p else genids if '_gen_' in p else evalids|realids if p=='candidate_anonymized.csv' else evalids
 assert set(raw[p[:-4]])==expected
assert len(evalids)==2220 and len(realids)==149 and len(genids)==162 and len(real)==150
arts={m:json.loads(Path(p).read_text()) for m,p in [('baseline',cfg['inputs']['baseline_calibration']),('candidate',cfg['candidate_calibration'])]}
for m,a in arts.items(): assert digest(a['checkpoint'])==a['checkpoint_sha256']==ex['checkpoints'][m]
def pvalues(values,t): return np.exp(-np.logaddexp(0,-np.array(values)/t))
probs={k:dict(zip(v,pvalues(list(v.values()),arts[k.split('_')[0]]['temperature']))) for k,v in raw.items()}
def metrics(ids,pr,art):
 y=np.array([int(rows[i]['label']) for i in ids]); p=np.array([pr[i] for i in ids]); pred=p>=art['threshold_probability']; tp=sum(pred&(y==1)); fp=sum(pred&(y==0)); fn=sum(~pred&(y==1)); precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
 values=dict(count=len(ids),accuracy=float(np.mean(pred==y)),precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0,brier=float(np.mean((p-y)**2)))
 logits=np.array([raw[current][i] for i in ids])/art['temperature']; values['nll']=float(np.mean(np.logaddexp(0,logits)-y*logits)); values['ece']=sum(abs(float(np.mean(p[(p*10).astype(int).clip(0,9)==b]))-float(np.mean(y[(p*10).astype(int).clip(0,9)==b])))*np.mean((p*10).astype(int).clip(0,9)==b) for b in range(10) if any((p*10).astype(int).clip(0,9)==b))
 if len(set(y))==2:
  positive=p[y==1]; negative=p[y==0]; values['roc_auc']=float(((positive[:,None]>negative).sum()+.5*(positive[:,None]==negative).sum())/(len(positive)*len(negative)))
  thresholds=sorted(set(p),reverse=True); tps=np.array([sum((p>=t)&(y==1)) for t in thresholds]); fps=np.array([sum((p>=t)&(y==0)) for t in thresholds]); values['pr_auc']=float(np.trapezoid(np.r_[1,tps/(tps+fps)],np.r_[0,tps/sum(y)]))
 else: values.update(roc_auc=None,pr_auc=None)
 return values
for m,conditions in result['evaluation'].items():
 for cond,data in conditions.items():
  current=m+'_'+cond; pr=probs[current]; art=arts[m]
  assert data['temperature']==art['temperature'] and data['threshold_probability']==art['threshold_probability']
  for cohort,report in data['cohorts'].items():
   ids=[i for i,r in rows.items() if r['split']==({'standard':'test'}.get(cohort,cohort))] if cohort!='unseen' else [i for i,r in rows.items() if r['split']=='test_unseen' or r['split']=='test' and r['label']=='1']
   for k,v in metrics(ids,pr,art).items(): assert report[k] is None if v is None else np.isclose(report[k],v,rtol=1e-10,atol=1e-11),(current,cohort,k,report[k],v)
   for field,key in [('generator','generator_wise'),('category','category_wise'),('source_domain','source_wise')]:
    for g,subreport in report[key].items():
     subids=[i for i in ids if rows[i][field]==g or field=='generator' and rows[i]['label']=='1' or field=='source_domain' and rows[i]['label']=='0']
     for k,v in metrics(subids,pr,art).items(): assert subreport[k] is None if v is None else np.isclose(subreport[k],v,rtol=1e-10,atol=1e-11),(current,cohort,key,g,k)
z=statistics.NormalDist().inv_cdf(.975)
def wilson(k,n):
 p=k/n; den=1+z*z/n; center=(p+z*z/(2*n))/den; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return [max(0,center-half),min(1,center+half)]
ref=probs['candidate_anonymized']; threshold=arts['candidate']['threshold_probability']
for cond in ('real_shape','real_size','gen_gray','gen_restore'):
 ids=sorted(realids if cond.startswith('real') else genids); var=probs['candidate_'+cond]; shift=np.array([(var[i]-ref[i])*100 for i in ids]); idx=np.random.Generator(np.random.PCG64(cfg['seed'])).integers(0,len(ids),size=(20000,len(ids))); ci=np.percentile(np.abs(shift)[idx].mean(axis=1),[2.5,97.5],method='linear'); harmful=sum((ref[i]>=threshold)==int(rows[i]['label']) and (var[i]>=threshold)!=int(rows[i]['label']) for i in ids); riskci=wilson(harmful,len(ids)); r=result['gates'][cond]; close(ci,r['absolute_shift_ci']);close(riskci,r['error_ci']);close(np.abs(shift).mean(),r['mean_absolute_shift']);assert harmful==r['correct_to_wrong'];assert r['status']==('pass' if ci[1]<=5 and riskci[1]<=.05 else 'fail')
groups={s:[] for s in cfg['face_concentration']['states']}
for r in anns:
 s='missed_visible_face' if int(r['uncovered_visible_faces']) else 'no_visible_face' if int(r['visible_faces'])==0 else 'anonymized';groups[s].append(r['image_id'])
for s,ids in groups.items():
 r=result['gates']['face_concentration']['states'][s]; assert len(ids)==r['count'] and sum(ref[i]>=threshold for i in ids)==r['false_positives']
for r in result['gates']['face_concentration']['comparisons']:
 a,b=r['states'];n1,n2=len(groups[a]),len(groups[b]);k1=sum(ref[i]>=threshold for i in groups[a]);k2=sum(ref[i]>=threshold for i in groups[b]);p1,p2=k1/n1,k2/n2;l1,u1=wilson(k1,n1);l2,u2=wilson(k2,n2);ci=[max(-1,p1-p2-math.sqrt((p1-l1)**2+(u2-p2)**2)),min(1,p1-p2+math.sqrt((u1-p1)**2+(p2-l2)**2))];close(ci,r['ci']);assert r['status']=='pass' and ci[0]>=-.1 and ci[1]<=.1
spec=yaml.safe_load(Path(cfg['inputs']['anonymization']).read_text()); bycandidate={r['candidate_id']:r for r in real}; notexpanded=realids.copy()
for g in result['geometry']['discs']:
 r=bycandidate[g['candidate_id']]; base=float(r['major'])/2+3*spec['edge_sigma']+1; target=float(r['width'])*reg['size_target_diameter_over_width']/2+3*spec['edge_sigma']+1; radius=max(base,target) if g['variant']=='real_size' else base;close(g['radius'],radius);assert g['raster_radius']==round(radius);close(g['expansion_ratio'],radius/base)
 if g['variant']=='real_size' and radius>base:notexpanded.discard(g['image_id'])
assert len(notexpanded)==result['geometry']['no_expansion_images']==8
assert result['adoption']['adopt'] and all(r['status']=='pass' for r in result['gates'].values())
for p in ('configs/anonymized_diagnostic.yaml','experiments/p08_anonymized/diagnostic/preregistration.json','experiments/p05_calibration/calibration.json'):
 assert subprocess.check_output(['git','show','0c4eb6e:'+p])==Path(p).read_bytes()
print(json.dumps(dict(hashes='all matched',predictions=sum(map(len,raw.values())),inputs=len(evalids|realids),metrics='all cohorts and breakdowns independently matched',interventions='all matched',states={k:len(v) for k,v in groups.items()},no_expansion=len(notexpanded),adopt=True),ensure_ascii=False))
```

이미지 원본·YuNet·clipping 검산은 다음 코드를 `/tmp/p08_image_audit.py`로 저장하여 실행한다.

```python
exec(open('/tmp/p08_independent_audit.py').read().split('arts=')[0])
from PIL import Image
cache={r['image_id']:r for r in read(cfg['inputs']['face_cache'])};spec=yaml.safe_load(Path(cfg['inputs']['anonymization']).read_text()); face=spec['face_detector']; detector=Path('/mnt/h/tracepector/checkpoints/face')/Path(face['model']).name
assert digest(detector)==face['model_sha256']
parameters=hashlib.sha256(json.dumps({k:v for k,v in face.items() if k not in ('model','model_sha256')},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
assert len(cache)==6000 and all(r['parameters_sha256']==parameters and r['detector_sha256']==face['model_sha256'] for r in cache.values())
for i in sorted(evalids|realids):
 path=Path('/mnt/h/tracepector/images')/Path(rows[i]['path']).relative_to('images'); assert digest(path)==cache[i]['image_sha256']; assert cache[i]['detector_sha256']==face['model_sha256']
for g in result['geometry']['discs']:
 path=Path('/mnt/h/tracepector/images')/Path(rows[g['image_id']]['path']).relative_to('images')
 with Image.open(path) as im: w,h=im.size
 x,y,r=round(g['cx']),round(g['cy']),g['raster_radius'];assert g['clipped']==(x-r<0 or y-r<0 or x+r>=w or y+r>=h)
print('2369 image hashes, YuNet and all clipping matched')
```

M1~M6의 정확한 자동 변이/복원 절차:

```python
from pathlib import Path
import subprocess
cases=[
('M1','src/diagnostic.py','absolute = np.abs(signed)','absolute = signed','tests/test_p08_diagnostic.py::test_intervention_bootstrap_is_paired_absolute_with_replacement'),
('M2','src/diagnostic.py',"interval[1] <= score_rules['max_upper']","interval[1] < score_rules['max_upper']",'tests/test_p08_diagnostic.py::test_intervention_bootstrap_is_paired_absolute_with_replacement'),
('M3','src/diagnostic.py',"cue_pass = all(gates.get(k, {}).get('status') == 'pass'","cue_pass = any(gates.get(k, {}).get('status') == 'pass'",'tests/test_p08_diagnostic.py::test_adoption_requires_both_aucs_and_every_cue_gate'),
('M4','scripts/p08_diagnostic.py',"return paint_circles(normal, [(g['cx'],g['cy'],g['radius'])","return paint_circles(original, [(g['cx'],g['cy'],g['radius'])",'tests/test_p08_diagnostic_runner.py::test_variants_preserve_other_masks_all_discs_and_no_second_anonymization'),
('M5','scripts/p08_diagnostic.py',"candidate_calibration_sha256=file_hash(settings['candidate_calibration'])","candidate_calibration_sha256='constant'",'tests/test_p08_diagnostic_runner.py::test_stub_end_to_end_fixed_calibration_and_resume'),
('M6','src/diagnostic.py',"interval[0] >= -limit and interval[1] <= limit","interval[0] > -limit and interval[1] < limit",'tests/test_p08_diagnostic.py::test_concentration_minimum_interval_boundaries_and_bad_predictions'),
]
log=[]
assert not subprocess.check_output(['git','status','--short']).strip()
for name,path,old,new,cell in cases:
 assert not subprocess.check_output(['git','status','--short']).strip()
 p=Path(path);original=p.read_bytes(); text=original.decode();assert text.count(old)==1
 try:
  p.write_text(text.replace(old,new))
  result=subprocess.run(['docker','compose','run','--rm','-T','dev','python','-m','pytest','-q',cell],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  log.append(dict(mutation=name,file=path,old=old,new=new,cell=cell,exit=result.returncode,output=result.stdout))
 finally:
  subprocess.run(['git','checkout','--',path],check=True)
  assert p.read_bytes()==original
  assert not subprocess.check_output(['git','status','--short']).strip()
 print(name, 'exit',result.returncode,flush=True)
Path('/tmp/p08_mutation_results.json').write_text(__import__('json').dumps(log,indent=2))
assert all(c['exit']==1 for c in log)
```

M7~M9는 위 표의 각 치환을 하나씩 적용하고 `docker compose run --rm -T dev python -m pytest -q tests/test_p08_diagnostic.py tests/test_p08_diagnostic_runner.py tests/test_p08_adoption.py`를 실행했다. 각 변이 전 clean 확인, `try/finally` HEAD 복원, 사전 백업 byte 비교, clean 확인 순서를 동일하게 적용했다. 세 변이는 모두 exit0으로 생존했다. B1 보강 후에는 동일 변이가 exit1로 바뀌어야 한다.

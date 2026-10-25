# P09-04 최종 얼굴 주석·단서 진단·채택 판정 독립검증

## 대상 메타데이터

- 날짜: 2026-10-25
- 요청자: 소유자(entangelk), 메인 세션 경유
- 검증자: Claude Opus 5.5 (독립 검증 서브에이전트, 구현에 관여하지 않음)
- 대상: P09-04 마지막 슬라이스. 커밋 `beb2be2`(소유자 확인 수령·요소→얼굴 변환·최종 주석 고정), `2e19c3b`(CPU preflight 기록), `4e5af55`(GPU 진단 결과·채택 판정). 실행기 경계 코드는 `729ae98`에서 들어왔으며 이번 범위에 포함했다.
- 정본 규격: `configs/p09_r1_diagnostic.yaml`(sha256 `a73d5b42…`), `experiments/p09_leakage_repair/r1/diagnostic/README.md`, `preregistration.json`(sha256 `2c33634f…`), `owner_review.md`, P08 선례 `experiments/p08_anonymized/diagnostic/README.md:68-72`·`face_review_lock.json`.
- 작업 원천: `main` HEAD `4e5af55`, 검증 시작 시 작업 트리 clean.

## 범위

1. 최종 얼굴 주석 정합성: 소유자 원본→변환, pending/reused/owner 집합, merge 결과, lock hash, P08 선례와의 일관성, 사전등록 확인 범위, 예측 전 커밋 순서.
2. 진단 결과 재계산: 예측 CSV hash·ID 집합·수, 개입 manifest 일치, 2×2 지표, 다섯 관문(Wilson/Newcombe, image 단위 paired bootstrap), AUC 관문, adopt 판정, calibration·checkpoint 계보.
3. 실행기 경계: `scripts/p09_diagnostic.py`, `scripts/p08_diagnostic.py`, `src/diagnostic.py`, `scripts/p09_face_review.py`와 테스트, mutation testing.

GPU 재실행은 하지 않았다. 모든 수치는 저장된 예측 CSV에서 재계산했다.

## 방법

- 주석 검사: 구현 코드를 import하지 않는 독립 스크립트 `docs/verifications/2026-10-25/p09_04_annotation_check.py`. 변환 규칙(요소 0~1→0, 2~4→1)을 보임·남은 값 각각에 적용해 `face_review_owner_new.csv`와 대조하고, P08 `face_review_owner_features.csv`→`face_review_owner.csv`에도 같은 규칙을 적용했다. owner 우선·agent 나머지 merge를 다시 만들어 `face_review.csv`와 비교했다.
- 소유자 확인 범위 재도출: face cache(`experiments/p08_anonymized/face_boxes.csv`)의 검출 수와 agent 주석에서 불일치 전수, 나머지의 `random.Random(20261013)` shuffle 앞 ceil(20%), `visual_review_new.csv`의 `owner_extra_check` 중 최소 목록 밖 항목을 다시 계산했다(인라인 python, 아래 재현 절 참고).
- hash: `sha256sum`으로 `face_review_lock.json`·`owner_review_lock.json`·`preregistration.json`·`execution.json`·`result.json.prediction_sha256`의 모든 값을 재계산 대조했다. checkpoint 두 개(`/mnt/h/tracepector/checkpoints/{baseline,leakage_repair/r1}/best.pt`)와 old/new metadata도 직접 hash했다.
- 진단 재계산: 독립 스크립트 `docs/verifications/2026-10-25/p09_04_recompute.py`(프로젝트 모듈 import 없음). sigmoid(logit/T), p≥threshold→REAL 예측, 자체 구현 Mann-Whitney AUC·AP·accuracy/precision/recall/F1·NLL·Brier·ECE(10 bin), Wilson(z=1.959963984540054), Newcombe method 10, `numpy.random.Generator(PCG64(20261013)).integers(0,n,(20000,n))` 후 linear percentile 2.5/97.5. ID 순서 의존성을 보려고 ID 순서를 5가지로 섞은 뒤 같은 seed로 상한을 다시 계산했다. 주석 민감도로 agent 주석만 쓴 얼굴 상태 관문도 계산했다.
- 테스트: `tests/test_p09_diagnostic_runner.py`, `tests/test_p09_face_review.py`, `tests/test_p08_diagnostic_runner.py`, `tests/test_p08_diagnostic.py`를 읽고 실행했다. 전체 suite는 1회 실행했다.
- mutation: `git status --short` 빈 상태에서 10개 변이를 하나씩 적용→해당 cell 실행→`git checkout -- <file>`→`git status --short` 빈 상태 확인.

## 발견 사항

### 1. 최종 얼굴 주석

- 소유자 원본 `face_review_owner_new_features.csv` 180행, ID 중복 없음, 값 0~4, 남은≤보임. 분포는 (4,0)102·(3,3)25·(0,0)24·(2,2)13·(1,1)6·(4,4)5·(3,0)4·(2,0)1이다. 변환 결과는 `face_review_owner_new.csv`와 180행 모두 일치하고 행 순서도 같다(불일치 0).
- `face_review_owner_pending.csv` 180 ID와 집합·순서 모두 일치한다. `face_review_owner_reused.csv` 111행과 교집합 0, 합집합이 `face_review_owner.csv` 291행과 값까지 같다. reused 111행은 P08 `face_review_owner.csv`(이미 변환된 얼굴 수)와 값이 모두 같다.
- `face_review_owner_check.csv` 291 ID = owner ID. 사유는 flagged 119·random 167·visual_ambiguity 5다. 재도출 결과 불일치 119, 나머지 833의 ceil(20%)=167, 시각 경계 9장 중 최소 목록 밖 5장이 저장 목록과 정확히 같다. 사전등록 범위(`configs/p09_r1_diagnostic.yaml:64-65`, README:11)를 줄이거나 바꾸지 않았다.
- `face_review.csv` 952행, ID 순서 = template, ID 집합 = agent. owner 291행 우선·나머지 agent로 다시 만든 결과와 불일치 0이다. 전부 confirmed=1이고 0≤남은≤보임을 만족한다. agent 대비 변경은 정확히 14행이다(gen_000006·gen_000064는 다중 얼굴→1/0, 나머지 12행은 0/0→1/1). 최종 상태는 익명화 601 / 얼굴 없음 224 / 남은 얼굴 127이다.
- 시각 표본 확인: `reports/errors/review/p09_leakage_repair/r1/face_review/pairs/gen_000064.jpg`는 주 인물 얼굴이 가려졌고 배경 인물은 작고 불명확하다. 소유자 1/0과 맞는다. `gen_000173.jpg`는 프레임 상단에서 잘린 얼굴의 코·입이 익명화 후에도 그대로 보여 1/1과 맞는다.
- P08 선례: P08 301행에 같은 규칙을 적용하면 `face_review_owner.csv`와 불일치 0이다. P09 변환은 P08 방식(`README.md:70`)과 같다.
- lock: `face_review_lock.json`의 sha256 9개와 `owner_review_lock.json` inputs_sha256 14개(config·training input_lock·P08 owner·visual_review_new·prior·template·preregistration·`scripts/p09_face_review.py`·`scripts/p08_face_review.html`·65MiB 페이지·agent·check·reused·pending)를 모두 재계산했고 전부 일치한다. `execution.json`의 annotation_lock_sha256 `8da064d8…`도 현재 lock 파일과 같다.
- 예측 전 커밋: `face_review.csv`·`face_review_lock.json`은 `beb2be2`(10:41:30 KST)에서만 바뀌었다. 예측 CSV는 `4e5af55`에서 처음 추가됐고 mtime은 11:11~11:14 KST, `execution.json`은 11:10 KST다. `execution.json.annotation_commit`=`beb2be2`. 실행기 `committed_annotations`(`scripts/p08_diagnostic.py:42-50`)는 HEAD 바이트 일치를 강제한다.
- 주석 민감도: agent 주석만 쓰면 상태 수가 599/236/117이 되고 세 Newcombe 구간이 [-2.42,1.59]·[-9.44,-0.75]·[-9.53,-0.20]%p로 여전히 ±10%p 안이다. 변경 14행 중 FP는 없다. 따라서 관문 결론은 14행 변환에 의존하지 않는다.

### 2. 진단 결과 재계산

- 예측 CSV 8개 sha256이 `result.json.prediction_sha256`과 모두 일치한다. 행 수는 baseline_original/anonymized·candidate_original 각 2,220, candidate_anonymized 2,327, real_shape/size 각 107, gen_gray/restore 각 161이다. ID 중복 없음, logit 모두 유한값이다.
- ID 집합: 2,220 = val 820 + test 800 + test_unseen 600. candidate_anonymized = 평가 2,220 ∪ REAL 개입 107(교집합 0). real_* = `real_interventions.csv` 107 ID(107행·107장, 전부 train REAL). gen_* = `gen_interventions.csv` 161 ID(전부 test/test_unseen GEN, generator·split이 metadata와 일치). 생성기별 적격 수 84/62/382/74/1과 선택 40/40/40/40/1은 `preregistration.json`과 같고, 표본은 적격 집합의 부분집합이다.
- 2×2 지표(baseline/candidate × original/anonymized × val/standard/unseen 12셀): ROC-AUC·accuracy·precision·recall·F1·NLL·Brier·ECE 차이는 모두 1e-9 미만이다. PR-AUC만 최대 6.6e-6 차이가 있는데, 동률 처리 방식이 다른 AP 정의 때문이며 관문과 무관하다. 각 모델은 자기 calibration의 T/threshold를 쓴다(baseline T 0.79848·thr 0.69670, candidate T 0.77704·thr 0.23513).
- 얼굴 상태 FP: 익명화 8/601, 얼굴 없음 3/224, 남은 얼굴 6/127. 저장값과 같다. Wilson 구간 차이는 1e-15 수준이다. Newcombe 구간은 [-2.615,1.541]·[-8.634,-0.551]·[-8.660,0.196]%p로 저장값과 같고 모두 ±10%p 안이라 pass다. 각 상태가 20장 이상이다. 익명화-남은 얼굴 구간은 0을 포함하지 않는다(남은 얼굴의 FP가 더 높음). 허용폭 안이라 통과지만 차이 0의 근거는 아니다. 구현자 기록도 같은 주의를 적었다.
- 개입 4종(재계산 = 저장값, bootstrap 구간 차이 ≤4e-15):

| 관문 | n | 평균 절대 변화 | 95% 구간 | 맞음→틀림 | 틀림→맞음 | Wilson 상한 | 판정 |
|---|---:|---:|---|---:|---:|---:|---|
| real_shape | 107 | 0.112 | [0.040, 0.210] | 0 | 0 | 3.47% | pass |
| real_size | 107 | 1.704 | [0.484, 3.323] | 0 | 0 | 3.47% | pass |
| gen_gray | 161 | 0.097 | [0.012, 0.244] | 0 | 0 | 2.33% | pass |
| gen_restore | 161 | 0.353 | [0.012, 1.016] | 0 | 1 | 2.33% | pass |

  ID 순서를 5가지로 바꿔 같은 seed로 다시 뽑아도 상한 최대값은 0.209/3.352/0.250/1.022로 5점보다 훨씬 작다. 결론은 ID 정렬 선택에 민감하지 않다. real_size의 signed 변화는 최소 -57.6·최대 +48.1점인 개별 이미지가 있으나 판정 전환은 0건이다.
- AUC 관문: candidate 익명화 Test A 0.9996131798(≥0.9), Test B 0.9994940476(≥0.8). 다섯 관문과 AUC 모두 통과해 `adopt=true`이며 `result.json.adoption`과 같다.
- 계보: candidate calibration sha256 `ce212d0b…`=`execution.json`. 이 calibration의 checkpoint_sha256 `8fcd4859…`은 실제 `best.pt` hash, `training/result.json.artifact_sha256`(파일 sha `305b0741…`=execution)와 같다. metadata_sha256 `5a323684…`은 `data/versions/p09_r1/metadata.csv`와 같다. candidate checkpoint config의 metadata_csv는 `data/versions/p09_r1/metadata.csv`이고 익명화 binding이 있다. baseline calibration `eb9e6396…`(사전등록 inputs와 같음)의 checkpoint `151244…`은 실제 hash와 같고, fitting metadata `039cbdd1…`은 `data/metadata.csv`와 같다. calibration·training result 파일은 각각 `2238980`·`52a640a` 이후 변경되지 않았다. `execution.json.source_sha256` 9개는 현재 소스와 모두 일치한다.

### 3. 실행기 경계

- `scripts/p08_diagnostic.py:53-68`의 `load_artifacts`는 `729ae98` 이전 인라인 코드와 같은 검사(두 calibration metadata = 사전등록 metadata, checkpoint config metadata hash, candidate 익명화 binding)를 유지한다. 차이는 `del saved` 한 줄뿐이다. 기본 `preflight`/`run`은 loader를 주입하지 않으면 이 방어를 그대로 쓴다(`:100`, `:263`). P08 기본 방어는 약화되지 않았다.
- `scripts/p09_diagnostic.py:13-50`은 baseline/candidate 모두 `checkpoint config metadata hash == calibration metadata_sha256`(:25)을 요구한다. candidate에는 사전등록 metadata(:29), 익명화 binding(:31), 고정 학습 결과 hash(:33)를 추가로 요구한다. baseline에는 ID 집합·중복·열 동일성과, split·REAL look_group 이외 모든 열의 불변성(:36-48)을 요구한다. 실제 old/new metadata 차이는 REAL look_group 3,000·REAL split 1,359·GEN split 1,105뿐이므로 실행이 통과한 것과 맞다.
- 테스트: focused 42 passed, 전체 287 passed·1 skipped.
- mutation(전부 clean tree에서 시작, 매번 `git checkout -- <file>` 후 `git status --short` 빈 것 확인):

| # | 변이 | 실행 cell | 결과 |
|---|---|---|---|
| M1 | p09 :29-30 candidate calibration metadata 검사 제거 | `test_artifact_loader_rejects_mixed_lineage[candidate_metadata]` | **생존**(exit 0). 변조한 checkpoint hash가 :33 training result 검사에 걸려 흡수됨 |
| M2 | p09 :33 training result 검사 무력화 | `[candidate_checkpoint]` | 실패(exit 1) |
| M3 | p09 :31 익명화 binding 검사 무력화 | `[candidate_binding]` | 실패 |
| M4 | p09 :47 불변 열 비교 무력화 | `[baseline_immutable]` | 실패 |
| M5 | p09 :25 fitting metadata hash 검사 무력화 | `[baseline_metadata]` | 실패 |
| M6 | p09 :38 baseline ID 집합 검사 무력화 | 파라미터 전체 | 실패 |
| M7 | p08 :59-60 기본 metadata hash 방어 제거 | `test_cross_split_evaluation_keeps_original_bindings` | 실패 |
| M8 | p09 :45 예외를 category까지 확대(과소 엄격) | `[baseline_immutable]` | 실패 |
| M9 | p09 :45 REAL look_group 예외 삭제(과잉 엄격) | `tests/test_p09_diagnostic_runner.py` 전체 | **생존**(10 passed) |
| M10 | p09_face_review :33 `u≤v` 검사 제거 | `tests/test_p09_face_review.py` | 실패 |

## 문제·위험

### 차단(계약 의무)

- **B1. REAL look_group 변경 허용의 과잉 엄격 guard 누락.** README:23은 P09 실행기가 baseline의 옛 학습·보정 계보를 보존하면서 새 평가 cohort를 분리해 평가하라고 요구한다. P09 resplit의 실제 변화는 REAL look_group 3,000행 전부와 split이다. 그런데 회귀 fixture(`tests/test_p09_diagnostic_runner.py:27-31`)는 split만 바꾸고 REAL look_group은 바꾸지 않는다. 그래서 `scripts/p09_diagnostic.py:45`에서 look_group 예외를 지워도(M9) 테스트가 전부 통과한다. 이 변이는 실제 P09 데이터에서는 preflight를 거부하게 만들지만 회귀 테스트는 이를 잡지 못한다. 또한 baseline 비교에서 바뀌어도 되는 열(split, REAL look_group)은 README에 적혀 있지 않고 코드에서만 정해진다. 재현: `scripts/p09_diagnostic.py:45`를 `if key == 'split':`로 바꾸고 `docker compose --profile training run --rm -T -e CUDA_VISIBLE_DEVICES= train python -m pytest tests/test_p09_diagnostic_runner.py -q`를 실행하면 10 passed다. 해소 조건은 두 가지다. fixture에서 REAL look_group도 바꿔 정상 교차 cohort가 허용됨을 고정하고, 가능하면 GEN look_group 변경은 거부됨을 고정한다. README의 실행·계보 경계에 허용 열 목록을 명시한다. 진단 수치와 adopt 판정에는 영향이 없다. 실제 실행이 이 경로를 통과했고 결과를 독립 재계산으로 확인했다.

### 비차단 보강 권고

- **H1. candidate calibration metadata 검사(:29-30)를 단독으로 고정하는 cell이 없다(M1 생존).** `[candidate_metadata]` damage가 checkpoint를 다시 저장해 hash가 바뀌므로 :33이 먼저 잡는다. 실제 계보에서는 checkpoint config metadata 경로가 사전등록 metadata 경로와 같아서, :25와 preflight 입력 hash 검사(`scripts/p08_diagnostic.py:77-79`)로 :29가 사실상 함의된다. 위험은 낮다. training result도 새 hash로 맞춘 damage cell을 추가하면 :29를 단독으로 고정할 수 있다. 재현: :29-30을 `pass`로 바꾸고 해당 cell을 실행하면 1 passed다.
- **H2. 요소→얼굴 변환이 코드에 없다.** `scripts/p09_face_review.py:123`의 merge는 lock에 `owner_input_semantics='face_count'`를 쓰고 원본 features hash를 기록하지 않는다. 커밋된 `face_review_lock.json:2`의 `visible_facial_features_not_face_count`와 `face_review_owner_new_features.csv` hash는 merge 뒤 수작업으로 추가된 것이다(작업 기록에 임시 변환 파일 삭제 명시). 이번 변환은 데이터에서 완전히 재현되고 P08 선례와 같아 결과 정합성에는 문제가 없다. 다음 cohort에서 같은 일이 반복되면 변환과 lock 기록을 merge 옵션과 테스트로 고정하는 것이 좋다. `owner_review_lock.json:8`의 `face_count`는 준비 시점의 의도로 남아 있어 최종 lock과 의미 표기가 다르다. 기록 보존상 문제는 아니다.
- **H3. 검토 페이지의 입력 단위가 지시문과 다르다.** `scripts/p09_face_review.py:82`는 "얼굴은 1개, 요소 개수를 입력하지 않음"이라고 안내하지만 선택지는 `scripts/p08_face_review.html:44`의 0~4라서, 소유자가 요소 단위로 입력했다. 구현자도 같은 문제를 이미 기록했다(작업 기록 "발견한 문제").
- **H4. 해석상 주의(결함 아님).** 익명화-남은 얼굴 FP 차이 구간 [-8.63,-0.55]%p는 0을 포함하지 않는다. gen_000064 같은 다중 얼굴 이미지는 소유자 주 인물 기준으로 1/0이 되어 배경 얼굴이 남은 얼굴로 집계되지 않는다(P08과 같은 정책). 채택 보고에서 "남은 얼굴 단서 없음"으로 단정하지 않아야 한다.

## 판정

**조건부 합격** — B1(REAL look_group 교차 cohort 허용의 과잉 엄격 회귀 cell과 README의 허용 열 명시)을 닫아야 한다.

- 최종 얼굴 주석(변환·merge·범위·lock·커밋 순서)은 원자료에서 독립 재도출한 결과와 완전히 일치한다.
- 다섯 관문·AUC·adopt=true는 구현과 독립된 코드로 저장 예측에서 재계산해 같은 값을 얻었다. agent 주석 민감도와 ID 순서 민감도에서도 결론이 바뀌지 않는다.
- 계보 hash(checkpoint·calibration·training result·metadata·소스)가 모두 일치한다. P08 기본 hash 방어는 약화되지 않았다.
- 조건 B1은 테스트·계약 문구 보강이며 진단 수치·채택 판정의 유효성에는 영향을 주지 않는다.

## 미결 사항

- primary 교체(`configs/primary.yaml`)는 하지 않았다. B1을 닫은 뒤 사전 규칙과 소유자 확인에 따라 구현자가 진행한다.
- 미검토 946,311쌍·GEN 계보 공유·개발 평가 한계와 Q5는 그대로 유지된다(이번 검증 범위 밖).

## 재현

```bash
cd /mnt/f/devel/Tracepecter
V=$PWD/docs/verifications/2026-10-25
# 주석 변환·merge·범위
docker compose run --rm -T -v $V:/v:ro dev python -I /v/p09_04_annotation_check.py
# 2×2 지표·다섯 관문·AUC·adopt·민감도
docker compose run --rm -T -v $V:/v:ro dev python -I /v/p09_04_recompute.py
# 소유자 확인 범위 재도출
python3 -c "import csv,json,random,math;D='experiments/p09_leakage_repair/r1/diagnostic/';c={r['image_id']:len(json.loads(r['boxes'])) for r in csv.DictReader(open('experiments/p08_anonymized/face_boxes.csv'))};a={r['image_id']:(int(r['visible_faces']),int(r['uncovered_visible_faces'])) for r in csv.DictReader(open(D+'face_review_agent.csv'))};ids=[r['image_id'] for r in csv.DictReader(open(D+'face_review_template.csv'))];f=sorted(i for i in ids if a[i][0]!=c[i] or a[i][1]>0);r=sorted(set(ids)-set(f));random.Random(20261013).shuffle(r);print(len(f),len(r),math.ceil(.2*len(r)))"
# hash
(cd experiments/p09_leakage_repair/r1/diagnostic && sha256sum *.csv *.json)
sha256sum /mnt/h/tracepector/checkpoints/{baseline,leakage_repair/r1}/best.pt data/metadata.csv data/versions/p09_r1/metadata.csv
# 테스트
docker compose --profile training run --rm -T -e CUDA_VISIBLE_DEVICES= train python -m pytest tests/test_p09_diagnostic_runner.py tests/test_p09_face_review.py tests/test_p08_diagnostic_runner.py tests/test_p08_diagnostic.py -q -p no:cacheprovider; echo exit=$?
docker compose --profile training run --rm -T -e CUDA_VISIBLE_DEVICES= train python -m pytest -q -p no:cacheprovider; echo exit=$?
# B1 재현(clean tree에서, 끝나면 git checkout -- scripts/p09_diagnostic.py)
sed -i "s/if key == 'split' or (key == 'look_group' and source\['source_type'\] == 'real'):/if key == 'split':/" scripts/p09_diagnostic.py
docker compose --profile training run --rm -T -e CUDA_VISIBLE_DEVICES= train python -m pytest tests/test_p09_diagnostic_runner.py -q; echo exit=$?
git checkout -- scripts/p09_diagnostic.py && git status --short
```

**합격** — 라운드 2에서 B1~B3·H1~H2 해결, 남은 차단·비차단 지적 없음.

# P08-03 진단·채택 규칙 사전등록 독립검증

> 아래 최초 검증은 라운드 1(`77da668`)의 역사적 기록이다. 현재 판정·남은 작업은 문서 끝의 라운드 2(`b0b1b84`)를 따른다.

## 대상·범위

- 일자: 2026-10-13. 요청자: 프로젝트 소유자. 검증자: Codex 독립검증 서브에이전트 1명.
- 대상: main `77da668701b17580e61d782ea6e7cf6fb766d8ab`의 `configs/anonymized_diagnostic.yaml`, `scripts/p08_preregister.py`, `tests/test_p08_preregister.py`, `experiments/p08_anonymized/diagnostic/` 및 연결 기록.
- 정본: `docs/sot.md` §2~3의 소유권·precedence, Resolved DB-06, `docs/project.md` v1.4 §15·20·22, `docs/plan/phase_8_face_anonymization.md` P08-03·계약·완료 조건. 작업 규칙은 `AGENTS.md`, `docs/guides/verification.md`, `docs/guides/records-and-handoff.md`.
- 구현자 설명·작업 이력을 읽기 전에 위 정본에서 경계 행렬을 만들었다. 작업 기록은 마지막에 실행 상태 일치만 확인했다.
- 결과 없는 사전등록을 검사했다. 진단 예측·실제 관문 실행기는 P08-06 범위이므로 아직 구현되지 않은 runner의 실행 테스트를 요구하지 않았다. 새 모델/GPU 추론·학습·기존 실험 변경을 하지 않았다.

## 방법·실행 결과

1. 정본부터 a/b/c/d·2×2·통계·채택 분기의 선언과 허용/거부 경계를 대조했다.
2. `docker compose run --rm -T dev python -m pytest -q tests/test_p08_preregister.py`: **11 passed (0.62s)**.
3. 아래 재현 코드로 생성기를 호출하지 않고 입력 SHA-256, 대상 선정·기하 투영, CSV LF 바이트를 독립 계산했다. config + 입력 7개 + CSV 3개의 바이트/해시가 일치했다. REAL 150원/149장, GEN 개입 162장, 얼굴 확인 952장, 목표 비율 0.1631602984208327이었다.
4. `docker compose run --rm -T dev python -m scripts.p08_preregister`: 기존 등록과 동일 결과, `git status --short` 빈 출력. CLI 재생성은 동일 바이트였다.
5. 변이 전 `git status --short` 빈 출력과 HEAD를 확인했다. 모든 변이 뒤 `git checkout -- <변이 파일>`, 원래 바이트와 직접 비교, `git status --short` 빈 출력을 확인했다. 보고서 작성은 모든 복구 후 시작했다.
6. 복구 후 `docker compose run --rm -T dev python -m pytest -q tests/test_p08_preregister.py tests/test_anonymize.py`: **30 passed (3.92s)**. 공유 `validate_boxes`/hash helper까지 포함한 관련 범위다. 모델 실행을 포함한 전체 학습·평가 테스트는 이 슬라이스에 필요하지 않아 실행하지 않았다.
7. `git diff --check`: 성공. README·계획·SoT·HANDOFF·인덱스·CHANGELOG·작업 기록의 관련 P08-03 링크/상태가 사전등록·독립검증 대기로 일치함을 확인했다.

## 경계 행렬·발견

| 표면 | 정본 계약과 관찰 | 회귀 셀/판정 |
| --- | --- | --- |
| 2×2 | config:18~28의 baseline/candidate × original/anonymized × val/standard/unseen. README:17~21은 모델별 calibration 고정, Test REAL 재사용, offline 원본 bypass를 명시한다. §15/22와 적용 범위가 구분돼 있다. | `test_preregistered_config_covers_all_adoption_gates`는 조합 이름만 잠근다. 재사용·calibration·metric/grouping 값은 B2. |
| (a) 집중 | config:80~95, README:28~29·47~49가 검출 수 대체 금지·missed 우선·세 쌍 Newcombe Wilson·20장/상태·±10%p·미확정을 고정한다. Newcombe 식은 독립 두 집단 Wilson 차이 방식으로 일관된다. | 해당 선언값 named config guard 없음: B2. 실제 주석·FP 계산은 P08-06. |
| (b) 원 모양 | config:53~57와 README:33~35는 기존 원을 포함하는 원/동일 중심·guard를 선언한다. 기존 픽셀을 흰색으로 덧칠하여 복원하지 않는 의도는 맞다. 정상 익명화 reference의 별개 YuNet 마스크 보존은 누락된다. | construction base 결함 B3. 기하·순서 guard 공백 B2. |
| (c) 회색/복원 | config:64~72, README:38~39의 모든 cached face gray/원본 GEN 대조는 계획 c와 일치한다. 합성 흰 원 재적용 금지는 README:33·config:73에 있다. | 모든 cached face·gray fill·재적용 금지 선언 guard 공백 B2. |
| (d) 원 크기 | config:58~63·74~78, README:36~37의 max 규칙·고정 GEN 중앙값·축소/REAL 복원 금지는 계획 d와 일치한다. 크기와 모양을 별개 reference 대비 진단한다. | 실제 목표 재현은 성공. construction base 결함 B3, 선언 guard 공백 B2. |
| 개입 구간 | config:98~118: image 단위·80장·절대 paired shift 평균·20,000 percentile bootstrap·상한 5점, 전체 selected denominator의 correct→incorrect Wilson 상한 5%. 역방향 전환 상쇄 금지. | bootstrap 문구 충돌 B1. 허용 경계·통계·결측·표본 부족 선언 guard 공백 B2. |
| 채택 | config:120~131·README:60: candidate anonymized AUC ≥0.90/0.80와 5개 관문 모두 통과, 미확정/실패 유지, P07 대기/P08 재시도, 재실패 소유자 문의, holdout 비관문. 계획·§20과 일치한다. | AUC/게이트 이름/all_required/indeterminate는 기존 셀. 실패·pass·non_adoption·retry_failed·holdout 값 guard 공백 B2. |
| 계보·표본 | script:35~81은 ID 중복/집합 동등·cache 파라미터·좌표·REAL confirmed/계보·양수 목표를 검사한다. 실제 원 기하와 review 투영/GEN 순차 shuffle 선정은 독립 재현 일치. | 기본 정상·잘못된 source 셀 존재. 복수 generator·40장 초과·다원 이미지의 계약 회귀가 없음: B2. cache/review 중복, cache ID 누락/추가, REAL label/image_id 불일치 등 실행 거부 분기도 named 셀 보강 필요. |
| 불변성·결과 없음 | script:88~103은 raw input/config 및 manifest 해시, 모든 existing output 확인 후 기록. script:31~104에 모델 호출 없음. | `test_registration_is_blind_deterministic_and_preserves_empty_faces`, `test_registration_rejects_changed_inputs_without_partial_overwrite` 성공, 변이에서도 해당 보호가 재실패했다. |
| 복잡도 | script:35~69·73~78은 CSV 전체 메모리 저장 및 정렬 O(n log n), generator별 GEN 반복 스캔 O(g·n). generator는 현재 5개라 본 실험에서 작은 고정 횟수다. | 불필요한 외부 호출·추론·unbounded retry 없음. 단일 사전등록 생성기로 범위가 좁고 복잡도는 허용 가능하다. |

## 차단 지적

### B1 — 복원추출 bootstrap와 '동일 이미지 한 번만 재추출' 충돌

`experiments/p08_anonymized/diagnostic/README.md:53`은 같은 이미지는 한 번만 재추출한다고 명시한다. `configs/anonymized_diagnostic.yaml:104`의 image cluster percentile bootstrap를 n개 이미지의 비복원추출로 구현하면 매 resample이 같은 n개 값의 순열이며 평균·구간이 퇴화한다. 이미지별 예측 한 번/원별 독립표본 금지와 bootstrap 반복 추출을 구분해야 한다. n개 이미지 인덱스를 **복원추출하고 반복 인덱스를 허용**, 같은 이미지의 원들은 공동 편집·한 예측으로 고정하는 계약으로 명확화해야 한다. 이 충돌은 통계 판정 자체를 바꾸므로 차단이다.

### B2 — 선언 계약·선정 경계의 회귀 행렬 공백

`tests/test_p08_preregister.py:103~113`은 2×2 이름·cue 모델·관문 목록·AUC·미확정만 assertion한다. 위 경계 행렬의 나머지 고정값과 실패 후 행동은 테스트가 잠그지 않는다. 또한 fixture(`tests/test_p08_preregister.py:32~38`)는 GEN 검출 1장/생성기 1개·REAL 원 1개라 cap/seed/generator 순서·부족 생성기 전수 포함·다원 이미지 집계 결함을 탐지하지 못한다.

실제로 cap을 `ids[:1]`로 잘못 줄여도 전체 **11 passed**, score `max_upper: 5.0`을 **50.0**으로 바꾸어도 전체 **11 passed**였다. 다른 보호층에 흡수된 사례가 아니다. 기존 시험 표본이 cap보다 작고 고정 허용폭 assertion이 없기 때문이다. 사전등록 config는 이 슬라이스의 공개 계약이므로 기능별 named 선언 guard와 >40/복수 generator/부족 generator/다원 이미지 fixture가 필요하다. 거부하는 ID·REAL 계보 분기도 정상 source 허용과 함께 잠가야 한다. runner 행동 테스트는 후속 범위로 남겨도 된다.

### B3 — REAL 개입이 원래 원 외 얼굴 마스크를 풀 수 있음

`experiments/p08_anonymized/diagnostic/README.md:33`은 모든 variant를 원본 RGB에서 만들고 resize/정규화만 하도록 정한다. REAL shape/size는 :35~36에서 confirmed 기존 원만 덧칠한다. 따라서 정상 익명화 reference에서 YuNet이 추가로 가린 **다른 위치의 얼굴**을 REAL variant에서는 원본으로 되돌린다.

실제 선택 표본 `experiments/p08_anonymized/diagnostic/real_interventions.csv:25`의 image_id `1287673`, candidate `0491_0` 원 중심은 (367.777,360.692), major 50.365다. `experiments/p08_anonymized/face_boxes.csv:170`은 별개 위치 bbox (202.9565,302.3285,48.4255,61.7307)를 가진다. 캐시 합성 원 중심은 약 (227.17,333.19)이므로 shape 원과 겹치지 않는다. 이 얼굴 복원으로 원 모양/크기 효과에 얼굴 정보 효과가 섞인다.

REAL shape/size variant는 **정상 익명화 RGB를 기반**으로 confirmed 원만 추가 overlay하여 모든 cache 마스크를 보존하도록 고정하고, GEN gray/restore만 원본 RGB 기반으로 구분해야 한다. config에도 construction base를 명시하면 후속 runner가 모순 없이 구현할 수 있다.

## 비차단 보강 후보

- **H1 — bootstrap 수치 재현 규약**: config:101~107과 README:53은 seed·횟수·percentile 구간을 고정하지만 bootstrap RNG 구현과 percentile 보간법은 명시하지 않는다. P08-06의 반복 재현을 쉽게 하려면 `random.Random` 또는 특정 NumPy generator, n개 인덱스 생성 순서, percentile interpolation 방법을 함께 선언해 두는 것이 좋다. 현 요구는 RNG 브랜드/보간법을 열거하지 않아 이 후보 자체는 차단이 아니다.
- **H2 — REAL 기하 입력 유효성**: script:66은 width/cx/cy/major/minor/angle을 문자열 그대로 투영한다. 현재 고정 artifact의 기하는 독립 투영과 일치하지만 새 등록을 위해 invalid numeric geometry를 수용할 가능성은 있다. width/축 양수·모든 값 유한·major≥minor를 검사하고 정상/비정상 셀을 추가하면 수동 손상된 측정 파일을 일찍 막을 수 있다. 현재 계획은 이 거부 규칙을 열거하지 않으므로 비차단이다.

## 변이 증거

pre-flight: HEAD `77da668`, `git status --short` 빈 출력. script SHA-256 `bd2282b1f92cfd56c8e0158d665e5a9f48af8931ea5e9de85fd2d6afd1ebc936`, config SHA-256 `b198b8a9df0c40f0e61d2d36298cbba0aa1590a4c09d9fce3e1c9f78fb3f5624`.

각 행은 `docker compose run --rm -T dev python -m pytest -q <셀>`을 실행했다. 전체 파일 셀은 `tests/test_p08_preregister.py`다.

| 변이 diff·원래 위치 | 실행 셀 | 관찰 |
| --- | --- | --- |
| script:99의 `if path.exists() and path.read_bytes() != data:` → `if False:` | `tests/test_p08_preregister.py::test_registration_rejects_changed_inputs_without_partial_overwrite` | 1 failed (0.45s), 변경 입력 거부가 사라져 재실패 |
| script:69 뒤 GEN에서 cache boxes 빈 이미지 제거 | `tests/test_p08_preregister.py::test_registration_is_blind_deterministic_and_preserves_empty_faces` | 1 failed (0.42s), face_review_images 2→1 |
| script:76의 설정 cap → `ids[:1]` | 전체 파일 | 11 passed (0.72s), B2 선정 과잉 제한 가드 공백 |
| config:107의 `max_upper: 5.0` → `max_upper: 50.0` | 전체 파일 | 11 passed (0.63s), B2 허용폭 가드 공백 |
| script:46의 detector hash `!=` → `==` | `tests/test_p08_preregister.py::test_registration_is_blind_deterministic_and_preserves_empty_faces` | 1 failed (0.44s), 정상 캐시 오거부 검출 |

각 복구 후 원래 바이트와 동일했고 clean이었다. 마지막 복구 후 관련 30개 회귀가 통과했다. 구현·테스트의 영구 수정은 없다.

## 판정·남은 작업

테스트 green과 실제 사전등록 재현은 확인했지만 B1~B3 때문에 P08-03을 닫을 수 없다. root 구현자가 위 지적을 보강한 뒤 같은 독립검증자에게 추적검증을 요청한다. H1·H2도 소유자 요청에 따라 보강 후보로 전달했다. 최종 합격 전 P08-04·P07 진행은 대기다. 이 기록만 커밋하며 다른 worker의 구현·기록은 수정하지 않는다.

## 재현

기본 실행은 방법 절의 pytest·CLI·diff 명령이다. 독립 artifact 재현은 다음 명령으로 실행했다(생성기 import 없음).

```bash
docker compose run --rm -T dev python - <<'PY'
import csv,io,json,hashlib,random,pathlib,yaml
def rows(path):return list(csv.DictReader(open(path,newline='')))
def digest(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def encode(fields,data):
 f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data);return f.getvalue().encode()
c=yaml.safe_load(open('configs/anonymized_diagnostic.yaml'));d=pathlib.Path(c['output_dir']);p=json.load(open(d/'preregistration.json'))
assert p['config_sha256']==digest('configs/anonymized_diagnostic.yaml')
assert p['inputs_sha256']=={k:digest(v) for k,v in c['inputs'].items()}
m=rows(c['inputs']['metadata']);cache={r['image_id']:json.loads(r['boxes']) for r in rows(c['inputs']['face_cache'])}
can={r['candidate_id']:r for r in rows(c['inputs']['real_candidates'])};real=[can[r['candidate_id']] for r in rows(c['inputs']['real_review']) if r['confirmed']=='1'];real.sort(key=lambda r:(r['image_id'],r['candidate_id']))
f=['candidate_id','image_id','width','cx','cy','major','minor','angle'];real=[{k:r[k] for k in f} for r in real]
gen=sorted([r for r in m if r['label']=='0' and r['split'] in ['test','test_unseen']],key=lambda r:r['image_id']);rng=random.Random(20261013);sel=[];cnt={}
for g in sorted(set(r['generator'] for r in gen)):
 ids=[r for r in gen if r['generator']==g and cache[r['image_id']]];rng.shuffle(ids);chosen=sorted(ids[:40],key=lambda r:r['image_id']);cnt[g]={'eligible':len(ids),'selected':len(chosen)};sel.extend({k:r[k] for k in ['image_id','generator','split']} for r in chosen)
expected={'real_interventions.csv':encode(f,real),'gen_interventions.csv':encode(['image_id','generator','split'],sel),'face_review_template.csv':encode(['image_id','visible_faces','uncovered_visible_faces','confirmed'],[dict(image_id=r['image_id'],visible_faces='',uncovered_visible_faces='',confirmed='') for r in gen])}
for name,value in expected.items():
 assert (d/name).read_bytes()==value
 assert p['manifests_sha256'][name]==hashlib.sha256(value).hexdigest()
assert p['gen_interventions_by_generator']==cnt
assert (len(real),len(set(r['image_id'] for r in real)),len(gen),len(sel))==(150,149,952,162)
assert p['size_target_diameter_over_width']==json.load(open(c['inputs']['measurement']))['synthetic']['selected_size']['synthetic_quartiles'][1]
print('Independent hashes/CSV bytes/selection/size target matched')
PY
```

## 라운드 2 — 보강 추적검증 (2026-10-13)

**합격** — 기존 B1~B3·H1~H2가 모두 해결됐고 새 차단·비차단 지적은 없다.

### 대상·방법

- 동일 소유자 요청·동일 독립검증자. 대상 main `b0b1b8490b46b256110301394d803d5bafa68ecb`, 시작 시 clean. 정본 범위는 라운드 1과 같다. `git show b0b1b84`로 변경 표면을 확인한 뒤 실제 config·README·코드·전체 focused 테스트를 대조했다.
- `docker compose run --rm -T dev python -m pytest -q tests/test_p08_preregister.py`: **31 passed (1.11s)**.
- 라운드 1 재현 절의 Python을 그대로 실행해 독립 재현: config/입력 SHA-256와 CSV 바이트·선정·목표가 모두 일치했다. 추가로 `git show 77da668:<artifact>` 원본 바이트와 비교해 CSV 3개가 byte 동일, preregistration의 입력 7개 해시·표본 수·목표·manifest 해시가 동일하고 **config_sha256만 변경**됐음을 확인했다. 이것은 선언 보강이며 모델 결과를 보고 표본/허용폭을 바꾼 변경이 아니다.
- 아래 변이 6종을 각각 focused cell로 실행했고 전부 재실패했다. 각 복구 후 원래 파일 바이트 직접 비교와 `git status --short` 빈 출력을 확인했다.
- 마지막 복구 후 `docker compose run --rm -T dev python -m pytest -q tests/test_p08_preregister.py tests/test_anonymize.py`: **50 passed (4.53s)**. `git diff --check` 성공·보고서 편집 전 clean.
- 복구 SHA-256: script `7ecb543d4cd1b5d6ab23221fe214f8e324fc0b4eaf89fad5b2625ea15ae94ce2`, config `b526e3923b95368f7ca99e2d44f87e723109009f21163e82934cab9a2ec605cb`.

### 지적별 종결·경계 행렬 갱신

| 지적 | 확인 근거·종결 |
| --- | --- |
| B1 bootstrap 충돌 | `experiments/p08_anonymized/diagnostic/README.md:55`이 n개 인덱스 복원추출·반복 허용·이미지당 한 예측·원별 독립 추출 금지를 구분한다. 구간이 퇴화하던 비복원 해석이 제거됐다. `test_intervention_equivalence_contract_uses_images_and_absolute_effects`가 config의 복원추출 선언을 잠근다. |
| B2 선언 계약 잠금 | `tests/test_p08_preregister.py:142`의 `test_face_state_and_annotation_contract`가 얼굴 상태·annotation·집중 구간을, :168의 construction 셀이 b/c/d·기하를, :188의 equivalence 셀이 이미지 단위/두 통계/상한/결측을, :206의 `test_sampling_and_non_adoption_contract`가 표본·Test REAL 재사용·calibration 고정·metric·실패 후 분기를 잠근다. 원래 채택 셀과 합쳐 라운드 1에서 지적한 사전등록 경계가 모두 추적된다. 실제 runner의 수치/입력 경로 행동은 P08-06에서 구현·검증한다. |
| B2 구현 표본·계보 | :227의 `test_stratified_cap_seed_undersized_generator_and_multi_disc_images`는 alpha45/beta43/gamma2/빈 검출1과 역순 metadata에서 고정 제외 ID를 검증한다. cap·순차 seed/generator 순서·부족분 전수·빈 검출 보존·다원 이미지 2원/1장·manifest hash를 잠근다. :257의 parametrized ID/REAL 계보 셀은 cache 중복/누락/추가·review 중복/image 불일치·label 불일치 거부를 추가한다. 선정 cap과 순서 변이가 직접 실패했다. |
| B3 REAL 기반 | README:35와 config 각 `construction_base`가 REAL은 normal_anonymized·GEN만 original로 일치한다. image_id 1287673의 별개 cache 마스크도 REAL 편집 기반에 남는다. construction 셀은 REAL 원복을 거부하고 GEN original을 허용한다. 원복 변이가 직접 실패했다. |
| H1 수치 재현 | README:55와 config score 블록이 `Generator(PCG64(seed))`, `integers(0,n,size=(20000,n))`, `percentile([2.5,97.5],method="linear")`를 고정한다. :188의 equivalence 셀이 RNG/index_draw/percentile_method를 잠근다. 현재 요구는 수치 규약 사전 고정이며 아직 예측 실행은 없다. |
| H2 기하 검사 | README:13에 선택 REAL의 유한 numeric/양수 width·두 축/major≥minor·음수 중심 허용/출력 전 거부가 명시됐다. script:66~70이 동일 검사하며 `minor>0`와 `major≥minor`로 major 양수도 보장한다. :281의 8개 거부 경우와 :294의 정상 음수 중심·등축 허용이 양방향으로 잠근다. 검사 제거/등축 오거부 변이가 직접 실패했다. |

### 라운드 2 변이 대응표

각 명령은 `docker compose run --rm -T dev python -m pytest -q tests/test_p08_preregister.py::<아래 함수명>`이다.

| 정확한 변이·위치 | 함수명 | 결과 |
| --- | --- | --- |
| script:81 설정 cap → `ids[:1]` | `test_stratified_cap_seed_undersized_generator_and_multi_disc_images` | 1 failed (0.41s). 라운드 1 생존 변이를 이제 검출 |
| script:78 generator `sorted(...)` → `sorted(..., reverse=True)` | `test_stratified_cap_seed_undersized_generator_and_multi_disc_images` | 1 failed (0.41s). RNG 소비 순서 변화로 golden 선정 불일치 검출 |
| config score `max_upper: 5.0` → `50.0` | `test_intervention_equivalence_contract_uses_images_and_absolute_effects` | 1 failed (0.41s). 라운드 1 생존 변이를 이제 검출 |
| config 첫 `construction_base: normal_anonymized` → `original` | `test_intervention_construction_preserves_other_real_face_masks` | 1 failed (0.43s). REAL shape의 원복 검출 |
| script:67~69 기하 조건 전체 → `if False:` | `test_registration_rejects_invalid_real_geometry` | 7 failed, 1 passed (0.70s). width0/major0/minor0/major8/cx NaN/cy inf/angle -inf가 재실패. width bad 셀은 앞선 float 변환이 계속 거부한 정상 이중 방어 |
| script:69의 major `<` minor → `<=` | `test_registration_allows_finite_clipped_disc_geometry` | 1 failed (0.44s). 정상 등축 오거부 검출 |

복구는 매 행 `git checkout -- <변이 파일>` 후 pre-mutation 바이트와 직접 비교·clean 확인으로 진행했다. 보고서는 모든 복구와 마지막 관련 suite 이후에만 수정했다.

### 현재 판정·남은 작업

사전등록 계약은 a/b/c/d·2×2·허용구간·채택/비채택·입력/표본 계보를 구체화했고 현재 scope의 회귀 셀과 독립 artifact 재현이 이를 잠근다. 보강 후 새 불필요한 외부 호출·unbounded retry·복잡도 증가가 없으며 유한 기하 검사 추가는 REAL 원 수에 선형이다. 이전 차단·비차단 모두 종결됐고 추가 지적은 없다.

P08-03 사전등록 슬라이스는 합격이다. 실제 얼굴 주석 완성/해시 고정, 새 모델 재학습·calibration·진단 실행·관문 판정은 후속 슬라이스에 남은 계획된 작업이며 이번 사전등록 합격이 실제 모델 채택을 뜻하지 않는다. 보고서만 커밋하며 구현·테스트의 영구 변경은 없다. P08-04 착수 상태 및 프로젝트 기록 종결은 root가 반영한다.

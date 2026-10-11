**합격** — P08-01 재개 변경 독립검증(전체 P08-01 완료 판정 제외).

# P08-01 중단 작업 재개 slice 독립검증

## 대상

- 날짜: 2026-10-11(KST).
- 요청자: 소유자(서브에이전트 독립검증 후 오늘 작업 마무리).
- 검증자: 구현에 참여하지 않은 Codex 서브에이전트 `verify_p08_resume`.
- 작업 출처: `main`, 기준 `dd680af`, working tree, uncommitted.
- 정본: `docs/project.md` v1.4 §15·§22, `docs/plan/phase_8_face_anonymization.md` P08-01 및 소유자 k=1.2 결정, `configs/anonymize_measure.yaml`(`dd680af` 사전등록), `configs/anonymize.yaml` 선택 규격. 사양 우선순위는 `docs/sot.md:33`을 확인했다.
- 절차: `docs/guides/verification.md`, `docs/guides/data-contracts.md`, `docs/guides/records-and-handoff.md`.

## 범위

현재 재개 slice는 선택 k 연결, 사전 크기 실패 보존, 재현율 최종 통과 오인 수정, Wilson 구간, sd35 보고 전용 구분, 소유자 검토 HTML·CSV, 원자료 계보·실측 수치·현재 인계 기록이다. **전체 P08-01 완료 판정은 범위 밖**이다. 소유자 육안 표시 및 사람 영역 보조 측정은 아직 이루어지지 않았다. P08-02 이후 전처리·학습·채택도 검증하지 않았다.

## 방법

### 실행 및 원자료

```bash
git status --short
git diff --check
docker compose run --rm -T dev python -m pytest \
  tests/test_p08_measure.py tests/test_face_mask_ci.py tests/test_p06_patterns.py -q
```

Python 표준 라이브러리로 다음을 별도로 재도출했다.

- `Path('configs/anonymize_measure.yaml').read_bytes()`와 `subprocess.check_output(['git','show','dd680af:configs/anonymize_measure.yaml'])`의 바이트 동일성.
- 측정 config·metadata의 SHA-256와 `report.json` provenance의 동일성. YuNet 파일 SHA-256는 아래 CPU 실측 컨테이너에서 다시 계산했다.
- metadata REAL train에서 `reports/errors/review_set.csv` ID를 제외해 정렬한 뒤 `random.Random(20261011).shuffle`한 순서와 `real_disc_order.json`의 일치. 확인 CSV의 후보 참조·중복·150개 확인, 마지막 확인 순위까지 후보 없는 pool에서 같은 seed의 `sample(pool,50)`과 missed 목록의 일치.
- GEN train·sd35 각 population의 ID 정렬 후 `random.Random(20261012).shuffle`한 표본과 `recall_sample.json`의 일치. 표시 CSV가 각 표본의 prefix와 일치함을 확인했다.
- 표시 CSV·검출 CSV를 ID로 결합하여 train 양성 97/검출 86, sd35 양성 71/검출 61을 재계산했다.
- train의 표시/검출 불일치 ID 12개와 나머지에서 동일 seed `sample(rest,round(.2*len(rest)))`한 28개가 `recall_owner_check.csv`·빈 template CSV와 일치함을 확인했다.

전체 CPU 측정은 **원자료와 기존 보고서를 임시 디렉터리에 복사**해 실행했다. 다음 명령은 기존 산출물에 쓰지 않는다. 실제 실행에서 세 산출물의 byte 비교를 모두 통과하고 exit 0으로 종료했다.

```bash
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev python - <<'PY'
import csv,hashlib,shutil,tempfile
from pathlib import Path
import yaml
from scripts import p08_measure as m
source=Path('experiments/p08_anonymized/measure')
settings=yaml.safe_load(Path(m.CONFIG).read_text())
settings['selected_anonymization']=yaml.safe_load(Path('configs/anonymize.yaml').read_text())
meta={r['image_id']:r for r in csv.DictReader(open(m.METADATA))}
assert hashlib.sha256(Path(settings['face_detector']['model']).read_bytes()).hexdigest()==settings['face_detector']['model_sha256']
with tempfile.TemporaryDirectory() as tmp:
    target=Path(tmp)
    for p in source.iterdir():
        if p.is_file(): shutil.copy2(p,target/p.name)
    m.measure_stage(settings,meta,target,target,0)
    for name in ('report.json','recall_detections.csv','recall_owner_check.csv'):
        assert (target/name).read_bytes()==(source/name).read_bytes(),name
PY
```

### HTML

생성된 `reports/errors/review/p08/index.html`의 `<script>`를 Node `vm.runInContext`로 실행했다. `document.createElement`, `querySelector`, append, button handler, dialog, Blob·URL에 최소 DOM 모형을 제공하여 40개 카드, 미완료 저장 거부, 전체 표시 후 41줄 CSV(header 포함), 이미지 확대와 닫기, 블라인드 payload의 정답·검출·선정 사유 부재를 확인했다. 실제 브라우저의 시각적 배치와 OS 다운로드 동작은 검증하지 않았다.

HTML 함수 실행 재현 명령:

```bash
node <<'JS'
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('reports/errors/review/p08/index.html','utf8');
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
assert(!/agent_face_visible|yunet_detected|disagreement/.test(code));
const ids={};let exported,clicked=false;
class E{constructor(tag){this.tag=tag;this.children=[];this.style={};this.attrs={};}append(...x){this.children.push(...x);}setAttribute(k,v){this.attrs[k]=v;}querySelectorAll(t){return this.children.filter(x=>x.tag===t);}click(){clicked=true;if(this.onclick)this.onclick();}showModal(){this.open=true;}close(){this.open=false;}}
for(const k of ['progress','cases','zoom','zoom-image','save','status','close'])ids['#'+k]=new E(k);
const ctx={document:{querySelector:k=>ids[k],createElement:t=>new E(t)},URL:{createObjectURL:b=>{exported=b;return 'blob:test'},revokeObjectURL:()=>{}},Blob,setTimeout:f=>f()};vm.createContext(ctx);vm.runInContext(code,ctx);
assert.equal(ids['#cases'].children.length,40);ids['#save'].onclick();assert(!exported);assert.equal(ids['#status'].textContent,'모든 사진을 확인해 주세요.');
const cards=ids['#cases'].children;cards[0].children[0].onclick();assert.equal(ids['#zoom'].open,true);ids['#close'].onclick();assert.equal(ids['#zoom'].open,false);
for(const c of cards)c.children[1].querySelectorAll('button')[0].onclick();assert.equal(ids['#progress'].textContent,'40 / 40 확인');ids['#save'].onclick();assert(exported&&clicked);exported.text().then(csv=>{const lines=csv.trim().split('\n');assert.equal(lines.length,41);assert.equal(lines[0],'image_id,owner_face_visible');assert(lines.slice(1).every(x=>x.endsWith(',1')));console.log('HTML 40 cases blind; incomplete download refused; all labels CSV; zoom and close verified with DOM harness')});
JS
```

### 변이

파괴적 검증 전 `git status --short`로 다른 작업자의 dirty tree임을 확인했다. 컨테이너에서 `shutil.copy2`로 `/tmp/p08_measure_verifier_backup.py`를 만들고, 아래 literal을 1회 치환한 뒤 지정된 pytest 셀만 실행했다. 각 실행 뒤 **역치환**하고 `read_bytes()`로 백업과 동일함을 확인했다. `git checkout`, commit, push, branch는 사용하지 않았다.

| 방향·변이(`scripts/p08_measure.py`) | 실패한 셀 |
| --- | --- |
| :156 `gate_applies and not missing` → `gate_applies`(미완료 확인도 통과) | `test_owner_review_requires_every_selected_id_and_keeps_test_reporting_only` |
| :156 최종 `passed` 식 → `None`(완료 확인도 차단) | 같은 셀의 `complete['passed'] is True` |
| :312 `selected_size['k']` → `size['k']`(선택 k 대신 과소 맞춤 k) | `test_measure_report_keeps_original_failure_and_waits_for_owner` |
| :133 `recall >= min_recall` → `wilson(hits,n)[0] >= min_recall`(구간 하한 관문) | `test_recall_gate_reports_wilson_and_rejects_low_recall_or_small_sample` |
| :156 `gate_applies and not missing` → `not missing`(sd35 관문 오적용) | `test_owner_review_requires_every_selected_id_and_keeps_test_reporting_only` |

최초 5종 모두 각 guarding cell이 exit 1로 재실패했다. 복원 후 combined suite는 **40 passed**였다. B1 보완 후에는 아래 두 변이를 추가했으며 복원 후 **47 passed**(5.79초)였다.

| B1 추가 변이 | guarding cell 결과 |
| --- | --- |
| :299 `if selected and (` → `if False and (` | `test_measure_report_keeps_original_failure_and_waits_for_owner[selected_update3-True]`~`[selected_update7-True]`: detector·shape·fill·k 하한 밖·상한 밖 5개 재실패, 정상 3개 통과 |
| :301 지름 범위의 양쪽 `<=` → `<` | 같은 셀 `[selected_update1-False]`, `[selected_update2-False]`: k=1.0/1.6 두 정상 사례 재실패, 나머지 6개 통과 |
 최초 컨테이너 변이 준비 명령은 컨테이너에 Git 실행 파일이 없어 변이 전에 종료됐다. host에서 preflight를 다시 실행한 뒤 본 검증을 진행했다. 원본 파일은 이 실패에서도 변경하지 않았다.

## 발견 사항

### 계약·선택 규격

`docs/plan/phase_8_face_anonymization.md:32`의 소유자 k=1.2와 `configs/anonymize.yaml:13`이 연결된다. 원래 맞춤 k의 실패를 `size_match`로 유지하면서 선택 분포는 `selected_size`에 별도로 기록한다(`scripts/p08_measure.py:297`, `:303`, `:354`). 경계 합성에 실제 선택 k를 넘긴다(`:312`). 정본 규격 → 선택 측정 입력 → 보고서 provenance의 흐름이며 사전 측정 config를 수정하지 않았다.

### 재현율·회귀 경계

`recall_gate`는 점추정 ≥0.80·양성 ≥80과 Wilson 보고를 분리한다(`scripts/p08_measure.py:128`). 소유자 필요한 ID가 남으면 `passed=null`이고 완결되면 수정값으로 재계산한다(`:149`). `test_owner_review_requires_every_selected_id_and_keeps_test_reporting_only`는 부분 확인 차단, 완료 허용, 소유자 수정으로 양성 부족 실패, sd35 보고 전용을 모두 보호한다(`tests/test_p08_measure.py:29`). 빈 표본·재현율 하한·양성 부족·Wilson 하한 관문 오적용을 별도로 검사한다(`:20`).

### 소유자 HTML·CSV

생성 페이지에는 `image_id`와 이미지 외 판정 정보가 없다(`scripts/p08_measure.py:167`). owner CSV는 중복·알 수 없는 ID·빈 표시·0/1 외 값을 거부한다(`:136`, `tests/test_p08_measure.py:44`). HTML 확대·전수 완료 확인·CSV 저장은 `scripts/p08_owner_review.html:33`, `:44`, `:47`에 있으며 함수 실행 검증을 통과했다. CSV template는 549 bytes이며 40개 빈 표시 행이 있어 정상이다. 사진은 원본 해상도로 JPEG quality 95로 재인코딩한 자료다(`scripts/p08_measure.py:166`).

### 원자료·수치·기록

원자료 계보와 재현율 분자는 위 방법으로 독립적으로 확인했다. 최초 snapshot `report_before_owner_decision.json`의 REAL 수치 및 `size_match` 전체 내용은 현재 보고서와 동일하다. 변경된 측정 README·계획·index·HANDOFF·일지·CHANGELOG의 상대 링크를 경로 해석하여 모두 존재함을 확인했고 `git diff --check`가 통과했다. 원자료의 기존 육안 정답 자체는 재판독하지 않았다. 기록은 잠정 train 재현율·reporting-only sd35·남은 소유자 확인 및 보조 측정을 구별한다(`experiments/p08_anonymized/measure/README.md:21`, `:59`, `HANDOFF.md:22`). 재학습·완료로 상태를 전환하지 않았다(`docs/plan/00_index.md:15`).

### 복잡도

새 `recall_summary`는 행 수와 필요한 ID 수에 선형인 결합·집합 차집합이며 누락 ID 정렬이 O(r log r)이다(`scripts/p08_measure.py:150`). 경계 측정은 사전 sigma grid × 최대 100장 ×72방향으로 유한하다(`:306`, `configs/anonymize_measure.yaml:46`). 새 retry·unbounded loop는 없다.

## 문제·위험

### Blocking — 계약 의무

- **최종 미해결 blocking 없음.** B1은 최초 slice의 `scripts/p08_measure.py:299` 선택 config 거부에 음성 회귀 가드가 없던 문제였다. 구현자가 `tests/test_p08_measure.py:70`에 정상 k=1.2/1.0/1.6과 detector·shape·fill·k=.99/1.61 거부 8개 case를 추가했다. 각 거부 case는 공개 `measure_stage`에서 `ValueError` 및 합성·보고서 생성 없음까지 확인한다(`:110`). 위 가드 제거 및 경계 과잉 제한 변이로 양방향 검출력을 독립적으로 입증하여 **B1 해소**했다.

### Hardening recommendations — 비차단

- H1: 소유자 표시 CSV·원 확인 CSV의 SHA-256를 report provenance에 추가하면 사람이 바꾼 원자료와 보고서 사이의 계보를 더 쉽게 식별할 수 있다. 현재 사전 config의 필수 provenance 계약은 해당 원자료 hash를 요구하지 않는다(`scripts/p08_measure.py:359`).
- H2: 브라우저 실제 화면·다운로드를 첫 소유자 확인 때 확인한다. Node 모형은 JS 제어 흐름을 검증하며 브라우저 배치·OS 저장을 대신하지 않는다(`scripts/p08_owner_review.html:48`).

## 판정

**합격**

B1 보완·7종 양방향/방어 제거 변이·47개 focused 회귀 검증을 통과했다. 임시 복사본 CPU 전량 재측정은 exit 0이며 `report.json`, `recall_detections.csv`, `recall_owner_check.csv`가 기존 산출물과 **바이트 동일**했다. k=1.2에서 σ=0.5·전이 중앙값 1px, train 86/97·Wilson 80.83~93.55%, sd35 61/71·Wilson 75.98~92.17%를 재현했다. 측정·metadata·YuNet hash 및 필요한 소유자 40장도 일치했다.

현재 재개 slice에 관한 판정이다. 전체 P08-01은 소유자 확인과 보조 측정 전이므로 완료 또는 최종 재현율 통과로 판정하지 않는다.

## 남은 운영 상태

1. **다음 작업은 소유자가 직접 train 40장을 확인하는 것부터 시작한다.** 확인 CSV를 저장한 뒤 재현율을 재계산한다.
2. sd35도 "같은 방식" 별도 보고하는 계획 계약(`docs/plan/phase_8_face_anonymization.md:39`)이 있다. 현재 owner 페이지는 train만 포함한다(`scripts/p08_measure.py:331`); sd35의 불일치·무작위 확인은 전체 P08-01 종료 전 별도 잔여로 남긴다. sd35에 학습 관문은 적용하지 않는다.
3. 사람 영역 높이 대비 REAL·GEN 보조 크기 측정이 남는다(`docs/plan/phase_8_face_anonymization.md:33`).
4. 전체 P08-01 완료 독립검증은 최종 원자료·보고서 기준으로 다시 수행해야 한다. 현재 구현에 쓰인 대표 얼굴 검출을 P08-02의 여러 얼굴 익명화에 그대로 쓰면 안 된다(`experiments/p08_anonymized/measure/README.md:65`).
5. 검증자는 로컬 commit을 만들지 않았다. 구현자에게 오늘 결과 보존을 인계한다.

## 재현

위 focused pytest 명령 → 원자료 표본·hash 재도출 → 임시 복사본 CPU 실측 → 변이 표의 literal을 1개씩 적용하고 `python -m pytest -q tests/test_p08_measure.py::<셀>` 실행 → 역편집·byte 비교 → combined focused pytest → `git diff --check` 순서다. 실측은 GPU를 사용하지 않는다. 컨테이너 실행은 Docker socket 권한 때문에 승인된 escalation을 사용했다.

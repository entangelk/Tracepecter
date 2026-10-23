# P09-02 재분할 독립검증

## 대상 정보

- 날짜: 2026-10-23 (Asia/Seoul).
- 요청자: 소유자, “서브에이전트 하나 스폰해서 제대로 되었는지 독립검증”.
- 검증자: 구현에 참여하지 않은 Codex 서브에이전트 `/root/verify_p09_02`.
- 대상: `main`의 `42a848183ab13e3e485ae47baca4ae0c697aea20`.
- 정본: `docs/sot.md` §2~3, `docs/plan/phase_9_leakage_repair.md`의 선행 보존·계약 소유권·P09-01 lock/DB-07 연결·P09-02(70~76행), Resolved DB-07 결정 결과, `docs/project.md` §10·12·13·14(v1.4), 선행 `grouping/final/group_lock.json` 및 `evidence_lock.json`.
- 절차: `AGENTS.md` 및 `docs/guides/verification.md` 직접 읽음. 정본 우선순위가 존재하며 이번 범위에서 소유자 결정이 필요한 사양 충돌은 발견하지 않았다.

## 범위

정본 경계, 분할 구현, 회귀 테스트/fixture, 실제 6,000행 metadata와 이미지, 고정 그룹·후보·이웃 검토 근거, split lock·보고서, 소비자의 Test B 선택, 기존 artifact 보존, 변이 및 집중/전체 CPU 회귀를 확인했다. 새 학습·평가 성능과 946,311개 미검토 후보의 시각 판정은 범위 밖이다. 과거 시각 판정 자체를 새로 1,386회 수행한 검증은 아니다.

## 방법과 경계 매트릭스

코드를 열기 전 정본 읽기 범위를 P09-02와 그 선행 참조로 정했다. 이후 정본 각 경계를 구현·명명 테스트·실물 산출물에 대조했다. 아래 테스트 이름은 `tests/test_p09_split.py` 소속이며 다른 파일은 명시한다. 빈 명명 회귀 칸은 합격으로 간주하지 않는다.

| 계약 경계: 차단 / 정상 허용 | 구현 | 명명 회귀/fixture | 관찰 |
| --- | --- | --- | --- |
| 누락·중복·추가·빈 매핑·중복 원본·옛 그룹 분해·class/unseen 모순 거부 / 정상 보수적 그룹 허용 | `scripts/split_dataset.py:121` | `test_invalid_mapping_rejected` 8개 매개변수, `fixture_rows` | 정상 통과, 옛 그룹 방어 제거 시 명명 셀 실패 |
| 추이·다중 셀 REAL 및 GEN 공동 배정 보존 / 다른 GEN의 prompt 공유로 자동 병합 금지 | `scripts/split_dataset.py:64`, `:143` | `test_groups_determinism_and_no_prompt_merging`, `fixture_rows`; `tests/test_p09_group_candidates.py:36`, `:55`, `:170` | REAL·prompt 정상 경계 존재. GEN 매핑 무시 변이는 명명 셀에서 생존: B1 |
| 순서 결정성·불변 필드·원본 불변 / 정상 GEN look_group 유지 | `scripts/split_dataset.py:148` | `test_groups_determinism_and_no_prompt_merging` | fixture 및 실물 6,000행 역순 결과 일치 |
| sd35 600장 격리 / standard 정상 분리 | `scripts/split_dataset.py:146` | 위 테스트, `test_invalid_mapping_rejected[unseen]`, 기존 `tests/test_split_dataset.py:112`, `:127` | 실물 600장 모두 unseen |
| 새 Test B REAL만 선택 / train·val REAL 제외 | `src/evaluate.py`의 `evaluation_indices` | `test_mapping_cli_and_new_test_b_real` | 소비자 연결 통과, 새 REAL 448장 |
| 잠금 hash 변경 거부 / 정상 잠금 허용 | `scripts/p09_resplit.py:12` | `test_locked_input_tampering_rejected` | 매핑 변조 검출 및 정상 lock 검증 |
| DB-07 초기 500/100·directed closure 누락 거부 / 정상 검토 허용 | `scripts/p09_resplit.py:80` | **직접 명명 회귀 없음**. 이웃 알고리즘은 `tests/test_p09_group_candidates.py:183`으로 별도 보호 | 현재 실물 600쌍/잔여 0 재현. scope 방어 제거 생존: B2 |
| 모든 split 경계의 동일/미확정 교차 거부 / 다른 룩 교차와 같은 split 미확정 허용 | `scripts/p09_resplit.py:26` | `test_review_crossings_both_directions` | 과잉 거부 변이 명명 셀 실패, 실물 교차는 다른 룩만 존재 |
| 빈 class/split·평가 불가능 셀 거부 / 정상 셀별 보고 허용 | `scripts/p09_resplit.py:42` | **직접 명명 회귀 없음** | 실물 정상이나 empty class 방어 제거 생존: B3 |
| 원본 6,000 ID·이미지 hash 및 기존 artifact 보존 / REAL look_group·split만 변경 | `scripts/p09_resplit.py:43`, `:157` | metadata 필드는 위 그룹 테스트; 이미지 검증 진입점의 직접 회귀 없음 | 실물 hash 6,000장 대조. 재현 명령으로 이번 입력을 검증했으나 전체 실행 경계의 회귀는 불완전 |
| GEN full prompt/seed 계보 공유 보고 / 공유만으로 자동 병합 금지 | `scripts/p09_resplit.py:144` | 병합은 그룹 테스트와 `tests/test_p09_group_candidates.py:55`; 새 보고 계산 직접 회귀 없음 | 원본 provenance hash 확인, 보고서 바이트 일치 |
| 기존 경로 호환·버전 출력·덮어쓰기 금지 | `scripts/split_dataset.py:188`, `scripts/p09_resplit.py:115` | `tests/test_split_dataset.py`의 기존 CLI 2개, `test_mapping_cli_and_new_test_b_real`; resplit 출력 존재 방어의 직접 회귀 없음 | 기존 suite 통과, 재현은 새 `/tmp` 경로만 사용 |

### 실행 명령

저장소 루트에서 실행했다. 아래 `/tmp` 경로가 이미 있으면 새 접미사를 사용한다.

```bash
python3 -m scripts.p09_resplit \
  --out /tmp/p09_independent_metadata.csv \
  --report /tmp/p09_independent_split \
  --image-root /mnt/h/tracepector/images

OPENBLAS_NUM_THREADS=1 python3 -m scripts.p09_group_candidates \
  --out /tmp/p09_independent_neighbors --queue /tmp/p09_independent_neighbors_queue \
  --neighbors-from \
  experiments/p09_leakage_repair/r1/grouping/visual_review_batch_01.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_batch_02.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_gen_batch_01.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_neighbors_round_01.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_catalog_extra.csv \
  experiments/p09_leakage_repair/r1/grouping/visual_review_neighbors_round_02.csv
python3 -m scripts.p09_finalize_groups --out /tmp/p09_independent_groups

docker compose run --rm -T dev python -m pytest \
  tests/test_p09_split.py tests/test_split_dataset.py \
  tests/test_p09_group_candidates.py tests/test_baseline.py -q
# 모든 변이 복원 후 전체 CPU 회귀 한 번
docker compose run --rm -T dev python -m pytest -q
```

추가 실물 대조 명령:

```bash
python3 - <<'PY'
import csv, hashlib, json
from pathlib import Path
from scripts.split_dataset import reviewed_group_split
read = lambda p: list(csv.DictReader(open(p)))
base = Path('experiments/p09_leakage_repair/r1/split')
for old, new in [
    (Path('data/versions/p09_r1/metadata.csv'), Path('/tmp/p09_independent_metadata.csv')),
    (base/'split_report.json', Path('/tmp/p09_independent_split/split_report.json')),
    (base/'review_boundaries.csv', Path('/tmp/p09_independent_split/review_boundaries.csv')),
]:
    assert old.read_bytes() == new.read_bytes()
lock = json.loads((base/'split_lock.json').read_text())
for section in ('source_sha256', 'verified_inputs_sha256'):
    for name, expected in lock[section].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
old = read('data/metadata.csv')
new = read('data/versions/p09_r1/metadata.csv')
mapping = read('experiments/p09_leakage_repair/r1/grouping/final/group_mapping.csv')
assert reviewed_group_split(old[::-1], mapping[::-1]) == new
by_id = {r['image_id']: r for r in new}
legacy = read('experiments/p08_anonymized/leakage_audit/visual_review.csv')
confirmed = [r for r in legacy if r['verdict'] == 'confirmed_same_look']
assert len(confirmed) == 8
assert all(by_id[r['image_id']]['split'] == by_id[r['train_image_id']]['split'] for r in confirmed)
for name in ('conservative_constraints.csv', 'group_mapping.csv', 'summary.json', 'visual_reviews.csv'):
    assert (Path('/tmp/p09_independent_groups')/name).read_bytes() == (
        Path('experiments/p09_leakage_repair/r1/grouping/final')/name).read_bytes()
print('실물 재현·잠금·역순·옛 8쌍·그룹 투영 모두 일치')
PY
git diff 42a8481^ 42a8481 --name-only
```

## 변이 검증

첫 변이 직전에 `git status --short`를 실행해 빈 출력을 확인했다. 이미 커밋된 `42a8481`이 checkpoint다. 각 대상 파일의 바이트를 `/tmp/<변이명>.backup`에 복사한 뒤 단일 문자열을 교체했다. 매 실행은 `try/finally`로 원래 바이트를 복원하고 백업과 바이트 일치 및 `git status --short` 빈 출력을 확인했다. 원본 lock·artifact는 변경하지 않았다. 최초 비승격 Python 하위 Docker 실행은 socket 권한 오류였으므로 테스트 실패 근거에서 제외하고, 동일 실험을 `require_escalated`로 다시 실행했다.

| 변이명·방향 | 정확한 교체(각 1회) | 실행 명명 셀 | 관찰 |
| --- | --- | --- | --- |
| `under_gen_group` / under-strict | `scripts/split_dataset.py:67`: `key = allocation_groups[row['image_id']] if allocation_groups is not None else group_key(row)` → `key = allocation_groups[row['image_id']] if allocation_groups is not None and row['source_type'] == 'real' else group_key(row)` | `tests/test_p09_split.py::test_groups_determinism_and_no_prompt_merging` | **1 passed**, exit 0 (0.36초). GEN 그룹 제약을 없애도 g0/g1가 우연히 같은 split이므로 검출하지 못함 |
| `over_different_look` / over-strict | `scripts/p09_resplit.py:37`: `if review['verdict'] != 'different_look':` → `if True:` | `tests/test_p09_split.py::test_review_crossings_both_directions` | **1 failed**, exit 1 (0.44초), 정상 different_look 교차 ValueError |
| `defensive_old_group` / 방어 제거 | `scripts/split_dataset.py:135`: `if any(len(values) != 1 for values in old_groups.values()):` → `if False:` | `tests/test_p09_split.py::test_invalid_mapping_rejected[old_group]` | **1 failed**, exit 1 (0.43초), DID NOT RAISE ValueError |
| `defensive_priority_missing` / 방어 제거 | `scripts/p09_resplit.py:98`: `if any(tuple(sorted((r['a'], r['b']))) not in reviewed for r in selected):` → `if False:` | `tests/test_p09_split.py tests/test_p09_group_candidates.py` | **26 passed**, exit 0 (2.76초). 다른 방어가 흡수한 것이 아니라 테스트가 `check_priority_scope`를 실행하지 않음 |
| `defensive_empty_class` / 방어 제거 | `scripts/p09_resplit.py:73`: `if {r['label'] for r in rows if r['split'] == split} != {'0', '1'}:` → `if False:` | `tests/test_p09_split.py tests/test_p09_group_candidates.py` | **26 passed**, exit 0 (2.50초). 테스트가 `split_report`를 실행하지 않음 |

재실행은 위 표의 각 교체를 대상 소스에 **하나씩** 적용한 후 다음 형태로 실행한다. `cells`는 표의 정확한 명명 셀/파일 목록이다. 변경 전에 clean gate를 실행하고, 각 변이 후 백업 바이트로 복원한다.

```python
from pathlib import Path
import subprocess
assert subprocess.check_output(['git', 'status', '--short']) == b''
p = Path(source)  # 표의 대상 파일
original = p.read_bytes()
backup = Path('/tmp/p09_verify_mutation.backup')
backup.write_bytes(original)
assert original.decode().count(before) == 1  # 표의 교체 전 문자열
try:
    p.write_text(original.decode().replace(before, after))
    subprocess.run(['docker', 'compose', 'run', '--rm', '-T', 'dev',
                    'python', '-m', 'pytest', *cells, '-q'], check=False)
finally:
    p.write_bytes(original)
    assert p.read_bytes() == backup.read_bytes()
    assert subprocess.check_output(['git', 'status', '--short']) == b''
```

## 표면별 발견

### 정본과 구현

P09-02의 확정 그룹 소비·보존·sd35·Test B 규칙은 `docs/plan/phase_9_leakage_repair.md:72`~`:76`과 `scripts/split_dataset.py:121`~`:159`에서 대응한다. 검토 판정과 배정 제약을 구별하며 단순 prompt 공유를 자동 병합하지 않는다. `scripts/p09_resplit.py:80`의 초기 scope 재선택은 split에 의존하지 않아 고정 판정의 새 split 재투영은 합리적이다. 그 함수의 방어와 보고서 검증은 구현되어 있으나 테스트가 실행하지 않는다.

### 실제 metadata·이미지·소비 경계

`split_report.json:2` 이하의 실제 배정 6,000행·5,692그룹과 train 3,780 / val 820 / test 800 / unseen 600을 재현했다. REAL 2,100/452/448, GEN 1,680/368/352/600이다. `scripts/p09_resplit.py:157`~`:170` 경로로 원본 6,000장 SHA-256을 실제 다시 읽어 확인했다. 불변 필드·ID·경로, 기존 그룹·새 그룹 교차 0도 재검사했다. 최대 셀 비율 편차는 0.003333…(0.333…%p)다. Test B 소비자 연결은 `tests/test_p09_split.py:105`에서 새 standard test REAL만 재사용함을 확인한다.

### 고정 그룹·후보·이웃·경계 보고

`grouping/final/group_lock.json:2` 이하 입력/코드/출력 hash와 `evidence_lock.json:2`의 결합을 실제 검증했다. cache 47개·2,220 최근접 query 검증 후 directed 이웃 0개를 재현했고, 최종 그룹 산출물 4개가 바이트 일치했다. `scripts/p09_resplit.py:138`~`:143`의 보고는 검토 1,386쌍 중 확정 53·미확정 269 교차 0, 다른 룩 교차 train/val 141·train/test 166·val/test 4다. 옛 확정 8쌍도 교차 0이다. 초기 600쌍 포함을 다시 확인했다. 미검토 초기 946,311쌍은 그대로 남는다.

### 계보·lock·보존

`split_report.json`의 `generation_train_overlap`은 train 대비 full prompt 공유 val/test/unseen 362/346/597, prompt+seed 360/344/596을 재현했다(`scripts/p09_resplit.py:144`~`:155`). metadata SHA-256은 `5a323684dbf157a1db38201f8fe8007185a7809f2ab1ab9564f225faed682161`이다. metadata·split_report·review_boundaries가 기존 출력과 바이트 일치했고 `split_lock.json:51`의 소스·입력 hash도 일치했다. 대상 커밋의 변경 파일 목록에는 기존 metadata·primary·P08 감사/주석·checkpoint·calibration이 없으며 검증자는 그 원본을 쓰지 않았다. checkpoint 전체를 새로 학습하거나 과거 바이너리 상태를 독립 재구축한 주장은 하지 않는다.

### 회귀 및 복잡도

집중 39 passed(36.61초), 변이 복원 후 P09 집중 26 passed(2.78초), 전체 CPU 242 passed / 1 skipped(49.47초), Pillow 기존 경고 12개였다. skip은 `tests/test_p08_training_config.py:47`의 실제 YuNet opt-in smoke다. 전체 녹색은 B1~B3의 필수 회귀 공백을 해소하지 않는다.

`stratified_group_split`은 그룹 정렬 O(g log g), 행 집계 O(n), 메모리 O(n)이다(`scripts/split_dataset.py:63`~`:103`). 그룹별 touched-cell 합은 전체 행 수로 제한된다. scope 검사는 후보 선형 스캔과 집합 조회이며 이미지 검증은 원본 총 바이트 수에 선형, worker 4개로 제한된다(`scripts/p09_resplit.py:91`, `:169`). 입력에 따라 무한 재시도하는 흐름은 없다. 선행 directed 이웃 재현은 anchor×class 후보 계산/정렬을 수행하므로 큰 데이터에서 비용이 증가하지만 이번 6,000행 실물에서 종결을 확인했다.

## 문제와 위험

### 차단 사항 — 계약 의무

- **B1 — GEN 그룹 회귀 fixture가 실제 분산 결함을 검출하지 못함.** `tests/test_p09_split.py:22`, `:35`의 g0/g1는 배정 제약을 무시해도 같은 split으로 우연히 배정된다. P09-02의 GEN 공동 배정 및 under-strict 의무(`docs/plan/phase_9_leakage_repair.md:76`)를 잠그지 못한다. 그룹을 무시하면 반드시 갈라지는 fixture로 바꾸고 같은 변이에서 명명 셀이 실패해야 한다.
- **B2 — DB-07 고정 scope 충족 방어의 명명 회귀 누락.** `scripts/p09_resplit.py:84`~`:102`의 후보 hash·최소 수량·검토 포함·closure pending 양/음 경계를 직접 호출하는 테스트가 없다. 특히 `:98`의 미검토 scope 차단을 제거해도 26개 집중 셀이 통과했다. `docs/plan/phase_9_leakage_repair.md:75`의 계약 필수 경계이며 정상 완료와 누락/미해결 양쪽을 잠가야 한다.
- **B3 — 실제 보고·평가 가능성 경계 및 실행 진입점의 명명 회귀 누락.** `scripts/p09_resplit.py:42`~`:77`의 불변 필드·원래/새 그룹 교차·빈 셀·빈 class 검증을 테스트가 호출하지 않는다. empty class 방어 제거가 26개 집중 셀을 통과했다. `docs/plan/phase_9_leakage_repair.md:73`~`:74`의 의무다. 새 진입점의 이미지 hash 변경 거부·기존 출력 거부 및 계보 보고도 직접 회귀 연결이 없어, 이번 실물 정상 재현만으로 후속 변경을 보호하지 못한다. fixture와 명명 테스트로 계약에 필요한 거부/정상 허용 및 보고 값을 연결해야 한다.

이번 실물 산출물에서 실제 ID 손실·이미지 변조·그룹 누출이 발견됐다는 뜻은 아니다. 차단 원인은 검증 지침의 “계약 필수 경계에는 명명 회귀가 있어야 한다”는 요구를 충족하지 못한 것이다. 구현자는 결함을 고친 뒤 해당 변이와 집중 suite로 재검증할 수 있다.

### 보강 권고 — 비차단

- 현재 범위 밖인 946,311쌍, 단일 REAL 출처, GEN prompt/seed 공유, 개발 표본 노출 한계를 후속 학습 보고에도 유지한다(`docs/plan/phase_9_leakage_repair.md:85`~`:92`). 이번 검증에서 새로운 수집이나 전수 검토를 요구하지 않는다.

## 판정

**조건부 합격** — B1 GEN 그룹 회귀의 변이 생존, B2 고정 검토 scope 및 B3 보고·평가 가능성/실행 경계의 명명 회귀 공백을 닫아야 한다.

현재 산출물의 재현·불변성·그룹 배정·고정 검토 범위는 실물에서 확인했다. 하지만 필수 방어 제거가 테스트를 통과하므로 P09-02의 회귀 증거를 완결된 것으로 승인하지 않는다. 소유자 결정이 필요한 데이터 범위 충돌은 발견하지 않았다.

## 남은 운영 사항

구현·테스트는 수정하지 않았다. 모든 변이 후 원본 바이트/clean 상태를 확인했고 검증 기록만 별도 커밋한다. B1~B3 보강과 재검증이 남아 있다. 재학습·primary 변경·push는 수행하지 않았다.

## 재현

위 실행 명령 → 실물 대조 Python → 표의 변이 5개(각각 clean gate·백업·복원) → 복원 후 집중 및 전체 CPU suite 순으로 수행하면 동일 경계를 재검증할 수 있다. Docker socket 제한이 있으면 Docker 호출을 `require_escalated`로 실행한다. 검증 기록 파일 이외의 변경이 없는지 `git status --short`와 `git diff --check`로 확인한다.

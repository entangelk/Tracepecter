# P06-02c 원형 얼굴 가림 의존 재진단(표본 확장·구간) — 독립검증 기록

## Verdict

**합격** — (3차 확인, HEAD `d7a09f2`) 2차 비차단 R-H1–R-H3와 기록 갱신(Outstanding)이 반영됐다. `src/`·`tests/`는 `a8812f2` 이후 변경이 없다(`git diff a8812f2 HEAD -- src tests` 0줄). 묶음 bootstrap 스크립트는 README 수치를 그대로 재현한다. QA 표본도 note의 절차로 재현된다. 기록의 수치·커밋 순서·판정은 산출물·본 기록과 정합한다. 남은 것은 문구 수준 비차단 2건(T-H1, T-H2)이다. 상세는 아래 "3차 확인" 절에 있다.

2차 판정(HEAD `a8812f2`, 이력 보존):

**합격** — (2차 추적 검증, HEAD `a8812f2`) 1차 Blocking B1–B5가 모두 해소됐다. 1차 생존 변이 11개와 새 변이 6개를 포함해 변이 36개가 전부 이름 있는 셀에서 죽는다. H1–H6도 반영됐다. 재생성 산출물은 GPU 재실행에서 `detections.csv`·`predictions.csv`가 byte 동일하고, `report.json`은 output_dir만 다르다. 남은 것은 비차단 문구 보정 3건(R-H1–R-H3)과 기록 갱신(Outstanding)이다. 상세는 아래 "2차 추적 검증" 절에 있다.

1차 판정(HEAD `97aaf12`, 이력 보존):

**조건부 합격** — 사전 고정 config의 경계·literal 일부를 잠그는 회귀 셀이 없어 변이 8개가 생존한다. D2 엄격 부등호(`>0`, 하한·점추정), 흰 원 전환율 점추정의 포함 부등호(`≥`), 전환 정의의 원본 엄격 부등호(`원본 p < threshold`), 얼굴 선택의 "왼쪽" 동점 규칙, `min_size_ratio` 필터, bootstrap `interval`·`resamples`·`seed` 연결이 해당한다. 이 셀들을 추가하면 닫힌다.

판정 근거:

- 산출물 수치는 독립 재계산과 **전부 일치**한다. README의 표·제외 수·생성기별 검출 수·전환 수·비율·val 대 test 비교·Wilson 하한이 모두 맞다. 본 검증자의 bootstrap(seed 20261011, 2000회, 백분위 2.5/97.5)은 metadata 순서로 정렬했을 때 `report.json`의 모든 구간과 부동소수 오차(≤1.8e-15)까지 일치한다.
- GPU 전체 재실행(본 검증자, 3분 44초)의 `detections.csv`·`predictions.csv`·`report.json`이 커밋본과 **byte 동일**하다. 판정은 confirmed / confirmed다.
- 별도로 작성한 YuNet 호출 코드로 검출을 재현했다. 1,320장 모두 검출 유무가 같고 좌표 차이는 0이다. off-face 규칙도 독립 구현으로 재현했다(180장 제외 일치, 불일치 0).
- 사전 고정 순서를 확인했다. config `60bad9a`(10:10:58) → 코드 `19ee42a`(10:13:14) → 결과 `97aaf12`(10:24:02) 순이다. config는 이후 바뀌지 않았다(`git diff 60bad9a HEAD -- configs/face_mask_ci.yaml` 0줄).
- 그러나 가이드의 "경계 행렬 빈칸 = blocking" 조항 때문에 합격이 아니다. 실제 실행값은 맞지만, 위 분기들은 코드가 회귀해도 녹색으로 남는다.

## Subject metadata

- 날짜: 2026-10-11
- 요청자: 소유자(오케스트레이터 경유)
- 검증자: Claude Code(Opus 5.5), 독립 검증자. 본 슬라이스를 작성하지 않았다.
- 대상: P06-02c "원형 얼굴 가림 의존 재진단 — 표본 확장·구간"
- 출처: git `main`, HEAD `97aaf12`, 검증 시작 시 작업 트리 clean. 커밋은 `60bad9a`(config), `19ee42a`(코드·테스트), `97aaf12`(실행 산출물·README)다.
- 정본 계약:
  - `configs/face_mask_ci.yaml`(`60bad9a`)
  - `docs/plan/phase_6_failure_analysis.md`의 목표·실험 전 정의·제외 절과 진행 상황 78행
  - P06-02b 사후 명시 절 `experiments/p06_failure_analysis/face_mask/README.md:59-68`
- 고정 입력:
  - `experiments/p05_calibration/calibration.json`(T 0.7984784236465634, threshold 0.6966991081858492, checkpoint sha `151244…95fe`, metadata sha `039cbdd1…81`)
  - `data/metadata.csv`(sha256 `039cbdd1…81`, artifact와 일치)
  - YuNet ONNX(sha256 `8f2383e4…2fa4`)

## Scope

1. 사전 고정 무결성(커밋 순서, 이후 수정 여부, 모델 결과로 조정될 수 있었던 항목)
2. config literal ↔ 코드 일치
3. 외부 artifact(YuNet) 해시·출처
4. README 수치 독립 재계산(bootstrap 포함)
5. 검출 품질 육안 표본 점검(검출·미검출·z_image_turbo·off-face 제외)
6. 통계 민감도(prompt 묶음 bootstrap)
7. 재실행 결정성(GPU 전체)
8. 테스트(집중·전체)와 경계 행렬
9. 변이 테스트

## Methodology

모든 경로는 저장소 루트(`/mnt/f/devel/Tracepecter`) 기준이다. `$S`는 본 검증자의 scratch 디렉터리(`/tmp/claude-1000/-mnt-f-devel-Tracepecter/a84d7a78-ae59-41e7-80eb-9e419fef0396/scratchpad/verify_p0602c`)다.

```bash
git log --format='%h %ad %s' --date=iso -5
git log --oneline -- configs/face_mask_ci.yaml
git diff 60bad9a HEAD -- configs/face_mask_ci.yaml | wc -l
sha256sum /mnt/h/tracepector/checkpoints/face/face_detection_yunet_2023mar.onnx data/metadata.csv
curl -s "https://api.github.com/repos/opencv/opencv_zoo/commits?path=models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
curl -sL -o $S/yunet_dl.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx && sha256sum $S/yunet_dl.onnx
# 독립 재계산(pandas, 호스트): 후보·검출·off-face 규칙 재구현·확률·D1~D3·전환·bootstrap·묶음 bootstrap
python3 $S/recompute.py; python3 $S/exact.py
# 육안 표본(seed 777, 본 검증자 선택): 검출 24, 미검출(z 제외) 16, z_image_turbo 미검출 16, off-face 제외 8
python3 $S/overlay_host.py   # → $S/{hit,miss,z,noroom}.jpg 를 직접 열람
# 독립 YuNet 호출(cv2.imread BGR, 동일 파라미터, 자체 선택 규칙) 1,320장 전체
docker compose run --rm -T -v $S:/scratch -v /mnt/h/tracepector/images:/images:ro dev python /scratch/yunet_indep.py
# GPU 재실행(nvidia-smi 1%, 1221MiB 확인 후)
sed 's#^output_dir: .*#output_dir: /scratch/rerun#' configs/face_mask_ci.yaml > $S/ci_rerun.yaml
docker compose --profile training run --rm -T -v $S:/scratch train python -m src.face_mask_ci --config /scratch/ci_rerun.yaml
cmp experiments/p06_failure_analysis/face_mask_ci/{detections.csv,predictions.csv,report.json} vs $S/rerun/*
# 테스트(exit code를 파이프 없이 확인)
docker compose run --rm -T dev python -m pytest tests/test_face_mask_ci.py -q; echo exit=$?
docker compose run --rm -T dev python -m pytest -q; echo exit=$?
# 변이: 매 변이 전 git status --short 비어 있음 assert → 치환 → 집중 파일 실행 → git checkout -- src/face_mask_ci.py → clean 재확인
python3 $S/mutate.py
```

## Findings

### 1. 사전 고정 무결성

- 커밋 순서는 config → 코드 → 결과이고, config는 이후 수정되지 않았다(위 명령, 0줄).
- 모델 결과로 조정될 수 있었던 항목을 점검했다.
  - YuNet `score_threshold 0.9`·`nms 0.3`·`top_k 5000`은 OpenCV YuNet 예제 기본값과 같다.
  - `disc_diameter_per_face 1.2`는 config 13행에 따르면 검출 QA(이미지 육안)로 정했다. 모델 출력이 아니다.
  - `min_flip_fraction 0.05`는 P06-02b 규칙을 승계했다.
  - `min_size_ratio 0.04`는 본 데이터에서 효과가 없다. 독립 YuNet 호출로 필터 유무를 비교하면 선택 상자가 바뀐 이미지는 0장이다. 검출 상자의 최소 비율은 0.064다.
  - 따라서 config 값이 P06-02c 모델 출력에 맞춰 조정됐다는 흔적은 없다.
- 남는 위험(비차단)이 두 가지 있다.
  - 재진단의 동기 자체가 P06-02b의 경계 근접 결과(모델 출력)다. 대상 중 test 461장은 P06-02b 표본과 겹친다. 그래서 이 결과는 독립 반복이 아니라 같은 test 표본의 재측정에 val 210장을 더한 것이다. README 63행 "더 큰 표본과 구간에서도 유지된다"는 이 점을 밝히지 않는다(H5).
  - 검출 QA 40장·미검출 20장의 image_id 목록이 저장되지 않아 재현할 수 없다(H6).
- config 2행의 소유자 승인(YuNet·test∪val 합산·bootstrap 규칙)은 work log·HANDOFF에 아직 기록되지 않았다. val 포함 자체는 plan 78행에 예정돼 있다(Outstanding).

### 2. config literal ↔ 코드

| config | 코드 | 일치 |
| --- | --- | --- |
| `splits: [test, test_unseen, val]`, GEN만 (8–10행) | `src/face_mask_ci.py:106` label==0 ∧ split∈splits | 예 |
| YuNet 파라미터·sha256 (14–19행) | `:34` create 인자, `:96-98` 해시 검사 | 예 |
| `min_size_ratio` 긴 변 ≥ 너비×0.04 (20행) | `:36` `max(f[2], f[3]) >= width * min_size_ratio` | 예 |
| score 최대 → 넓이 → 위 → 왼쪽 (21행) | `:27` key `(score, w*h, -y, -x)` | 예 |
| 지름 = 긴 변×1.2 (22행) | `src/face_mask.py:75-77` `max(w,h)*ratio/2` = 반지름 | 예 |
| off-face 후보 순서·2r·이미지 안 (24–25행) | `src/face_mask.py:80-87` | 예 |
| 조건·fill (26–29행) | `:41-47` | 예 |
| shift = 100×(p조건−p원본), 전환 = 원본 p<thr ∧ 조건 p≥thr (31행) | `:50-60` | 예 |
| bootstrap 2000 / 20261011 / 0.95, 공유 재추출 (32–36행) | `:63-73`, `:151-152` | 예 |
| confirmed: D1·D2 하한 >0 ∧ F 하한 ≥0.05 (41행) | `:80` | 예 |
| suggestive: D1·D2 점추정 >0 ∧ F 점추정 ≥0.05 (42행) | `:82` | 예 |
| D3: 하한 >0 / 점추정 >0 (45행) | `:86` | 예 |
| 판정은 합산 대상에만 (38행) | `:161` `decide(pooled, …)` | 예 |

- P06-02b 사후 명시 세부(off-face 규칙, 동점 처리)는 이번 config 21·24–25행에 사전 고정으로 들어갔다. REAL 회색 덮기(r+3)는 이번 슬라이스에 REAL 조건이 없어 해당하지 않는다.
- 계약 내부 모순: plan의 "validation은 별도 표시하여 검토 보충용으로만 쓴다"(실험 전 정의)는 P06-01/03 검토군 문맥의 문장이다. P06-02c는 val을 판정 대상에 합산하고 따로도 보고한다(config 9행). plan 78행이 "val 포함"을 예정했고 config가 소유자 승인을 명시하므로 Blocking 모순으로 보지 않는다. 다만 승인 기록은 work log에 남겨야 한다(Outstanding).

### 3. 외부 artifact

- 로컬 ONNX와 opencv_zoo `main` raw 다운로드의 sha256이 모두 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`이고 config 16행과 같다(232,589 B).
- GitHub API 기준 이 파일의 마지막 변경 커밋은 `f12e127` 2023-06-06 "update yunet to v2 (#151)"이다. config 12행 주장과 일치한다.

### 4. README 수치 독립 재계산

계산 경로: `predictions.csv` logit → `1/(1+exp(−logit/T))` → 본 검증자 구현의 shift·D·전환 → 자체 bootstrap.

| 항목 | 주장 | 재계산 |
| --- | --- | --- |
| 후보 / 검출 / 검출률 | 1,320 / 851 / 64.5% | 1,320 / 851 / 64.47% |
| 제외 no_face / no_offface_room | 469 / 180 | 469 / 180(off-face 규칙 독립 구현, in_target 불일치 0) |
| 대상(test / val) | 671 (461 / 210) | 671 (test 200 + test_unseen 261 / 210) |
| 생성기별 검출 | pg 173, sdxl 164, qwen 130, sd35 382/600, z 2/180 | 같음 |
| 흰 원 전환 | 51(7.6%) [5.7, 9.5] | 51, [5.66, 9.54] |
| 회색 / 얼굴 밖 전환 | 6.3% / 0.9% | 42 / 6장 |
| D1 / D2 / D3 | +3.94 [3.19, 4.72] / +11.35 [9.58, 13.27] / +7.41 [5.95, 8.88] | 같음(bit 일치) |
| 회색/흰 비율 | 약 69% | 0.6856 |
| 학습 생성기 비교(val / test) | +8.78·+4.22·10/210 / +6.25·+3.41·5/200 | 같음 |
| Wilson 40/40 하한 | 91% | 0.9124 |
| 하위 집합 표(test·val·생성기 5개) | README 53–59행 | `report.json`과 전 칸 일치, 자체 bootstrap과 bit 일치 |

- 원본에서 이미 threshold 이상(REAL 판정)인 대상이 1장 있다. 이 표본은 전환될 수 없지만 분모 671에는 들어간다. config 31행 정의대로이며 결과 영향은 무시할 수준이다.
- val 대 test 학습 생성기 비교에서 차이의 95% bootstrap 구간이 모두 0을 포함한다(흰 원 +2.53 [−1.20, 6.17], 전환 +2.3%p [−1.6, 6.1]). README 66행 "비슷한 범위"는 정합한다.
- val만 보면 흰 원 전환율 점추정이 4.76%로 5% 미만이다. 같은 규칙을 val에 적용하면 insufficient다. README 73행은 하한 1.9%만 적는다. 하위 집합은 보고용이라 판정과 무관하지만, 새로 추가된 표본만으로는 규칙이 성립하지 않는다는 점을 명시하는 편이 정확하다(H5).

### 5. 검출 품질 육안 점검(본 검증자 표본, seed 777)

- **검출 24장**(`hit.jpg`): 24/24가 실제 사람 얼굴이다. 1.2배 원(녹색)이 얼굴을 덮는다. 얼굴 밖 원(파랑)은 배경에 있고 몸·머리와 겹치지 않는다. 구현자 주장(40/40, 원이 얼굴을 덮음)과 정합한다.
- **미검출 16장**(z_image_turbo 제외, `miss.jpg`): 얼굴이 화면에 없는 것(뒷모습·목 아래 크롭)은 7장(000956, 002756, 001801, 001093, 002673, 002649, 001637)이다. 보이는 얼굴을 놓친 것은 9장이다(측면 002582·001783·002887·002816·002859, 고개 숙임 002803, 정면에 가까운 002394·000932·000685).
  - README 24행 "미검출 20장 중 16장 얼굴 없음, 놓친 것 4장"보다 놓친 비율이 높다.
  - 구현자 표본에는 z_image_turbo 미검출(178장, 전부 얼굴 없음)이 섞였을 수 있다. 그래서 두 표본을 직접 비교할 수는 없다.
  - z 제외 미검출 291장에 본 표본 비율(9/16)을 적용하면, 보이는 얼굴을 놓친 경우는 미검출 469장의 약 35%로 추정된다. 대상이 정면 얼굴 쪽으로 치우친다는 한계(README 74행)는 이미 적혀 있으므로 판정 영향은 없다. 다만 24행 수치를 보정해야 한다(H6).
- **z_image_turbo 미검출 16장**(`z.jpg`): 16/16이 머리 없는 크롭이다(입·턱 일부만 보이는 2장 포함). README 27행 주장이 맞다.
- **off-face 제외 8장**(`noroom.jpg`): 모두 얼굴이 크거나 상단 가장자리에 붙은 근접 구도다. 대상이 전신·작은 얼굴 구도로 치우치는 선택 효과가 있다. README 74행 한계에 포함된다.

### 6. 통계 민감도 — prompt 묶음 bootstrap

- `look_group`은 GEN에서 전부 비어 있다. `prompt_id`는 대상 671장에 99개 묶음으로 채워져 있다.
- 묶음 재추출(seed 20261011, 2000회, 묶음 합/표본 수) 결과:

| 통계 | 이미지 단위 하한 | prompt 묶음 하한 | 생성기×prompt 묶음 하한(293개) | 기준 |
| --- | --- | --- | --- | --- |
| D1 | 3.19 | 2.89 | 3.05 | >0 |
| D2 | 9.58 | 8.94 | 9.13 | >0 |
| D3 | 5.95 | 5.76 | 5.66 | >0 |
| 흰 원 전환율 F | 5.66% | **5.38%** | 5.49% | ≥5% |

- prompt 묶음 하한은 seed 1–5에서 F 5.27–5.48%, D1 2.87–2.98%다.
- **사전 판정은 묶음 bootstrap에서도 바뀌지 않는다**(confirmed / confirmed).
- README 71행 "여유가 있다"는 D1·D3에는 맞다. F는 여유가 0.66%p에서 약 0.3–0.5%p로 줄어 기준에 가깝다. 거짓은 아니므로 비차단이고, 이 민감도 값을 명시하도록 권고한다(H4).

### 7. 재실행 결정성

- GPU 상태: 시작 시 1%·1,221MiB였고, 실행 중 최대 31%였다.
- 전체 재실행은 exit 0, 3분 44초다. stdout 판정은 `{"targets": 671, "excluded": {"no_face": 469, "no_offface_room": 180}, "decision": {"white_disc_dependence": "confirmed", "face_occlusion_dependence": "confirmed"}}`다.
- `cmp` 결과 세 산출물이 모두 byte 동일하다. logit 최대 차이는 0.0이다.
- README 86행의 실행 시간 "약 4분"과도 정합한다.

### 8. 테스트·경계 행렬

- `tests/test_face_mask_ci.py`는 **19 passed**, exit 0이다. 전체 suite는 **91 passed**(경고 12), exit 0이다. 파이프 없이 exit code를 직접 기록했다.
- 경계 행렬(계약 분기 → 셀). 변이 번호는 9절을 본다.

| 계약 분기 | 잠금 셀 | 상태 |
| --- | --- | --- |
| confirmed: D1 하한 >0(엄격) | `test_white_disc_rule_three_levels[summary2]` | 잠김(M5) |
| confirmed: D2 하한 >0(엄격) | 경계값 0 케이스 없음(−1만) | **빈칸(M1 생존)** |
| confirmed: F 하한 ≥0.05(포함) | `[summary1]`·`[summary4]` | 잠김(M4) |
| confirmed에 D2 필요 | `[summary3]`·`[summary6]` | 잠김(M9) |
| suggestive: D1 점추정 >0(엄격) | `[summary5]` | 잠김(M6) |
| suggestive: D2 점추정 >0(엄격) | 경계값 0 케이스 없음 | **빈칸(M2 생존)** |
| suggestive: F 점추정 ≥0.05(포함) | 점추정=0.05 케이스 없음 | **빈칸(M3 생존)** |
| suggestive에 F 필요 | `[summary7]`, CLI `[0.65-0.6]` | 잠김(M10) |
| D3 하한 >0 / 점추정 >0 | `test_occlusion_rule_three_levels` | 잠김(M7, M8) |
| 전환: 조건 p ≥ thr(포함) | `test_per_image_…` | 잠김(M16) |
| 전환: 원본 p < thr(엄격) | 원본 = thr 케이스 없음 | **빈칸(M15 생존)** |
| 흰 원 전환이 흰 원 조건을 사용 | `test_per_image_…`, CLI | 잠김(M29) |
| calibration threshold 연결 | CLI `[0.65-0.6]` | 잠김(M22) |
| temperature 적용 | CLI 3케이스 | 잠김(M27) |
| 얼굴 선택: score > 넓이 > 위 | `test_pick_face_…` | 잠김(M12) |
| 얼굴 선택: 왼쪽 동점 | 같은 y·다른 x 케이스 없음 | **빈칸(M11 생존)** |
| `min_size_ratio` 필터(≥, 너비 기준) | `detect_face`를 쓰는 셀 없음(전부 monkeypatch) | **빈칸(M13·M14 생존)** |
| 대응표본·off-face 위치·제외 | `test_condition_edits_…`, CLI 2셀 | 잠김(M28) |
| splits 필터 | CLI | 잠김(M21) |
| test 부분집합 = test∪test_unseen | CLI | 잠김(M20) |
| val 부분집합 | CLI | 잠김(M30) |
| 공유 재추출 | `test_bootstrap_summary_…` doubled | 잠김(M18) |
| 구간 수준 0.95(백분위 2.5/97.5) | 수준을 고정하는 단언 없음 | **빈칸(M17·M26 생존)** |
| resamples 2000·seed 20261011 연결 | 없음 | **빈칸(M24·M25 생존)** |
| 판정 입력 = pooled | CLI 2번째 셀(test 부분집합 count 0 → KeyError) | 간접 잠김(M19) |
| 모델 sha256 검사 | CLI 2번째 셀 | 잠김(M23) |

- 판정 입력(M19)은 우연한 KeyError로만 잡힌다. 첫 CLI 셀에서는 모든 표본이 같은 값을 가져 pooled와 부분집합의 판정이 같기 때문이다. 부분집합과 pooled의 판정이 갈리는 CLI 케이스가 있으면 더 견고하다(H2).
- 복잡도: `bootstrap_summary`는 통계량 k개에 대해 O(B·n·k) 시간, draws 행렬 O(B·n) 메모리다(B=2000, n≤671, 약 10.7MB int64). 검출은 이미지당 1회로 O(N)이다. 모두 고정 상한이 있다.

### 9. 변이 테스트

- 사전 점검: 매 변이 전에 `git status --short`가 비어 있음을 assert했다. 복원은 `git checkout -- src/face_mask_ci.py`로 했고, 매번 clean을 재확인했다(30/30 clean). 종료 후 `git status --short`·`git diff --stat`도 비어 있다.
- 실행: 집중 파일 `tests/test_face_mask_ci.py`만 돌렸다.

| # | 변이 | 결과 | 실패 셀 |
| --- | --- | --- | --- |
| M1 | D2 하한 `>0`→`>=0` | **생존** | — |
| M2 | D2 점추정 `>0`→`>=0` | **생존** | — |
| M3 | F 점추정 `>=`→`>` | **생존** | — |
| M4 | F 하한 `>=`→`>` | 사망 | `white_disc_rule[summary1-confirmed]` |
| M5 | D1 하한 `>0`→`>=0` | 사망 | `white_disc_rule[summary2-suggestive]` |
| M6 | D1 점추정 `>0`→`>=0` | 사망 | `white_disc_rule[summary5-insufficient]` |
| M7 | D3 하한 `>0`→`>=0` | 사망 | `occlusion_rule[d31-suggestive]` |
| M8 | D3 점추정 `>0`→`>=0` | 사망 | `occlusion_rule[d32-insufficient]` |
| M9 | confirmed에서 D2 제거 | 사망 | `white_disc_rule[summary3]`, `[summary6]` |
| M10 | suggestive에서 F 제거 | 사망 | `white_disc_rule[summary7]`, CLI `[0.65-0.6]` |
| M11 | 왼쪽 동점 반전 `-f[0]`→`f[0]` | **생존** | — |
| M12 | 위 동점 반전 | 사망 | `test_pick_face_…` |
| M13 | min_size 필터 제거 | **생존** | — |
| M14 | min_size `>=`→`>` | **생존** | — |
| M15 | 원본 `< thr`→`<= thr` | **생존** | — |
| M16 | 조건 `>= thr`→`> thr` | 사망 | `test_per_image_…` |
| M17 | 구간 꼬리 2.5→5(90% 구간) | **생존** | — |
| M18 | 통계량별 독립 재추출 | 사망 | `test_bootstrap_summary_…` |
| M19 | `decide(subsets['test'])` | 사망 | `test_cli_excludes_…`(KeyError, 간접) |
| M20 | test 부분집합에서 test_unseen 제외 | 사망 | CLI 3케이스 |
| M21 | splits 필터 제거 | 사망 | CLI 4셀 |
| M22 | per_image threshold 0.5 | 사망 | CLI `[0.65-0.6]` |
| M23 | 해시 검사 제거 | 사망 | `test_cli_excludes_…` |
| M24 | resamples 연결 무시(200) | **생존** | — |
| M25 | seed 연결 무시(0) | **생존** | — |
| M26 | interval 연결 무시(0.9) | **생존** | — |
| M27 | temperature 미적용 | 사망 | CLI 3케이스 |
| M28 | 얼굴 밖 조건이 얼굴 원 사용 | 사망 | `test_condition_edits_…`, CLI 3케이스 |
| M29 | 흰 원 전환이 회색 조건 사용 | 사망 | `test_per_image_…`, CLI `[0.75-0.69]` |
| M30 | val 부분집합을 test로 | 사망 | CLI 3케이스 |

- 생존 변이(M1–M3, M11, M13–M15, M17, M24–M26)의 실제 실행값은 재실행·독립 재계산으로 올바르다고 확인했다. 결함은 산출물이 아니라 회귀 잠금이다.
- 이 중 M13·M14(`min_size_ratio`)는 본 데이터에서 효과가 0이다(5절).

## Issues / Risks

### Blocking (계약 의무)

- **B1 판정 규칙 경계 미잠금.**
  - 위치: `src/face_mask_ci.py:80,82`, `tests/test_face_mask_ci.py:73-84`. 계약: config 41–42행.
  - 잠기지 않은 경계: D2 하한 `>0`(M1), D2 점추정 `>0`(M2), F 점추정 `≥0.05`(M3).
  - 조치: `_summary(d2=(5, 0))` → suggestive, `_summary(d2=(0, -1))` → insufficient, `_summary(flip=(0.05, 0.01))` → suggestive 케이스를 추가한다.
- **B2 전환 정의의 원본 엄격 부등호 미잠금.**
  - 위치: `src/face_mask_ci.py:58-60`. 계약: config 31행 "원본 p < threshold".
  - 조치: `test_per_image_…`에 원본 = threshold(예 0.7)이고 조건 ≥ threshold인 표본을 넣고 전환 0을 단언한다(M15).
- **B3 얼굴 선택 "왼쪽" 동점 미잠금.**
  - 위치: `src/face_mask_ci.py:27`. 계약: config 21행.
  - 조치: `tests/test_face_mask_ci.py:17-24`에 같은 score·넓이·y, 다른 x인 두 상자를 두 순서로 넣어 왼쪽을 단언한다(M11).
- **B4 `min_size_ratio` 필터 미잠금.**
  - 위치: `src/face_mask_ci.py:36`. 계약: config 20행 "긴 변 ≥ 너비 × 0.04".
  - `detect_face`를 실제로 호출하는 셀이 없다.
  - 조치: `cv2.FaceDetectorYN.create`를 stub해 상자 목록(긴 변 = 너비×0.04 정확히, 그보다 작은 것, 높이만 긴 것)을 돌려주게 한다. 포함 경계와 너비 기준을 단언한다(M13, M14).
- **B5 bootstrap 구간 수준·반복 수·seed 연결 미잠금.**
  - 위치: `src/face_mask_ci.py:67,151-152`. 계약: config 33–36행.
  - 조치: `bootstrap_summary`에 결정적 입력을 넣는다. 그다음 `np.percentile(…, [2.5, 97.5])`를 직접 계산한 기대값과 low/high가 일치하는지 단언한다(M17).
  - 조치: CLI 셀에서 비상수 값으로 `pooled`의 low/high가 config의 resamples·seed·interval로 재계산한 값과 같은지 단언한다(M24–M26).

### Hardening recommendations (비차단)

- **H1** `report.json`에 config 사본(또는 sha256)과 git commit이 없다(`src/face_mask_ci.py:158-161`). P05 artifact처럼 `config`·`git_commit`을 기록하면 사전 고정본과 실행의 연결이 산출물 안에서 닫힌다.
- **H2** 판정 입력 = pooled(M19)는 빈 부분집합의 KeyError로만 잡힌다(`tests/test_face_mask_ci.py:169-177`). 부분집합과 pooled의 판정이 갈리도록 이미지별 예측값을 다르게 주는 CLI 케이스를 추가한다(`_fake_predict`가 split별로 다른 값을 내게 한다).
- **H3** YuNet 파라미터 전달(`src/face_mask_ci.py:34`의 score·nms·top_k 순서)은 단위 셀이 없다. 실제 데이터 재현(검출 1,320장 좌표 일치)으로만 확인됐다. B4의 stub에서 `create` 인자를 함께 단언하면 닫힌다.
- **H4** `experiments/p06_failure_analysis/face_mask_ci/README.md:71`의 "여유가 있다"에 prompt 묶음 bootstrap 민감도를 추가한다. F 하한은 5.38%(seed 1–5에서 5.27–5.48%)로, 여유가 약 0.3–0.5%p다. D1 2.89, D3 5.76이고 판정은 불변이다.
- **H5** `README.md:63`·`:73` 보완.
  - test 461장이 P06-02b 표본과 겹쳐 독립 반복이 아니라는 점을 밝힌다.
  - val(새 표본)만으로는 흰 원 전환율 점추정 4.76%로 규칙상 insufficient라는 점을 밝힌다.
- **H6** `README.md:23-24` 보완.
  - QA 표본의 image_id 목록을 저장하지 않아 재현할 수 없다. 목록을 산출물로 남긴다.
  - 미검출 중 "보이는 얼굴을 놓친" 비율을 보정한다. 본 검증 표본(z 제외)에서는 9/16, 주로 측면이었다.

## Outstanding items

- P06-02c 작업의 work log·HANDOFF·CHANGELOG·plan 진행 상황이 아직 갱신되지 않았다. config 2행이 주장하는 소유자 승인(YuNet, test∪val 합산, bootstrap 규칙)도 work log의 "User Decisions" 기록이 없다.
- 본 검증자는 저장소에 이 기록 파일만 추가했다. 커밋하지 않았다.

## Reproduction

```bash
cd /mnt/f/devel/Tracepecter
git status --short                              # 비어 있어야 함
git diff 60bad9a HEAD -- configs/face_mask_ci.yaml | wc -l   # 0
sha256sum /mnt/h/tracepector/checkpoints/face/face_detection_yunet_2023mar.onnx
docker compose run --rm -T dev python -m pytest tests/test_face_mask_ci.py -q; echo exit=$?
docker compose run --rm -T dev python -m pytest -q; echo exit=$?
S=<scratch>; sed 's#^output_dir: .*#output_dir: /scratch/rerun#' configs/face_mask_ci.yaml > $S/ci_rerun.yaml
docker compose --profile training run --rm -T -v $S:/scratch train python -m src.face_mask_ci --config /scratch/ci_rerun.yaml
for f in detections.csv predictions.csv report.json; do cmp experiments/p06_failure_analysis/face_mask_ci/$f $S/rerun/$f; done
# 변이: Methodology의 mutate.py와 같은 치환을 하나씩 적용 → 집중 파일 실행 → git checkout -- src/face_mask_ci.py → git status --short 비어 있음 확인
```

## 2차 추적 검증 (HEAD `a8812f2`)

### Subject metadata

- 날짜: 2026-10-11. 검증자는 1차와 같다(Claude Code, Opus 5.5, 독립).
- 대상 커밋:
  - `5fe461e`: 테스트 추가와 `report.json`의 `config`·`git_commit` 기록
  - `2670a30`: 1차 기록 커밋. 본 검증자 원문과 같다(`git diff HEAD`로 확인).
  - `b980841`: README 보완과 `qa_sample.json` 추가
  - `a8812f2`: `report.json` 재생성
- 시작 시 작업 트리는 clean이었다. 정본 계약은 1차와 같다. `configs/face_mask_ci.yaml`은 `60bad9a` 이후 바뀌지 않았다.

### Scope

1. B1–B5 잠금 셀
2. 코드 변경(`src/face_mask_ci.py`)
3. 재생성 산출물과 재실행 결정성
4. H1–H6 반영 주장(README·`qa_sample.json`)의 1차 자료 대조
5. 변이 테스트(1차 30개 재실행과 신규 6개)
6. 집중·전체 suite

### Methodology

```bash
git diff 97aaf12 HEAD -- src/face_mask_ci.py configs/ tests/test_face_mask_ci.py experiments/p06_failure_analysis/face_mask_ci/
# report.json: 97aaf12 판과 키별 비교, config 사본 == yaml
# qa_sample.json: 정렬한 검출/미검출 id 목록에 random.Random(20261011) 하나로 found 40 → miss 20 순서 sample을 적용해 재현 시도
# P06-02b 겹침: face_mask/detections.csv의 test·test_unseen GEN 얼굴 검출(581)과 ci 대상 test 461의 교집합
# 미검출 QA 비-z 8장 육안 확인($S/qa_miss.jpg)
# GPU 상태: 4–41%, 약 1GB(ai_writte_system 가동 중, 고부하 아님). 그다음 재실행:
docker compose --profile training run --rm -T -e GIT_COMMIT=b9808418b23a7438c486e3dcfd907413aeb32b8f -v $S:/scratch train python -m src.face_mask_ci --config /scratch/ci_rerun2.yaml
docker compose run --rm -T dev python -m pytest tests/test_face_mask_ci.py -q; echo exit=$?
python3 $S/mutate2.py     # 매 변이 전 git status --short 비어 있음 assert, 복원 후 clean 재확인
docker compose run --rm -T dev python -m pytest -q; echo exit=$?
```

### Findings

**코드 변경**
- 코드 변경은 `src/face_mask_ci.py:8,159-160`뿐이다. `report`에 `config=settings`와 `git_commit=os.environ.get('GIT_COMMIT')`를 더했다. 계산 경로는 바뀌지 않았다.

**Blocking 해소 확인**

| 1차 항목 | 추가 셀 | 확인 |
| --- | --- | --- |
| B1 D2 하한·점추정 엄격, F 점추정 포함 | `test_white_disc_rule_three_levels`의 `d2=(5,0)`→suggestive, `flip=(0.05,0.01)`→suggestive, `d2=(0,-1)`→insufficient | M1·M2·M3 사망 |
| B2 원본 `< thr` 엄격 | `test_per_image_…`의 원본 = thr → 0, thr−0.01 → 1 | M15 사망 |
| B3 왼쪽 동점 | `test_pick_face_…`의 같은 score·넓이·y 두 순서 | M11 사망 |
| B4(+H3) 너비 기준·포함 경계·YuNet 인자 | `test_detect_face_filters_small_boxes_by_width_inclusive_and_passes_yunet_settings` | M13·M14·M31·M34·M36 사망 |
| B5 구간 수준·연결 | `test_bootstrap_summary_…` 직접 백분위 대조(0.95, 0.9); `test_cli_decides_on_pooled_targets_with_configured_bootstrap` 인자 spy | M17·M24·M25·M26 사망 |

- B4 셀은 YuNet stub이 세 상자를 돌려준다.
  - 3.9×3.9(score 0.99)는 너비 100×0.04 = 4 미만이라 제외된다.
  - 3×6(긴 변 6)은 높이 기준(8)이면 제외되지만, 너비 기준이라 남는다.
  - 4×4는 경계에 정확히 걸리고 포함된다.
  - 이 구성은 필터 제거·부등호 완화·높이 기준 세 방향을 각각 깬다.
- H2 셀은 val 표본을 흰 > 회색 > 얼굴 밖으로, test_unseen 표본을 그 반대로 둔다.
  - 그 결과 val 부분집합은 confirmed, test 부분집합은 insufficient, pooled는 suggestive다.
  - pooled가 suggestive인 이유: n=2라 F 하한이 0이다.
  - 판정 입력을 test·val로 바꾼 변이 M19·M35가 이 셀에서 직접 죽는다(1차의 KeyError 간접 잠금 해소).

**산출물·재실행**
- `report.json`(a8812f2)은 97aaf12 판과 비교해 키 `config`·`git_commit`만 추가됐다. 나머지 키는 전부 같다. `config` 사본은 `configs/face_mask_ci.yaml`과 같다.
- `detections.csv`·`predictions.csv`는 97aaf12 이후 변경이 없다.
- GPU 재실행(`GIT_COMMIT=b980841…`)은 exit 0, 3분 40초다.
  - `detections.csv`·`predictions.csv`가 byte 동일하다.
  - `report.json`은 `config.output_dir`(scratch 경로)만 다르다.
  - 기록된 `git_commit`의 코드는 HEAD와 같다(b980841 이후 코드 변경 없음).

**H4 — prompt 묶음 bootstrap**
- 묶음 수 99, 최대 27장이 README와 일치한다.
- README 구간: D1 [2.92, 5.08], D3 [5.65, 9.36], F [5.36%, 10.07%].
- 본 검증자 구간(묶음 합/표본 수 방식): D1 [2.89, 5.09], D3 [5.76, 9.32], F [5.38%, 10.11%].
- 차이는 재추출 방식의 Monte Carlo 차이 범위다(1차에서 seed 1–5의 F 하한이 5.27–5.48%). "여유 0.36%p"와 판정 불변은 정합한다.

**H5**
- val 단독 점추정 4.76% → insufficient가 맞다(1차 재계산).
- test 대상 461장 중 390장이 P06-02b의 GEN 얼굴 검출 581장과 겹친다. 재계산 결과가 같다.

**H6 — QA 표본 재현**
- `qa_sample.json`은 다음 절차로 정확히 재현된다: 정렬한 검출 id 851개와 미검출 id 469개에 `random.Random(20261011)` 하나를 쓰고, found 40을 먼저 뽑은 뒤 miss 20을 뽑는다(found·miss 둘 다 일치). 다른 순서·독립 rng로는 재현되지 않는다.
- miss 20장의 생성기는 z_image_turbo 12, sd35_medium 6, qwen_image_21 2다. README의 "12장 z"가 맞다.
- 비-z 8장 육안 결과:
  - 보이는 얼굴 4장은 `miss_visible_face`와 같다. 002889는 고개 숙인 3/4 얼굴, 002659·002923은 측면, 000588은 어깨 너머 얼굴이다.
  - 나머지 4장(002767·002721 목 아래 크롭, 000936 뒷모습, 000685 뒤돌아선 원경)은 얼굴이 사실상 보이지 않는다.
- 본 검증자 1차 기록 정정: 5절에서 gen_000685를 "정면에 가까운" 보이는 얼굴로 셌다. 다시 보면 뒤돌아 고개만 약간 돌린 원경이라 경계 사례다. 1차 표본의 보이는 얼굴은 8–9/16이다. README의 "약 절반" 문구는 이 범위와 정합한다.

**테스트**
- 집중 파일은 **24 passed**, exit 0이다. 전체 suite는 **96 passed**(경고 12), exit 0이다.

### 변이 테스트(2차)

- 사전 점검: 매 변이 전에 `git status --short`가 비어 있음을 assert했다. 복원은 `git checkout -- src/face_mask_ci.py`로 했고, 36/36 clean을 재확인했다.
- 1차 M1–M30을 다시 돌렸다. 1차 생존 11개는 이제 모두 죽는다. 기존 사망 19개도 그대로 죽는다.

| # | 변이 | 실패 셀 |
| --- | --- | --- |
| M1 | D2 하한 `>=0` | `white_disc_rule[summary5-suggestive]` |
| M2 | D2 점추정 `>=0` | `white_disc_rule[summary9-insufficient]` |
| M3 | F 점추정 `>` | `white_disc_rule[summary6-suggestive]` |
| M11 | 왼쪽 동점 반전 | `test_pick_face_…` |
| M13 | min_size 필터 제거 | `test_detect_face_…` |
| M14 | min_size `>` | `test_detect_face_…` |
| M15 | 원본 `<= thr` | `test_per_image_…` |
| M17 | 구간 꼬리 5% | `test_bootstrap_summary_…` |
| M19 | `decide(subsets['test'])` | `test_cli_decides_on_pooled_…`, `test_cli_excludes_…` |
| M24 | resamples 200 | `test_cli_decides_on_pooled_…` |
| M25 | seed 0 | `test_cli_decides_on_pooled_…` |
| M26 | interval 0.9 | `test_cli_decides_on_pooled_…` |
| M31(신규) | YuNet score·nms 인자 교환 | `test_detect_face_…` |
| M32(신규) | `git_commit=None` | `test_cli_decides_on_pooled_…` |
| M33(신규) | `config=None` | `test_cli_decides_on_pooled_…` |
| M34(신규) | min_size 높이 기준 | `test_detect_face_…` |
| M35(신규) | `decide(subsets['val'])` | `test_cli_decides_on_pooled_…` |
| M36(신규) | YuNet 입력 크기 (h, w) | `test_detect_face_…` |

- 나머지 M4–M10, M12, M16, M18, M20–M23, M27–M30은 1차와 같은 셀(또는 그 셀에 새 셀이 더해진 조합)에서 죽는다. 전체 출력은 `$S/mutations2.log`에 있다.

### Issues / Risks (2차)

**Blocking**
- 없음.

**Hardening recommendations(비차단)**
- **R-H1** `experiments/p06_failure_analysis/face_mask_ci/README.md:76`의 "look_group은 GEN에서 모두 단독"은 정확하지 않다. `data/metadata.csv`의 GEN 3,000행은 look_group이 전부 비어 있다(NaN, 고유값 0). "비어 있어 묶음이 정의되지 않는다"로 바꾼다. 결론(묶음 단위 = 이미지 단위)은 같다.
- **R-H2** `experiments/p06_failure_analysis/face_mask_ci/qa_sample.json:2`의 `note`에 추출 절차를 적는다. 정렬한 id 목록, 하나의 `random.Random(20261011)`, found → miss 순서다. 이 절차 없이는 seed만으로 재현되지 않는다.
- **R-H3** README의 묶음 bootstrap 값은 사후 계산이고, 이를 만든 코드가 저장소에 없다. 재현용 스크립트나 명령을 남기면 이 수치도 다른 수치처럼 재계산할 수 있다.

### Outstanding items(2차)

- P06-02c의 work log·HANDOFF·CHANGELOG·plan 진행 상황 갱신과, config 2행 소유자 승인의 "User Decisions" 기록은 아직 없다(1차와 같음).
- 이 2차 절은 본 검증자가 기록 파일에만 추가했다. 커밋하지 않았다.

### Reproduction(2차)

```bash
cd /mnt/f/devel/Tracepecter && git status --short   # 비어 있어야 함
docker compose run --rm -T dev python -m pytest tests/test_face_mask_ci.py -q; echo exit=$?   # 24 passed
docker compose run --rm -T dev python -m pytest -q; echo exit=$?                              # 96 passed
sed 's#^output_dir: .*#output_dir: /scratch/rerun2#' configs/face_mask_ci.yaml > $S/ci_rerun2.yaml
docker compose --profile training run --rm -T -e GIT_COMMIT=$(git rev-parse b980841) -v $S:/scratch train python -m src.face_mask_ci --config /scratch/ci_rerun2.yaml
cmp experiments/p06_failure_analysis/face_mask_ci/predictions.csv $S/rerun2/predictions.csv
# 변이: 위 표의 치환을 하나씩 적용 → 집중 파일 → git checkout -- src/face_mask_ci.py → git status --short 비어 있음
```

## 3차 확인 (HEAD `d7a09f2`)

### Subject metadata·Scope

- 대상 커밋:
  - `3856f5e`: 묶음 bootstrap 스크립트, look_group 문구, QA 추출 절차. 본 기록 2차 절도 이 커밋에 들어갔으며, 삭제 줄은 0이다.
  - `d7a09f2`: work log·CHANGELOG·plan·HANDOFF 갱신
- 시작 시 작업 트리는 clean이었다.
- 범위:
  1. 코드 무변경
  2. R-H1–R-H3
  3. 기록 4종의 정합성
- 코드 변경이 없어 변이 테스트는 하지 않았다.

### Methodology

```bash
git diff a8812f2 HEAD --stat; git diff a8812f2 HEAD -- src tests | wc -l     # 0
git diff a8812f2 HEAD -- experiments/ CHANGELOG.md HANDOFF.md docs/plan/phase_6_failure_analysis.md docs/daily_logs/2026-10-11/work_log.md
docker compose run --rm -T dev python scripts/p06_02c_cluster_bootstrap.py; echo exit=$?    # 파이프 없이 exit 확인
python3 -c "…sorted 검출/미검출 id → random.Random(20261011): sample(found,40), sample(miss,20) == qa_sample.json"
```

### Findings

- **코드**: `src/`·`tests/`는 0줄 변경이다. 2차의 변이 결과(36/36 사망)와 테스트 결과(24/96 passed)가 그대로 유효하다.
- **R-H1**: `experiments/p06_failure_analysis/face_mask_ci/README.md:76`이 "look_group은 GEN 3,000행 모두 비어 있어 묶음을 정의할 수 없다"로 바뀌었다. metadata 집계(GEN 3,000행 NaN, 고유값 0)와 일치한다.
- **R-H2**: `qa_sample.json:2`의 note에 추출 절차가 적혔다(정렬한 id 목록, 하나의 `random.Random(20261011)`, found 40 → miss 20). 그 절차대로 재실행하면 found·miss가 모두 일치한다(`True True`, 검출 1,320행).
- **R-H3**: `scripts/p06_02c_cluster_bootstrap.py`
  - 입력: temperature·threshold와 `config.bootstrap`(seed·resamples·interval)을 모두 `report.json`에서 읽는다(16–18행, 33–36행).
  - 실행: exit 0. 출력은 `clusters 99, max_cluster 27, D1 [2.9179, 5.0791], D3 [5.6534, 9.3552], flip [0.0536, 0.1007]`다.
  - README 71–74행의 D1 [2.92, 5.08], D3 [5.65, 9.36], F [5.36%, 10.07%], 여유 0.36%p와 일치한다.
- **기록 정합성**:
  - `docs/daily_logs/2026-10-11/work_log.md` P06-02c 절의 수치가 `report.json`·README와 같다. 대상 671(469/180), +12.54/+8.60/+1.19, D1 +3.94 [3.19, 4.72], D3 +7.41 [5.95, 8.88], F 7.6% [5.7, 9.5], 묶음 하한 5.36%다.
  - 커밋 순서(`60bad9a` → `19ee42a` → `97aaf12`), 1차 생존 11개 → 2차 36개 사망·합격, 24/96 passed도 본 기록과 같다.
  - Decisions에 소유자 결정(YuNet, test∪val 합산과 val 별도 보고, 구간 판정)과 GPU 실행 기준(다른 컨테이너가 떠 있어도 점유가 낮으면 실행)이 기록됐다.
  - `CHANGELOG.md:31`, `docs/plan/phase_6_failure_analysis.md:78-82`, `HANDOFF.md`의 다음 작업 1(P06-04)과 GPU 주의 문구도 같은 수치·결정·판정을 쓴다. 모순은 없다.

### Issues / Risks (3차)

**Blocking**
- 없음.

**Hardening recommendations(비차단)**
- **T-H1** work log의 구현자 변이 표(`docs/daily_logs/2026-10-11/work_log.md`, "P06-02c 변이 테스트" 표)가 "M27 YuNet 인자 순서"라고 쓴다. 본 기록의 M27은 "temperature 미적용"이고, YuNet 인자 교환은 M31이다. 같은 M 번호가 다른 변이를 가리키므로 구현자 측 번호를 C 계열로 바꾸거나 "검증자 M31"로 적는다.
- **T-H2** `CHANGELOG.md:31`의 "독립검증 합격(2라운드)"는 합격 판정 시점 기준으로는 맞다. 이 3차 확인까지 포함하려면 "3라운드"로 바꾼다.
- 본 기록 자체의 정정: 1차 Verdict 줄의 "변이 8개가 생존"은 경계 항목 8개를 센 것이다. 생존 변이 수는 11개다(1차 9절 표 기준). work log의 "11개"가 맞다.

### Outstanding items(3차)

- 없음(기록 갱신 완료). 이 3차 절과 상단 Verdict 갱신은 커밋하지 않았다.

### Reproduction(3차)

```bash
cd /mnt/f/devel/Tracepecter
git diff a8812f2 HEAD -- src tests | wc -l          # 0
docker compose run --rm -T dev python scripts/p06_02c_cluster_bootstrap.py; echo exit=$?
```

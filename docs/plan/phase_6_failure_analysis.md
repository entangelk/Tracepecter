# P06 — Failure analysis

**상태:** In Progress (2026-10-09 계획 승인)

## 목표·선행 조건

§27 Phase 6에 따라 고정 primary SigLIP checkpoint(`checkpoints/baseline/best.pt`)와 [P05 calibration artifact](../../experiments/p05_calibration/calibration.json)로 오류 사례를 자동 저장하고, 수동 검토로 오류 패턴을 문서화한다. 아울러 §20의 "특정 source만 보고 판단하지 않음" 조건을 확인하기 위해 [결과 해석 분석](../../experiments/p03_comparison/analysis_2026-10-09.md)이 제기한 데이터 제작 조건 편향 가설(압축·크기·종횡비·구도)을 통제 진단한다. 모델·temperature·threshold·split은 바꾸지 않는다.

## 범위·검증

1. **P06-01 표본별 예측·오류 자동 저장** → `reports/errors/{false_positive,false_negative,low_confidence}/`에 score·label·category·source·generator·split 기록. 검증: 저장된 오류 수가 P05 `metrics.json`의 calibrated threshold 기준 오분류 수(A 5, B 11)와 일치, 공유 REAL은 이미지 ID 기준 중복 제거 후 고유 수 보고.
2. **P06-02 편향 통제 진단** → 고정 모델에 아래 조건을 적용해 Test A/B의 generator/source별 ROC-AUC·클래스별 score 변화·threshold 판정 전환을 기록. 검증: 원본 조건 재현값이 P05 지표와 일치, 변환 결정성(같은 입력 → 같은 출력).
3. **P06-03 검토군 구성·수동 검토** → DB-05 결정에 따라 최소 100개 검토군을 만들고 사례별로 구조화된 관찰(구도·배경·얼굴 노출·조명/보정·생성 결함 등)을 기록.
4. **P06-04 오류 패턴 문서** → 패턴별 빈도·대표 사례·다음 데이터 수집 방향. DB-03 얼굴 재검 트리거 판정, Test B NLL/Brier 악화의 표본별 분해(어떤 표본의 loss가 temperature로 커졌는가)를 포함.

## 실험 전 정의

- REAL=1(positive). `false_positive` = GEN인데 `p_cal >= threshold`, `false_negative` = REAL인데 `p_cal < threshold`. `p_cal`·threshold는 P05 artifact에서 읽는다.
- `low_confidence` = 오분류가 아니면서 score가 [10, 90]인 표본. 경계값은 config가 소유한다. validation에서 이 구간이 9장뿐이므로 표본 수가 적을 것으로 예상하며 결과를 그대로 보고한다.
- 대상 집합: Test A(800) + Test B(1,048), 공유 REAL 448은 한 번만 집계한다(고유 1,400장). validation(820)은 threshold/temperature fitting에 쓰였으므로 별도 표시하여 검토 보충용으로만 쓴다.
- 통제 조건(양 클래스 동일 적용, 모델 입력 직전 기존 평가 전처리 유지):
  - C0 원본(재현 기준)
  - C1 JPEG 재인코딩 q=90, C2 q=75
  - C3 공통 다운스케일(긴 변 512, bicubic) 후 기존 전처리
  - C4 중앙 정사각 crop 후 기존 전처리(종횡비 왜곡 제거)
  - C5 GEN만 JPEG 재인코딩(q는 REAL 양자화 테이블에서 추정한 대표 품질) — GEN score가 REAL 쪽으로 이동하면 JPEG 흔적 의존 근거
- 종횡비 층화: 원본 h/w가 1.0인 표본만으로 A/B AUC를 따로 계산한다. GEN은 h/w 1.0(1,500)·1.46(1,500) 두 종류뿐이고 REAL에는 가로형 0.67(237) 등 GEN에 없는 비율이 있다(2026-10-09 헤더 전수 집계).
- 해석 규칙: 양 클래스 동일 변환에서의 AUC 하락은 "단서 의존" 또는 "정보 손실" 모두로 설명될 수 있으므로 단독으로 원인을 확정하지 않는다. C5처럼 한 클래스만 바꾼 조건과 C4·종횡비 층화처럼 정보 손실이 작은 조건을 함께 보고 판단한다. 이 진단 결과로 모델·threshold를 조정하지 않는다.

## 계약·소유권

label/split/category/source/generator는 canonical `data/metadata.csv`, temperature/threshold는 P05 artifact가 소유한다. `reports/errors/`의 manifest CSV는 `image_id`·split·조건·logit만 저장하고 나머지 metadata는 조인으로 읽어 덧붙인 파생 보고물이다. 이미지 사본은 Git 비추적(데이터 정책과 동일), manifest와 문서만 추적한다. 진단 조건·low_confidence 경계는 `configs/failure_analysis.yaml`이 소유한다.

## 완료 조건

- `reports/errors/` 자동 저장 동작 및 P05 오분류 수와의 일치.
- 통제 진단 결과 기록(조건별·generator/source별 AUC, score 변화, 판정 전환, 해석 한계).
- DB-05 기준을 충족하는 ≥100 사례 수동 검토 기록. 오류와 보충 사례를 구분해 보고한다.
- 오류 패턴 문서와 다음 데이터 수집 방향, DB-03 얼굴 트리거 판정, Test B calibration 악화 분해.

## 제외·병행

- 제외: 재학습·LoRA(P04)·threshold/temperature 재선정·split 변경·신규 데이터 수집·최종 holdout 구축·사람 pairwise 평가(§21).
- 병행 후속(별도 항목): GEN pHash/embedding 근사중복 점검, 미사용 최종 REAL/FAKE holdout 설계. P06 결과가 이들의 설계 입력이다.
- GPU 작업은 소유자 작업이 없을 때만 수행하고 큐잉하지 않는다(추론만 필요, 조건당 고유 1,400장).

## 관련 결정 브리프

- [DB-05](../decision_briefs/DB-05_P06_review-set.md) — Resolved: 오류 전수 + 보충 ≥100(유형 구분, 실제 오류 수 별도 보고), 에이전트 1차 검토 + 소유자가 오류 전수·무작위 20건 확인(2026-10-09).
- [DB-03](../decision_briefs/DB-03_P01_face-policy.md) — Resolved(A 무처리), P06-04에서 얼굴 집중 오류 시 재상정 트리거.
- [DB-04](../decision_briefs/DB-04_P02_unseen-real.md) — Resolved, Test B 구성 유지.

## 진행 상황

- **P06-01·P06-02 완료**(2026-10-09, `35db1fb`·`eb246ea`) — [결과](../../experiments/p06_failure_analysis/README.md). 오분류 수가 P05와 같다(A 5, B 11, test 고유 12, val 3). low_confidence는 24장이다. JPEG·다운스케일·종횡비 통제에서는 AUC 변화가 미미했다(JPEG 흔적 의존의 근거는 약함). 중앙 정사각 crop에서는 sd35 GEN 11장이 FP로 바뀌었다(구도·크롭 민감, 정보 손실과 분리되지 않음).
- Test B NLL/Brier 악화 분해(P06-04 일부): 악화된 표본 12장이 전부 logit이 양수인 sd35_medium GEN이다.
- **P06-03 검토군 확정**(이미지 열람 전 `configs/failure_analysis.yaml`의 `review_set`에 규칙 고정, `scripts/build_review_set.py`) — `reports/errors/review_set.csv` **103건**: FP 10 · FN 5 · low_confidence 24 · 통제 조건 판정 전환 10 · 층화 고확신 54(GEN 생성기별 6, REAL 부위별 6). 소유자 확인 대상 35건 = 오류 15 전수 + 보충 무작위 20(seed 42).
- 검토 도구: `scripts/build_review_page.py`가 `scripts/review_page.html` 템플릿으로 정적 페이지 `reports/errors/review/index.html`(원본 이미지 사본 포함, Git 비추적)을 만든다. Windows 브라우저에서 파일로 연다(WSL 로컬 서버는 방화벽에 막혀 폐기). 소유자 판정은 `reports/errors/review_owner.csv`, 에이전트 1차 검토는 `reports/errors/review_agent.csv`에 같은 schema(`image_id,perceived,cues,agent_agreement,note,updated_at`)로 저장한다.
- **P06-03 수동 검토 완료**(2026-10-10). 소유자 확인 35건이 먼저 끝났다(`review_owner.csv`, 판정·단서 35/35). 그 뒤 에이전트가 소유자 결과를 열지 않고 103건 1차 검토를 했다(`review_agent.csv`). 라벨·파일명·형식이 드러나지 않게 이미지를 무작위 번호 JPEG 사본으로 바꿔 판정했다.
  - 에이전트 103건: REAL 33건 전부 `photo_like`. GEN 70건은 `synthetic_like` 45, `ambiguous` 23, `photo_like` 2(qwen_image_21 FP 2건).
  - 소유자·에이전트 일치(35건): 체감 판정 19/35 일치. 정반대 판정(photo↔synthetic)은 5건이다. 나머지 불일치 11건은 한쪽이 `ambiguous`이며, 대부분 소유자가 `synthetic_like`, 에이전트가 `ambiguous`였다(에이전트가 보수적). 단서 Jaccard 평균은 0.28이다.
  - 순서가 계획(에이전트 → 소유자)과 반대여서 `agent_agreement` 칸은 비어 있다. 동의 여부는 두 판정을 비교해 계산하므로 별도 입력은 받지 않는다.
  - P06-04 가설 후보: REAL에만 데이터셋 익명화용 흰 원형 얼굴 가림이 있다. 이 가림이 있는 비율은 고확신 REAL 11/24, 오류·경계 REAL 2/9다. 모델이 이 가림을 REAL 단서로 쓸 수 있다(표본이 적어 확정하지 않음).
- **P06-02b 원형 얼굴 가림 의존 진단**(소유자 승인 2026-10-10). 모델 결과를 보기 전에 [`configs/face_mask_diagnostic.yaml`](../../configs/face_mask_diagnostic.yaml)에 검출 기준·조건·판정 규칙을 고정했다. 구현은 `src/face_mask.py`이고, 의존성으로 `opencv-python-headless==4.13.0.92`를 추가했다(4.12는 numpy<2.3 제약 때문에 쓸 수 없음).
  - A 단축 단서 베이스라인(GPU 불필요): 6,000장 전체에서 흰 원을 검출해 클래스·split별 출현율을 센다. "원 있음 → REAL" 규칙 하나로 Test A/B AUC를 낸다. REAL을 원 유무로 나눠 모델 score·FN을 비교한다.
  - B 개입 실험(Test A ∪ B, 추론만): GEN 얼굴에 흰 원(주 조건), 회색 원(가림 대조), 얼굴 밖 흰 원(위치 대조)을 그린다. REAL의 흰 원은 회색으로 바꾼다.
  - 사전 판정: 주 조건의 GEN score 상승이 두 대조보다 각각 크고, 대상 GEN의 5% 이상이 REAL 판정으로 바뀌면 "의존 근거 있음"으로 본다.
  - 검출기는 검토군 103장에 맞춰 정했다(눈 판정 원 13/13, 오검출 0). 따라서 그 밖의 표본을 따로 육안 확인해 보고한다.
- **P06-02b 결과**([보고서](../../experiments/p06_failure_analysis/face_mask/README.md)).
  - 사전 규칙상 **의존 근거 있음**: GEN 얼굴에 흰 원을 그리면 +10.19점, 전환 36/581(6.2%)이다. 대조는 회색 원 +7.20(28), 얼굴 밖 흰 원 +1.91(5)이다.
  - 효과의 약 70%는 가림 일반에서 나온다. 모델은 "얼굴이 보이지 않음"을 REAL 단서로 쓰고, 흰색에만 있는 추가분은 작다.
  - 단축 규칙 단독 AUC는 약 0.64~0.65다. REAL 원 출현율은 약 25~31%이고, 실제 GEN 원은 0장이다(GEN 검출 37장은 전부 오검출).
- 다음: P06-02b 독립검증 → P06-02c 표본 확장 재진단(새 config로 사전 고정: val 포함, 얼굴 검출 개선, bootstrap 신뢰구간) → P06-04 패턴 문서(불일치 16건 재확인, 얼굴 노출·구도 편향 정리, DB-03 얼굴 트리거 판정 포함).

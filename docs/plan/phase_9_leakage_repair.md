# P09 — 동일 룩 누출 수리와 재학습

**상태:** In Progress (P09-01~03 Complete, P09-04 진행 중). [후보 생성·검토 기록](../../experiments/p09_leakage_repair/r1/grouping/README.md). 새 metadata와 [사전등록](../../experiments/p09_leakage_repair/r1/diagnostic/README.md)으로 [10epoch 학습 결과](../../experiments/p09_leakage_repair/r1/training/README.md)를 고정했다. 재보정·새 cohort 주석/진단 실행기를 준비 중이며 채택 검토는 대기다. 소유자는 [DB-07](../decision_briefs/DB-07_P09_review-coverage.md)에서 우선순위 검토와 미검토 범위 명시를 선택했다.

## 목표와 근거

[누출 감사](../../experiments/p08_anonymized/leakage_audit/README.md)에서 드러난 REAL 동일 룩의 train/val/test 교차를 그룹 보강으로 수리한다. `docs/project.md` §8·§13·§14의 기존 독립성 요구를 충족하기 위한 후속 페이즈이며, P08의 split 불변 범위 밖에서 진행한다. P08-01~06의 완료·사전등록 결과는 소급 변경하지 않는다.

확인된 8쌍(test 4·val 4)은 하한이다. 알려진 test 4장만 제외하거나 pHash≤10·cosine≥.99로 자르면 수리가 아니다. 재분할한 기존 6,000장은 개발 과정에 노출됐으므로 수리 후에도 **개발 평가**다. 새 미접촉·출처 독립 holdout에서의 일반화는 이 페이즈가 증명하지 않는다.

## 선행 조건과 보존

- 기준 문서: [SoT 우선순위](../sot.md), [P01](phase_1_data_pipeline.md), [P08](phase_8_face_anonymization.md), [감사 검증 기록](../verifications/2026-10-20/test_leakage_adversarial.md).
- 감사의 `audit_lock.json`에 고정된 metadata·source·원자료 hash를 먼저 검증한다. 파일이 없거나 hash가 다르면 이유를 확인하기 전 재사용하지 않는다. 기존 감사 코드를 고쳐 lock을 덮어쓰지 않는다.
- 기존 `data/metadata.csv`, `configs/primary.yaml`, `checkpoints/anonymized/best.pt`, P08 calibration·진단·301장 소유자 주석 원본/변환본/최종본과 감사 디렉터리 전체를 보존한다. P05 baseline·DINO도 변경하지 않는다.
- 원본 이미지·ID·label·category·generator·익명화 규격을 유지한 6,000장 재배정을 기본 범위로 한다. 삭제·신규 수집·encoder 변경·LoRA·데모 구현은 제외한다. 그룹 때문에 목표 비율이 어려워도 그룹을 쪼개거나 몰래 표본을 빼지 않는다.

## 계약의 소유권과 데이터 흐름

metadata의 12열 schema 소유자는 `docs/project.md` §12다. 새 열을 추가하지 않고 REAL `look_group`과 전체 `split`만 새 버전에서 유도한다. `prompt_id`를 실제 전체 prompt의 대용으로 쓰지 않는다.

| 값 | 정본·변경 권한 | 파생·소비 경로 |
| --- | --- | --- |
| 원본 ID·경로·label 등 | 보존된 기존 metadata·이미지 | 새 metadata에 원래 값 유지; loader는 기존 schema 소비 |
| REAL 동일 룩 관계 | 새 검토 기록의 이미지 쌍·판정·근거, 검토자가 확정 | 확정 관계 + 옛 그룹/미확정의 공동 배정 제약 → 배정 매핑 → `look_group` |
| GEN 렌더 계보 | 원본 PNG graph의 full positive prompt·noise seed·generator | 보존된 `generation_provenance.json`을 원본 hash 확인 후 참조; 계보 교차 보고 |
| 새 split | 고정한 그룹 매핑·분할 규칙 | 새 metadata의 `split`이 학습·평가·calibration의 유일한 배정 정본 |
| 얼굴 상자 | P08 `face_boxes.csv`의 이미지·검출기 hash 결합 | 원본 불변 시 재사용; split을 상자 캐시에 복제하지 않음 |
| checkpoint·보정 | 새 학습 checkpoint와 이에 결합한 calibration artifact | config와 metadata hash로 계보 확인; 기존 primary 전환은 별도 채택 결과 이후 |

쌍별 검토, 연결 성분, metadata는 각각 근거·그룹 투영·소비용 투영이다. 그룹 매핑과 metadata를 따로 수작업 수정하지 않는다. GEN 계보는 metadata에 중복 저장하지 않는다. 구현 착수 시 실제 소비자인 `scripts/split_dataset.py`, `src/dataset.py`, `src/train.py`, `src/calibrate.py`, `src/evaluate.py`, `src/score.py`와 관련 테스트의 계약을 대조한다.

## 버전별 경로

아래 버전 경로를 사용하며 기존 출력 기본값으로 실행하지 않는다. r1의 최종 입력 고정 지점은 `grouping/final/group_lock.json`이다. 검토 중 배치별 `input_lock.json`은 해당 배치만 고정하고 후속 검토는 새 배치로 추가한다. 고정된 배치는 덮어쓰지 않으며 최종 그룹 lock 이후 규칙·검토·입력이 바뀌면 r2로 올린다.

| 산출물 | r1 경로 | 내용 |
| --- | --- | --- |
| 그룹·분할 근거 | `experiments/p09_leakage_repair/r1/grouping/` | input lock, 후보 목록, 쌍별 판정, 그룹 매핑, GEN 계보 교차, split 보고서 |
| metadata | `data/versions/p09_r1/metadata.csv` | 기존 schema, 6,000 ID 유지, 갱신된 REAL 그룹과 split |
| 학습 설정 | `configs/p09_r1_train.yaml` | 새 metadata·출력 경로 지정, 기존 `configs/anonymized.yaml`의 모델/학습/익명화 설정 유지 |
| checkpoint | `checkpoints/leakage_repair/r1/{best,last}.pt` | 새 head 학습·재개 상태, 새 metadata와 익명화 규격 결합 |
| 학습 보고 | `experiments/p09_leakage_repair/r1/training/` | config snapshot·hash·epoch log·split별 실제 sample ID 근거 |
| 보정 설정 | `configs/p09_r1_calibration.yaml` | 새 checkpoint와 전용 calibration 출력 경로 |
| 보정·평가 | `experiments/p09_leakage_repair/r1/calibration/` | `calibration.json`, val logit·새 Test A/B 지표와 입력 hash |
| 채택 진단 | `experiments/p09_leakage_repair/r1/diagnostic/` | 새 cohort에 맞춘 사전등록과 결과; 기존 P08 진단 파일 재사용/덮어쓰기 금지 |

checkpoint 경로는 Compose의 기존 checkpoint mount 안이다. 실제 실행 전 mount·가용 용량·쓰기 경로를 확인한다. 대량 embedding·검토 이미지 사본은 `reports/errors/review/p09_leakage_repair/r1/`에 두고 Git에는 근거 CSV/JSON과 재현 방법만 남긴다.

## 슬라이스와 통과 기준

| ID | 작업 | 선행 조건 | 완료 증거 | 상태 |
| --- | --- | --- | --- | --- |
| P09-01 | 후보 확장·관계 검토·그룹 확정 | 감사 lock 검증 | [한정 검토·연결 성분·계보 보고](../../experiments/p09_leakage_repair/r1/grouping/README.md), [최종 그룹 lock](../../experiments/p09_leakage_repair/r1/grouping/final/group_lock.json); 전체 후보 독립성 통과 아님 | Complete |
| P09-02 | 결정적 그룹 재분할 | P09-01 final/group_lock.json과 group_mapping.csv | [새 metadata·lock·경계 재감사·검증 기록](../../experiments/p09_leakage_repair/r1/split/README.md), 기존 artifact 보존 | Complete |
| P09-03 | 익명화 SigLIP 재학습 | P09-02 통과, 진단 규칙 사전 커밋, GPU 여유 | [사전등록](../../experiments/p09_leakage_repair/r1/diagnostic/README.md)·[10epoch 결과/검증](../../experiments/p09_leakage_repair/r1/training/README.md), best/last·ID/metadata 결합·기존 artifact 불변 | Complete |
| P09-04 | val-only 재보정·고정 평가·채택 검토 | P09-03 새 checkpoint | 새 calibration 결합 검증·Test A/B·단서 진단·채택 여부와 한계 보고 준비 중 | In Progress |

### P09-01 — 거리 기준 대신 검토 가능한 관계를 구축

1. `visual_review.csv` 14쌍을 보존된 근거로 가져온다. 확정 8쌍과 미확정 6쌍을 구별하며 미확정을 다른 룩으로 바꾸지 않는다. 기존 그룹 전체를 연결 시작점으로 쓴다.
2. `embedding_nearest_train.json` 2,220행은 평가→train 최근접 **1개**다. 이를 전체 관계 그래프로 간주하지 않는다. `cross_split_phash.json` 145쌍도 현재 split 교차에 제한된 후보다. 둘 다 검토 시작점으로 쓴다.
3. 원래 metadata 행 순서와 identity를 확인한 6,000 embedding cache로 REAL 3,000장의 split 무관 all-pairs 유사도를 계산한다. GPU 재추출은 cache 부재·불일치 시에만 한다. 초기 후보는 이미지별 top-10 이웃의 합집합, 전 REAL pHash≤26, 원본 파일명 촬영 시퀀스 후보와 기존 그룹 연결로 만든다. 이 수치는 **검토 탐색 범위**이며 동일 룩 확정 기준이 아니다. top-10 밖·거리26 밖의 누락 가능성을 기록한다.
4. 같은 옷·인물·배경/소품·촬영 세트를 원본으로 비교한다. 단순 배경·카테고리 유사성만으로 확정하지 않는다. 쌍별 ID·후보 생성 이유·거리·판정·근거를 저장한다. 확인된 관계가 생기면 양 끝의 기존 그룹과 이웃을 확장하며 신규 확정 연결이 없어질 때까지 반복한다.
5. 확정 관계와 기존 REAL 그룹의 연결 성분을 배정 단위로 만든다. 옛 pHash 그룹·미확정 공동 배정은 시각적 동일성의 증명이 아니므로 확정 관계 그래프와 구별한다. 성분은 안정적으로 정렬한 멤버 ID에서 식별자를 유도한다. A–B와 B–C면 A–C 직접 점수가 낮아도 한 그룹이다. 비정상적으로 큰 성분·상충 판정은 원본 근거를 재검토한다.
6. 검토 범위 안의 미확정 관계는 재검토한다. 끝내 분리할 근거가 부족하면 양쪽 성분을 보수적으로 함께 배정하고 그 이유를 남긴다. 범위 밖 미검토 후보는 자동 결합하지 않는다. 후보 검토 범위와 잔여 불확실성을 명시하며 전체 실제 룩을 완벽하게 찾았다고 주장하지 않는다.
7. GEN은 실제 prompt+seed 동일 family와 positive prompt 공유를 별도로 집계한다. pHash/embedding 근사 이미지 후보는 시각 검토한다. 숫자 seed 또는 prompt가 같다는 사실만으로 같은 이미지/룩으로 합치지 않는다. 확정된 GEN 근사중복은 standard split 안에서 같은 그룹으로 배정한다(별도 그룹 매핑 소비, REAL용 `look_group` 의미 유지).
8. sd35는 전량 `test_unseen`을 유지한다. 다른 생성기와 계보가 겹치는 것은 현 generator holdout 계약 위반이 아니며 교차 수·새 prompt/seed 부분집합을 보고한다. sd35와 train용 생성기 사이에 **실제 근사중복 관계**가 확정돼 두 요구를 함께 만족할 수 없다면 재분할 전에 소유자에게 범위 결정을 제기한다. 단순 prompt 공유만으로 이 충돌을 선언하지 않는다.

### P09-02 — 그룹 보존을 우선한 재분할

- 기존 `scripts/split_dataset.py` 경계를 확장해 검토로 고정한 그룹 매핑을 소비한다. 입력 누락·중복 ID·기존 그룹 분해·모순 매핑을 거부하고 기존 실행 경로의 동작도 검증한다.
- standard는 source_type×category×generator 셀을 고려한 70/15/15 목표, sd35 600장은 `test_unseen` 유지. 그룹을 쪼개지 않고 목표/실제 비율과 셀별 표본 수·독립 그룹 수·최대 그룹을 보고한다. 빈 class/split 또는 평가 불가능한 셀은 학습 전 해결한다.
- 6,000개 ID·원본 경로/hash·불변 필드를 이전 버전과 대조한다. 알려진 8쌍, 기존 그룹, 새 연결 성분의 train/val/test 교차는 모두 0이어야 한다. Test B REAL은 **새** standard test REAL만 재사용한다(DB-04).
- 새 split의 모든 경계(train↔val, train↔test, val↔test 포함)에서 DB-07의 고정 검토 범위에 해당하는 후보를 다시 조회·검토한다. 해당 범위의 미해결 교차 후보가 남으면 P09-01로 돌아가 그룹을 보강한다. 지문 검사만 통과하고 종료하지 않는다.
- 회귀 가드는 under-strict(알려진 누출·추이 연결을 놓침)와 over-strict(명백히 다른 룩·단순 prompt 공유를 자동 병합) 양쪽을 명시한다. 입력 순서 변경 시 결정성, 다중 셀 그룹 보존, sd35 격리, Test B REAL 선택도 확인한다. 집중 테스트 후 관련 broader suite를 한 번 실행한다.

### P09-03·04 — 새 계보로 학습·보정·평가

- 새 split을 고정한 뒤 기존 frozen SigLIP encoder에서 head를 새로 초기화해 10 epoch 학습한다. 기존 best checkpoint에서 head를 이어 학습하지 않는다. validation loss로만 best를 고르고 sample ID 근거를 저장한다. GPU 점유가 높으면 작업을 큐잉하지 않는다. 장시간 실행은 디스크 기반 재개 상태를 둔다.
- calibration은 새 val ID만으로 temperature·threshold를 다시 fitting한다. 기존 P08 parameter를 복사하지 않는다. checkpoint·metadata·익명화 hash 결합과 다른 버전 artifact 혼용 거부를 확인한다.
- 새 Test A/B는 설정·선택·보정 고정 후 평가한다. `docs/project.md` §20 지표와 표본 수, REAL 공유, 그룹 수, 오류·얼굴 상태별 결과를 함께 보고한다. 기존 평가와 표본 구성이 달라 직접 대응표본 개선으로 해석하지 않는다.
- P08 얼굴 단서 관문을 새 cohort에 적용할 범위·표본·주석 ID·bootstrap 단위를 **새 모델 결과 전에** 명시하고 커밋한다. 소유자 301장 확인은 해당 ID의 원본 근거로 보존하되 새 표본 전부의 확인으로 간주하지 않는다. 적용 범위가 불명확하면 P09-03 진입 전 해소한다.
- 새로운 단서 진단·통계 결과·데이터 수리 검토가 끝나기 전 `configs/primary.yaml`과 SoT의 채택 경로를 바꾸지 않는다. 실패 시 낮은 결과도 보존하고 원인·후속 범위를 기록한다. 현 P08 채택 규칙의 Q5를 임의로 폐기하지 않는다.

## 완료 조건과 후속 작업

- P09-01~04의 증거와 검증을 갖추고 알려진 같은 룩 교차·확정 그룹 교차가 없어야 한다. 테스트 통과만으로 독립 일반화가 복구됐다고 판정하지 않는다.
- 최종 보고에 검토 탐색 범위·미확인 누락 위험, 단일 REAL 출처·해상도/압축 교란, GEN 계보 중복, 이미 개발에 사용한 표본이라는 한계를 남긴다. 기존 높은 AUC 전체를 누출 하나로 설명하지 않는다.
- 출처·해상도·압축을 맞춘 신규 미접촉 REAL/GEN holdout과 얼굴 노출 실사는 별도 수집 설계 후 진행한다. 기존 ‘P08-07 외부 holdout은 P07 관문이 아님’ 결정을 바꾸지 않는다.
- P07 상세 계획·데모는 별도 작업이다. 이 계획은 P07에 새 holdout 또는 P09 완료 관문을 추가하지 않는다. 현재 artifact로 데모 구현이 가능한 상태와 모델 일반화 근거를 구분한다.
- [DB-07](../decision_briefs/DB-07_P09_review-coverage.md) Resolved: 947,696쌍 전수 검토 대신 우선순위 범위를 고정하고 잔여 미검토를 보고한다. 초기 REAL 500·GEN 100쌍 및 확정 배정 성분 각 멤버의 자신의 같은 class directed top-10 반복 검토를 실행 범위로 삼고, 범위 밖 누락 가능성을 보존한다. 현재 소유자 결정을 요구하는 미해결 사양 충돌은 없다. 실제 그룹 검토에서 계약 충돌·표본 삭제/추가 필요가 드러날 경우에만 구체적인 선택지와 근거를 갖춰 결정 브리프를 작성한다.

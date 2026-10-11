# P08 — 공통 얼굴 익명화 재학습

**상태:** Planned (2026-10-11 작성, 소유자 승인 대기)

`docs/project.md` §27의 Phase 0~6 밖에서 [DB-06](../decision_briefs/DB-06_P06_face-exposure.md)(C, 2026-10-11)으로 생긴 페이즈다. P07(API)은 이 페이즈가 정한 전처리 계약과 checkpoint를 쓴다.

## 목표·선행 조건

[P06-04](../../experiments/p06_failure_analysis/patterns/README.md)에서 확인한 두 단서를 학습·평가·추론의 같은 전처리로 없앤다.

- 얼굴이 보이면 GEN(얼굴 노출 비율이 REAL 학습 0.4%, GEN 학습 64.5%)
- 흰 원이면 REAL(K-Fashion 익명화)

방법: 검출된 얼굴에 K-Fashion과 같은 형태의 흰 원을 두 클래스 모두에 씌운 뒤 primary 모델을 다시 학습하고 calibration한다. 그다음 단서가 사라졌는지 진단한다.

선행: P06 Complete, DB-06 Resolved. 고정 split(`data/metadata.csv`)과 기존 baseline checkpoint·calibration artifact는 보존한다. 덮어쓰지 않는다.

## 범위·검증

1. **P08-01 원 규격·검출 관문 측정** (모델 결과 없이 이미지만 사용)
   - K-Fashion 흰 원의 분포를 잰다: 크기(이미지 너비 대비 반지름), 모양(원·타원 비율), 경계 질감(JPEG 경계 번짐 폭).
   - 합성 원의 지름 비율·경계 처리를 그 분포에 맞춘다. 맞춘 규격을 P08-02 config에 고정한다.
   - YuNet 재현율을 잰다. 학습 GEN 무작위 표본(100장 이상)에 사람이 보기에 얼굴이 보이는지(측면 포함)를 표시하고 검출과 비교한다.
   - **관문**: 보이는 얼굴 재현율이 80% 미만이면 P08-03 전에 소유자에게 검출 보강 여부를 묻는다.
   - 검증: 측정 표본 목록·seed 저장, 수치 재현.
2. **P08-02 익명화 전처리 모듈**
   - 학습·평가·추론이 같은 함수를 쓴다. 학습·평가용 얼굴 좌표는 원본 이미지 기준으로 한 번 검출해 파생 CSV에 저장한다(이미지 sha256과 검출기 sha256으로 결합). 추론은 같은 검출 함수를 바로 호출한다.
   - 익명화는 증강보다 먼저 원본 이미지에 적용한다.
   - 검증: 저장된 좌표 경로와 즉시 검출 경로의 결과가 일치, 결정성, 좌표 CSV와 이미지 해시 불일치 거부, 얼굴 없는 이미지는 그대로 통과, REAL의 기존 원은 건드리지 않음.
3. **P08-03 재학습** — `configs/primary.yaml`과 같은 설정(SigLIP frozen + MLP, 10 epoch, seed 42)에 익명화만 켠다. checkpoint는 `checkpoints/anonymized/`에 저장한다.
   - 검증: val·Test A·Test B 지표를 baseline과 나란히 기록한다. 원본 baseline 재현값이 P02/P03 기록과 일치하는지도 확인한다.
4. **P08-04 재calibration** — P05 절차(val temperature·threshold)를 그대로 적용해 새 artifact를 만든다(checkpoint 해시 결합).
   - 검증: P05와 같은 회귀 가드, Test A/B calibrated 지표.
5. **P08-05 단서 제거 진단** — 실행 전에 config를 커밋해 사전 고정한다. 판정 규칙도 이 config에서 정한다. 후보 진단:
   - (a) P06-04 집계(`scripts/p06_patterns.py`)를 새 모델에 다시 돌린다. GEN 오류가 얼굴 상태에 몰리는지 본다(원래 얼굴 있음은 이제 익명화됨, 얼굴 없음).
   - (b) REAL의 원래 흰 원을 합성 원으로 바꿨을 때 score 변화를 잰다(원 모양 단서가 남았는지).
   - (c) 익명화를 끈 입력과 켠 입력의 차이를 잰다(얼굴 노출 의존이 남았는지).
6. **P08-06 얼굴이 보이는 실사 평가 holdout 설계** — K-Fashion 밖 출처·라이선스·규모를 정한다. 출처 선택은 소유자 결정이 필요하므로 착수 시 결정 브리프로 올린다. 수집은 이 페이즈의 완료 조건이 아니다.

## 계약·소유권

- 익명화 규격(검출기 모델과 sha256, score threshold, 원 지름 비율, 모양, fill, 경계 처리)은 새 config(`configs/anonymize.yaml` 예정)가 소유한다. 학습 config는 이를 참조만 한다.
- 얼굴 좌표 CSV는 파생 artifact다. canonical metadata(`data/metadata.csv`)에 열을 추가하지 않는다.
- API(P07)는 같은 config와 같은 함수를 쓴다. `project.md` §22의 전처리 조항이 상위 계약이다.

## 완료 조건

- P08-01 측정 기록과 원 규격 고정, 재현율 관문 통과(또는 소유자 결정).
- 익명화 모듈의 경로 일치·결정성 회귀 테스트.
- 새 checkpoint와 calibration artifact, baseline 대비 지표 표.
- P08-05 사전 고정 진단 결과와 판정.
- 슬라이스별 독립검증 합격.

## 제외·병행

- 제외: split 변경, 신규 데이터 수집(P08-06은 설계만), encoder 변경, LoRA(P04 조건 불변), DINO 재학습.
- 병행 가능: P08-06 설계, GEN 근사중복 점검.
- GPU 작업은 소유자의 다른 작업 점유가 낮을 때만 하고 큐잉하지 않는다(2026-10-11 기준).

## 관련 결정 브리프

- [DB-06](../decision_briefs/DB-06_P06_face-exposure.md) — Resolved: C(공통 흰 원 익명화 + 얼굴 노출 실사 평가 holdout).
- [DB-03](../decision_briefs/DB-03_P01_face-policy.md) — DB-06이 A(무처리)를 대체한다.

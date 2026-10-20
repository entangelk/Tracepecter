# P08 테스트 누출 적대적 감사

## 대상·범위

- 요청: 소유자가 높은 성능에 대해 테스트 누출을 재점검하고 적대적으로 검증하도록 요청했다.
- 날짜: 2026-10-20. 대상 HEAD `7e5433a`, 현재 metadata 6000장·P08 채택 checkpoint/calibration.
- 검증자: Codex(root). P08-06 구현 참여자이며 이번 결과를 별도 에이전트 독립검증으로 주장하지 않는다. P01 그룹 구성과 데이터·수집 출처·실행 경로를 추가 감사했다.
- 정본: `docs/project.md` §8(같은 룩의 근사 이미지 train/test 분리), §13(pHash+embedding), §14(group split); P01 계획; P08 진단 계약. 기존 명시 관문 계산과 데이터 독립성은 서로 다른 표면이다.

## 방법과 결과

[전체 감사 보고서](../../../experiments/p08_anonymized/leakage_audit/README.md)에 명령·표본·원자료·정량 결과를 보존했다. 요약을 근거 없이 반복하지 않고 관련 입력을 직접 검사했다.

- 원본 6000개 파일/decoded RGB 지문과 pHash, 모든 PNG 3000개 실제 full positive prompt/seed를 전수 읽었다. 원본 SHA는 학습 전 고정 face cache의 6000개 해시와 전부 일치한다.
- 실제 익명화 입력 6000장 frozen embedding과 train 최근접을 계산하고 REAL 후보 14쌍을 시각 확인했다. 최소8쌍에서 같은 옷·촬영 세트의 다른 컷이 교차한다. train/test4쌍·train/val4쌍이며 모두 기존 pHash10을 넘고 그룹ID가 다르다.
- 원본 헤더 3개(width,height,log bytes)만으로 train-only ridge가 Test A/B accuracy1.0을 낸다. 이미지 tensor만 보는 실제 모델이 헤더를 직접 읽는다는 주장은 하지 않는다.
- 현재 학습 코드·데이터 경로·과거 실행 commit을 대조했고 직접 test fitting 경로를 발견하지 못했다. 실제 코드와 같은 metadata 설정의 loader를 stub 실행하여 train/val ID 집합을 관측했다.
- 같은 JPEG 조건 대조, 상수 tensor·상수 logit·평가 labels 셔플과 train labels 셔플 대조를 실행했다. 누출 후보 몇 장 제거·새 prompt/seed 부분집합에서도 AUC는 높다. 이는 실제 누출 부재나 source 일반화를 증명하지 않는다.

## 차단·비차단

### 데이터 독립성 차단

1. 확인된 동일 룩 교차 8쌍. `experiments/p08_anonymized/leakage_audit/visual_review.csv`가 사례의 정본이다. 기존 `scripts/deduplicate.py`에는 embedding 층이 없고 `scripts/split_dataset.py`는 선언된 look_group 값만 검사한다. 값이 다르게 붙은 같은 촬영 시퀀스를 검증하지 못한다.
2. 기존 테스트는 개발 판단에 이미 노출됐고 REAL 출처가 하나다. 현재 수치를 미접촉·출처 독립 일반화로 확정할 근거가 없다. 이 한계는 기존 P08 통계 관문 구현의 오류와 구분한다.

### 추가 설계 위험

- sd35 GEN 600 중420은 train 다른 generator와 positive prompt+seed가 같다. 현 generator holdout 계약 위반은 아니나 새로운 생성 시나리오의 holdout은 아니다.
- 형식·해상도·용량과 class의 교란, K-Fashion 한 REAL 출처. 통일 JPEG 대조에도 AUC가 높아 압축 하나만을 원인으로 확정하지 않는다.
- 사전학습 원자료와의 중복, 전체 REAL 동일 룩 연결성은 아직 배제하지 못했다. 8쌍은 하한이며 전체 누출 수의 추정이 아니다.

## 판정

**불합격** — 평가 데이터 독립성에 실제 반례가 있다. 직접 fitting 혼입·완전 복제는 확인되지 않았지만 같은 룩의 train/test 및 train/val 교차가 확인됐다.

생산 모델·split·calibration은 수리하지 않았다. 원자료가 바뀌지 않은 기존 점수의 산술적 재현성은 유지한다. 소유자의 요청은 점검이므로 후속 수리 범위는 이 보고 후 결정한다.

## 변이·검사

감사 도구 양성/음성 대조와 실제 loader 관측 가드는 통과했다(집중 5 passed, 기존 split 포함10 passed). 커밋 checkpoint와 clean pre-flight 후 누출 방어를 제거하는 변이를 실행하고 정확한 회귀 셀·원복 결과를 여기에 추가한다.

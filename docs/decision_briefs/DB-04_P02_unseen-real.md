# DB-04 — Test B의 REAL 구성

**Status:** Resolved
**Related phase:** [P02](../plan/phase_2_baseline.md)

## 필요한 결정

§10은 REAL+미학습 생성기 평가를 예시로 들지만 현재 `test_unseen`은 생성 이미지만 포함한다. ROC-AUC 계산에는 양 클래스가 필요하다.

## 선택지

| 옵션 | 내용 | 장점 | 비용 |
| --- | --- | --- | --- |
| A | Standard test REAL 재사용 | 기존 split 유지, 학습 누출 없이 비교 | 두 테스트의 REAL 표본이 공유됨 |
| B | 별도 REAL holdout 확보 | 테스트별 독립 표본 | 기존 split 재설계 또는 추가 수집 필요 |

## 권고

A: 현재 split을 보존하며 평가를 구현할 수 있다. Test B는 `test`의 REAL + `test_unseen`의 Generated만 사용한다.

## 결정

2026-10-09 소유자가 A 선택. train/val REAL은 사용하지 않는다. 평가 기록에 REAL 공유를 명시하고 단일 클래스 집합에는 ROC-AUC를 부여하지 않는다.

현재 P01 CSV 기준 Test B는 REAL 448장 + `test_unseen` Generated 600장(sd35_medium), 총 1,048장이다. 테스트 간 REAL 재사용 자체는 학습 누출이 아니지만 두 평가의 표본 독립성은 없다.

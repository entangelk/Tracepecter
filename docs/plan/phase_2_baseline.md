# P02 — Baseline 모델

**상태:** Complete (2026-10-09)

## 목표·선행 조건

P01의 `data/metadata.csv` 6,000행과 고정 split을 사용하여 frozen SigLIP + MLP head를 학습·평가한다. 사양은 `docs/project.md` §15–§16·§19·§25–§27, 우선순위는 `docs/sot.md`를 따른다.

## 범위·완료 조건

| 슬라이스 | 범위 | 확인 |
| --- | --- | --- |
| P02-01 | pretrained vision encoder·freeze·약한 전처리 | 다운로드 없는 작은 SigLIP 모델 테스트, head만 갱신·freeze 해제 검증 |
| P02-02 | split 기반 학습·validation·best checkpoint·실험 기록 | synthetic end-to-end 회귀 테스트와 실데이터 학습 |
| P02-03 | Standard·Unseen 평가·그룹별 metric | 양 클래스 metric·단일 클래스 처리·REAL 재사용 가드 |
| P02-04 | CUDA 환경·exact pin·실학습 실행 | 실제 checkpoint와 validation/test metric 보관 |

1-명령 학습, `best.pt` 저장, validation metric 출력, test evaluation 실행이 완료 조건이다. MVP 성능 목표 달성과 P02 실행 가능 여부는 구분한다.

## 계약·소유권

- split·label·category·generator·source_domain의 원본은 §12 v1.2 CSV이며, 별도 split CSV를 복제하지 않고 Dataset이 split을 선택한다.
- 모델 ID·전처리·학습 parameter는 `configs/baseline.yaml`이 소유한다. pretrained embedding 차원은 모델 config에서 유도한다(stub만 명시 차원 사용).
- provider SDK는 encoder adapter 내부에서 사용한다. 텍스트 encoder는 학습 경로에 포함하지 않는다.
- checkpoint의 config는 실행 시점 스냅샷이며 평가가 이를 읽는다. validation만 best checkpoint 선택에 사용한다.

## 평가 결정·제외

[DB-04](../decision_briefs/DB-04_P02_unseen-real.md): Standard test REAL을 Test B에도 재사용한다(소유자 2026-10-09). 기존 split은 불변이며 테스트 간 REAL 공유를 결과에 기록한다.

DINO 비교는 P03, calibration은 P05, GEN pHash/embedding 중복 점검은 별도 후속 작업이다. GPU에 소유자의 연산 작업이 있으면 실학습을 중단하고 큐잉하지 않는다.

## 참조

SigLIP의 vision pooled output 및 전처리는 [Transformers 공식 문서](https://huggingface.co/docs/transformers/model_doc/siglip)와 [모델 카드](https://huggingface.co/google/siglip-base-patch16-224)를 확인했다. baseline은 224×224, RGB mean/std 0.5이며 pretrained revision을 config에 고정한다.

## 실행·완료 근거

- 기존 split으로 10 epoch CUDA 실학습. validation BCE 기준 best는 epoch 10, `checkpoints/baseline/best.pt`·`last.pt` 저장.
- validation ROC-AUC 0.999874, Test A ROC-AUC 0.999937(800장), Test B ROC-AUC 0.999766(1,048장).
- P02-01~04 실행 조건 충족. 최종 CPU 회귀 35 passed, CUDA 전체 및 집중 검증 기록은 [실험 기록](../../experiments/p02_siglip_baseline/README.md)과 [work log](../daily_logs/2026-10-09/work_log.md) 참고. 독립검증은 미수행이다.
- config·dataset hash·구현 commit·checkpoint hash·학습/평가 metric의 스냅샷을 `experiments/p02_siglip_baseline/`에 보관한다. 바이너리는 로컬 비추적 경로에 둔다.
- 다음은 P03 계획/비교. 현재 Test A/B는 개발 평가이며, 독립 최종 holdout은 별도 후속 설계 항목이다.

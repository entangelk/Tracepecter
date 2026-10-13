# P08-02 공통 얼굴 익명화 전처리

현재 상태: **Complete (2026-10-13)**. [독립검증 합격](../../docs/verifications/2026-10-13/p08_02_anonymize_module.md) 후 비차단 H1(검출·칠하기 좌표순 정렬)·H2(legacy/null 캐시 단독 거부) 회귀를 보강하고 변이 재실패를 확인했다. 재학습·재calibration·primary 채택은 아직 수행하지 않았다. [계획](../../docs/plan/phase_8_face_anonymization.md), [P08-01 측정](measure/README.md)이 선행 근거다.

## 규격·계보

- 정본은 [configs/anonymize.yaml](../../configs/anonymize.yaml)이다. k=1.2 원·흰 fill·σ=0.5 Gaussian alpha를 원본 RGB 이미지에 칠한 뒤 기존 resize·증강·정규화를 적용한다. 모든 검출 얼굴을 처리하며 기존 원과 겹쳐도 예외를 두지 않는다. 무얼굴이면 픽셀은 그대로다.
- 신규 학습 config의 최상위 `anonymization`은 규격 YAML 경로 또는 명시적 `null`이다. 누락은 거부한다. 기존 baseline·DINO·primary config는 `null`을 명시한다(모델·artifact·학습 설정 불변).
- 학습 진입 시 YAML 경로를 `{spec: <전체 규격>, sha256: <규격 해시>}`로 변환해 best/last checkpoint의 config에 저장한다. 해시는 UTF-8 canonical JSON(`sort_keys=True`, `separators=(',', ':')`, `allow_nan=False`)의 SHA256이다. 학습 중 원본 YAML이 바뀌어도 snapshot은 바뀌지 않는다. 재개는 같은 snapshot과 config를 요구한다.
- 평가·calibration·score는 checkpoint snapshot만 읽고 내용 해시와 YuNet 파일 해시를 검증한다. 파일 누락·불일치 또는 지원하지 않는 규격은 거부한다. legacy 키 없음/명시 null은 평가·calibration에서만 원본 입력을 허용하며 score에서는 거부한다. API는 아직 없고 P07에서 같은 `checkpoint_anonymizer(..., required=True)` 계약을 사용해야 한다.
- legacy/null 비교 평가만 `src.evaluate --anonymize <YAML>` 또는 calibration 설정의 `anonymize: <YAML>`로 명시적 익명화 입력을 허용한다. 결합된 checkpoint의 규격 덮어쓰기는 거부한다. 평가 CLI는 checkpoint 디렉터리에 지표를 기록하므로 **비교용 checkpoint 사본 디렉터리**에서 실행해 기존 baseline 실험 지표를 보존한다. 새 모델의 원본 입력 진단 경로는 P08-03에서 별도 구현해야 한다.

## 얼굴 좌표 캐시

[face_boxes.csv](face_boxes.csv)는 이미지와 검출기로부터 유도된 artifact이며 metadata schema는 변경하지 않는다. 모든 split을 포함하고 무얼굴도 `boxes=[]`인 행으로 남긴다.

| 필드 | 소유·의미 |
| --- | --- |
| `image_id` | metadata의 이미지 식별자 |
| `image_sha256` | 원본 이미지 파일 바이트 해시 |
| `detector_sha256` | 실제 YuNet 파일 해시(규격의 모델 해시와 일치 필수) |
| `parameters_sha256` | 검출 파라미터의 canonical JSON 해시. 모델 경로·모델 해시는 제외(별도 identity 키) |
| `boxes` | 원본 좌표 `[x,y,w,h]` 목록의 JSON. P06 대표 얼굴 검출 결과와 구분 |

검출 score 0.9·NMS 0.3·top_k 5000·너비 대비 최소 긴 변 0.04를 사용한다. 최소 크기 경계는 포함하며 얼굴 목록을 좌표순 정렬해 겹침 처리 순서를 고정한다. 원 모양 파라미터는 좌표 검출에 영향이 없으므로 캐시 파라미터 해시에 넣지 않는다. 칠하기는 현재 checkpoint 규격을 사용한다.

캐시를 지정하면 누락 행·이미지 해시 불일치·검출기/파라미터 해시 불일치·중복 ID·잘못된 좌표를 거부한다. 즉시 검출로 조용히 대체하지 않는다. Dataset은 파일 바이트 해시를 매 접근마다 확인한다. 캐시는 선택 사항이며 미지정 시 같은 전처리에서 즉시 검출한다.

```bash
# CPU, 원본 이미지 읽기 전용. 각 행 flush 후 저장하므로 재실행 시 검증 후 이어간다.
docker compose run --rm -T -v /mnt/h/tracepector/images:/images:ro dev \
  python -m src.anonymize
```

학습에는 `data.face_cache: experiments/p08_anonymized/face_boxes.csv`, 평가에는 `--face-cache experiments/p08_anonymized/face_boxes.csv`, calibration에는 `face_cache: experiments/p08_anonymized/face_boxes.csv`를 지정한다. score는 즉시 검출만 사용한다. 캐시는 LF로 체크아웃한다. 손상된 부분 행은 거부하므로 전원 단절 후 손상 행이 있으면 별도 확인·복구해야 한다.

## 검증·한계

실측 캐시는 6,000행(얼굴 있음 1,949장·없음 4,051장·다중 얼굴 7장·전체 얼굴 1,957개)이다. SHA256은 `319d5376f71e3c65155857b33fa2e4dc653d2094a7b8f8cbef90812393d15af8`이다. 이미지 hash 전수 확인 후 재개 실행은 byte 동일했고, seed 20261013의 split × source_type 층화 35장에서 즉시 좌표·얼굴 수·가림 픽셀과 동일했다. 모든 이미지의 즉시 재검출을 반복한 검증은 아니다.

자가 검증 결과와 실제 캐시 재현 확인은 [작업 기록](../../docs/daily_logs/2026-10-13/work_log.md)에 기록한다. 신규 회귀는 모든 얼굴·무얼굴·겹침·원본 전처리 순서·P08-01 경계 커널 일치·캐시/즉시 경로 일치·snapshot 변조 거부·legacy/null·새 학습 키 필수·통합 실행 경로를 확인한다. API 응답의 `faces_anonymized`·`model_version`은 P07 범위다. 원 규격·검출 재현율의 한계는 P08-01 기록대로 유지한다.

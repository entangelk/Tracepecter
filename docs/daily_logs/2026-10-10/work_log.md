# 2026-10-10 work log

## Goals

- F: 용량 부족 해소: 생성·학습 이미지, K-Fashion 원천 zip, checkpoint를 다른 드라이브로 옮긴다.
- P06-03 수동 검토 마무리: 에이전트 1차 검토와 소유자 확인 결과를 비교한다.

## Completed work

### 저장 위치 이전 (F: → H:)

- 원인: Ubuntu vhdx가 `F:\WSL\Ubuntu`에 있어서 WSL 안의 데이터도 F:를 차지했다(F: 여유 1.3G).
- 첫 이전 대상 Z:(USB HDD)는 읽기 중 I/O 오류(disk 이벤트 51, "장치가 준비되지 않았습니다")가 반복됐다. 그래서 H:(외장 SSD)로 바꿨다.
- 옮긴 것: `/mnt/h/tracepector/{images,comfy_output,data,checkpoints}`. 파일마다 sha256 또는 rsync checksum이 일치한 뒤에만 원본을 지웠다. `~/data/kfashion_zips` 사본 3개도 H: 원본과 해시가 같아 지웠다.
- checkpoint는 Z:로 옮긴 직후 F: 원본을 지웠는데, 그 뒤 Z:에 장애가 생겼다. 소유자가 Z:를 다시 연결한 뒤 robocopy로 H:에 복구했다. best.pt sha256은 실험 기록과 일치한다(baseline `151244…`, DINO `456c99…`). `hf_cache`는 복사가 불완전해서 지웠고, 첫 실행 때 다시 받는다.
- 소유자가 Training `라벨링데이터.zip`을 H:로 옮겼고, sha256 `63b9fb8a…`가 일치했다.
- compose 기본 경로를 H:로 바꿨다(`IMAGE_DIR`·`DATA_DIR`·`CHECKPOINT_DIR`·`COMFY_OUTPUT_DIR`로 재지정 가능). `data/images` 링크도 H:로 바꿨다. 커밋 `d5b93d1`.
- F: 여유 공간 1.3G → 67G. vhdx 압축(약 58G 추가 확보)은 소유자가 직접 실행할 예정이다.

### P06-03 수동 검토

- 소유자 확인 35건이 먼저 끝났다(`review_owner.csv`). 자동 저장 연결을 쓰지 않아 브라우저 저장소에서 CSV로 내보냈다.
- 에이전트 블라인드 1차 검토 103건(`review_agent.csv`): 소유자 결과는 열지 않았다. 이미지를 무작위 번호(c001–c103)의 1024px JPEG 사본으로 바꿔 판정했고, 그 뒤 image_id로 되돌렸다.
- 결과: REAL 33건은 전부 `photo_like`. GEN 70건은 `synthetic_like` 45, `ambiguous` 23, `photo_like` 2. 소유자와의 체감 판정 일치는 19/35이고, 정반대 판정은 5건이다. 상세는 [P06 계획](../../plan/phase_6_failure_analysis.md) 진행 상황에 있다.
- 검토 페이지를 다시 만들어 에이전트 판정을 반영했다.

### P06-02b 원형 얼굴 가림 의존 진단

- 소유자 승인 후 config에 사전 규칙을 고정했다. `src/face_mask.py`, `tests/test_face_mask.py`(6개)를 추가하고, `opencv-python-headless==4.13.0.92`를 의존성에 넣었다(4.12는 numpy<2.3 제약 때문에 쓸 수 없음). dev·train 이미지를 다시 빌드했다.
- 실행: 검출 약 12분 + 추론. 결과는 사전 규칙상 의존 근거가 있다. 다만 효과의 약 70%는 회색 원(가림 일반)으로도 생긴다. 상세는 [보고서](../../../experiments/p06_failure_analysis/face_mask/README.md)에 있다.
- 육안 확인: GEN 원 검출 37장은 전부 오검출, REAL 원 있음 표본 16/16 정확, REAL 원 없음 표본 16장 중 1장 누락. 판정이 바뀐 36장은 실제 얼굴 30장, 머리 경계 2장, 옷 4장이다.

## Verification

- 소유자 CSV 구조: 35행, 확인 대상 35/35 판정, 미지의 id 0.
- 에이전트 CSV: 103행, 검토군 id 집합과 일치, `perceived`·`cues` 값이 페이지 어휘 안에 있는지 어설션으로 확인했다.
- 전체 pytest 56 passed(dev 컨테이너). 원 검출 테스트는 양방향을 확인했다. 기준을 엄격하게 하면 붙은 원을 놓치고, Hough를 느슨하게 하면 흰 사각형을 원으로 잡는다.

## Issues / follow-up

- P06-04: 불일치 16건 재확인, 얼굴 노출·구도 편향 정리(P06-02b 결과 반영), DB-03 얼굴 트리거 판정.
- 검토 페이지 안내 문구: "저장 파일 연결을 하지 않으면 브라우저에만 저장된다"를 더 눈에 띄게 할 것(소유자 혼동 사례).
- Z: HDD는 사용 금지. `014.KFashion` 저작도구만 Z:에 남아 있다(파이프라인과 무관).

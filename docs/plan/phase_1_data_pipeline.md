# P01 — 데이터 파이프라인

## 목표

`docs/project.md` §27 Phase 1: REAL(AIHub K-Fashion)·AI 생성 이미지로 학습 데이터셋을 구축하고 metadata·dedup·split을 완료한다. §35 thin-slice 원칙에 따라 씨드 데이터(Real 500 + Generated 500)를 최우선으로 확보해 P02 착수를 연다.

## 선행 조건

- P00 Complete(2026-10-07).
- 소유자의 K-Fashion 다운로드 — **라벨링데이터(Training)는 수신 완료**(2026-10-07 관측, 967,806 JSON·파싱 오류 0). 원천 이미지는 수신 중.
- AI 생성기 접근 수단 — [DB-02](../decision_briefs/DB-02_P01_ai-generators.md) Resolved(2026-10-07): 전량 로컬 오픈소스 무비용. 5종 구성은 P01-04 설계 시 확정.

## 라벨 분포 분석 결과 (2026-10-07, 라벨링데이터 전수)

스크립트: P01-02에서 `scripts/analyze_kfashion_labels.py`로 등록(재현성). 원본 통계는 work log 2026-10-07 세션 2 참고.

- 스키마: 스타일 폴더(24종) → JSON per image. `라벨링` 섹션에 부위별(아우터/상의/하의/원피스) 속성(카테고리·색상·소재 등) + `렉트좌표`/`폴리곤좌표`에 부위별 좌표.
- 부위 라벨 존재: 상의 617,304(63.8%) · 하의 557,589(57.6%) · 원피스 183,572(19.0%) · 아우터 179,274(18.5%). 부위 조합 16종, 최다 `상의+하의` 368,336(38.1%).
- 부위별 카테고리 값: 아우터 7종(재킷·가디건·코트 등) · 상의 7종(티셔츠·블라우스 등) · 하의 5종(팬츠·청바지·스커트 등) · 원피스 2종(드레스·점프수트).
- 스타일 분포: 스트리트 449,494(46.4%) 압도적 편중 → 페미닌 9.1% · 리조트 8.6% · 모던 8.3% · 로맨틱 7.6% 순. `기타` 폴더(4,400)는 스타일 라벨 부재.
- 파일명 패턴(전수): 쇼핑몰 출처 3단 패턴 `PREFIX_NNN_MM.jpg`(예: `LIME_193_00.jpg`)이 23.1%(224,002) — `PREFIX_NNN`이 동일 룩(같은 인물·착장) 그룹 키 후보. 나머지는 카메라 원본·SNS 출처 등으로 파일명 그룹핑 불가 → §13 pHash 근사중복 클러스터가 보완 그룹 키.

### 카테고리 목록 확정 (소유자 승인 2026-10-07)

§3의 1차 후보(K-Fashion 부위 라벨 기반)를 분포가 지지하므로 **4개 부위 카테고리로 확정**했다.

- `category`(대표 부위, 단일값): 규칙 — 이미지에 라벨된 부위 중 **원피스 > 아우터 > 상의 > 하의** 우선순위로 대표 1개. 근거: 시각적으로 지배적인 겉 부위 우선. 규칙 적용 시 분포: 상의 54.4% · 원피스 19.0% · 아우터 17.4% · 하의 8.9% · 라벨 없음 0.4%(제외 대상).
- `parts`(전체 부위, 파이프 구분 다중값): 대표 부위 선택으로 잃는 정보를 보존. 생성 프롬프트 타겟팅·층화 샘플링·평가 분석에 사용.
- 세부 카테고리(티셔츠·청바지 등 21종)는 metadata에 보존하되 balancing·평가 단위는 부위 4개로 둔다. 6,000장 규모에서 21개 셀은 과소 셀이 된다.
- 부위별 balance는 총량 내에서 층화 샘플링으로 조정한다(§7의 균형 정신). 스트리트 편중(46.4%)은 자연 분포를 유지하되 `style` 필드로 항상 추적 가능하게 한다.

## metadata schema v1.2 (§12 개정, 확정)

DB-01 후속("상품 가정 필드 조정")에 따라 개정했다. `docs/project.md` §12에 v1.2로 반영 완료.

| 필드 | REAL(K-Fashion) | Generated | 비고 |
| --- | --- | --- | --- |
| `image_id` | 라벨 JSON `이미지 식별자` 값 | `gen_000001` 순차 발급 | |
| `path` | images/ 상대경로 | 동일 | 기존 유지 |
| `label` | 1 | 0 | 기존 유지(§16) |
| `category` | 대표 부위(4종 중 1) | 프롬프트 타겟 대표 부위 | 신규 정의(위 규칙) |
| `parts` | 라벨된 전체 부위(`상의|하의`) | 타겟 전체 부위 | **신규** |
| `source_type` | `real` | `generated` | 기존 유지 |
| `source_domain` | `kfashion` | `null` | 기존 유지(다중 real 소스 확장 대비) |
| `generator` | `null` | DB-02 확정 식별자 | 기존 유지 |
| `style` | K-Fashion 스타일 라벨 | `null` | **신규**(provenance·편향 분석) |
| `look_group` | 파일명 룩 키 또는 pHash 클러스터 ID | `null` | **신규**(§13·§14 그룹 split 키) |
| `prompt_id` | `null` | §9 프롬프트 변형 ID | **신규**(§9 프롬프트 다양성 추적) |
| `split` | train/val/test(+별도 unseen test) | 동일 | 기존 유지 |
| ~~`product_id`~~ | 제거 | 제거 | 상품 가정 필드(DB-01) |

## 슬라이스 인덱스

| ID | 슬라이스 | 선행 | 산출물 | 완료 확인 | 상태 |
| --- | --- | --- | --- | --- | --- |
| P01-01 | 원천 데이터 수신 확인·정합 검증 | 다운로드 완료 | zip 해제(`data/raw/real/`), 라벨↔이미지 파일명 매핑 검증, 스타일 폴더·개수 정합 보고 | 매핑 불일치 이미지 비율 보고 + 유효 이미지 수 확정 | Planned |
| P01-02 | 카테고리·metadata schema 확정 | 본 계획서 승인 | `scripts/analyze_kfashion_labels.py` repo 등록, `docs/project.md` §12 v1.2 갱신, 인덱스·SoT 버전 로그 | 스크립트 재실행 결과 = 본 문서 수치와 일치 + §12 개정 반영 | 완료 (2026-10-07) |
| P01-03 | REAL 선별·metadata 빌드 | P01-01 | `scripts/build_metadata.py`(라벨→행 변환, 부위 층화 샘플링, 씨드 500 우선) | REAL 씨드 500장 split 행 생성 + 필드 결측 0 | Planned |
| P01-04 | AI 생성 파이프라인 | DB-02(Resolved)·GPU 여유 | `scripts/generate_ai.py`(생성기별 어댑터, §9 프롬프트·배경 변형) | 생성기 ≥3종에서 500장(씨드) 생성 + `prompt_id` 기록 | Planned |
| P01-05 | 중복 제거·그룹핑 | P01-03 | `scripts/deduplicate.py`(pHash + embedding 유사도, §13) | 근사중복 클러스터링 결과로 `look_group` 채움 + 동일 그룹 split 배정 검증 | Planned |
| P01-06 | Dataset split | P01-03·P01-04·P01-05 | `scripts/split_dataset.py`(§14 group split: look_group·generator·source_domain + unseen generator test) | train/val/test 70/15/15 + Test B(unseen) 구성 파일 + 그룹 누출 검사 통과 | Planned |
| P01-07 | 전체 규모 확장·완료 확인 | P01-06 | Real ≥3,000 + Generated ≥3,000, `metadata.csv` 최종화 | §27 Phase 1 완료 조건 전부 충족 보고 | Planned |

씨드 게이트: P01-03 + P01-04(씨드분) 완료 시점에 Real 500 + Generated 500 split이 확보되므로 P02가 병렬 착수 가능하다(§35). 이후 P01은 P01-05~P01-07로 규모를 확장한다.

## 완료 기준

`docs/project.md` §27 Phase 1 완료 조건을 그대로 적용한다.

```text
최소 6,000 이미지 (Real >= 3,000, Generated >= 3,000)
축소된 패션 category 구성(본 문서의 4부위 확정 제안)
metadata.csv 생성
train / val / test split 완료
unseen_generator_test 생성
```

## 병렬 작업 및 제외

- P01-02는 원천 이미지 없이 진행 가능(라벨 zip 완료). P01-04 코드 골격도 DB-02 해결 전에 작성 가능하나 실행·검증은 해결 후.
- P01-03·P01-05의 코드는 원천 수신 전에 작성해 둘 수 있으나, 완료 확인(검증)은 P01-01 이후에만 가능하다.
- 제외: 실제 학습·평가(P02), SigLIP/DINO 연결(P02), 얼굴 전처리 구현(DB-03 옵션 A 무처리 확정 — 전처리 단계 불필요. P06 재검 트리거 발동 시 재상정), LoRA(P04), §32 금지 항목 전체.

## 관련 결정 브리프

- [DB-01](../decision_briefs/DB-01_P01_real-data-domain.md) — Resolved: REAL=K-Fashion 착용컷 재정의(2026-10-07).
- [DB-02](../decision_briefs/DB-02_P01_ai-generators.md) — Resolved: 전량 로컬 오픈소스 무비용(Qwen-Image 보유·Z-Image 추가 가능, 5종 구성은 P01-04 설계 시 확정)(2026-10-07).
- [DB-03](../decision_briefs/DB-03_P01_face-policy.md) — Resolved: 옵션 A 무처리 + P06 재검 트리거(2026-10-07).

## 비고

- 실행 환경: **Docker Compose 체계**(소유자 결정 2026-10-07, venv 대체) — `Dockerfile` + `compose.yaml`. 검증·학습 명령은 `docker compose run --rm dev ...`로 실행한다. `requirements.txt`는 의존성 canonical으로 유지된다. P00의 venv 절차는 P00 머신 기준 역사 기록으로 남는다.
- **GPU 사용 정책(소유자 지시 2026-10-07)**: RTX 3060은 소유자의 다른 AI 모델 작업이 점유 중이다. 학습·이미지 생성 등 GPU 작업은 그 작업이 끝난 뒤 **남는 시간에만** 수행하고, GPU에 여유가 생기기 전에는 큐에 쌓거나 실행하지 않는다. DB-02의 로컬 생성과 P02 학습 스케줄은 이 제약을 전제로 한다. GPU 서비스(profile)는 필요 시점에 compose에 추가한다.
- 다운로드 상태(2026-10-07 관측): `/mnt/f/data/K-Fashion 이미지/Training/` — 라벨링데이터.zip 완료, 원천데이터 수신 중(부분 파일 존재). `/mnt/f/data/014.KFashion/03.저작도구`(라벨링 도구)도 수신 완료 — 본 파이프라인에서 불필요.
- K-Fashion 재배포 제한(DB-01): `data/raw/`는 .gitignore 비추적 유지. provenance는 `source_domain`·`style` 필드와 work log로 기록.
- 원천 zip의 폴더 구조가 라벨과 1:1(스타일 폴더)인지는 P01-01에서 최초 확인한다. 상이하면 매핑 테이블을 P01-01 산출물로 추가한다.

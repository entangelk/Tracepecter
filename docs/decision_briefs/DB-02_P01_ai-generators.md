# DB-02 — AI 생성 데이터의 생성기 접근 수단 확정

**Status:** Resolved
**Related phase:** P01 (P01-04)

## Decision needed

Generated 데이터는 최소 3개 이상의 서로 다른 생성 source로 구성해야 하고(§9), unseen generator test(Test B, §10)를 위해 학습에서 완전히 제외할 생성기가 추가로 1종 필요하다. 즉 **총 5종**(train 4 + unseen 1) 확보가 목표다. 어떤 생성기 조합을 어떤 접근 수단(로컬 GPU / 상용 API / 수동)으로 확보할지는 비용·계정·GPU 가용성에 걸린 소유자 판단이며, P01-04 구현의 전제다.

## 전제 사실 (2026-10-07)

- 필요 생성량(추정): train 4종 × 약 800장 + unseen 1종 약 400~800장 ≈ **3,600~4,000장** (씨드 500장 우선 확보).
- 로컬 GPU: RTX 3060 12GB (WSL2). **소유자의 다른 AI 모델 작업이 점유 중** — GPU 작업은 그 작업 후 남는 시간에만 가능하고 큐잉 금지(소유자 지시 2026-10-07). SDXL 급 모델 1024² 생성 약 15~30초/장 → 800장 = 약 4~7시간 GPU 시간.
- 상용 API 가격대(2026-10 조사): 장당 약 $0.002~0.06 (예: gpt-image 계열 $0.03~0.06, FLUX.1-dev fal.ai 약 $0.025/MP, 저가 provider $0.002~0.02). 3,600~4,000장 전량 API 시 **약 $10~240** (선택 조합에 따라).
- 참고: [가격 비교 조사 링크](https://linkmodel.ai) · [API 비교](https://getapipulse.com) — 실제 단가는 계약 시점 재확인 필요.

## Options

| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| A | 전량 로컬 오픈소스 5종 — 예: SDXL, FLUX.1-schnell, SD3.5-medium, PixArt-Σ(train 4) + PlayGround 등 1종(unseen) | 비용 0. diffusers 단일 스택으로 관리·재현 용이. 전량 동일 하드웨어에서 파라미터 통제 가능 | GPU 시간 약 20~35시간 필요 — 다른 AI 작업과 병행 시 며칠 걸림. 상용 최신 생성기(일반화 성능의 실질 타깃) 커버 불가 |
| B | 전량 상용 API 5종 — 예: gpt-image, Gemini/Imagen, FLUX API, Recraft/Ideogram 등에서 5종 | GPU 점유 없음. 최신 고픈질 생성기 다양성 — Test B 대표성 최선. 생성速度快 | 비용 약 $40~240(조합·해상도 의존). 계정·API key 확보 필요. 생성 파라미터 재현성은 provider 정책에 의존 |
| C | 혼합 — 로컬 2종(SDXL, FLUX.1-schnell) + 상용 API 2종(train) + 상용 API 1종(unseen) | 비용 절충(약 $15~100). 오픈소스/상용 계열이 섞여 artifact 다양성 확보. 로컬분은 남는 GPU 시간에 분산 실행 가능 | 두 접근 수단 관리(로컬 스택 + API 어댑터). GPU 여유 일정에 생성 완료 시점 의존 |
| D | 무료 웹 UI(Midjourney 무료 크레딧, Bing 등) 수동 수집 | 즉시 비용 0 | 재현성·프롬프트 통제 불가, 수천 장 수동 노동 비현실적. metadata provenance 열화 — **비권장** |

## Recommendation + reason

**C.** 소유자 GPU 제약(타 AI 작업 점유·남는 시간만 사용)하에서 전량 로컬(A)은 일정 리스크가 크고, 전량 API(B)는 비용이 예산 불확실성에 걸린다. C는 로컬 2종을 남는 GPU 시간에 분산 실행하면서 핵심인 **unseen generator를 최신 상용 생성기로** 둘 수 있어, Test B(프로젝트 핵심 지표)의 대표성을 비용 최소로 확보한다. 소유자가 이미 보유한 API 계정·크레딧이 많다면 B도 합리적이다.

## Follow-up considerations

- 결정 시 생성기별 식별자(`generator` 필드 값)와 어댑터 목록을 P01-04에 내려준다.
- §9 프롬프트 6형태 × 배경 7종 변형 매트릭스와 `prompt_id` 체계는 P01-04 설계에서 확정한다.
- 로컬 생성 파이프라인 구축·드라이런 자체는 GPU 없이(CPU로 코드 검증) 가능하나, 본 생성은 GPU 여유 시간에만 실행한다(소유자 GPU 정책).
- API 후보별 실제 단가·이용약관(재현·연구 사용 허용 여부)은 선정 시점에 재확인하고 work log에 기록한다.

## Deferred / out of scope

- 생성 이미지 업스케일·후보정 변형(Hard negative §11의 HYBRID 계열)은 P01 MVP 분량에 포함하지 않는다. P06 이후 개선 분량.

## Resolution

- 선택: **A(전량 로컬 오픈소스, 무비용)** — 소유자 변형: 보유 모델 중심으로 구성. 로컬에 Qwen-Image 가 이미 있고, 필요 시 Z-Image 를 추가 설치할 수 있다. 5종(train 4 + unseen 1) 구성은 이들 + 무료 오픈소스(SDXL·FLUX.1-schnell 등)에서 P01-04 설계 시 VRAM 12GB 적합성을 보고 확정한다.
- 일자: 2026-10-07
- 근거: 소유자 결정 — "돈이 들지 않는 것으로 한다". 추가로 외부 AI 생성 데이터셋 보완 확보도 허용(라이선스·provenance 확인 조건, §8). GPU 실행은 소유자의 다른 AI 작업 종료 후 남는 시간에만(큐잉 금지).
- 반영: `docs/plan/phase_1_data_pipeline.md` P01-04 전제 해소, `docs/decision_briefs/00_index.md`.

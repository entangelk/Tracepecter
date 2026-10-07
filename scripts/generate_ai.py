r"""AI 생성 파이프라인 — P01-04 (docs/plan/phase_1_data_pipeline.md, §9·DB-02·DB-03).

ComfyUI(Windows, F:\AI)의 HTTP API로 생성기를 구동해 착용 패션 컷을 생성하고
§12 v1.2 Generated 행 metadata를 기록한다.

로스터(소유자 확정 2026-10-07, DB-02):
  train 4종 — qwen_image_21(Qwen-Image 2.1 int8 + viggle turbo 6step, 보유),
              z_image_turbo(Z-Image Turbo int8), sdxl(SDXL base 1.0),
              playground_25(Playground v2.5)
  unseen 1종 — sd35_medium(SD 3.5 Medium, Test B 전용 — 학습 데이터 생성에 쓰지 않는다)

프롬프트 매트릭스(§9): 6형태 × 7배경 × 3얼굴노출(DB-03 프롬프트 정합) —
스타일 힌트는 REAL(K-Fashion) 스타일 분포를 따라 샘플링한다.
얼굴 처리는 DB-03 옵션 A(무처리) — 어떤 얼굴 전처리도 하지 않는다.

사용:
    python scripts/generate_ai.py <generator> --count 125 --seed 42 \
        --comfyui-url http://<host>:8188 \
        --out data/metadata_gen_<generator>.csv --images-dir ~/data/tracepector/images
    # 서버 없이 작업 계획만 검증: --dry-run

GPU 정책: 실생성은 ComfyUI(Windows)가 GPU를 사용한다 — 소유자의 다른 AI 작업이
끝난 뒤 남는 시간에만 실행(큐잉 금지). --dry-run은 GPU·서버 무관.
워크플로우 그래프는 ComfyUI v0.38 blueprints·소유자 워크플로우 핸드오프 기준 —
첫 실생성 시 /object_info 로 노드 스펙을 재검증한다(--check-server).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kfashion_common import PARTS  # noqa: E402

COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]

GENERATORS = ("qwen_image_21", "z_image_turbo", "sdxl", "playground_25")
UNSEEN_GENERATORS = ("sd35_medium",)

# §9 프롬프트 6형태 (f1~f6)
PROMPT_FORMS = {
    "f1": "street style fashion photography",
    "f2": "lookbook outfit photography",
    "f3": "fashion editorial photography",
    "f4": "casual full-body outfit snapshot",
    "f5": "natural daylight street fashion",
    "f6": "e-commerce model wearing photography",
}
# §9 배경 7종 (b1~b7)
BACKGROUNDS = {
    "b1": "urban street",
    "b2": "indoor",
    "b3": "outdoor natural",
    "b4": "simple studio backdrop",
    "b5": "lifestyle scene",
    "b6": "high-gloss editorial",
    "b7": "minimal background",
}
# DB-03 프롬프트 정합 — 얼굴 노출 변형 (v1~v3). REAL 분포에 맞춰 얼굴 노출을
# 다양화한다("얼굴 없음 → AI" 단서 제거).
FACE_VARIANTS = {
    "v1": "face clearly visible",
    "v2": "face partially visible, turned to the side",
    "v3": "face turned away or out of frame",
}
# 카테고리(대표 부위)별 의상 구성 문구 — parts 타겟과 1:1
CATEGORY_OUTFITS = {
    "원피스": ("원피스", "wearing a one-piece dress"),
    "아우터": ("아우터", "wearing a long coat over the outfit"),
    "상의": ("상의|하의", "wearing a top and bottoms"),
    "하의": ("상의|하의", "wearing a top and bottoms"),
}
# REAL(K-Fashion) 스타일 분포 근사(상위 5 + 기타) — 전수 분석 기준
STYLE_WEIGHTS = {
    "street fashion look": 0.46,
    "feminine look": 0.09,
    "resort look": 0.09,
    "modern look": 0.08,
    "romantic look": 0.08,
    "casual everyday look": 0.20,
}
# 생성 해상도(REAL 800px 롱사이드 근사, 32배수) — 초상/정방 혼합
SIZES = ((832, 1216), (832, 832))


def build_prompt(category: str, style: str, form: str, bg: str, face: str) -> str:
    outfit = CATEGORY_OUTFITS[category][1]
    return (
        f"a person {outfit}, {PROMPT_FORMS[form]}, {BACKGROUNDS[bg]}, "
        f"{FACE_VARIANTS[face]}, {style}, full-body shot, realistic photo"
    )


def plan_jobs(generator: str, count: int, seed: int) -> list[dict]:
    """부위 층화 × 프롬프트 매트릭스 샘플링으로 생성 작업 목록(결정적)."""
    rng = random.Random(seed)
    categories = list(CATEGORY_OUTFITS)  # 원피스·아우터·상의·하의
    per_category = count // len(categories)
    jobs = []
    styles = list(STYLE_WEIGHTS)
    style_weights = list(STYLE_WEIGHTS.values())
    for category in categories:
        for _ in range(per_category):
            form = rng.choice(list(PROMPT_FORMS))
            bg = rng.choice(list(BACKGROUNDS))
            face = rng.choices(list(FACE_VARIANTS), weights=[0.6, 0.25, 0.15])[0]
            style = rng.choices(styles, weights=style_weights)[0]
            width, height = SIZES[len(jobs) % len(SIZES)]
            jobs.append({
                "generator": generator,
                "category": category,
                "parts": CATEGORY_OUTFITS[category][0],
                "style": style,
                "prompt_id": f"{form}{bg}{face}",
                "prompt": build_prompt(category, style, form, bg, face),
                "width": width,
                "height": height,
                "seed": rng.randrange(2**31),
            })
    return jobs


# --- ComfyUI 워크플로우 빌더 (API 포맷 그래프) -------------------------------

def _save_tail(decode_output: str) -> dict:
    return {
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "tracepecter", "images": [decode_output, 0]}},
    }


def build_workflow_qwen_image_21(prompt: str, seed: int, width: int, height: int) -> dict:
    """Qwen-Image 2.1 int8 + viggle turbo 6step — 소유자 워크플로우(2026-10-02 핸드오프) 기준.

    ViggleTurboLora(런타임 side-branch, weight-merge 아님 — int8에서 merge는 손실)와
    ViggleTurboSigmas(latent 입력 필수 — 해상도 시프트)는 viggle_turbo 커스텀 노드.
    """
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "ViggleTurboLora", "inputs": {"model": ["1", 0], "lora_name": "Qwen-Image-2.1-viggle-turbo-v0.3-6step-lora-r128.safetensors", "strength": 1.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors", "type": "qwen_image", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "5": {"class_type": "TextEncodeQwenImage21", "inputs": {"text": prompt, "clip": ["3", 0], "vae": ["4", 0]}},
        "6": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "7": {"class_type": "ViggleTurboSigmas", "inputs": {"latent": ["6", 0], "nodes": "1.0, 0.9375, 0.875, 0.75, 0.5, 0.25"}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "10": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["5", 0]}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0], "sigmas": ["7", 0], "latent_image": ["6", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "SaveImage", "inputs": {"filename_prefix": "tracepecter", "images": ["12", 0]}},
    }


def build_workflow_z_image_turbo(prompt: str, seed: int, width: int, height: int) -> dict:
    """Z-Image Turbo — ComfyUI v0.38 blueprint 'Text to Image (Z-Image-Turbo)' 그래프."""
    return {
        "28": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_int8_convrot.safetensors", "weight_dtype": "default"}},
        "30": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b_fp8_mixed.safetensors", "type": "lumina2", "device": "default"}},
        "29": {"class_type": "VAELoader", "inputs": {"vae_name": "z_image_ae.safetensors"}},
        "27": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["30", 0]}},
        "33": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["27", 0]}},
        "13": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "11": {"class_type": "ModelSamplingAuraFlow", "inputs": {"shift": 3, "model": ["28", 0]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": seed, "control_after_generate": "fixed", "steps": 8, "cfg": 1.0, "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1.0, "model": ["11", 0], "positive": ["27", 0], "negative": ["33", 0], "latent_image": ["13", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["29", 0]}},
        **_save_tail("8"),
    }


def build_workflow_sdxl(prompt: str, seed: int, width: int, height: int) -> dict:
    """SDXL base 1.0 — 표준 CheckpointLoaderSimple 그래프."""
    negative = "anime, illustration, painting, deformed hands, extra limbs, watermark, text"
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "control_after_generate": "fixed", "steps": 30, "cfg": 6.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        **_save_tail("6"),
    }


def build_workflow_playground_25(prompt: str, seed: int, width: int, height: int) -> dict:
    """Playground v2.5 — SDXL 계열 단일 체크포인트, CLIP-L+G 이중 인코딩."""
    negative = "anime, illustration, painting, deformed hands, extra limbs, watermark, text"
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "playground-v2.5-1024px-aesthetic.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "control_after_generate": "fixed", "steps": 30, "cfg": 3.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        **_save_tail("6"),
    }


def build_workflow_sd35_medium(prompt: str, seed: int, width: int, height: int) -> dict:
    """SD 3.5 Medium(all-in-one) — unseen 전용. 표준 SD3 그래프(cfg 4.5, 28step)."""
    negative = "anime, illustration, painting, deformed hands, extra limbs, watermark, text"
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd3.5_medium_incl_clips_t5xxlfp8scaled.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "control_after_generate": "fixed", "steps": 28, "cfg": 4.5, "sampler_name": "dpmpp_2m", "scheduler": "sgm_uniform", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        **_save_tail("6"),
    }


WORKFLOW_BUILDERS = {
    "qwen_image_21": build_workflow_qwen_image_21,
    "z_image_turbo": build_workflow_z_image_turbo,
    "sdxl": build_workflow_sdxl,
    "playground_25": build_workflow_playground_25,
    "sd35_medium": build_workflow_sd35_medium,
}


# --- ComfyUI API 클라이언트 ---------------------------------------------------

def api_get(base_url: str, path: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=timeout) as resp:
        return json.load(resp)


def api_post(base_url: str, path: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def check_server(base_url: str) -> dict:
    """헬스 체크 + 워크플로우 노드 스펙 재검증(GPU 여유 시점 첫 실행용)."""
    stats = api_get(base_url, "/system_stats")
    object_info = api_get(base_url, "/object_info")
    known = set(object_info)
    return {"system": stats["system"], "nodes_available": len(known), "object_info_keys": known}


def run_job(base_url: str, workflow: dict, poll_interval: float = 2.0, timeout: float = 600.0) -> list[dict]:
    """작업 제출 → 완료 대기 → 결과 이미지 메타 반환(다운로드는 caller)."""
    client_id = str(uuid.uuid4())
    result = api_post(base_url, "/prompt", {"prompt": workflow, "client_id": client_id})
    prompt_id = result["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        history = api_get(base_url, f"/history/{prompt_id}")
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            images = []
            for node_output in outputs.values():
                images.extend(node_output.get("images", []))
            if images:
                return images
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI 작업 {prompt_id} 시간 초과")


def download_image(base_url: str, image_meta: dict, out_path: Path) -> None:
    query = (
        f"/view?filename={urllib.parse.quote(image_meta['filename'])}"
        f"&subfolder={urllib.parse.quote(image_meta.get('subfolder', ''))}"
        f"&type={urllib.parse.quote(image_meta.get('type', 'output'))}"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{base_url}{query}", timeout=120) as resp, open(out_path, "wb") as f:
        f.write(resp.read())


def write_metadata_rows(jobs: list[dict], generator: str, start_index: int, out_csv: str) -> None:
    """§12 v1.2 Generated 행 기록. split 미배정(P01-06)."""
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for i, job in enumerate(jobs):
            image_id = f"gen_{start_index + i:06d}"
            writer.writerow([
                image_id,
                f"images/generated/{generator}/{image_id}.png",
                0,
                job["category"],
                job["parts"],
                "generated",
                "",
                generator,
                "",
                "",
                job["prompt_id"],
                "",
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generator", choices=WORKFLOW_BUILDERS,
                        help="생성기 식별자(sd35_medium은 unseen 전용)")
    parser.add_argument("--count", type=int, default=125, help="생성 수(부위별 균등 분할)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--comfyui-url", default=None,
                        help="ComfyUI 서버 URL(예: http://192.168.x.x:8188)")
    parser.add_argument("--check-server", action="store_true",
                        help="생성 없이 헬스 체크·노드 스펙만 확인")
    parser.add_argument("--dry-run", action="store_true",
                        help="서버 없이 작업 계획·프롬프트만 출력")
    parser.add_argument("--out", default=None, help="출력 metadata CSV 경로")
    parser.add_argument("--images-dir", default=None, help="이미지 저장 물리 경로")
    parser.add_argument("--start-index", type=int, default=1, help="gen_ID 시작 번호")
    args = parser.parse_args()

    if args.generator in UNSEEN_GENERATORS:
        print("주의: sd35_medium은 unseen(Test B) 전용 — 학습 데이터 생성에 쓰지 않는다(§10).")

    jobs = plan_jobs(args.generator, args.count, args.seed)
    print(f"작업 {len(jobs)}건 계획(부위별 {args.count // 4}, seed {args.seed})")
    cats: dict[str, int] = {}
    for job in jobs:
        cats[job["category"]] = cats.get(job["category"], 0) + 1
    print(f"  카테고리 분포: {cats}")
    if args.dry_run:
        print(f"  프롬프트 예시: {jobs[0]['prompt']!r}")
        print(f"  prompt_id 예시: {jobs[0]['prompt_id']}")
        if args.out:
            write_metadata_rows(jobs, args.generator, args.start_index, args.out)
            print(f"  dry-run CSV 기록: {args.out}")
        return 0

    if not args.comfyui_url:
        parser.error("실생성에는 --comfyui-url 이 필요하다(GPU 여유 시점에만 실행).")
    if args.check_server:
        info = check_server(args.comfyui_url)
        print(f"서버 정상 — 노드 {info['nodes_available']}종 사용 가능")
        return 0

    if not (args.out and args.images_dir):
        parser.error("실생성에는 --out 과 --images-dir 이 필요하다.")

    images_dir = Path(args.images_dir)
    done = []
    for i, job in enumerate(jobs):
        workflow = WORKFLOW_BUILDERS[job["generator"]](
            job["prompt"], job["seed"], job["width"], job["height"]
        )
        image_meta = run_job(args.comfyui_url, workflow)[0]
        image_id = f"gen_{args.start_index + i:06d}"
        out_path = images_dir / "generated" / job["generator"] / f"{image_id}.png"
        download_image(args.comfyui_url, image_meta, out_path)
        done.append(job)
        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{len(jobs)}")
    write_metadata_rows(done, args.generator, args.start_index, args.out)
    print(f"완료: {len(done)}장 — {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

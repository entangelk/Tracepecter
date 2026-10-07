"""병렬 청크 다운로더 — HF CDN 단일 스트림 throttling 회피(소유자 pdl.sh 방식).

用法: python3 chunk_dl.py [chunks]
청크 단위 resume 지원(.chunkN 파일), 완료 시 병합 + 크기 검증.

히스토리:
- 2026-10-07 야간: curl -C -(resume) + -r(range) 조합이 범위 겹침 어펜드를
  일으켜 청크 오염(3.15GB×8 > 원본 13.9GB) → v3 "정확한 범위 재개"로 교체.
  -C -와 -r의 조합은 금지.
- 2026-10-08: 전원 단절(00:00 KST)로 /tmp 원본 유실 — 세션 로그의
  원문+패치 전문으로 복원, scripts/ 에 보관해 재유실 방지.
  clip_g는 단독 처리(전량 수신 상태에서 꼬리만 이어받기).
"""
import concurrent.futures
import os
import sys
import time
import urllib.request

UA = {"User-Agent": "tracepecter-setup"}


def head_size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch_chunk(url: str, start: int, end: int, path: str) -> int:
    want = end - start + 1
    have = os.path.getsize(path) if os.path.exists(path) else 0
    if have == want:
        return want
    if have > want:  # 오염(-C - + -r 시대 유물) — 재시작
        os.remove(path)
        have = 0
    # 범위 재개: 이미 받은 만큼 start를 옮기고 파일에 append. -C -와 -r의
    # 조합은 범위 겹침 어펜드를 일으키므로 사용 금지(2026-10-07 야간 사고).
    import subprocess
    with open(path, "ab" if have else "wb") as out:
        subprocess.run(
            ["curl", "-sSL", "--fail", "--retry", "5", "--retry-all-errors",
             "--speed-time", "30", "--speed-limit", "20000",
             "-r", f"{start + have}-{end}", url],
            check=True, timeout=14400, stdout=out,
        )
    got = os.path.getsize(path)
    if got != want:
        raise IOError(f"청크 불완전 {path}: {got}/{want}")
    return got


def download(url: str, out: str, chunks: int = 8) -> None:
    if os.path.exists(out + ".done"):
        print(f"SKIP {out}")
        return
    total = head_size(url)
    step = total // chunks
    ranges = [(i * step, (i + 1) * step - 1 if i < chunks - 1 else total - 1)
              for i in range(chunks)]
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=chunks) as pool:
        futures = {
            pool.submit(fetch_chunk, url, s, e, f"{out}.chunk{i}"): i
            for i, (s, e) in enumerate(ranges)
        }
        for fut in concurrent.futures.as_completed(futures):
            fut.result()
    with open(out + ".part", "wb") as dst:
        for i in range(chunks):
            with open(f"{out}.chunk{i}", "rb") as src:
                while True:
                    block = src.read(1 << 22)
                    if not block:
                        break
                    dst.write(block)
            os.remove(f"{out}.chunk{i}")
    got = os.path.getsize(out + ".part")
    if got != total:
        raise IOError(f"병합 크기 불일치 {out}: {got}/{total}")
    os.rename(out + ".part", out)
    open(out + ".done", "w").close()
    rate = total / 1e6 / (time.time() - t0)
    print(f"OK {out} ({total/1e9:.1f}GB, {rate:.1f}MB/s)")


if __name__ == "__main__":
    # 큐 순서: z_image 인코더(qwen_3_4b) 우선 → sdxl → playground → sd3.5
    jobs = [
        ("https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors",
         "/mnt/f/AI/ComfyUI-models/text_encoders/qwen_3_4b_fp8_mixed.safetensors"),
        ("https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
         "/mnt/f/AI/ComfyUI-models/checkpoints/sd_xl_base_1.0.safetensors"),
        ("https://huggingface.co/playgroundai/playground-v2.5-1024px-aesthetic/resolve/main/playground-v2.5-1024px-aesthetic.safetensors",
         "/mnt/f/AI/ComfyUI-models/checkpoints/playground-v2.5-1024px-aesthetic.safetensors"),
        ("https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/resolve/main/sd3.5_medium_incl_clips_t5xxlfp8scaled.safetensors",
         "/mnt/f/AI/ComfyUI-models/checkpoints/sd3.5_medium_incl_clips_t5xxlfp8scaled.safetensors"),
    ]
    for url, out in jobs:
        download(url, out, chunks=int(sys.argv[1]) if len(sys.argv) > 1 else 8)
    print("ALL_FAST_DONE")

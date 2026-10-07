"""병렬 청크 다운로더 — HF CDN 단일 스트림 throttling 회피(소유자 pdl.sh 방식).

用法: python3 chunk_dl.py [chunks]
청크 단위 resume 지원(.chunkN 파일), 완료 시 병합 + 크기 검증.

히스토리:
- 2026-10-07 야간: 청크 오염(3.15GB×8 > 원본 13.9GB) — 당시 -C -+-r 조합 탓으로
  진단하고 v3 "정확한 범위 재개"로 교체.
- 2026-10-08 재발으로 근본 원인 정정: 범인은 curl 내부 --retry — 재시도마다
  range 시작부터 전체를 재스트리밍하는데 출력이 append라 겹침 데이터가 쌓임.
  -C -+-r 은 악화 요인이었을 뿐 필수 조건이 아니었다. v4: curl --retry 제거,
  재시도를 Python 루프(매 시도마다 수신량 재측정 → start 조정)로 이동.
- 2026-10-08: 전원 단절(00:00 KST)로 /tmp 원본 유실 — 세션 로그의
  원문+패치 전문으로 복원, scripts/ 에 보관해 재유실 방지.
  clip_g는 단독 처리(전량 수신 상태에서 꼬리만 이어받기).
"""
import concurrent.futures
import os
import subprocess
import sys
import time
import urllib.request

UA = {"User-Agent": "tracepecter-setup"}


def head_size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch_chunk(url: str, start: int, end: int, path: str, attempts: int = 10) -> int:
    want = end - start + 1
    for attempt in range(1, attempts + 1):
        have = os.path.getsize(path) if os.path.exists(path) else 0
        if have == want:
            return want
        if have > want:  # 오염(재스트리밍 겹침 유물) — 재시작
            os.remove(path)
            have = 0
        # curl --retry 금지: 내부 재시도가 range 시작부터 재스트리밍하며 append
        # 출력에 겹침을 쌓는다(2026-10-08 오염, 10-07 야간 사고의 진짜 원인).
        # 재시도가 없으면 한 호출의 부분 수신은 항상 진짜 연속 접두사이므로
        # 크기 기반 재개가 안전하다(오염은 반드시 과대로 나타나 아래에서 리셋).
        # 실패한 시도의 부분 수신은 유지하고 다음 시도에서 start+have부터 이어받는다.
        with open(path, "ab" if have else "wb") as out:
            rc = subprocess.call(
                ["curl", "-sSL", "--fail",
                 "--speed-time", "30", "--speed-limit", "20000",
                 "-r", f"{start + have}-{end}", url],
                stdout=out, timeout=3600,
            )
        have = os.path.getsize(path) if os.path.exists(path) else 0
        if rc == 0 and have == want:
            return want
        print(f"  재시도 {attempt}/{attempts} {os.path.basename(path)} rc={rc} {have}/{want}", flush=True)
    raise IOError(f"청크 실패 {path}: {attempts}회 재시도 후에도 불완전")


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

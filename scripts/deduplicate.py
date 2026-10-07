"""근사중복 제거·룩 그룹핑 — P01-05 (docs/plan/phase_1_data_pipeline.md, §13).

metadata CSV의 이미지들에 pHash(64-bit DCT hash)를 계산해 해밍 거리 기준
근사중복 클러스터링(union-find)을 수행하고, 비어 있는 look_group 을 채운다.
파일명 유래 look_group 이 이미 있는 행은 그 값을 유지하며, 클러스터가 기존
그룹과 합쳐지면 그 그룹 ID를 채택한다(동일 룩). 동일 그룹 → 동일 split 배정은
P01-06(split_dataset)이 소비한다.

embedding 유사도(§13 두 번째 층)는 실제 encoder 연결 시점(P02+)에 추가한다 —
P01-05 는 pHash 층만 구현(계획서 비고 기록).

사용:
    python scripts/deduplicate.py --metadata data/metadata_real.csv [--threshold 10]

path 컬럼은 CSV 디렉터리 기준 상대 경로로 해석한다(src/dataset.py 규칙).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HASH_SIZE = 8  # 저주파 8x8 = 64-bit hash

# DCT-II 기저 행렬(32점) — 이미지 크기와 무관하게 재사용
_N = 32
_DCT = np.zeros((_N, _N))
for _u in range(_N):
    for _x in range(_N):
        _DCT[_u, _x] = np.cos(np.pi * (2 * _x + 1) * _u / (2 * _N))


def compute_phash(image: Image.Image) -> int:
    """64-bit pHash — 32x32 grayscale DCT 저주파 8x8의 중앙값 임계 비트."""
    gray = image.convert("L").resize((_N, _N), Image.Resampling.LANCZOS)
    coeffs = _DCT @ np.asarray(gray, dtype=np.float64) @ _DCT.T
    low = coeffs[:HASH_SIZE, :HASH_SIZE].flatten()
    bits = low > np.median(low)
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def cluster_by_phash(hashes: list[int], threshold: int) -> list[int]:
    """해밍 거리 <= threshold 인 쌍을 union-find 로 묶어 대표 인덱스 목록 반환."""
    n = len(hashes)
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if hamming(hashes[i], hashes[j]) <= threshold:
                uf.union(i, j)
    return [uf.find(i) for i in range(n)]


def fill_look_groups(
    rows: list[dict], hashes: list[int], threshold: int
) -> tuple[list[dict], dict]:
    """클러스터링으로 비어 있는 look_group 을 채운다.

    우선순위: (1) 파일명 유래 기존 값 유지 (2) 클러스터에 기존 값이 있으면 그
    값 채택 (3) 없으면 phash_<k> 신규 발급. 클러스터에 서로 다른 기존 값 여러
    개가 있으면(파일명 그룹끼리 근사중복) 더 작은(등장 순서 빠른) 값을 쓴다.
    """
    roots = cluster_by_phash(hashes, threshold)
    cluster_members: dict[int, list[int]] = {}
    for idx, root in enumerate(roots):
        cluster_members.setdefault(root, []).append(idx)

    cluster_id: dict[int, str] = {}
    next_new = 0
    for root in sorted(cluster_members):
        existing = sorted(
            {rows[i]["look_group"] for i in cluster_members[root]
             if rows[i]["look_group"]}
        )
        if existing:
            cluster_id[root] = existing[0]
        else:
            cluster_id[root] = f"phash_{next_new}"
            next_new += 1

    filled = 0
    out_rows = [dict(r) for r in rows]
    for idx, root in enumerate(roots):
        if not out_rows[idx]["look_group"]:
            out_rows[idx]["look_group"] = cluster_id[root]
            filled += 1

    stats = {
        "total": len(rows),
        "clusters": len(cluster_members),
        "multi_clusters": sum(1 for m in cluster_members.values() if len(m) > 1),
        "filled": filled,
        "covered_before": sum(1 for r in rows if r["look_group"]),
        "covered_after": sum(1 for r in out_rows if r["look_group"]),
    }
    return out_rows, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, help="metadata CSV 경로")
    parser.add_argument("--threshold", type=int, default=10,
                        help="근사중복 해밍 거리 임계(64-bit, 기본 10)")
    args = parser.parse_args()

    csv_path = Path(args.metadata)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        rows = list(reader)

    hashes = []
    for row in rows:
        image_path = csv_path.parent / row["path"]
        with Image.open(image_path) as img:
            hashes.append(compute_phash(img))

    out_rows, stats = fill_look_groups(rows, hashes, args.threshold)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"pHash 클러스터링(임계 {args.threshold}): "
          f"{stats['total']}장 → {stats['clusters']} 클러스터 "
          f"(복수 멤버 {stats['multi_clusters']})")
    print(f"look_group 커버: {stats['covered_before']} → {stats['covered_after']} "
          f"({stats['covered_after'] / stats['total']:.1%}), 신규 채움 {stats['filled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

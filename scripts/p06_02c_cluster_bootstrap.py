"""P06-02c 사후 민감도: prompt_id 묶음 단위 bootstrap으로 D1·D3·흰 원 전환율의 95% 구간을 다시 낸다.

사전 판정에는 쓰지 않는다(README 한계 절의 수치). 실행: python3 scripts/p06_02c_cluster_bootstrap.py
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

OUT = Path('experiments/p06_failure_analysis/face_mask_ci')


def main():
    report = json.loads((OUT/'report.json').read_text())
    temperature, threshold = report['temperature'], report['threshold_probability']
    boot = report['config']['bootstrap']
    meta = {row['image_id']: row for row in csv.DictReader(open('data/metadata.csv'))}
    p = {}
    for row in csv.DictReader(open(OUT/'predictions.csv')):
        p.setdefault(row['image_id'], {})[row['condition']] = 1 / (1 + math.exp(-float(row['logit']) / temperature))
    groups = {}
    for image_id in p:  # predictions.csv 순서(대상 index 순)
        groups.setdefault(meta[image_id]['prompt_id'], []).append(image_id)
    clusters = list(groups.values())

    def stats(selected):
        ids = [i for cluster in selected for i in cluster]
        o, w, g, f = (np.array([p[i][c] for i in ids]) for c in ('original', 'white_face', 'gray_face', 'white_offface'))
        return 100 * (w - g).mean(), 100 * (g - f).mean(), ((o < threshold) & (w >= threshold)).mean()

    rng = np.random.default_rng(boot['seed'])
    draws = np.array([stats([clusters[k] for k in rng.integers(0, len(clusters), len(clusters))])
                      for _ in range(boot['resamples'])])
    tail = 100 * (1 - boot['interval']) / 2
    low, high = np.percentile(draws, [tail, 100 - tail], axis=0)
    result = dict(clusters=len(clusters), max_cluster=max(map(len, clusters)),
                  **{name: [round(float(a), 4), round(float(b), 4)]
                     for name, a, b in zip(('d1_white_minus_gray', 'd3_gray_minus_offface', 'flip_white'), low, high)})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

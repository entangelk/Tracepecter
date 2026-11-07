"""P10-02: directed top-10 neighbors of confirmed components after adding P10 verdicts.

Reuses the P09 rule and feature cache; P09-closed components must yield no pairs.
"""
import argparse
import json
from pathlib import Path

from scripts.p09_group_candidates import (load_features, read_csv, review_neighbors, sha256,
                                          verify_audit_lock, write_csv, write_json)

AUDIT = Path('experiments/p08_anonymized/leakage_audit')
CACHE = Path('reports/errors/review/p08_leakage_probe')
P09_REVIEWS = Path('experiments/p09_leakage_repair/r1/grouping/final/visual_reviews.csv')
FIELDS = ['a', 'b', 'cosine', 'phash_distance', 'reasons', 'label', 'split_a', 'split_b', 'stratum']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', type=Path, nargs='+', required=True, help='P10 verdict CSVs')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists; use a new directory, never overwrite')
    verify_audit_lock(AUDIT/'audit_lock.json')
    rows = read_csv('data/metadata.csv')
    artifact = json.loads(Path('experiments/p08_anonymized/calibration/calibration.json').read_text())
    identity = dict(checkpoint=artifact['checkpoint_sha256'], calibration=sha256('experiments/p08_anonymized/calibration/calibration.json'),
                    metadata=sha256('data/metadata.csv'), cache=sha256('experiments/p08_anonymized/face_boxes.csv'),
                    source=sha256('scripts/p08_leakage_probe.py'))
    features = load_features(CACHE, identity, len(rows))
    images = {r['image_id']: r for r in map(json.loads, (AUDIT/'image_audit.jsonl').read_text().splitlines())}
    hashes = [int(images[r['image_id']]['phash'], 16) for r in rows]
    reviews = [{k: r[k] for k in ('a', 'b', 'verdict', 'reason')} for r in read_csv(P09_REVIEWS)]
    reviews += [{k: r[k] for k in ('a', 'b', 'verdict', 'reason')} for path in args.reviews for r in read_csv(path)]
    splits = {r['image_id']: r['split'] for r in read_csv('data/versions/p09_r1/metadata.csv')}
    labels = {r['image_id']: r['label'] for r in rows}
    pairs = [dict(p, label=labels[p['a']], split_a=splits[p['a']], split_b=splits[p['b']], stratum='neighbor')
             for p in review_neighbors(rows, features, hashes, reviews)]
    args.out.mkdir(parents=True)
    write_csv(args.out/'pairs.csv', pairs, FIELDS)
    write_json(args.out/'input_lock.json', dict(
        source_sha256=sha256(__file__), p09_reviews_sha256=sha256(P09_REVIEWS),
        reviews_sha256={str(p): sha256(p) for p in args.reviews},
        cache_sha256={p.name: sha256(p) for p in sorted(CACHE.glob('*.npz'))},
        outputs_sha256={'pairs.csv': sha256(args.out/'pairs.csv')}))
    print(f'{len(pairs)} unreviewed directed neighbor pairs: {args.out}')


if __name__ == '__main__':
    main()

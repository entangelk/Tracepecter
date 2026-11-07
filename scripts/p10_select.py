"""P10-01: select unreviewed P09 candidates that cross r1 split boundaries (DB-09 A).

Top bands are taken in full; lower bands are a fixed-seed random sample. The
selection is a review queue, not a list of leaks. Inputs are never modified.
"""
import argparse
import csv
import gzip
import json
import random
from collections import Counter
from pathlib import Path

from scripts.p09_group_candidates import read_csv, sha256, write_csv, write_json

P09 = Path('experiments/p09_leakage_repair/r1')
QUEUE = Path('reports/errors/review/p09_leakage_repair/r1/candidate_run_01/candidates.csv.gz')
METADATA = Path('data/versions/p09_r1/metadata.csv')
# (stratum, label, lower cosine inclusive, upper cosine exclusive, sample size or None for all)
STRATA = (
    ('real_ge90', '1', 0.90, None, None),
    ('real_85_90', '1', 0.85, 0.90, 100),
    ('real_80_85', '1', 0.80, 0.85, 100),
    ('real_lt80', '1', None, 0.80, 100),
    ('gen_ge95', '0', 0.95, None, None),
    ('gen_90_95', '0', 0.90, 0.95, 100),
    ('gen_lt90', '0', None, 0.90, 0),
)
SEED = 20261107
FIELDS = ['a', 'b', 'cosine', 'phash_distance', 'reasons', 'label', 'split_a', 'split_b', 'stratum']


def stratum(label, cosine):
    for name, owner, low, high, _ in STRATA:
        if owner == label and (low is None or cosine >= low) and (high is None or cosine < high):
            return name
    raise ValueError(f'no stratum: {label} {cosine}')


def select_pairs(candidates, splits, labels, reviewed, seed=SEED):
    """Return (selected rows, population per stratum) for cross-split same-class pairs."""
    population = {name: [] for name, *_ in STRATA}
    for row in candidates:
        a, b = row['a'], row['b']
        if labels[a] != labels[b] or splits[a] == splits[b] or tuple(sorted((a, b))) in reviewed:
            continue
        name = stratum(labels[a], float(row['cosine']))
        population[name].append(dict(row, label=labels[a], split_a=splits[a], split_b=splits[b], stratum=name))
    selected = []
    for name, _, _, _, size in STRATA:
        rows = sorted(population[name], key=lambda r: (-float(r['cosine']), r['a'], r['b']))
        if size is not None and size < len(rows):
            rows = sorted(random.Random(f'{seed}:{name}').sample(rows, size),
                          key=lambda r: (-float(r['cosine']), r['a'], r['b']))
        selected += rows
    return selected, {name: len(rows) for name, rows in population.items()}


def verify_inputs():
    split_lock = json.loads((P09/'split/split_lock.json').read_text())
    group_lock_path = P09/'grouping/final/group_lock.json'
    group_lock = json.loads(group_lock_path.read_text())
    expected = {str(METADATA): split_lock['metadata_sha256'],
                str(group_lock_path): split_lock['group_lock_sha256'],
                str(QUEUE): group_lock['full_candidate_queue_sha256']}
    expected.update({str(P09/'grouping/final'/name): value for name, value in group_lock['outputs_sha256'].items()})
    for name, value in expected.items():
        if sha256(name) != value:
            raise ValueError(f'hash mismatch: {name}')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists; use a new directory, never overwrite')
    verified = verify_inputs()
    rows = read_csv(METADATA)
    splits = {r['image_id']: r['split'] for r in rows}
    labels = {r['image_id']: r['label'] for r in rows}
    reviewed = {tuple(sorted((r['a'], r['b']))) for r in read_csv(P09/'grouping/final/visual_reviews.csv')}
    with gzip.open(QUEUE, 'rt', encoding='utf-8', newline='') as handle:
        selected, population = select_pairs(csv.DictReader(handle), splits, labels, reviewed)
    args.out.mkdir(parents=True)
    write_csv(args.out/'pairs.csv', selected, FIELDS)
    counts = Counter(r['stratum'] for r in selected)
    summary = dict(seed=SEED, strata=[dict(stratum=name, label=label, cosine_min=low, cosine_max=high,
                                           population=population[name], selected=counts[name],
                                           mode='all' if size is None else 'sample' if size else 'unreviewed')
                                      for name, label, low, high, size in STRATA],
                   reviewed_excluded=len(reviewed), selected_pairs=len(selected))
    write_json(args.out/'summary.json', summary)
    write_json(args.out/'input_lock.json', dict(verified_inputs_sha256=verified, source_sha256=sha256(__file__),
                                                outputs_sha256={p.name: sha256(p) for p in sorted(args.out.iterdir())}))
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

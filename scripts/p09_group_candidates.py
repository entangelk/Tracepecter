"""P09: expand review candidates from locked P08 features; never modify splits.

The compressed candidate list is a review queue, not a list of confirmed matches.
Groups written here are provisional until visual review coverage is resolved.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def verify_audit_lock(path):
    path = Path(path)
    lock = json.loads(path.read_text())
    verified = {}
    for section in ('inputs_sha256', 'source_sha256', 'artifacts_sha256'):
        for name, expected in lock[section].items():
            source = path.parent/name if section == 'artifacts_sha256' else Path(name)
            if not source.is_file() or sha256(source) != expected:
                raise ValueError(f'audit hash mismatch: {source}')
            verified[str(source)] = expected
    return verified


def load_features(cache, identity, count, chunk_size=128):
    cache = Path(cache)
    if json.loads((cache/'identity.json').read_text()) != identity:
        raise ValueError('embedding cache identity mismatch')
    expected = {f'{start:05}.npz' for start in range(0, count, chunk_size)}
    if {p.name for p in cache.glob('*.npz')} != expected:
        raise ValueError('embedding cache chunk set mismatch')
    chunks = []
    dimension = None
    for start in range(0, count, chunk_size):
        with np.load(cache/f'{start:05}.npz', allow_pickle=False) as chunk:
            features, logits = chunk['features'], chunk['logits']
        n = min(chunk_size, count-start)
        if features.ndim != 2 or features.shape[0] != n or logits.shape != (n,):
            raise ValueError('embedding cache shape mismatch')
        if dimension is None:
            dimension = features.shape[1]
        if features.shape[1] != dimension or not np.isfinite(features).all() or not np.isfinite(logits).all():
            raise ValueError('embedding cache shape/nonfinite mismatch')
        if (np.linalg.norm(features, axis=1) == 0).any():
            raise ValueError('zero embedding')
        chunks.append(features)
    return np.concatenate(chunks)


def normalized(features):
    values = np.asarray(features, dtype=np.float64)
    return values/np.linalg.norm(values, axis=1, keepdims=True)


def verify_nearest(rows, features, nearest):
    """Replay all saved queries to detect stale or permuted cached row ordering."""
    vectors = normalized(features)
    index = {r['image_id']: i for i, r in enumerate(rows)}
    train = [i for i, r in enumerate(rows) if r['split'] == 'train']
    expected = {r['image_id'] for r in rows if r['split'] != 'train'}
    if len(nearest) != len(expected) or {r['image_id'] for r in nearest} != expected:
        raise ValueError('nearest query IDs mismatch')
    # Float64 CPU versus original float32 CUDA: tolerate rounding, not row swaps.
    for start in range(0, len(nearest), 128):
        sample = nearest[start:start+128]
        similarities = vectors[[index[r['image_id']] for r in sample]] @ vectors[train].T
        for r, scores in zip(sample, similarities):
            target = index[r['nearest_train']]
            if target not in train:
                raise ValueError('nearest target is not train')
            score = scores[train.index(target)]
            if abs(score-r['cosine']) > 2e-6 or scores.max()-score > 2e-6:
                raise ValueError(f'cache row order/nearest mismatch: {r["image_id"]}')


def candidate_pairs(rows, features, hashes, top_k=10, real_phash=26, seeds=()):
    """Yield deterministic undirected candidates, including same-split pairs.

    REAL pHash covers the planned wide search. GEN uses <=10 and top-k among
    GEN. Cross-class legacy candidates remain visible but cannot merge groups.
    Neither similarity nor a candidate reason is a review verdict.
    """
    vectors = normalized(features)
    by_id = {r['image_id']: i for i, r in enumerate(rows)}
    if len(by_id) != len(rows):
        raise ValueError('duplicate image ID')
    reasons = defaultdict(set)
    for label in ('1', '0'):
        indices = sorted((i for i, r in enumerate(rows) if r['label'] == label),
                         key=lambda i: rows[i]['image_id'])
        for i in indices:
            others = [j for j in indices if j != i]
            scores = vectors[others] @ vectors[i]
            order = np.argsort(-scores, kind='stable')[:top_k]
            for position in order:
                reasons[tuple(sorted((i, others[position])))].add('embedding_topk')
    existing = defaultdict(list)
    filenames = defaultdict(list)
    for i, r in enumerate(rows):
        if r['label'] == '1':
            if r['look_group']:
                existing[(r['source_domain'], r['look_group'])].append(i)
            # The established K-Fashion rule is PREFIX_NNN_MM; no numeric-ID proximity rule.
            import re
            match = re.fullmatch(r'(.+_\d+)_\d+', Path(r['path']).stem)
            if match:
                filenames[(r['source_domain'], match[1])].append(i)
    for mapping, reason in ((existing, 'existing_group'), (filenames, 'filename_sequence')):
        for members in mapping.values():
            for i, j in combinations(members, 2):
                reasons[tuple(sorted((i, j)))].add(reason)
    for a, b, reason in seeds:
        if a not in by_id or b not in by_id or a == b:
            raise ValueError('invalid seed IDs')
        reasons[tuple(sorted((by_id[a], by_id[b])))].add(reason)
    # Streaming pHash enumeration avoids holding ~1M REAL pairs in Python objects.
    for i, left in enumerate(rows):
        for j in range(i+1, len(rows)):
            right = rows[j]
            distance = (hashes[i]^hashes[j]).bit_count()
            pair_reasons = set(reasons.get((i, j), ()))
            if left['label'] == right['label'] and distance <= (real_phash if left['label'] == '1' else 10):
                pair_reasons.add('phash')
            if not pair_reasons:
                continue
            a, b = sorted((left['image_id'], right['image_id']))
            yield dict(a=a, b=b, cosine=round(float(vectors[i] @ vectors[j]), 9),
                       phash_distance=distance, reasons='|'.join(sorted(pair_reasons)))


def build_groups(rows, reviews):
    by_id = {r['image_id']: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('duplicate image ID')
    parent = {i: i for i in by_id}
    def find(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b):
        if by_id[a]['label'] != by_id[b]['label']:
            raise ValueError('cross-class group relation')
        parent[find(b)] = find(a)
    seen = set()
    for review in reviews:
        a, b = review['a'], review['b']
        if a not in by_id or b not in by_id or a == b:
            raise ValueError('unknown or invalid review IDs')
        pair = tuple(sorted((a, b)))
        if pair in seen:
            raise ValueError('duplicate review pair')
        seen.add(pair)
        if review['verdict'] not in ('confirmed_same_look', 'different_look', 'unconfirmed', 'conservative_colocation'):
            raise ValueError('unknown review verdict')
        if not review['reason'].strip():
            raise ValueError('empty review reason')
        if review['verdict'] == 'confirmed_same_look':
            union(a, b)
    for review in reviews:
        if review['verdict'] == 'different_look' and find(review['a']) == find(review['b']):
            raise ValueError('review conflict within connected component')
    existing = {}
    for i, r in by_id.items():
        if r['label'] == '1' and r['look_group']:
            key = (r['source_domain'], r['look_group'])
            if key in existing:
                union(existing[key], i)
            existing[key] = i
    # Co-location is an allocation constraint, not a claim of visual equivalence.
    for review in reviews:
        if review['verdict'] == 'conservative_colocation':
            union(review['a'], review['b'])
    members = defaultdict(list)
    for i in by_id:
        members[find(i)].append(i)
    result = {}
    for ids in members.values():
        group = 'p09_'+hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()[:20]
        for i in ids:
            result[i] = group
    return dict(sorted(result.items()))



def review_neighbors(rows, features, hashes, reviews, top_k=10):
    """Expand each confirmed member's directed neighbors, excluding resolved pairs."""
    semantic = [dict(r, verdict='unconfirmed') if r['verdict'] == 'conservative_colocation' else r
                for r in reviews]
    groups = build_groups(rows, semantic)
    anchor_groups = {groups[r[k]] for r in semantic if r['verdict'] == 'confirmed_same_look'
                     for k in ('a', 'b')}
    anchors = {i for i in groups if groups[i] in anchor_groups}
    seen = {tuple(sorted((r['a'], r['b']))) for r in reviews}
    vectors = normalized(features)
    pairs = {}
    for label in ('1', '0'):
        indices = sorted((i for i, r in enumerate(rows) if r['label'] == label),
                         key=lambda i: rows[i]['image_id'])
        for i in indices:
            if rows[i]['image_id'] not in anchors:
                continue
            others = [j for j in indices if j != i]
            scores = vectors[others] @ vectors[i]
            for position in np.argsort(-scores, kind='stable')[:top_k]:
                j = others[position]
                a, b = sorted((rows[i]['image_id'], rows[j]['image_id']))
                if (a, b) not in seen and groups[a] != groups[b]:
                    pairs[a, b] = dict(a=a, b=b, cosine=round(float(scores[position]), 9),
                                       phash_distance=(hashes[i]^hashes[j]).bit_count(),
                                       reasons='confirmed_member_directed_topk')
    return sorted(pairs.values(), key=lambda r: (-r['cosine'], r['a'], r['b']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, default=Path('experiments/p08_anonymized/leakage_audit'))
    parser.add_argument('--cache', type=Path, default=Path('reports/errors/review/p08_leakage_probe'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--queue', type=Path, required=True)
    parser.add_argument('--neighbors-from', type=Path, nargs='+', help='additional visual reviews; original 14 are implicit')
    args = parser.parse_args()
    if args.out.exists() or args.queue.exists():
        raise ValueError('output exists; use a new run directory, never overwrite')
    verified = verify_audit_lock(args.audit/'audit_lock.json')
    rows = read_csv('data/metadata.csv')
    artifact = json.loads(Path('experiments/p08_anonymized/calibration/calibration.json').read_text())
    identity = dict(checkpoint=artifact['checkpoint_sha256'], calibration=sha256('experiments/p08_anonymized/calibration/calibration.json'),
                    metadata=sha256('data/metadata.csv'), cache=sha256('experiments/p08_anonymized/face_boxes.csv'),
                    source=sha256('scripts/p08_leakage_probe.py'))
    features = load_features(args.cache, identity, len(rows))
    nearest = json.loads((args.audit/'embedding_nearest_train.json').read_text())
    verify_nearest(rows, features, nearest)
    print('audit hashes, cache identity/shape and all nearest queries verified', flush=True)
    images = {r['image_id']: r for r in map(json.loads, (args.audit/'image_audit.jsonl').read_text().splitlines())}
    if set(images) != {r['image_id'] for r in rows}:
        raise ValueError('image audit ID mismatch')
    hashes = [int(images[r['image_id']]['phash'], 16) for r in rows]
    legacy = read_csv(args.audit/'visual_review.csv')
    reviews = [dict(a=r['image_id'], b=r['train_image_id'], verdict=r['verdict'], reason=r['reason']) for r in legacy]
    if args.neighbors_from:
        # Keep rich visual evidence in its source CSV; grouping consumes this projection.
        reviews += [{k: r[k] for k in ('a', 'b', 'verdict', 'reason')}
                    for path in args.neighbors_from for r in read_csv(path)]
    seeds = [(r['a'], r['b'], 'legacy_review') for r in reviews]
    seeds += [(r['image_id'], r['nearest_train'], 'legacy_nearest') for r in nearest]
    seeds += [(r['a'], r['b'], 'legacy_cross_phash') for r in json.loads((args.audit/'cross_split_phash.json').read_text())]
    groups = build_groups(rows, reviews)
    args.out.mkdir(parents=True)
    args.queue.mkdir(parents=True)
    fields = ['a', 'b', 'cosine', 'phash_distance', 'reasons']
    counts, labels, boundaries = Counter(), Counter(), Counter()
    by_id = {r['image_id']: r for r in rows}
    priority = []
    total = 0
    queue = args.queue/'candidates.csv.gz'
    # mtime=0 makes compressed content reproducible.
    import io
    with queue.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
        with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fields, lineterminator='\n'); writer.writeheader()
            candidates = (review_neighbors(rows, features, hashes, reviews) if args.neighbors_from
                          else candidate_pairs(rows, features, hashes, seeds=seeds))
            for pair in candidates:
                writer.writerow(pair); total += 1
                counts.update(pair['reasons'].split('|'))
                a, b = by_id[pair['a']], by_id[pair['b']]
                labels[''.join(sorted((a['label'], b['label'])))] += 1
                boundaries['|'.join(sorted((a['split'], b['split'])))] += 1
                if any(reason != 'phash' for reason in pair['reasons'].split('|')):
                    priority.append(pair)
    priority.sort(key=lambda r: (-r['cosine'], r['a'], r['b']))
    write_csv(args.out/'priority_candidates.csv', priority, fields)
    write_csv(args.out/'seed_review.csv', reviews, ['a', 'b', 'verdict', 'reason'])
    write_csv(args.out/'provisional_groups.csv', [dict(image_id=i, group_id=g) for i, g in groups.items()], ['image_id', 'group_id'])
    provenance = json.loads((args.audit/'generation_provenance.json').read_text())
    overlap = {}
    for keys in [('prompt',), ('prompt', 'noise_seed')]:
        known = {tuple(r[k] for k in keys) for r in provenance if r['split'] == 'train'}
        overlap['+'.join(keys)] = {s: sum(tuple(r[k] for k in keys) in known for r in provenance if r['split'] == s)
                                  for s in ('val', 'test', 'test_unseen')}
    summary = dict(candidate_pairs=total, priority_pairs=len(priority), reasons=dict(counts), labels=dict(labels),
                   split_boundaries=dict(boundaries), seed_review=dict(Counter(r['verdict'] for r in reviews)),
                   provisional_groups=len(set(groups.values())), generation_train_overlap=overlap,
                   review_complete=False, grouping_final=False)
    write_json(args.out/'summary.json', summary)
    input_lock = dict(verified_audit_files=verified, audit_lock_sha256=sha256(args.audit/'audit_lock.json'),
                      cache_identity=identity, cache_sha256={p.name: sha256(p) for p in sorted(args.cache.glob('*.npz'))},
                      source_sha256=sha256(__file__), parameters=dict(top_k=10, real_phash=26, gen_phash=10, mode='neighbors' if args.neighbors_from else 'initial'),
                      review_inputs_sha256={str(p): sha256(p) for p in args.neighbors_from or []},
                      outputs_sha256={p.name: sha256(p) for p in sorted(args.out.iterdir()) if p.is_file()},
                      queue=dict(path=str(queue), sha256=sha256(queue)))
    write_json(args.out/'input_lock.json', input_lock)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

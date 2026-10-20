"""Lock reviewed P09 allocation groups without changing metadata or visual verdicts."""
import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.generate_ai import UNSEEN_GENERATORS
from scripts.p09_group_candidates import build_groups, read_csv, sha256, verify_audit_lock, write_csv, write_json


def prepare_groups(rows, reviews):
    constraints = [dict(r, verdict='conservative_colocation',
                        reason='검토한 미확정 관계의 보수적 공동 배정; 시각적 동일 룩 확정 아님: '+r['reason'])
                   for r in reviews if r['verdict'] == 'unconfirmed']
    effective = [r for r in reviews if r['verdict'] != 'unconfirmed']+constraints
    groups = build_groups(rows, effective)
    generators = defaultdict(set)
    for row in rows:
        if row['label'] == '0':
            generators[groups[row['image_id']]].add(row['generator'])
    for values in generators.values():
        if values.intersection(UNSEEN_GENERATORS) and values.difference(UNSEEN_GENERATORS):
            raise ValueError('unseen generator group conflicts with standard generators; owner decision required')
    return groups, constraints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grouping-root', type=Path, default=Path('experiments/p09_leakage_repair/r1/grouping'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists; never overwrite')
    root = args.grouping_root
    verified = verify_audit_lock('experiments/p08_anonymized/leakage_audit/audit_lock.json')
    closure = json.loads((root/'neighbor_closure.json').read_text())
    if closure['pending_pairs'] != 0 or closure['source_sha256'] != sha256('scripts/p09_group_candidates.py'):
        raise ValueError('neighbor closure/source mismatch')
    reviews = []
    for path, expected in closure['review_inputs_sha256'].items():
        if sha256(path) != expected:
            raise ValueError(f'review input hash mismatch: {path}')
        reviews.extend({k: r[k] for k in ('a', 'b', 'verdict', 'reason')} for r in read_csv(path))
    rows = read_csv('data/metadata.csv')
    groups, constraints = prepare_groups(rows, reviews)
    initial = json.loads((root/'candidate_run_01/input_lock.json').read_text())
    queue = initial['queue']
    if sha256(queue['path']) != queue['sha256']:
        raise ValueError('full candidate queue hash mismatch')
    reviewed_keys = {tuple(sorted((r['a'], r['b']))) for r in reviews}
    with gzip.open(queue['path'], 'rt') as handle:
        inside = sum((r['a'], r['b']) in reviewed_keys for r in csv.DictReader(handle))
    total = json.loads((root/'candidate_run_01/summary.json').read_text())['candidate_pairs']
    sizes = Counter(groups.values())
    by_id = {r['image_id']: r for r in rows}
    confirmed = [r for r in reviews if r['verdict'] == 'confirmed_same_look']
    summary = dict(review_scope_complete=True, full_candidate_review_complete=False, grouping_final=True,
                   metadata_rows=len(rows), allocation_groups=len(sizes), largest_allocation_groups=sizes.most_common(10),
                   visual_reviews=dict(Counter(r['verdict'] for r in reviews)), reviewed_pairs=len(reviews),
                   initial_candidate_pairs=total, reviewed_initial_candidates=inside, unreviewed_initial_candidates=total-inside,
                   conservative_colocation_edges=len(constraints),
                   confirmed_original_split_pairs=dict(Counter('|'.join(sorted((by_id[r['a']]['split'], by_id[r['b']]['split']))) for r in confirmed)),
                   neighbor_pending_pairs=0, split_changed=False, retrained=False)
    args.out.mkdir(parents=True)
    write_csv(args.out/'group_mapping.csv', [dict(image_id=i, group_id=g) for i, g in groups.items()], ['image_id', 'group_id'])
    write_csv(args.out/'visual_reviews.csv', reviews, ['a', 'b', 'verdict', 'reason'])
    write_csv(args.out/'conservative_constraints.csv', constraints, ['a', 'b', 'verdict', 'reason'])
    write_json(args.out/'summary.json', summary)
    lock = dict(metadata_sha256=sha256('data/metadata.csv'), audit_verified_files=verified,
                closure_sha256=sha256(root/'neighbor_closure.json'), review_inputs_sha256=closure['review_inputs_sha256'],
                full_candidate_queue_sha256=queue['sha256'],
                sources_sha256={name: sha256(name) for name in ('scripts/p09_group_candidates.py', 'scripts/p09_finalize_groups.py', 'scripts/generate_ai.py')},
                outputs_sha256={p.name: sha256(p) for p in sorted(args.out.iterdir())})
    write_json(args.out/'group_lock.json', lock)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()

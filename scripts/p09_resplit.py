"""P09-02: verify frozen evidence, resplit allocation groups and audit new boundaries."""
import argparse
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.p09_group_candidates import read_csv, sha256, write_csv, write_json
from scripts.split_dataset import SPLITS, SPLIT_RATIO, group_key, reviewed_group_split


def verify_group_lock(path, metadata):
    path, metadata = Path(path), Path(metadata)
    lock = json.loads(path.read_text())
    expected = {str(metadata): lock['metadata_sha256'],
                str(path.parent.parent/'neighbor_closure.json'): lock['closure_sha256']}
    for section in ('audit_verified_files', 'review_inputs_sha256', 'sources_sha256'):
        expected.update(lock[section])
    expected.update({str(path.parent/name): value for name, value in lock['outputs_sha256'].items()})
    for name, value in expected.items():
        if sha256(name) != value:
            raise ValueError(f'hash mismatch: {name}')
    return expected


def audit_reviews(rows, reviews):
    by_id = {r['image_id']: r for r in rows}
    boundaries = { '|'.join(sorted((a, b))): Counter()
                   for i, a in enumerate((*SPLITS, 'test_unseen'))
                   for b in (*SPLITS, 'test_unseen')[i+1:] }
    for review in reviews:
        a, b = by_id[review['a']], by_id[review['b']]
        if a['split'] == b['split']:
            continue
        boundary = '|'.join(sorted((a['split'], b['split'])))
        boundaries[boundary][review['verdict']] += 1
        if review['verdict'] != 'different_look':
            raise ValueError(f'unresolved reviewed crossing: {review}')
    return {key: dict(value) for key, value in sorted(boundaries.items())}


def split_report(original, rows, mapping):
    by_id = {r['image_id']: r for r in rows}
    for old in original:
        for key, value in old.items():
            if key == 'split' or (key == 'look_group' and old['source_type'] == 'real'):
                continue
            if by_id[old['image_id']][key] != value:
                raise ValueError(f'immutable metadata changed: {old["image_id"]}:{key}')
    groups, old_groups, cells = defaultdict(set), defaultdict(set), defaultdict(list)
    for row in rows:
        groups[mapping[row['image_id']]].add(row['split'])
        cells[row['source_type'], row['category'], row['generator']].append(row)
    for old in original:
        old_groups[group_key(old)].add(by_id[old['image_id']]['split'])
    if any(len(s) != 1 for s in (*groups.values(), *old_groups.values())):
        raise ValueError('allocation or original group crossing')
    cell_report = []
    for (source, category, generator), members in sorted(cells.items()):
        unseen = members[0]['split'] == 'test_unseen'
        split_names = ('test_unseen',) if unseen else SPLITS
        for split in split_names:
            subset = [r for r in members if r['split'] == split]
            if not subset:
                raise ValueError(f'empty evaluation cell: {source}/{category}/{generator}/{split}')
            sizes = Counter(mapping[r['image_id']] for r in subset)
            target = len(members) * (1 if unseen else SPLIT_RATIO[SPLITS.index(split)])
            cell_report.append(dict(source_type=source, category=category, generator=generator,
                                    split=split, count=len(subset), target=target,
                                    actual_ratio=len(subset)/len(members),
                                    independent_allocation_groups=len(sizes), largest_group=max(sizes.values())))
    for split in SPLITS:
        if {r['label'] for r in rows if r['split'] == split} != {'0', '1'}:
            raise ValueError(f'empty class: {split}')
    return dict(rows=len(rows), allocation_groups=len(groups), allocation_crossings=0,
                original_group_crossings=0, immutable_fields_preserved=True,
                by_split=dict(Counter(r['split'] for r in rows)), cells=cell_report)


def check_priority_scope(root, original, reviews):
    """The frozen priority and directed-neighbor rules do not depend on split."""
    by_id = {r['image_id']: r for r in original}
    initial = json.loads((root/'candidate_run_01/input_lock.json').read_text())
    for name, expected in initial['outputs_sha256'].items():
        if sha256(root/'candidate_run_01'/name) != expected:
            raise ValueError(f'initial candidate output hash mismatch: {name}')
    reviewed = {tuple(sorted((r['a'], r['b']))) for r in reviews}
    seeds = {tuple(sorted((r['a'], r['b']))) for r in read_csv(root/'candidate_run_01/seed_review.csv')}
    candidates = read_csv(root/'candidate_run_01/priority_candidates.csv')
    selected = []
    for label, count in (('1', 500), ('0', 100)):
        eligible = [r for r in candidates if by_id[r['a']]['label'] == by_id[r['b']]['label'] == label
                    and (r['a'], r['b']) not in seeds
                    and group_key(by_id[r['a']]) != group_key(by_id[r['b']])]
        selected.extend(eligible[:count])
        if len(eligible) < count:
            raise ValueError('priority scope smaller than preregistered count')
    if any(tuple(sorted((r['a'], r['b']))) not in reviewed for r in selected):
        raise ValueError('missing initial priority review')
    closure = json.loads((root/'neighbor_closure.json').read_text())
    if closure['pending_pairs'] != 0:
        raise ValueError('unresolved directed neighbor scope')
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group-lock', type=Path, default=Path('experiments/p09_leakage_repair/r1/grouping/final/group_lock.json'))
    parser.add_argument('--metadata', type=Path, default=Path('data/metadata.csv'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--image-root', type=Path, required=True, help='root containing real/ and generated/')
    args = parser.parse_args()
    if args.out.exists() or args.report.exists():
        raise ValueError('output exists; never overwrite')
    verified = verify_group_lock(args.group_lock, args.metadata)
    root = args.group_lock.parent.parent
    evidence = json.loads((root/'evidence_lock.json').read_text())
    if sha256(args.group_lock) != evidence['group_lock_sha256']:
        raise ValueError('group lock/evidence mismatch')
    for name, expected in evidence['supporting_artifacts_sha256'].items():
        if sha256(name) != expected:
            raise ValueError(f'supporting hash mismatch: {name}')
        verified[name] = expected
    initial = json.loads((root/'candidate_run_01/input_lock.json').read_text())
    group_lock = json.loads(args.group_lock.read_text())
    queue = initial['queue']
    if sha256(queue['path']) != queue['sha256'] or queue['sha256'] != group_lock['full_candidate_queue_sha256']:
        raise ValueError('full candidate queue hash mismatch')
    verified[queue['path']] = queue['sha256']
    original = read_csv(args.metadata)
    mapping_rows = read_csv(args.group_lock.parent/'group_mapping.csv')
    mapping = {r['image_id']: r['group_id'] for r in mapping_rows}
    rows = reviewed_group_split(original, mapping_rows)
    reviews = read_csv(args.group_lock.parent/'visual_reviews.csv')
    selected = check_priority_scope(root, original, reviews)
    report = split_report(original, rows, mapping)
    report['reviewed_boundary_verdicts'] = audit_reviews(rows, reviews)
    report['initial_priority_pairs_checked'] = len(selected)
    report['directed_neighbor_pending_pairs'] = 0
    report['full_candidate_independence_passed'] = False
    report['unreviewed_initial_candidates'] = json.loads((args.group_lock.parent/'summary.json').read_text())['unreviewed_initial_candidates']
    by_id = {r['image_id']: r for r in rows}
    provenance = json.loads(Path('experiments/p08_anonymized/leakage_audit/generation_provenance.json').read_text())
    overlap = {}
    for keys in [('prompt',), ('prompt', 'noise_seed')]:
        known = {tuple(r[k] for k in keys) for r in provenance if by_id[r['image_id']]['split'] == 'train'}
        overlap['+'.join(keys)] = {
            s: sum(tuple(r[k] for k in keys) in known for r in provenance if by_id[r['image_id']]['split'] == s)
            for s in ('val', 'test', 'test_unseen')}
    report['generation_train_overlap'] = overlap
    boundary_rows = [dict(r, split_a=by_id[r['a']]['split'], split_b=by_id[r['b']]['split']) for r in reviews]
    # Reproject the frozen image hashes by ID; images are neither rewritten nor copied.
    audit = Path('experiments/p08_anonymized/leakage_audit/image_audit.jsonl')
    images = [json.loads(line) for line in audit.read_text().splitlines()]
    if {r['image_id'] for r in images} != set(by_id):
        raise ValueError('image ledger identity mismatch')
    def verify_image(image):
        row = by_id[image['image_id']]
        path = args.image_root/Path(row['path']).relative_to('images')
        if sha256(path) != image['sha256']:
            raise ValueError(f'image hash mismatch: {image["image_id"]}')
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(verify_image, images))
    report['image_files_verified'] = len(images)
    report['image_hash_ledger_sha256'] = sha256(audit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.mkdir(parents=True)
    write_csv(args.out, rows, list(original[0]))
    write_csv(args.report/'review_boundaries.csv', boundary_rows, list(boundary_rows[0]))
    write_json(args.report/'split_report.json', report)
    write_json(args.report/'split_lock.json', dict(
        group_lock_sha256=sha256(args.group_lock), verified_inputs_sha256=verified,
        evidence_lock_sha256=sha256(root/'evidence_lock.json'),
        source_sha256={p: sha256(p) for p in ('scripts/split_dataset.py', 'scripts/p09_resplit.py')},
        metadata_sha256=sha256(args.out),
        outputs_sha256={p.name: sha256(p) for p in sorted(args.report.iterdir())}))
    print(json.dumps({k: v for k, v in report.items() if k != 'cells'}, ensure_ascii=False))


if __name__ == '__main__':
    main()

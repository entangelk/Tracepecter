"""P09-02 B2/B3: exercise frozen scope, report and CLI without production data writes.

Under-strict guards reject missing scope, invalid reports and tampered evidence.
Over-strict guards accept complete scope, valid cells and independent shared prompts.
"""
import copy
import json
import sys
from itertools import combinations
from pathlib import Path

import pytest

from scripts import p09_resplit
from scripts.p09_group_candidates import read_csv, sha256, write_csv, write_json
from test_split_dataset import COLUMNS, _gen_row, _real_row


def build_scope(root):
    initial = root/'candidate_run_01'
    initial.mkdir(parents=True)
    rows = [_real_row(f'r{i:02}', f'old{i}') for i in range(35)]
    rows += [_gen_row(f'g{i:02}') for i in range(16)]
    rows[1]['look_group'] = rows[0]['look_group']
    seed = dict(a='r00', b='r02', verdict='different_look', reason='seed')
    candidates = [dict(a='g00', b='r00')]
    real_pairs = [dict(a=a['image_id'], b=b['image_id']) for a, b in combinations(rows[:35], 2)]
    gen_pairs = [dict(a=a['image_id'], b=b['image_id']) for a, b in combinations(rows[35:], 2)]
    candidates += real_pairs + gen_pairs
    # Both exclusions precede the first 500 REAL candidates. Extra candidates stay unreviewed.
    selected = [r for r in real_pairs if (r['a'], r['b']) not in {('r00', 'r01'), ('r00', 'r02')}][:500] + gen_pairs[:100]
    reviews = [dict(r, verdict='different_look', reason='different clothes') for r in selected] + [seed]
    write_csv(initial/'priority_candidates.csv', candidates, ['a', 'b'])
    write_csv(initial/'seed_review.csv', [seed], list(seed))
    write_json(root/'neighbor_closure.json', dict(pending_pairs=0))
    seal_scope(root)
    return rows, reviews, selected


def seal_scope(root):
    path = root/'candidate_run_01/input_lock.json'
    lock = json.loads(path.read_text()) if path.exists() else {}
    lock['outputs_sha256'] = {name: sha256(root/'candidate_run_01'/name)
                              for name in ('priority_candidates.csv', 'seed_review.csv')}
    write_json(path, lock)


def test_priority_scope_complete_with_exclusions(tmp_path):
    """Under: required pairs lost; over: seeds/old groups/out-of-scope forced into review."""
    rows, reviews, selected = build_scope(tmp_path)
    # Pair endpoint order is irrelevant in the review evidence.
    reviews[0]['a'], reviews[0]['b'] = reviews[0]['b'], reviews[0]['a']
    assert p09_resplit.check_priority_scope(tmp_path, rows, reviews) == selected
    assert len(selected) == 600


@pytest.mark.parametrize('defect', ['hash', 'real_count', 'gen_count', 'missing_review', 'pending'])
def test_priority_scope_rejects_incomplete_evidence(tmp_path, defect):
    """Under: hash/count/review/closure defence removed; over: intact fixture accepted above."""
    rows, reviews, _ = build_scope(tmp_path)
    if defect == 'hash':
        with (tmp_path/'candidate_run_01/priority_candidates.csv').open('a') as handle:
            handle.write('r00,r01\n')
        message = 'initial candidate output hash mismatch'
    elif defect in ('real_count', 'gen_count'):
        path = tmp_path/'candidate_run_01/priority_candidates.csv'
        prefix = 'r' if defect == 'real_count' else 'g'
        candidates = [r for r in read_csv(path) if not (r['a'].startswith(prefix) and r['b'].startswith(prefix))]
        write_csv(path, candidates, ['a', 'b'])
        seal_scope(tmp_path)
        message = 'priority scope smaller'
    elif defect == 'missing_review':
        reviews.pop(0)
        message = 'missing initial priority review'
    else:
        write_json(tmp_path/'neighbor_closure.json', dict(pending_pairs=1))
        message = 'unresolved directed neighbor scope'
    with pytest.raises(ValueError, match=message):
        p09_resplit.check_priority_scope(tmp_path, rows, reviews)


def report_fixture():
    original = []
    for kind in ('real', 'gen'):
        for i, split in enumerate(('train', 'train', 'val', 'test')):
            row = _real_row(f'r{i}', f'old{i}') if kind == 'real' else _gen_row(f'g{i}')
            row['split'] = split
            original.append(row)
    unseen = _gen_row('u', 'sd35_medium')
    unseen['split'] = 'test_unseen'
    original.append(unseen)
    original[1]['look_group'] = original[0]['look_group']
    rows = copy.deepcopy(original)
    mapping = {r['image_id']: r['image_id'] for r in rows}
    mapping['r1'] = mapping['r0']
    mapping['g1'] = mapping['g0']
    for row in rows:
        if row['source_type'] == 'real':
            row['look_group'] = mapping[row['image_id']]
    return original, rows, mapping


def test_split_report_counts_targets_and_groups():
    """Under: bad aggregation; over: valid REAL rewrites/GEN groups/unseen rejected."""
    original, rows, mapping = report_fixture()
    result = p09_resplit.split_report(original, rows, mapping)
    assert result == dict(rows=9, allocation_groups=7, allocation_crossings=0,
                          original_group_crossings=0, immutable_fields_preserved=True,
                          by_split={'train': 4, 'val': 2, 'test': 2, 'test_unseen': 1},
                          cells=result['cells'])
    cells = {(r['source_type'], r['generator'], r['split']): r for r in result['cells']}
    assert len(cells) == 7
    for source, generator in [('real', ''), ('generated', 'qwen_image_21')]:
        for split, count, target, ratio, largest in [('train', 2, 2.8, .5, 2), ('val', 1, .6, .25, 1), ('test', 1, .6, .25, 1)]:
            assert cells[source, generator, split] == dict(source_type=source, category='상의', generator=generator,
                split=split, count=count, target=target, actual_ratio=ratio,
                independent_allocation_groups=1, largest_group=largest)
    assert cells['generated', 'sd35_medium', 'test_unseen'] == dict(source_type='generated', category='상의',
        generator='sd35_medium', split='test_unseen', count=1, target=1, actual_ratio=1,
        independent_allocation_groups=1, largest_group=1)


@pytest.mark.parametrize('defect', ['immutable', 'gen_look_group', 'allocation_crossing', 'old_crossing', 'empty_cell', 'empty_class'])
def test_split_report_rejects_contract_violations(defect):
    """Under: invalid reports accepted; over: unchanged normal fixture passes above."""
    original, rows, mapping = report_fixture()
    if defect == 'immutable':
        rows[0]['path'] = 'images/changed.jpg'
        message = 'immutable metadata changed'
    elif defect == 'gen_look_group':
        rows[4]['look_group'] = 'unexpected'
        message = 'immutable metadata changed'
    elif defect in ('allocation_crossing', 'old_crossing'):
        # Keep every cell populated: link already different splits instead of moving a row.
        if defect == 'allocation_crossing':
            mapping['g2'] = mapping['g3']
        else:
            original[2]['look_group'] = original[3]['look_group']
        message = 'allocation or original group crossing'
    elif defect == 'empty_cell':
        rows = [r for r in rows if r['image_id'] != 'r2']
        original = [r for r in original if r['image_id'] != 'r2']
        message = 'empty evaluation cell'
    else:
        rows = [r for r in rows if r['label'] == '0']
        original = [r for r in original if r['label'] == '0']
        message = 'empty class'
    with pytest.raises(ValueError, match=message):
        p09_resplit.split_report(original, rows, mapping)


@pytest.fixture
def locked_run(tmp_path, monkeypatch):
    """Self-contained locked CLI evidence: 600 priority pairs and 52 tiny image files."""
    repo = Path(__file__).resolve().parent.parent
    for name in ('split_dataset.py', 'p09_resplit.py'):
        target = tmp_path/'scripts'/name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((repo/'scripts'/name).read_bytes())
    monkeypatch.chdir(tmp_path)
    root = tmp_path/'grouping'
    original, reviews, _ = build_scope(root)
    original.append(_gen_row('u', 'sd35_medium'))
    metadata = tmp_path/'metadata.csv'
    write_csv(metadata, original, COLUMNS)
    mapping = {r['image_id']: 'group_'+r['image_id'] for r in original}
    mapping['r01'] = mapping['r00']
    mapping_rows = [dict(image_id=i, group_id=g) for i, g in mapping.items()]
    result = p09_resplit.reviewed_group_split(original, mapping_rows)
    audit_root = Path('experiments/p08_anonymized/leakage_audit')
    audit_root.mkdir(parents=True)
    images = tmp_path/'images'
    ledger = []
    for row in original:
        image = tmp_path/row['path']
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(row['image_id'].encode())
        ledger.append(dict(image_id=row['image_id'], sha256=sha256(image)))
    audit = audit_root/'image_audit.jsonl'
    audit.write_text(''.join(json.dumps(r)+'\n' for r in ledger))
    # All prompts are shared; one val prompt and one test seed are deliberately novel.
    provenance = [dict(image_id=r['image_id'], prompt='shared full prompt', noise_seed=7)
                  for r in result if r['source_type'] == 'generated']
    gen_val = [r['image_id'] for r in result if r['source_type'] == 'generated' and r['split'] == 'val']
    gen_test = [r['image_id'] for r in result if r['source_type'] == 'generated' and r['split'] == 'test']
    for row in provenance:
        if row['image_id'] == gen_val[0]:
            row['prompt'] = 'novel full prompt'
        if row['image_id'] == gen_test[0]:
            row['noise_seed'] = 999
    provenance_path = audit_root/'generation_provenance.json'
    write_json(provenance_path, provenance)
    queue = tmp_path/'queue.csv.gz'
    queue.write_bytes(b'frozen queue evidence')
    initial_path = root/'candidate_run_01/input_lock.json'
    initial = json.loads(initial_path.read_text())
    initial['queue'] = dict(path=str(queue), sha256=sha256(queue))
    write_json(initial_path, initial)
    final = root/'final'
    final.mkdir()
    write_csv(final/'group_mapping.csv', mapping_rows, ['image_id', 'group_id'])
    write_csv(final/'visual_reviews.csv', reviews, ['a', 'b', 'verdict', 'reason'])
    write_json(final/'summary.json', dict(unreviewed_initial_candidates=17))
    lock = dict(metadata_sha256=sha256(metadata), closure_sha256=sha256(root/'neighbor_closure.json'),
                audit_verified_files={str(p): sha256(p) for p in (audit, provenance_path)},
                review_inputs_sha256={}, sources_sha256={},
                outputs_sha256={p.name: sha256(p) for p in final.iterdir()},
                full_candidate_queue_sha256=sha256(queue))
    group_lock = final/'group_lock.json'
    write_json(group_lock, lock)
    evidence = root/'evidence_lock.json'
    write_json(evidence, dict(group_lock_sha256=sha256(group_lock),
                             supporting_artifacts_sha256={str(initial_path): sha256(initial_path)}))
    out, report = tmp_path/'out/metadata.csv', tmp_path/'out/report'
    monkeypatch.setattr(sys, 'argv', ['p09_resplit', '--metadata', str(metadata), '--group-lock', str(group_lock),
                                    '--out', str(out), '--report', str(report), '--image-root', str(images)])
    return dict(root=root, metadata=metadata, out=out, report=report, images=images,
                group_lock=group_lock, evidence=evidence, audit=audit, queue=queue,
                result=result, gen_val=len(gen_val), gen_test=len(gen_test))


def test_resplit_cli_report_lineage_and_locks(locked_run):
    """Under: verification/report wiring dropped; over: valid locked shared-prompt data rejected."""
    run = locked_run
    p09_resplit.main()
    assert read_csv(run['out']) == run['result']
    report = json.loads((run['report']/'split_report.json').read_text())
    assert report['rows'] == report['image_files_verified'] == 52
    assert report['initial_priority_pairs_checked'] == 600
    assert report['directed_neighbor_pending_pairs'] == 0
    assert report['unreviewed_initial_candidates'] == 17
    assert report['full_candidate_independence_passed'] is False
    assert report['generation_train_overlap'] == {
        'prompt': dict(val=run['gen_val']-1, test=run['gen_test'], test_unseen=1),
        'prompt+noise_seed': dict(val=run['gen_val']-1, test=run['gen_test']-1, test_unseen=1)}
    assert report['image_hash_ledger_sha256'] == sha256(run['audit'])
    boundaries = read_csv(run['report']/'review_boundaries.csv')
    by_id = {r['image_id']: r for r in run['result']}
    assert len(boundaries) == 601
    for pair in boundaries:
        assert pair['split_a'] == by_id[pair['a']]['split']
        assert pair['split_b'] == by_id[pair['b']]['split']
    lock = json.loads((run['report']/'split_lock.json').read_text())
    assert lock['metadata_sha256'] == sha256(run['out'])
    assert lock['group_lock_sha256'] == sha256(run['group_lock'])
    assert lock['evidence_lock_sha256'] == sha256(run['evidence'])
    assert set(lock['outputs_sha256']) == {'split_report.json', 'review_boundaries.csv'}
    for name, expected in lock['outputs_sha256'].items():
        assert sha256(run['report']/name) == expected
    for section in ('verified_inputs_sha256', 'source_sha256'):
        for name, expected in lock[section].items():
            assert sha256(name) == expected


@pytest.mark.parametrize('defect', ['image', 'ledger_ids', 'out_exists', 'report_exists', 'group_evidence', 'support', 'queue'])
def test_resplit_cli_rejects_bad_evidence_without_output(locked_run, defect):
    """Under: tampering/overwrite accepted; over: intact evidence accepted in CLI test above."""
    run = locked_run
    if defect == 'image':
        row = read_csv(run['metadata'])[0]
        (Path(row['path'])).write_bytes(b'tampered image')
        message = 'image hash mismatch'
    elif defect == 'ledger_ids':
        run['audit'].write_text('')
        # Re-lock the changed ledger to reach the identity defence rather than its hash gate.
        lock = json.loads(run['group_lock'].read_text())
        lock['audit_verified_files'][str(run['audit'])] = sha256(run['audit'])
        write_json(run['group_lock'], lock)
        evidence = json.loads(run['evidence'].read_text())
        evidence['group_lock_sha256'] = sha256(run['group_lock'])
        write_json(run['evidence'], evidence)
        message = 'image ledger identity mismatch'
    elif defect in ('out_exists', 'report_exists'):
        target = run['out'] if defect == 'out_exists' else run['report']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'keep existing output')
        message = 'output exists'
    elif defect == 'group_evidence':
        evidence = json.loads(run['evidence'].read_text())
        evidence['group_lock_sha256'] = 'invalid'
        write_json(run['evidence'], evidence)
        message = 'group lock/evidence mismatch'
    elif defect == 'support':
        with (run['root']/'candidate_run_01/input_lock.json').open('a') as handle:
            handle.write(' ')
        message = 'supporting hash mismatch'
    else:
        run['queue'].write_bytes(b'changed queue')
        message = 'full candidate queue hash mismatch'
    with pytest.raises(ValueError, match=message):
        p09_resplit.main()
    if defect == 'out_exists':
        assert run['out'].read_bytes() == b'keep existing output'
    else:
        assert not run['out'].exists()
    if defect == 'report_exists':
        assert run['report'].read_bytes() == b'keep existing output'
    else:
        assert not run['report'].exists()

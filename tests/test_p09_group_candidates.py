"""P09 후보는 검토 근거이며 숫자 유사도를 동일 룩 확정으로 승격하지 않는다."""
import csv
import json

import numpy as np
import pytest

from scripts.p09_group_candidates import (
    build_groups, candidate_pairs, load_features, verify_audit_lock,
)


def rows():
    return [dict(image_id=i, label='1', source_domain='kfashion', look_group='',
                 path=f'images/real/{i}.jpg', split=s)
            for i, s in [('a', 'train'), ('b', 'train'), ('c', 'val'), ('d', 'test')]]


def test_candidates_cover_same_split_neighbors_and_wide_phash_without_auto_confirmation():
    """Under: retain same-split/wide-pHash pairs; over: exclude unrelated pairs."""
    data = rows()
    features = np.array([[1, 0], [1, .01], [0, 1], [-1, 0]], dtype=float)
    hashes = [0, (1 << 26)-1, (1 << 64)-1, ((1 << 64)-1) ^ 1]
    pairs = list(candidate_pairs(data, features, hashes, top_k=1, real_phash=26))
    by_pair = {(p['a'], p['b']): p for p in pairs}
    assert 'embedding_topk' in by_pair['a', 'b']['reasons']
    assert 'phash' in by_pair['a', 'b']['reasons']
    assert by_pair['a', 'b']['phash_distance'] == 26
    assert ('a', 'd') not in by_pair
    assert all('verdict' not in p for p in pairs)
    # Evaluation labels/split do not control candidate discovery.
    changed = [dict(r, split='test') for r in data]
    assert list(candidate_pairs(changed, features, hashes, top_k=1, real_phash=26)) == pairs


def test_grouping_preserves_existing_groups_and_transitivity_without_merging_unconfirmed():
    """Under: retain original/transitive groups; over: never merge unconfirmed pairs."""
    data = rows()
    data[0]['look_group'] = data[1]['look_group'] = 'original'
    reviews = [dict(a='b', b='c', verdict='confirmed_same_look', reason='checked'),
               dict(a='c', b='d', verdict='unconfirmed', reason='uncertain')]
    groups = build_groups(data, reviews)
    assert groups['a'] == groups['b'] == groups['c']
    assert groups['d'] != groups['a']
    assert build_groups(list(reversed(data)), reviews) == groups
    reviews[1]['verdict'] = 'different_look'
    assert build_groups(data, reviews) == groups
    with pytest.raises(ValueError, match='conflict'):
        build_groups(data, reviews + [dict(a='a', b='b', verdict='confirmed_same_look', reason='visual'),
                                     dict(a='a', b='c', verdict='different_look', reason='opposite')])
    with pytest.raises(ValueError, match='unknown'):
        build_groups(data, [dict(a='a', b='missing', verdict='unconfirmed', reason='bad')])


def test_generation_prompt_or_seed_sharing_does_not_merge_groups():
    """Under: merge confirmed GEN pairs; over: never merge from prompt/seed alone."""
    data = [dict(r, label='0', generator='g', prompt_id='same', noise_seed=42) for r in rows()]
    groups = build_groups(data, [])
    assert len(set(groups.values())) == 4
    groups = build_groups(data, [dict(a='a', b='b', verdict='confirmed_same_look', reason='visual')])
    assert groups['a'] == groups['b'] != groups['c']


def test_audit_lock_accepts_matching_files_and_rejects_tampering(tmp_path):
    """Under: reject tampering; over: accept unchanged authoritative files."""
    import hashlib
    source = tmp_path/'metadata.csv'
    source.write_text('original')
    lock = dict(inputs_sha256={str(source): hashlib.sha256(source.read_bytes()).hexdigest()},
                source_sha256={}, artifacts_sha256={})
    path = tmp_path/'audit_lock.json'; path.write_text(json.dumps(lock))
    assert verify_audit_lock(path)
    source.write_text('changed')
    with pytest.raises(ValueError, match='hash'):
        verify_audit_lock(path)


def test_cache_requires_complete_chunks_finite_features_and_exact_identity(tmp_path):
    """Under: reject missing/stale/malformed chunks; over: allow valid short last chunks."""
    identity = {'metadata': 'hash'}
    (tmp_path/'identity.json').write_text(json.dumps(identity))
    np.savez(tmp_path/'00000.npz', features=np.ones((2, 3)), logits=[1, 2])
    np.savez(tmp_path/'00002.npz', features=np.ones((1, 3)), logits=[3])
    assert load_features(tmp_path, identity, 3, chunk_size=2).shape == (3, 3)
    with pytest.raises(ValueError, match='identity'):
        load_features(tmp_path, {'metadata': 'different'}, 3, chunk_size=2)
    np.savez(tmp_path/'00002.npz', features=np.ones((2, 3)), logits=[3, 4])
    with pytest.raises(ValueError, match='shape'):
        load_features(tmp_path, identity, 3, chunk_size=2)
    (tmp_path/'00002.npz').unlink()
    with pytest.raises(ValueError, match='chunk'):
        load_features(tmp_path, identity, 3, chunk_size=2)


def test_nearest_replay_detects_row_permutation_but_accepts_float_rounding():
    """Under: catch cache row swaps; over: accept original float32 rounding."""
    from scripts.p09_group_candidates import verify_nearest
    data = rows()
    features = np.array([[1, 0], [0, 1], [1, .1], [.2, 1]], dtype=np.float32)
    queries = [dict(image_id='c', nearest_train='a', cosine=float(1/np.sqrt(1.01))),
               dict(image_id='d', nearest_train='b', cosine=float(1/np.sqrt(1.04)))]
    verify_nearest(data, features, queries)
    with pytest.raises(ValueError, match='row order'):
        verify_nearest(data, features[[1, 0, 2, 3]], queries)
    with pytest.raises(ValueError, match='query IDs'):
        verify_nearest(data, features, queries[:1])


def test_grouping_rejects_cross_class_and_duplicate_review_relations():
    """Under: refuse inconsistent merges; over: retain valid single-class groups."""
    data = rows()
    data[-1]['label'] = '0'
    review = dict(a='a', b='b', verdict='confirmed_same_look', reason='visual')
    assert build_groups(data, [review])['a'] == build_groups(data, [review])['b']
    with pytest.raises(ValueError, match='duplicate review'):
        build_groups(data, [review, dict(review, a='b', b='a')])
    with pytest.raises(ValueError, match='cross-class'):
        build_groups(data, [dict(review, b='d')])


@pytest.mark.parametrize('label', ['1', '0'])
def test_contact_sheets_accept_originals_and_reject_changed_images(tmp_path, monkeypatch, label):
    """Under: reject stale originals; over: allow valid hash-matched review images."""
    from PIL import Image
    from scripts.p09_group_candidates import sha256, write_csv
    from scripts.p09_review_pairs import main
    monkeypatch.chdir(tmp_path)
    audit = tmp_path/'experiments/p08_anonymized/leakage_audit'; audit.mkdir(parents=True)
    (audit/'audit_lock.json').write_text(json.dumps(dict(inputs_sha256={}, source_sha256={}, artifacts_sha256={})))
    (tmp_path/'data').mkdir()
    data = [dict(r, label=label) for r in rows()[:2]]; data[0]['look_group'] = 'g1'; data[1]['look_group'] = 'g2'
    write_csv(tmp_path/'data/metadata.csv', data, list(data[0]))
    images = tmp_path/'images/real'; images.mkdir(parents=True)
    for i in ('a', 'b'):
        Image.new('RGB', (12, 20), 'red').save(images/f'{i}.jpg')
    (audit/'image_audit.jsonl').write_text(''.join(json.dumps(dict(image_id=i, sha256=sha256(images/f'{i}.jpg')))+'\n' for i in ('a', 'b')))
    run = tmp_path/'run'; run.mkdir()
    pair = dict(a='a', b='b', cosine=.99, phash_distance=12, reasons='embedding_topk')
    write_csv(run/'priority_candidates.csv', [pair], list(pair))
    write_csv(run/'seed_review.csv', [], ['a', 'b', 'verdict', 'reason'])
    (run/'input_lock.json').write_text(json.dumps(dict(outputs_sha256={p.name: sha256(p) for p in run.iterdir()})))
    args = ['review', '--run', str(run), '--image-root', str(images.parent), '--label', label]
    if label == '0':
        args.append('--unique-images')
    args += ['--out', str(tmp_path/'valid')]
    monkeypatch.setattr('sys.argv', args)
    main()
    assert (tmp_path/'valid/000.jpg').exists()
    Image.new('RGB', (12, 20), 'blue').save(images/'a.jpg')
    monkeypatch.setattr('sys.argv', args[:-1]+[str(tmp_path/'invalid')])
    with pytest.raises(ValueError, match='original image hash'):
        main()


def test_original_label_filenames_recover_sequences_without_using_numeric_id_proximity(tmp_path):
    """Under: recover renamed source sequences; over: never group numeric neighbors."""
    import zipfile
    from scripts.p09_filename_sequences import extract_sequences
    data = [dict(r, style='modern') for r in rows()]
    archive = tmp_path/'labels.zip'
    with zipfile.ZipFile(archive, 'w') as handle:
        for i, name in zip(('a', 'b', 'c', 'd'), ('MALL_001_00.jpg', 'MALL_001_01.jpg', '123.jpg', '124.jpg')):
            handle.writestr(f'modern/{i}.json', json.dumps({'데이터셋 정보': {'파일 이름': name}}))
    records, pairs = extract_sequences(data, archive)
    assert len(records) == 4
    assert pairs == [dict(a='a', b='b', filename_group='MALL_001')]
    assert all(len(r['label_sha256']) == 64 for r in records)


def test_conservative_colocation_does_not_claim_all_members_are_the_same_look():
    """Under: keep uncertain edges together; over: allow distinct looks in that split group."""
    data = rows()
    reviews = [dict(a='a', b='b', verdict='conservative_colocation', reason='uncertain, keep together'),
               dict(a='b', b='c', verdict='confirmed_same_look', reason='visual'),
               dict(a='a', b='c', verdict='different_look', reason='visually distinct')]
    groups = build_groups(data, reviews)
    assert groups['a'] == groups['b'] == groups['c'] != groups['d']
    reviews[0]['verdict'] = 'confirmed_same_look'
    with pytest.raises(ValueError, match='conflict'):
        build_groups(data, reviews)


def test_neighbor_expansion_uses_each_confirmed_members_own_topk_and_keeps_reviewed_pairs_out():
    """Under: include a confirmed member's new neighbor; over: exclude incoming-only links."""
    from scripts.p09_group_candidates import review_neighbors
    data = rows()
    features = np.array([[1, 0], [1, .01], [.9, .1], [0, 1]])
    reviews = [dict(a='a', b='b', verdict='confirmed_same_look', reason='visual')]
    assert review_neighbors(data, features, [0, 0, 0, 0], reviews, top_k=1) == []
    result = review_neighbors(data, features, [0, 0, 0, 0], reviews, top_k=2)
    assert {(p['a'], p['b']) for p in result} == {('a', 'c'), ('b', 'c')}
    reviews.append(dict(a='a', b='c', verdict='different_look', reason='different'))
    assert [(p['a'], p['b']) for p in review_neighbors(data, features, [0, 0, 0, 0], reviews, top_k=2)] == [('b', 'c')]


def test_existing_phash_group_is_preserved_as_allocation_without_asserting_visual_identity():
    """Under: preserve old split groups; over: allow known different looks in coarse old groups."""
    data = rows()
    data[0]['look_group'] = data[1]['look_group'] = 'coarse_phash'
    reviews = [dict(a='a', b='b', verdict='different_look', reason='distinct outfits')]
    assert build_groups(data, reviews)['a'] == build_groups(data, reviews)['b']
    reviews.append(dict(a='b', b='c', verdict='confirmed_same_look', reason='visual'))
    assert build_groups(data, reviews)['a'] == build_groups(data, reviews)['c']


def test_neighbor_cli_projects_rich_reviews_and_locks_outputs_without_overwriting(tmp_path, monkeypatch):
    """Under: consume real review metadata; over: preserve raw evidence and refuse overwrites."""
    from scripts.p09_group_candidates import main, sha256, write_csv
    monkeypatch.chdir(tmp_path)
    audit = tmp_path/'audit'; audit.mkdir()
    cache = tmp_path/'cache'; cache.mkdir()
    (tmp_path/'data').mkdir(); (tmp_path/'scripts').mkdir()
    (tmp_path/'scripts/p08_leakage_probe.py').write_text('pinned source')
    p08 = tmp_path/'experiments/p08_anonymized'; (p08/'calibration').mkdir(parents=True)
    (p08/'face_boxes.csv').write_text('face cache')
    artifact = p08/'calibration/calibration.json'; artifact.write_text(json.dumps(dict(checkpoint_sha256='checkpoint')))
    data = rows()[:3]
    write_csv(tmp_path/'data/metadata.csv', data, list(data[0]))
    identity = dict(checkpoint='checkpoint', calibration=sha256(artifact), metadata=sha256('data/metadata.csv'),
                    cache=sha256(p08/'face_boxes.csv'), source=sha256('scripts/p08_leakage_probe.py'))
    (cache/'identity.json').write_text(json.dumps(identity))
    np.savez(cache/'00000.npz', features=np.array([[1., 0], [1., 0], [0, 1.]]), logits=np.zeros(3))
    # a/b are train, so only c is a saved query.
    (audit/'embedding_nearest_train.json').write_text(json.dumps([dict(image_id='c', nearest_train='a', cosine=0.)]))
    (audit/'audit_lock.json').write_text(json.dumps(dict(inputs_sha256={}, source_sha256={}, artifacts_sha256={})))
    (audit/'image_audit.jsonl').write_text(''.join(json.dumps(dict(image_id=r['image_id'], phash='0'))+'\n' for r in data))
    (audit/'cross_split_phash.json').write_text('[]'); (audit/'generation_provenance.json').write_text('[]')
    write_csv(audit/'visual_review.csv', [], ['image_id', 'train_image_id', 'verdict', 'reason'])
    rich = dict(a='a', b='b', verdict='confirmed_same_look', reason='visual', reviewer='Codex', sheet='000.jpg')
    review = tmp_path/'review.csv'; write_csv(review, [rich], list(rich)); original = review.read_bytes()
    out, queue = tmp_path/'out', tmp_path/'queue'
    monkeypatch.setattr('sys.argv', ['tool', '--audit', str(audit), '--cache', str(cache), '--out', str(out),
                                   '--queue', str(queue), '--neighbors-from', str(review)])
    main()
    snapshot = list(csv.DictReader((out/'seed_review.csv').open()))
    assert snapshot == [{k: rich[k] for k in ('a', 'b', 'verdict', 'reason')}]
    assert review.read_bytes() == original
    lock = json.loads((out/'input_lock.json').read_text())
    assert lock['parameters']['mode'] == 'neighbors'
    assert all(sha256(out/name) == h for name, h in lock['outputs_sha256'].items())
    with pytest.raises(ValueError, match='output exists'):
        main()

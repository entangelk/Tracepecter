"""Owner reuse preserves the preregistered minimum and waits for actual new answers."""
import json

import pytest
import yaml

from scripts import p09_face_review as review
from scripts.p09_face_review import owner_plan, merge_answers
from src.anonymize import file_hash


def test_owner_plan_reuses_only_selected_prior_answers():
    """Under: missing review silently confirmed; over: valid prior answers requested again."""
    ids = ['a', 'b', 'c', 'd', 'e', 'f']
    agent = {i: (1, 0) for i in ids}
    agent['a'] = (1, 1)
    detected = {i: 1 for i in ids}
    settings = dict(seed=42, annotations=dict(owner_random_fraction=.2))
    check, reused, pending = owner_plan(ids, agent, detected, settings, {'a': (2, 1), 'foreign': (1, 0)}, ['f'])
    assert check == [dict(image_id='a', reason='flagged'), dict(image_id='e', reason='random'), dict(image_id='f', reason='visual_ambiguity')]
    assert reused == {'a': (2, 1)}
    assert pending == ['e', 'f']
    with pytest.raises(ValueError, match='pending'):
        merge_answers(check, reused, {'e': (1, 0)})
    assert merge_answers(check, reused, {'e': (0, 0), 'f': (1, 0)}) == {'a': (2, 1), 'e': (0, 0), 'f': (1, 0)}
    with pytest.raises(ValueError):
        merge_answers(check, reused, {'e': (1, 2), 'f': (1, 0)})
    with pytest.raises(ValueError):
        merge_answers(check, reused, {'e': (1, 0), 'f': (1, 0), 'a': (1, 0)})


def test_extra_review_cannot_replace_minimum_or_add_foreign_ids():
    """Under: extra scope changes minimum; over: already selected extra duplicated."""
    settings = dict(seed=42, annotations=dict(owner_random_fraction=.2))
    args = (['a'], {'a': (1, 1)}, {'a': 1}, settings, {})
    assert owner_plan(*args, ['a'])[0] == [dict(image_id='a', reason='flagged')]
    with pytest.raises(ValueError, match='extra'):
        owner_plan(*args, ['foreign'])


@pytest.fixture
def merge_fixture(tmp_path, monkeypatch):
    config = tmp_path/'config.yaml'
    config.write_text(yaml.safe_dump(dict(output_dir=str(tmp_path), annotations=dict(output='face_review.csv'))))
    monkeypatch.setattr(review, 'CONFIG', str(config))
    review.shared.write_csv(tmp_path/'face_review_template.csv', ['image_id'], [dict(image_id=i) for i in ['a', 'b', 'c']])
    review.write_counts(tmp_path/'face_review_agent.csv', {i: (1, 0) for i in ['a', 'b', 'c']})
    review.shared.write_csv(tmp_path/'face_review_owner_check.csv', ['image_id', 'reason'], [dict(image_id=i, reason='flagged') for i in ['a', 'b']])
    review.write_counts(tmp_path/'face_review_owner_reused.csv', {'a': (0, 0)})
    review.shared.write_csv(tmp_path/'face_review_owner_pending.csv', ['image_id', 'reason'], [dict(image_id='b', reason='flagged')])
    paths = [config, *tmp_path.glob('*.csv')]
    (tmp_path/'owner_review_lock.json').write_text(json.dumps(dict(inputs_sha256={str(p):file_hash(p) for p in paths})))
    owner = tmp_path/'answer.csv'
    review.write_counts(owner, {'b': (2, 1)})
    return tmp_path, owner


def test_complete_owner_merge_keeps_reuse_and_overrides(merge_fixture):
    """Under: override/reuse lost; over: unchecked normal agent annotation rejected."""
    root, answer = merge_fixture
    review.merge(answer)
    rows = review.shared.read_csv(root/'face_review.csv')
    assert [(r['image_id'], r['visible_faces'], r['uncovered_visible_faces'], r['confirmed']) for r in rows] == [('a','0','0','1'), ('b','2','1','1'), ('c','1','0','1')]
    lock = json.loads((root/'face_review_lock.json').read_text())
    assert (lock['owner_rows'], lock['reused_owner_rows'], lock['new_owner_rows']) == (2, 1, 1)
    assert all(file_hash(root/name) == digest for name, digest in lock['sha256'].items())


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'invalid', 'fractional', 'foreign', 'evidence'])
def test_invalid_owner_input_writes_no_final(merge_fixture, damage):
    """Under: incomplete/corrupt evidence confirmed; over: valid merge accepted above."""
    root, answer = merge_fixture
    if damage == 'missing':
        answer.write_text('image_id,visible_faces,uncovered_visible_faces\n')
    elif damage == 'duplicate':
        answer.write_text(answer.read_text()+'b,2,1\n')
    elif damage == 'invalid':
        review.write_counts(answer, {'b': (0, 1)})
    elif damage == 'fractional':
        answer.write_text('image_id,visible_faces,uncovered_visible_faces\nb,1.5,0\n')
    elif damage == 'foreign':
        review.write_counts(answer, {'foreign': (1, 0)})
    else:
        (root/'face_review_agent.csv').write_text('tampered')
    with pytest.raises(ValueError):
        review.merge(answer)
    assert not any((root/name).exists() for name in ['face_review.csv', 'face_review_lock.json', 'face_review_owner.csv', 'face_review_owner_new.csv'])

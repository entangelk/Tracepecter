"""P09-02: reject lost groups without merging different looks or shared prompts."""
import csv
import json
import sys

import pytest

from scripts.split_dataset import reviewed_group_split
from scripts.p09_resplit import audit_reviews, verify_group_lock
from test_split_dataset import _real_row, _gen_row


def fixture_rows():
    rows = [_real_row(f'r{i}', f'old{i}') for i in range(30)]
    rows += [_gen_row(f'g{i}') for i in range(30)]
    rows += [_gen_row('u', 'sd35_medium')]
    rows[1]['look_group'] = rows[0]['look_group']
    rows[2]['category'] = '하의'
    mapping = {r['image_id']: 'group_'+r['image_id'] for r in rows}
    for i in range(3):
        mapping[f'r{i}'] = 'transitive'
    # The legacy per-image allocation separates g0 (train) and g4 (test).
    mapping['g4'] = mapping['g0']
    return rows, [dict(image_id=i, group_id=g) for i, g in mapping.items()]


def test_groups_determinism_and_no_prompt_merging():
    """Under: transitive/multicell/GEN groups split; over: shared prompts merge."""
    rows, mapping = fixture_rows()
    result = reviewed_group_split(rows, mapping)
    again = reviewed_group_split(list(reversed(rows)), list(reversed(mapping)))
    assert result == again
    by_id = {r['image_id']: r for r in result}
    assert len({by_id[f'r{i}']['split'] for i in range(3)}) == 1
    assert len({by_id[f'r{i}']['look_group'] for i in range(3)}) == 1
    assert by_id['g0']['split'] == by_id['g4']['split']
    assert by_id['u']['split'] == 'test_unseen'
    assert {r['split'] for r in result if r['source_type'] == 'generated' and r['image_id'] != 'u'} == {'train', 'val', 'test'}
    for row in rows:
        for key, value in row.items():
            if key != 'split' and not (key == 'look_group' and row['source_type'] == 'real'):
                assert by_id[row['image_id']][key] == value
    assert all(not r['split'] for r in rows), 'input must not be mutated'


@pytest.mark.parametrize('defect', ['missing', 'duplicate_mapping', 'extra', 'empty', 'duplicate_id', 'old_group', 'class', 'unseen'])
def test_invalid_mapping_rejected(defect):
    """Under: invalid mappings pass; over: complete conservative groups rejected."""
    rows, mapping = fixture_rows()
    if defect == 'missing':
        mapping.pop()
    elif defect == 'duplicate_mapping':
        mapping.append(mapping[0].copy())
    elif defect == 'extra':
        mapping.append(dict(image_id='unknown', group_id='extra'))
    elif defect == 'empty':
        mapping[0]['group_id'] = ''
    elif defect == 'duplicate_id':
        rows.append(rows[0].copy())
    elif defect == 'old_group':
        mapping[1]['group_id'] = 'split_old'
    elif defect == 'class':
        mapping[30]['group_id'] = mapping[0]['group_id']
    elif defect == 'unseen':
        mapping[-1]['group_id'] = mapping[30]['group_id']
    with pytest.raises(ValueError):
        reviewed_group_split(rows, mapping)


def test_review_crossings_both_directions():
    """Under: unresolved crossing accepted; over: different-look crossing rejected."""
    rows = [_real_row('a', 'a'), _real_row('b', 'b')]
    rows[0]['split'], rows[1]['split'] = 'val', 'test'
    review = dict(a='a', b='b', verdict='different_look', reason='different clothes')
    report = audit_reviews(rows, [review])
    assert report['test|val']['different_look'] == 1
    for verdict in ('confirmed_same_look', 'unconfirmed'):
        with pytest.raises(ValueError):
            audit_reviews(rows, [dict(review, verdict=verdict)])
    rows[1]['split'] = 'val'
    audit_reviews(rows, [dict(review, verdict='unconfirmed')])


def test_locked_input_tampering_rejected(tmp_path):
    """Under: changed output passes; over: intact locked data rejected."""
    from scripts.p09_group_candidates import sha256
    output = tmp_path/'group_mapping.csv'
    output.write_text('image_id,group_id\na,g\n')
    metadata = tmp_path/'metadata.csv'
    metadata.write_text('metadata')
    lock = dict(metadata_sha256=sha256(metadata), audit_verified_files={}, review_inputs_sha256={},
                sources_sha256={}, outputs_sha256={'group_mapping.csv': sha256(output)},
                closure_sha256=sha256(metadata))
    # Closure is addressed relative to final/ just like production.
    final = tmp_path/'final'
    final.mkdir()
    output.rename(final/output.name)
    (tmp_path/'neighbor_closure.json').write_text('metadata')
    (final/'group_lock.json').write_text(json.dumps(lock))
    verify_group_lock(final/'group_lock.json', metadata)
    (final/'group_mapping.csv').write_text('tampered')
    with pytest.raises(ValueError, match='hash mismatch'):
        verify_group_lock(final/'group_lock.json', metadata)


def test_mapping_cli_and_new_test_b_real(tmp_path, monkeypatch):
    """Under: GEN mapping ignored or old REAL reused; over: valid roots/splits rejected."""
    from scripts import split_dataset
    from src.dataset import MetadataDataset
    from src.evaluate import evaluation_indices
    from test_split_dataset import _write_csv

    rows, mapping = fixture_rows()
    source = tmp_path/'original.csv'
    _write_csv(source, rows)
    mapping_path = tmp_path/'mapping.csv'
    with mapping_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, ['image_id', 'group_id'])
        writer.writeheader()
        writer.writerows(mapping)
    out = tmp_path/'versions'/'p09_r1'/'metadata.csv'
    monkeypatch.setattr(sys, 'argv', ['split_dataset.py', '--inputs', str(source),
                                    '--out', str(out), '--group-mapping', str(mapping_path)])
    assert split_dataset.main() == 0
    dataset = MetadataDataset(out, 16, False, False, image_root=tmp_path/'images')
    assert dataset.image_path(0) == tmp_path/dataset.rows[0].path
    standard, test_b = evaluation_indices(dataset.rows)
    expected_real = {r.image_id for r in dataset.rows if r.split == 'test' and r.label == 1}
    assert expected_real
    assert {dataset.rows[i].image_id for i in test_b if dataset.rows[i].label == 1} == expected_real
    assert {dataset.rows[i].image_id for i in test_b if dataset.rows[i].label == 0} == {'u'}
    actual = {r.image_id: r.split for r in dataset.rows}
    assert actual['g0'] == actual['g4']
    assert set(actual) == {r['image_id'] for r in rows}

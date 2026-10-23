"""P09-03 preregistration: lock the new cohort without changing P08 training or cue gates."""
import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from experiments.p09_leakage_repair.r1.training.prepare import freeze

ROOT = Path('experiments/p09_leakage_repair/r1')


def read(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def test_p09_training_preserves_model_and_new_artifact_boundaries():
    """Under: old split/head output reused; over: model/augmentation settings changed."""
    old = yaml.safe_load(Path('configs/anonymized.yaml').read_text())
    new = yaml.safe_load(Path('configs/p09_r1_train.yaml').read_text())
    assert new['data']['metadata_csv'] == 'data/versions/p09_r1/metadata.csv'
    assert new['output']['checkpoint_dir'] == 'checkpoints/leakage_repair/r1'
    new['data']['metadata_csv'] = old['data']['metadata_csv']
    new['output'] = old['output']
    assert new == old


def test_p09_diagnostic_rules_unchanged_except_cohort_and_artifacts():
    """Under: gates weakened or old cohort used; over: seed/annotation/threshold rules drift."""
    old = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    new = yaml.safe_load(Path('configs/p09_r1_diagnostic.yaml').read_text())
    assert new['output_dir'] == str(ROOT/'diagnostic')
    assert new['inputs']['metadata'] == 'data/versions/p09_r1/metadata.csv'
    assert new['inputs']['real_review'] == str(ROOT/'diagnostic/real_disc_review_train.csv')
    assert new['candidate_calibration'] == str(ROOT/'calibration/calibration.json')
    for key in ('output_dir', 'candidate_calibration'):
        new[key] = old[key]
    for key in ('metadata', 'real_review'):
        new['inputs'][key] = old['inputs'][key]
    assert new == old


def test_preregistration_new_ids_lineage_and_sample_manifest():
    """Under: unreviewed IDs claimed confirmed or old split used; over: valid old evidence discarded."""
    metadata = read('data/versions/p09_r1/metadata.csv')
    meta = {r['image_id']: r for r in metadata}
    manifest = read(ROOT/'training/sample_ids.csv')
    assert manifest == [{k: r[k] for k in ('image_id', 'split', 'path', 'label')}
                        for r in metadata if r['split'] in ('train', 'val')]
    source = read('experiments/p08_anonymized/measure/real_disc_review.csv')
    selected = read(ROOT/'diagnostic/real_disc_review_train.csv')
    assert selected == [r for r in source if meta[r['image_id']]['split'] == 'train']
    interventions = read(ROOT/'diagnostic/real_interventions.csv')
    assert {r['candidate_id'] for r in interventions} == {r['candidate_id'] for r in selected if r['confirmed'] == '1'}
    assert len({r['image_id'] for r in interventions}) >= 80
    target = {r['image_id'] for r in metadata if r['label'] == '0' and r['split'] in ('test', 'test_unseen')}
    assert {r['image_id'] for r in read(ROOT/'diagnostic/face_review_template.csv')} == target
    prior = read('experiments/p08_anonymized/diagnostic/face_review.csv')
    reused = read(ROOT/'diagnostic/prior_face_review.csv')
    assert reused == [r for r in prior if r['image_id'] in target]
    owner = {r['image_id'] for r in read('experiments/p08_anonymized/diagnostic/face_review_owner.csv')}
    lineage = read(ROOT/'diagnostic/annotation_lineage.csv')
    prior_ids = {r['image_id'] for r in prior}
    assert lineage == [dict(image_id=i, prior_final=str(int(i in prior_ids)), prior_owner=str(int(i in owner)))
                       for i in sorted(target)]
    assert all(r['confirmed'] == '' for r in read(ROOT/'diagnostic/face_review_template.csv'))
    lock = json.loads((ROOT/'training/input_lock.json').read_text())
    for name, expected in lock['inputs_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
    assert lock['start_from_previous_head'] is False
    assert lock['bootstrap_unit'] == 'image'


def test_projection_freeze_rejects_changes_and_allows_identical_bytes(tmp_path):
    """Under: changed preregistration overwrites; over: identical regeneration refused."""
    path = tmp_path/'projection.csv'
    freeze(path, b'frozen')
    freeze(path, b'frozen')
    with pytest.raises(ValueError, match='differs'):
        freeze(path, b'changed')
    assert path.read_bytes() == b'frozen'

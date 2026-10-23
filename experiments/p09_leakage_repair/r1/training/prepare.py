"""Freeze P09 input projections before training; no model predictions."""
import csv
import hashlib
import io
import json
from pathlib import Path

import yaml

from scripts.p08_preregister import prepare

ROOT = Path('experiments/p09_leakage_repair/r1')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def freeze(path, content):
    path = Path(path)
    if path.exists() and path.read_bytes() != content:
        raise ValueError(f'frozen projection differs: {path}')
    path.write_bytes(content)


def freeze_csv(path, records, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    freeze(path, stream.getvalue().encode())


def main():
    lock = json.loads((ROOT/'split/split_lock.json').read_text())
    for section in ('verified_inputs_sha256', 'source_sha256'):
        for name, expected in lock[section].items():
            if digest(name) != expected:
                raise ValueError(f'split input/source mismatch: {name}')
    if digest(ROOT/'grouping/final/group_lock.json') != lock['group_lock_sha256']:
        raise ValueError('group lock mismatch')
    for name, expected in lock['outputs_sha256'].items():
        if digest(ROOT/'split'/name) != expected:
            raise ValueError(f'split output mismatch: {name}')
    train_path = Path('configs/p09_r1_train.yaml')
    diagnostic_path = Path('configs/p09_r1_diagnostic.yaml')
    train = yaml.safe_load(train_path.read_text())
    diagnostic = yaml.safe_load(diagnostic_path.read_text())
    if digest(train['data']['metadata_csv']) != lock['metadata_sha256']:
        raise ValueError('new metadata mismatch')
    metadata = rows(train['data']['metadata_csv'])
    meta = {r['image_id']: r for r in metadata}
    prior = Path('experiments/p08_anonymized')
    review = rows(prior/'measure/real_disc_review.csv')
    selected = [r for r in review if meta[r['image_id']]['split'] == 'train']
    freeze_csv(diagnostic['inputs']['real_review'], selected, list(review[0]))
    registration = prepare(diagnostic_path)
    target = {r['image_id'] for r in rows(ROOT/'diagnostic/face_review_template.csv')}
    previous = rows(prior/'diagnostic/face_review.csv')
    reused = [r for r in previous if r['image_id'] in target]
    freeze_csv(ROOT/'diagnostic/prior_face_review.csv', reused, list(previous[0]))
    owner = {r['image_id'] for r in rows(prior/'diagnostic/face_review_owner.csv')}
    freeze_csv(ROOT/'diagnostic/annotation_lineage.csv', [dict(
        image_id=i, prior_final='1' if i in {r['image_id'] for r in reused} else '0',
        prior_owner='1' if i in owner else '0') for i in sorted(target)],
        ['image_id', 'prior_final', 'prior_owner'])
    freeze_csv(ROOT/'training/sample_ids.csv', [
        {key: r[key] for key in ('image_id', 'split', 'path', 'label')}
        for r in metadata if r['split'] in ('train', 'val')], ['image_id', 'split', 'path', 'label'])
    freeze(ROOT/'training/config.yaml', train_path.read_bytes())
    sources = [str(p) for p in (train_path, diagnostic_path, ROOT/'training/prepare.py',
               ROOT/'diagnostic/preregistration.json', ROOT/'diagnostic/prior_face_review.csv',
               ROOT/'diagnostic/annotation_lineage.csv', ROOT/'training/sample_ids.csv',
               prior/'diagnostic/face_review_lock.json', prior/'diagnostic/face_review.csv',
               prior/'diagnostic/face_review_owner.csv', ROOT/'split/split_lock.json',
               Path(train['data']['metadata_csv']), Path('src/train.py'), Path('src/dataset.py'),
               Path('src/model.py'), Path('src/anonymize.py'), Path(train['data']['face_cache']),
               Path(train['anonymization']))]
    record = dict(inputs_sha256={p: digest(p) for p in sources},
                  real_images=registration['real_images'], real_discs=registration['real_discs'],
                  face_review_images=registration['face_review_images'],
                  prior_annotations=len(reused), prior_owner_annotations=len(target & owner),
                  pending_new_annotations=len(target)-len(reused),
                  bootstrap_unit=diagnostic['intervention_rules']['unit'],
                  start_from_previous_head=False, train_images=sum(r['split']=='train' for r in metadata),
                  validation_images=sum(r['split']=='val' for r in metadata))
    freeze(ROOT/'training/input_lock.json', (json.dumps(record, indent=2, ensure_ascii=False)+'\n').encode())
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()

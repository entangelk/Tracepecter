"""Prepare a score-blind P09 owner review, then merge only complete owner answers."""
import argparse
import base64
import io
import json
from pathlib import Path

import yaml

from scripts import p08_face_review as shared
from src.anonymize import file_hash

CONFIG = 'configs/p09_r1_diagnostic.yaml'
PAGE = Path('reports/errors/review/p09_leakage_repair/r1/face_review/owner/index.html')
PRIOR_OWNER = Path('experiments/p08_anonymized/diagnostic/face_review_owner.csv')


def owner_plan(ids, agent, detected, settings, prior_owner, extra):
    check = shared.owner_check_rows(ids, agent, detected, settings)
    if not set(extra) <= set(ids):
        raise ValueError('extra review IDs outside cohort')
    selected = {r['image_id'] for r in check}
    check += [dict(image_id=i, reason='visual_ambiguity') for i in sorted(set(extra)-selected)]
    reused = {r['image_id']: prior_owner[r['image_id']] for r in check if r['image_id'] in prior_owner}
    return check, reused, [r['image_id'] for r in check if r['image_id'] not in reused]


def merge_answers(check, reused, answers):
    selected = {r['image_id'] for r in check}
    if not set(reused) <= selected or set(answers) != selected-set(reused):
        raise ValueError('pending owner answer IDs mismatch')
    result = {**reused, **answers}
    if any(not all(type(n) is int for n in counts) or not 0 <= counts[1] <= counts[0] for counts in result.values()):
        raise ValueError('invalid owner face counts')
    return result


def write_counts(path, counts):
    shared.write_csv(path, shared.FIELDS, [dict(zip(shared.FIELDS, (i, *value))) for i, value in sorted(counts.items())])


def prepare():
    settings, meta, worker = shared.load(CONFIG)
    output = Path(settings['output_dir'])
    if (output/'owner_review_lock.json').exists() or PAGE.exists():
        raise ValueError('owner evidence exists; preserve frozen review')
    training_lock = output.parent/'training/input_lock.json'
    inputs = json.loads(training_lock.read_text())['inputs_sha256']
    # Preserve prior normalized owner evidence and its image/anonymization lineage.
    for path, digest in inputs.items():
        if file_hash(path) != digest:
            raise ValueError(f'training input changed: {path}')
    ids = shared.template_ids(settings)
    prior_rows = shared.read_csv(output/'prior_face_review.csv')
    if any(r['confirmed'] != '1' for r in prior_rows):
        raise ValueError('unconfirmed prior annotation')
    prior = {r['image_id']: (int(r['visible_faces']), int(r['uncovered_visible_faces'])) for r in prior_rows}
    new_path = output/'visual_review_new.csv'
    new_rows = shared.read_csv(new_path)
    new_ids = [r['image_id'] for r in new_rows]
    if len(set(new_ids)) != len(new_ids) or set(new_ids) != set(ids)-set(prior):
        raise ValueError('new manual annotation IDs mismatch')
    agent = {**prior, **{r['image_id']: (int(r['visible_faces']), int(r['uncovered_visible_faces'])) for r in new_rows}}
    if set(agent) != set(ids) or any(not 0 <= u <= v for v, u in agent.values()):
        raise ValueError('agent annotation cohort/count mismatch')
    old_ids = [r['image_id'] for r in shared.read_csv(PRIOR_OWNER)]
    old_owner = shared.read_counts(PRIOR_OWNER, old_ids)
    detected = {i: len(worker.cache[i]['boxes']) for i in ids}
    check, reused, pending = owner_plan(ids, agent, detected, settings, old_owner,
                                      [r['image_id'] for r in new_rows if r['owner_extra_check'] == '1'])
    # Rendering checks each original image hash against the unchanged face cache.
    cases = []
    for i in ids:
        path = shared.IMAGE_ROOT/Path(meta[i]['path']).relative_to('images')
        worker.boxes(None, i, path)
    for i in pending:
        buffer = io.BytesIO()
        shared.pair_image(meta[i], worker).save(buffer, format='JPEG', quality=95)
        cases.append(dict(image_id=i, image=base64.b64encode(buffer.getvalue()).decode('ascii')))
    template_path = Path(shared.__file__).with_name('p08_face_review.html')
    template = template_path.read_text().replace('P08', 'P09')
    template = template.replace('사진을 누르면 크게', '한 사람의 얼굴은 1개입니다(눈·코·입의 개수를 입력하지 않습니다). 사진을 누르면 크게')
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(template.replace('/*CASES*/null', json.dumps(cases).replace('</', '<\\/')))
    write_counts(output/'face_review_agent.csv', agent)
    shared.write_csv(output/'face_review_owner_check.csv', ('image_id', 'reason'), check)
    write_counts(output/'face_review_owner_reused.csv', reused)
    shared.write_csv(output/'face_review_owner_pending.csv', ('image_id', 'reason'), [r for r in check if r['image_id'] in pending])
    paths = [Path(CONFIG), training_lock, PRIOR_OWNER, new_path, output/'prior_face_review.csv',
             output/'face_review_template.csv', output/'preregistration.json', Path(__file__), template_path, PAGE]
    paths += [output/name for name in ('face_review_agent.csv', 'face_review_owner_check.csv', 'face_review_owner_reused.csv', 'face_review_owner_pending.csv')]
    lock = dict(cohort=len(ids), new_manual=len(new_ids), owner_required=len(check), reused=len(reused), pending=len(pending),
                score_blind=True, owner_input_semantics='face_count',
                inputs_sha256={str(p): file_hash(p) for p in paths})
    (output/'owner_review_lock.json').write_text(json.dumps(lock, ensure_ascii=False, indent=2)+'\n')
    print(f'owner required={len(check)}, reused={len(reused)}, pending={len(pending)}: {PAGE}')


def merge(owner_file):
    settings = yaml.safe_load(Path(CONFIG).read_text())
    output = Path(settings['output_dir'])
    if (output/'face_review.csv').exists() or (output/'face_review_lock.json').exists():
        raise ValueError('final annotations already exist')
    lock = json.loads((output/'owner_review_lock.json').read_text())
    for path, digest in lock['inputs_sha256'].items():
        if file_hash(path) != digest:
            raise ValueError(f'owner review evidence changed: {path}')
    pending = [r['image_id'] for r in shared.read_csv(output/'face_review_owner_pending.csv')]
    answers = shared.read_counts(owner_file, pending)
    reused_ids = [r['image_id'] for r in shared.read_csv(output/'face_review_owner_reused.csv')]
    reused = shared.read_counts(output/'face_review_owner_reused.csv', reused_ids) if reused_ids else {}
    check = shared.read_csv(output/'face_review_owner_check.csv')
    owner = merge_answers(check, reused, answers)
    # Validate the full agent cohort before creating any final output.
    shared.read_counts(output/'face_review_agent.csv', shared.template_ids(settings))
    raw = output/'face_review_owner_new.csv'
    raw.write_bytes(Path(owner_file).read_bytes())
    write_counts(output/'face_review_owner.csv', owner)
    shared.merge(settings)
    names = ['face_review_agent.csv', 'face_review_owner_check.csv', 'face_review_owner_reused.csv',
             'face_review_owner_pending.csv', 'face_review_owner_new.csv', 'face_review_owner.csv',
             'owner_review_lock.json', 'face_review.csv']
    final = dict(owner_input_semantics='face_count', owner_rows=len(owner), reused_owner_rows=len(reused),
                 new_owner_rows=len(answers), sha256={name: file_hash(output/name) for name in names})
    (output/'face_review_lock.json').write_text(json.dumps(final, ensure_ascii=False, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'merge'])
    parser.add_argument('--owner-file')
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare()
    elif args.owner_file:
        merge(args.owner_file)
    else:
        parser.error('merge requires --owner-file')


if __name__ == '__main__':
    main()

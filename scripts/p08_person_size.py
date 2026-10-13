"""P08-01 보고 전용 크기: REAL 의복 rect 합집합, GEN 수동 사람 높이."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import zipfile
from pathlib import Path

import yaml

from scripts import p08_measure as measure
from scripts.kfashion_common import PARTS


def rect_union_height(data):
    rects = data.get('데이터셋 정보', {}).get('데이터셋 상세설명', {}).get('렉트좌표', {})
    extents = []
    for part in PARTS:
        for rect in rects.get(part, []):
            if not rect:
                continue
            y, width, height = (float(rect[k]) for k in ('Y좌표', '가로', '세로'))
            if not all(math.isfinite(v) for v in (y, width, height)) or min(width, height) <= 0:
                raise ValueError('invalid clothing rect')
            extents.append((y, y + height))
    if not extents:
        raise ValueError('no clothing rect')
    return max(bottom for _, bottom in extents) - min(top for top, _ in extents)


def manual_height(top, bottom, image_height):
    if not 0 <= top < bottom <= 1:
        raise ValueError('invalid manual person extent')
    return (bottom - top) * image_height


def gen_sample(rows, detected, owner, seed):
    ids = [r['image_id'] for r in rows if r['pool'] == 'train_gen' and detected[r['image_id']]
           and owner.get(r['image_id'], int(r['agent_face_visible']))]
    selected = measure.seeded_order(ids, seed)[:50]
    if len(selected) != 50:
        raise ValueError('need 50 detected visible train faces')
    return selected


def file_hash(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def run(label_zip):
    settings = yaml.safe_load(Path(measure.CONFIG).read_text())
    config = Path('configs/anonymize.yaml')
    selected = yaml.safe_load(config.read_text())
    if selected['face_detector'] != settings['face_detector']:
        raise ValueError('selected detector differs from fixed measurement config')
    if file_hash(selected['face_detector']['model']) != selected['face_detector']['model_sha256']:
        raise ValueError('face detector hash mismatch')
    output = Path(settings['output_dir'])
    read = lambda name: list(csv.DictReader((output / name).open()))
    meta = {r['image_id']: r for r in csv.DictReader(open(measure.METADATA))}
    labels = read('recall_labels_agent.csv')
    owner = measure.read_owner_labels(output / 'recall_labels_owner.csv',
                                      {r['image_id'] for r in labels if r['pool'] == 'train_gen'})
    detected = {r['image_id']: bool(int(r['yunet_detected'])) for r in read('recall_detections.csv')}
    sample = gen_sample(labels, detected, owner, settings['real_discs']['seed'])
    if sample != [r['image_id'] for r in read('person_sample_gen.csv')]:
        raise ValueError('person sample differs from fixed selection')
    manual_rows = read('person_height_gen.csv')
    manual = {r['image_id']: r for r in manual_rows}
    if len(manual_rows) != len(manual) or set(manual) != set(sample):
        raise ValueError('manual person IDs must match the 50-image sample exactly')
    candidates = {r['candidate_id']: r for r in read('real_disc_candidates.csv')}
    real_rows, gen_rows, annotation_subset = [], [], {}
    with zipfile.ZipFile(label_zip) as archive:
        for reviewed in read('real_disc_review.csv'):
            if reviewed['confirmed'] != '1':
                continue
            disc = candidates[reviewed['candidate_id']]
            image_id = disc['image_id']
            member = f"{meta[image_id]['style']}/{image_id}.json"
            data = json.loads(archive.read(member))
            annotation_subset[member] = data['데이터셋 정보']['데이터셋 상세설명']['렉트좌표']
            height = rect_union_height(data)
            diameter = float(disc['major'])
            real_rows.append(dict(image_id=image_id, candidate_id=reviewed['candidate_id'],
                                  disc_major_px=diameter, part_union_height_px=height,
                                  diameter_per_part_height=diameter / height))
    for image_id in sample:
        rgb = measure.load_rgb(meta[image_id])
        top, bottom = (float(manual[image_id][k]) for k in ('top_fraction', 'bottom_fraction'))
        height = manual_height(top, bottom, rgb.shape[0])
        face = measure.detect_face(rgb, **selected['face_detector'])
        if face is None:
            raise ValueError(f'fixed detected face missing: {image_id}')
        diameter = max(face[2], face[3]) * selected['diameter_per_face']
        gen_rows.append(dict(image_id=image_id, image_height_px=rgb.shape[0], person_height_px=height,
                             diameter_px=diameter, diameter_per_person_height=diameter / height))
    write_csv(output / 'person_size_real.csv', real_rows)
    write_csv(output / 'person_size_gen.csv', gen_rows)
    (output / 'person_rects_real.json').write_text(
        json.dumps(annotation_subset, indent=2, ensure_ascii=False, sort_keys=True) + '\n')
    inputs = [measure.CONFIG, measure.METADATA, str(config), str(label_zip)] + [str(output / name) for name in (
        'real_disc_candidates.csv', 'real_disc_review.csv', 'recall_labels_agent.csv',
        'recall_detections.csv', 'recall_labels_owner.csv', 'person_sample_gen.csv', 'person_height_gen.csv')]
    report = dict(
        real=dict(n=len(real_rows), denominator='clothing_part_rect_union_height',
                  ratio_quartiles=measure.quartiles([r['diameter_per_part_height'] for r in real_rows])),
        gen=dict(n=len(gen_rows), denominator='manually_marked_visible_person_height',
                 ratio_quartiles=measure.quartiles([r['diameter_per_person_height'] for r in gen_rows]),
                 frame_clipped=sum(float(r['top_fraction']) == 0 or float(r['bottom_fraction']) == 1
                                   for r in manual_rows)),
        gate_applies=False, sample_seed=settings['real_discs']['seed'],
        selected_k=selected['diameter_per_face'], inputs_sha256={path: file_hash(path) for path in inputs})
    (output / 'person_size_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-zip', type=Path, required=True)
    run(parser.parse_args().label_zip)

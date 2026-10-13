"""P08-03: 예측 없이 진단 표본·입력 해시·사전등록 규격을 고정한다."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
from pathlib import Path

import yaml

from src.anonymize import file_hash, spec_hash, validate_boxes


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def csv_bytes(fields, rows):
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode('utf-8')


def prepare(config_path):
    config_path = Path(config_path)
    settings = yaml.safe_load(config_path.read_text())
    inputs = settings['inputs']
    metadata = read_csv(inputs['metadata'])
    meta = {r['image_id']: r for r in metadata}
    cache_rows = read_csv(inputs['face_cache'])
    cache = {r['image_id']: r for r in cache_rows}
    if len(meta) != len(metadata) or len(cache) != len(cache_rows) or set(meta) != set(cache):
        raise ValueError('metadata/cache IDs must be unique and equal')
    spec = yaml.safe_load(Path(inputs['anonymization']).read_text())
    detector = spec['face_detector']
    parameters = spec_hash({k: v for k, v in detector.items() if k not in ('model', 'model_sha256')})
    for row in cache_rows:
        validate_boxes(json.loads(row['boxes']))
        if row['detector_sha256'] != detector['model_sha256'] or row['parameters_sha256'] != parameters:
            raise ValueError('face cache detector/parameters mismatch')
    candidate_rows = read_csv(inputs['real_candidates'])
    candidates = {r['candidate_id']: r for r in candidate_rows}
    if len(candidates) != len(candidate_rows):
        raise ValueError('duplicate real candidate ID')
    reviews = read_csv(inputs['real_review'])
    if len({r['candidate_id'] for r in reviews}) != len(reviews):
        raise ValueError('duplicate real review ID')
    real = []
    for review in reviews:
        if review['confirmed'] not in ('0', '1'):
            raise ValueError('incomplete real review')
        if review['candidate_id'] not in candidates:
            raise ValueError('real review candidate missing')
        if review['confirmed'] == '1':
            row = candidates[review['candidate_id']]
            source = meta[row['image_id']]
            if review['image_id'] != row['image_id'] or source['label'] != '1' or source['split'] != settings['sampling']['real_split']:
                raise ValueError('real review lineage mismatch')
            real.append({k: row[k] for k in ('candidate_id', 'image_id', 'width', 'cx', 'cy', 'major', 'minor', 'angle')})
    real.sort(key=lambda r: (r['image_id'], r['candidate_id']))
    gen = sorted((r for r in metadata if r['label'] == '0' and r['split'] in settings['sampling']['gen_splits']),
                 key=lambda r: r['image_id'])
    selected = []
    rng = random.Random(settings['seed'])
    counts = {}
    for generator in sorted({r['generator'] for r in gen}):
        ids = [r['image_id'] for r in gen if r['generator'] == generator and json.loads(cache[r['image_id']]['boxes'])]
        rng.shuffle(ids)
        chosen = sorted(ids[:settings['sampling']['gen_detected_per_generator']])
        counts[generator] = dict(eligible=len(ids), selected=len(chosen))
        selected.extend(dict(image_id=i, generator=generator, split=meta[i]['split']) for i in chosen)
    target = json.loads(Path(inputs['measurement']).read_text())['synthetic']['selected_size']['synthetic_quartiles'][1]
    if not math.isfinite(target) or target <= 0:
        raise ValueError('invalid size target')
    outputs = {
        'real_interventions.csv': csv_bytes(('candidate_id', 'image_id', 'width', 'cx', 'cy', 'major', 'minor', 'angle'), real),
        'gen_interventions.csv': csv_bytes(('image_id', 'generator', 'split'), selected),
        'face_review_template.csv': csv_bytes(('image_id', 'visible_faces', 'uncovered_visible_faces', 'confirmed'),
                                             [dict(image_id=r['image_id'], visible_faces='', uncovered_visible_faces='', confirmed='') for r in gen]),
    }
    record = dict(version=settings['version'], config_sha256=file_hash(config_path),
                  inputs_sha256={name: file_hash(path) for name, path in inputs.items()},
                  size_target_diameter_over_width=target,
                  real_discs=len(real), real_images=len({r['image_id'] for r in real}),
                  face_review_images=len(gen), gen_interventions_by_generator=counts,
                  manifests_sha256={name: hashlib.sha256(data).hexdigest() for name, data in outputs.items()})
    outputs['preregistration.json'] = (json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')
    output = Path(settings['output_dir'])
    # 고정 후 다른 입력으로 덮어쓰지 않는다. 모든 파일을 확인한 뒤 쓴다.
    for name, data in outputs.items():
        path = output/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f'preregistration differs: {path}')
    output.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (output/name).write_bytes(data)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description='P08 diagnostic preregistration, no inference')
    parser.add_argument('--config', default='configs/anonymized_diagnostic.yaml')
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.config), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""P08-06 선행: 진단 예측 전에 GEN 얼굴 상태 주석을 만들고 소유자 확인을 거쳐 고정한다.

sheets: 원본·익명화 비교 이미지(비추적) → agent: 에이전트 표시 CSV(수동) →
owner: 확인 목록·블라인드 페이지 → merge: 최종 face_review.csv. 모델 예측은 사용하지 않는다.
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import math
import random
from pathlib import Path

import yaml
from PIL import Image

from src.anonymize import Anonymizer, bind_spec

IMAGE_ROOT = Path('/images')
FIELDS = ('image_id', 'visible_faces', 'uncovered_visible_faces')


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def template_ids(settings):
    ids = [r['image_id'] for r in read_csv(Path(settings['output_dir'])/'face_review_template.csv')]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate template image_id')
    return ids


def read_counts(path, ids):
    """두 얼굴 수가 정수이고 0 ≤ 남은 얼굴 ≤ 보이는 얼굴인 행을 정확히 ids만큼 읽는다."""
    rows = read_csv(path)
    if not rows or tuple(rows[0]) != FIELDS:
        raise ValueError(f'invalid columns: {path}')
    counts = {}
    for row in rows:
        if row['image_id'] in counts:
            raise ValueError(f'duplicate image_id: {row["image_id"]}')
        try:
            visible, uncovered = int(row['visible_faces']), int(row['uncovered_visible_faces'])
        except ValueError as exc:
            raise ValueError(f'non-integer face count: {row["image_id"]}') from exc
        if not 0 <= uncovered <= visible:
            raise ValueError(f'invalid face counts: {row["image_id"]}')
        counts[row['image_id']] = (visible, uncovered)
    if set(counts) != set(ids):
        raise ValueError(f'image_id set mismatch: {path}')
    return counts


def owner_check_rows(ids, agent, detected, settings):
    """보임 수≠검출 수 또는 남은 얼굴≥1은 전부, 나머지는 seed 정렬·shuffle 앞 ceil(fraction*n)."""
    flagged = [i for i in ids if agent[i][0] != detected[i] or agent[i][1] > 0]
    flagged_ids = set(flagged)
    rest = sorted(i for i in ids if i not in flagged_ids)
    random.Random(settings['seed']).shuffle(rest)
    extra = rest[:math.ceil(settings['annotations']['owner_random_fraction'] * len(rest))]
    return [dict(image_id=i, reason='flagged') for i in sorted(flagged)] + \
           [dict(image_id=i, reason='random') for i in sorted(extra)]


def pair_image(row, worker, panel=(768, 1024)):
    path = IMAGE_ROOT/Path(row['path']).relative_to('images')
    with Image.open(path) as handle:
        original = handle.convert('RGB')
    anonymized, _ = worker(original, row['image_id'], path)
    panels = []
    for image in (original, anonymized):
        image = image.copy()
        image.thumbnail(panel)
        panels.append(image)
    sheet = Image.new('RGB', (sum(p.width for p in panels) + 16, max(p.height for p in panels)), 'black')
    sheet.paste(panels[0], (0, 0))
    sheet.paste(panels[1], (panels[0].width + 16, 0))
    return sheet


def load(config):
    settings = yaml.safe_load(Path(config).read_text())
    meta = {r['image_id']: r for r in read_csv(settings['inputs']['metadata'])}
    spec = yaml.safe_load(Path(settings['inputs']['anonymization']).read_text())
    worker = Anonymizer(bind_spec(spec), settings['inputs']['face_cache'])
    return settings, meta, worker


def sheets_stage(settings, meta, worker, sheets):
    sheets.mkdir(parents=True, exist_ok=True)
    for image_id in template_ids(settings):
        pair_image(meta[image_id], worker).save(sheets/f'{image_id}.jpg', quality=90)


def owner_stage(settings, meta, worker, sheets):
    output = Path(settings['output_dir'])
    ids = template_ids(settings)
    agent = read_counts(output/'face_review_agent.csv', ids)
    detected = {i: len(worker.cache[i]['boxes']) for i in ids}
    rows = owner_check_rows(ids, agent, detected, settings)
    write_csv(output/'face_review_owner_check.csv', ('image_id', 'reason'), rows)
    cases = []
    for row in rows:
        buffer = io.BytesIO()
        pair_image(meta[row['image_id']], worker).save(buffer, format='JPEG', quality=90)
        cases.append(dict(image_id=row['image_id'], image=base64.b64encode(buffer.getvalue()).decode('ascii')))
    template = Path(__file__).with_name('p08_face_review.html').read_text()
    sheets.mkdir(parents=True, exist_ok=True)
    (sheets/'index.html').write_text(template.replace('/*CASES*/null', json.dumps(cases).replace('</', '<\\/')))
    print(f'{sheets/"index.html"}: {len(rows)} images')


def merge(settings):
    """소유자 확인 목록 전부가 소유자 값으로 채워졌을 때만 confirmed=1 최종 파일을 쓴다."""
    output = Path(settings['output_dir'])
    ids = template_ids(settings)
    agent = read_counts(output/'face_review_agent.csv', ids)
    check = [r['image_id'] for r in read_csv(output/'face_review_owner_check.csv')]
    owner = read_counts(output/'face_review_owner.csv', check)
    rows = []
    for image_id in ids:
        visible, uncovered = owner.get(image_id, agent[image_id])
        rows.append(dict(image_id=image_id, visible_faces=visible, uncovered_visible_faces=uncovered, confirmed=1))
    write_csv(output/settings['annotations']['output'], FIELDS + ('confirmed',), rows)
    changed = sum(owner[i] != agent[i] for i in check)
    print(f'{len(rows)} images, owner checked {len(check)}, changed {changed}')
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description='P08 GEN face-state annotation, no inference')
    parser.add_argument('stage', choices=['sheets', 'owner', 'merge'])
    parser.add_argument('--config', default='configs/anonymized_diagnostic.yaml')
    parser.add_argument('--sheets', default='reports/errors/review/p08_face_review')
    args = parser.parse_args(argv)
    if args.stage == 'merge':
        merge(yaml.safe_load(Path(args.config).read_text()))
        return
    settings, meta, worker = load(args.config)
    sheets = Path(args.sheets)
    if args.stage == 'sheets':
        sheets_stage(settings, meta, worker, sheets/'agent')
    else:
        owner_stage(settings, meta, worker, sheets/'owner')


if __name__ == '__main__':
    main()

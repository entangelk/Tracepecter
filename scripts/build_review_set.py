"""P06-03: config에 고정한 규칙으로 ≥100 검토군을 결정적으로 구성한다(DB-05 A)."""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import yaml

from src.evaluate import file_sha256

PRIORITY = ('false_positive', 'false_negative', 'low_confidence', 'transform_flip', 'high_confidence')


def build_review_set(metadata, logits, cases, temperature, threshold, rules) -> list[dict]:
    """metadata: image_id→row, logits: (image_id, condition)→logit, cases: image_id→오류/경계 유형."""
    from src.calibration import apply_temperature

    def probability(image_id, condition='original'):
        return float(apply_temperature([logits[image_id, condition]], temperature)[0])

    conditions = sorted({c for _, c in logits} - {'original'})
    targets = sorted({i for i, c in logits if c == 'original' and metadata[i]['split'] != 'val'})
    chosen = dict(cases)
    for image_id in targets:
        original = probability(image_id) >= threshold
        if image_id not in chosen and any(
                (image_id, c) in logits and (probability(image_id, c) >= threshold) != original
                for c in conditions):
            chosen[image_id] = 'transform_flip'
    rng = random.Random(rules['seed'])
    strata = {}
    for image_id in targets:
        if image_id in chosen:
            continue
        row = metadata[image_id]
        key = ('generator', row['generator']) if row['label'] == '0' else ('category', row['category'])
        strata.setdefault(key, []).append(image_id)
    for (kind, _), members in sorted(strata.items()):
        count = rules[f'high_confidence_per_{kind}']
        for image_id in rng.sample(members, min(count, len(members))):
            chosen[image_id] = 'high_confidence'
    supplementary = sorted(i for i, t in chosen.items() if t not in ('false_positive', 'false_negative'))
    owner_random = set(rng.sample(supplementary, min(rules['owner_random_check'], len(supplementary))))
    result = []
    for image_id, case in chosen.items():
        row = metadata[image_id]
        scores = {c: round(100 * probability(image_id, c), 4) for c in ['original', *conditions]
                  if (image_id, c) in logits}
        result.append(dict(image_id=image_id, case_type=case, label=int(row['label']),
                           category=row['category'], generator=row['generator'], split=row['split'],
                           owner_check=case in ('false_positive', 'false_negative') or image_id in owner_random,
                           scores=json.dumps(scores, ensure_ascii=False)))
    return sorted(result, key=lambda r: (PRIORITY.index(r['case_type']), r['image_id']))


def main(argv=None) -> list[dict]:
    parser = argparse.ArgumentParser(description='P06-03 review set')
    parser.add_argument('--config', default='configs/failure_analysis.yaml')
    parser.add_argument('--metadata', default='data/metadata.csv')
    args = parser.parse_args(argv)
    settings = yaml.safe_load(Path(args.config).read_text())
    calibration = json.loads(Path(settings['calibration']).read_text())
    if file_sha256(args.metadata) != calibration['metadata_sha256']:
        raise ValueError('metadata does not match the calibration artifact')
    metadata = {r['image_id']: r for r in csv.DictReader(open(args.metadata, encoding='utf-8'))}
    logits = {(r['image_id'], r['condition']): float(r['logit'])
              for r in csv.DictReader(open(Path(settings['output_dir'], 'predictions.csv')))}
    cases = {}
    for kind in ('false_positive', 'false_negative', 'low_confidence'):
        for r in csv.DictReader(open(Path(settings['errors_dir'], kind, 'manifest.csv'), encoding='utf-8')):
            cases[r['image_id']] = kind
    rows = build_review_set(metadata, logits, cases, calibration['temperature'],
                            calibration['threshold_probability'], settings['review_set'])
    output = Path(settings['review_set']['output'])
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({t: sum(r['case_type'] == t for r in rows) for t in PRIORITY}
                     | dict(total=len(rows), owner_check=sum(r['owner_check'] for r in rows))))
    return rows


if __name__ == '__main__':
    main()

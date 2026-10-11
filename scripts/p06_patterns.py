"""P06-04: 오류가 얼굴 노출·흰 원·구도·생성기·부위 중 어디에 몰리는지 정상 분류 표본과 비교한다.

대상은 P06-01 원본 logit이 있는 test·test_unseen·val 2,220장이다. 얼굴은 P06-02c YuNet 설정, 흰 원은 P06-02b 검출 결과를 쓴다.
학습 분포 확인용으로 train split의 얼굴 상태도 센다(오류 집계에는 넣지 않는다).
실행: docker compose --profile training run --rm -T train python -m scripts.p06_patterns
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from src.calibration import apply_temperature
from src.face_mask_ci import detect_face
from src.score import load_calibration

METADATA = 'data/metadata.csv'
CALIBRATION = 'experiments/p05_calibration/calibration.json'
PREDICTIONS = 'experiments/p06_failure_analysis/predictions.csv'
DISCS = 'experiments/p06_failure_analysis/face_mask/detections.csv'
FACE_CONFIG = 'configs/face_mask_ci.yaml'
IMAGE_ROOT = Path('/images')
OUTPUT = Path('experiments/p06_failure_analysis/patterns')


def face_state(label: int, disc: bool, face) -> str:
    """REAL은 흰 원(익명화)·얼굴 보임·얼굴 없음, GEN은 얼굴 보임·없음. GEN의 원 검출은 전부 오검출이었다(P06-02b)."""
    if label == 1 and disc:
        return 'disc'
    return 'visible' if face is not None else 'none'


def is_error(label: int, probability: float, threshold: float) -> bool:
    return (probability >= threshold) != (label == 1)


def is_low_confidence(label: int, probability: float, threshold: float) -> bool:
    """P06-01 정의: 오분류가 아니면서 score가 [10, 90]."""
    return not is_error(label, probability, threshold) and 10 <= 100 * probability <= 90


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    centre = (k + z * z / 2) / (n + z * z)
    half = z * math.sqrt(k * (n - k) / n + z * z / 4) / (n + z * z)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def fisher_greater(errors_a: int, n_a: int, errors_b: int, n_b: int) -> float:
    """한쪽 Fisher 정확검정: 집단 a의 오류 비율이 b보다 크다는 대립가설의 p값(초기하분포 위쪽 꼬리)."""
    total, errors = n_a + n_b, errors_a + errors_b
    denominator = math.comb(total, n_a)
    upper = min(errors, n_a)
    return sum(math.comb(errors, k) * math.comb(total - errors, n_a - k) for k in range(errors_a, upper + 1)) / denominator


def crop_keeps_face(face, size) -> bool:
    """P06-02 중앙 정사각 crop(src/failure_analysis.py와 같은 정수 기하, 반열린 구간) 뒤에도 얼굴 상자 중심이 남는가."""
    x, y, w, h = face
    width, height = size
    side = min(width, height)
    left, top = (width - side) // 2, (height - side) // 2
    return left <= x + w / 2 < left + side and top <= y + h / 2 < top + side


def rate(rows, key='error') -> dict:
    n, k = len(rows), sum(r[key] for r in rows)
    return dict(n=n, errors=k, rate=round(k / n, 4) if n else None, ci95=wilson(k, n))


def summarize(features: list[dict]) -> dict:
    by = defaultdict(list)
    for r in features:
        cls = 'real' if r['label'] else 'generated'
        by[(cls, r['face_state'])].append(r)
        by[(cls, 'all')].append(r)
        if not r['label']:
            by[('generator', r['generator'], r['face_state'])].append(r)
        by[('category', cls, r['category'])].append(r)
        by[('aspect', cls, r['aspect'])].append(r)
    face = {f'{cls}/{state}': dict(rate(by[(cls, state)]), low_confidence=sum(r['low_confidence'] for r in by[(cls, state)]))
            for cls, states in (('generated', ('all', 'visible', 'none')), ('real', ('all', 'disc', 'visible', 'none')))
            for state in states}

    def test(a, b):
        ra, rb = rate(a), rate(b)
        return dict(a=ra, b=rb, p_one_sided=float(f"{fisher_greater(ra['errors'], ra['n'], rb['errors'], rb['n']):.3g}"))
    tests = {
        'generated: none > visible': test(by[('generated', 'none')], by[('generated', 'visible')]),
        'real: none > disc': test(by[('real', 'none')], by[('real', 'disc')]),
        'real: none > visible': test(by[('real', 'none')], by[('real', 'visible')]),
    }
    generators = sorted({r['generator'] for r in features if not r['label']})
    generator = {g: {s: rate(by[('generator', g, s)]) for s in ('visible', 'none')} for g in generators}
    category = {f'{cls}/{c}': rate(by[('category', cls, c)])
                for cls in ('generated', 'real') for c in sorted({r['category'] for r in features})}
    aspect = {f'{cls}/{a}': rate(by[('aspect', cls, a)])
              for cls in ('generated', 'real') for a in sorted({r['aspect'] for r in features}) if by[('aspect', cls, a)]}
    crop = {}
    groups = dict(gen_face_kept_by_crop=lambda r: r['face_state'] == 'visible' and r['crop_keeps_face'],
                  gen_face_removed_by_crop=lambda r: r['face_state'] == 'visible' and not r['crop_keeps_face'],
                  gen_no_face_before_crop=lambda r: r['face_state'] == 'none')
    for name, member in groups.items():
        rows = [r for r in features if not r['label'] and r['center_square_error'] is not None and member(r)]
        correct = [r for r in rows if not r['error']]
        crop[name] = dict(n=len(rows), errors_original=sum(r['error'] for r in rows),
                          errors_center_square=sum(r['center_square_error'] for r in rows),
                          originally_correct=len(correct), new_errors=sum(r['center_square_error'] for r in correct))
    return dict(face_state=face, concentration_tests=tests, generator_by_face=generator, category=category,
                aspect=aspect, center_crop=crop)


def main() -> dict:
    artifact = load_calibration(CALIBRATION)
    temperature, threshold = artifact['temperature'], artifact['threshold_probability']
    face_settings = yaml.safe_load(Path(FACE_CONFIG).read_text())['face_detector']
    if hashlib.sha256(Path(face_settings['model']).read_bytes()).hexdigest() != face_settings['model_sha256']:
        raise ValueError('face detector model sha256 mismatch')
    meta = {r['image_id']: r for r in csv.DictReader(open(METADATA))}
    logits = defaultdict(dict)
    for r in csv.DictReader(open(PREDICTIONS)):
        if r['condition'] in ('original', 'center_square'):
            logits[r['condition']][r['image_id']] = float(r['logit'])
    discs = {r['image_id'] for r in csv.DictReader(open(DISCS)) if r['disc_r']}
    ids = sorted(logits['original'])
    probability = dict(zip(ids, apply_temperature([logits['original'][i] for i in ids], temperature)))
    crop_ids = sorted(logits['center_square'])
    crop_probability = dict(zip(crop_ids, apply_temperature([logits['center_square'][i] for i in crop_ids], temperature)))

    def load(row):
        with Image.open(IMAGE_ROOT / Path(row['path']).relative_to('images')) as handle:
            return np.asarray(handle.convert('RGB'))

    train_states = defaultdict(lambda: defaultdict(int))
    for image_id, row in meta.items():
        if row['split'] == 'train':
            label = int(row['label'])
            state = face_state(label, image_id in discs, detect_face(load(row), **face_settings))
            train_states['real' if label else 'generated'][state] += 1

    features = []
    for image_id in ids:
        row = meta[image_id]
        label = int(row['label'])
        rgb = load(row)
        size = (rgb.shape[1], rgb.shape[0])
        face = detect_face(rgb, **face_settings)
        p = float(probability[image_id])
        crop_p = crop_probability.get(image_id)
        features.append(dict(
            image_id=image_id, split=row['split'], label=label, generator=row['generator'], category=row['category'],
            aspect=round(size[1] / size[0], 2), score=round(100 * p, 4), error=is_error(label, p, threshold),
            low_confidence=is_low_confidence(label, p, threshold),
            disc=image_id in discs, face=face, face_state=face_state(label, image_id in discs, face),
            crop_keeps_face=None if face is None else crop_keeps_face(face, size),
            center_square_error=None if crop_p is None else is_error(label, float(crop_p), threshold)))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    columns = ['image_id', 'split', 'label', 'generator', 'category', 'aspect', 'score', 'error', 'low_confidence',
               'disc', 'face_state', 'crop_keeps_face', 'center_square_error']
    with (OUTPUT/'features.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(features)
    report = dict(population=len(features), threshold_probability=threshold, temperature=temperature,
                  splits=sorted({r['split'] for r in features}),
                  train_face_state={cls: dict(sorted(states.items())) for cls, states in sorted(train_states.items())},
                  **summarize(features))
    (OUTPUT/'patterns.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(main()['concentration_tests'], ensure_ascii=False, indent=1))

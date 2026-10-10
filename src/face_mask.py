"""P06-02b: REAL에만 있는 흰 원형 얼굴 가림에 모델이 의존하는지 진단한다."""
from __future__ import annotations

import argparse
import csv
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw
from torch.utils.data import Dataset

from src.calibrate import predict_logits
from src.calibration import apply_temperature
from src.dataset import MetadataDataset
from src.evaluate import binary_metrics, evaluation_indices, load_model
from src.failure_analysis import _condition_metrics
from src.score import load_calibration

_ANGLES = np.linspace(0, 2 * np.pi, 180, endpoint=False)


def detect_disc(rgb: np.ndarray, white_min: int, outside_max: int, min_edge_fraction: float,
                min_fill: float, radius_ratio: list[float], hough_param2: int):
    """순백으로 채워진 원 (x, y, r). 배경과 일부 붙어도 둘레의 일정 비율이 경계면 인정한다."""
    height, width = rgb.shape[:2]
    darkest = rgb.min(axis=2)
    mask = cv2.GaussianBlur(((darkest >= white_min) * 255).astype(np.uint8), (5, 5), 1.5)
    circles = cv2.HoughCircles(mask, cv2.HOUGH_GRADIENT, dp=1, minDist=width * 0.05, param1=100,
                               param2=hough_param2, minRadius=int(width * radius_ratio[0]),
                               maxRadius=int(width * radius_ratio[1]))
    if circles is None:
        return None
    yy, xx = np.ogrid[:height, :width]
    best = None
    for x, y, r in circles[0][:30]:
        inside = (xx - x) ** 2 + (yy - y) ** 2 <= (0.9 * r) ** 2
        if r < 6 or not inside.any() or (darkest[inside] >= white_min).mean() < min_fill:
            continue

        def ring(offset):
            return (np.clip((x + offset * np.cos(_ANGLES)).astype(int), 0, width - 1),
                    np.clip((y + offset * np.sin(_ANGLES)).astype(int), 0, height - 1))
        (xi, yi), (xo, yo) = ring(r - 3), ring(r + 4)
        edge = float(((darkest[yi, xi] >= white_min) & (darkest[yo, xo] < outside_max)).mean())
        if edge >= min_edge_fraction and (best is None or edge > best[3]):
            best = (float(x), float(y), float(r), edge)
    return best[:3] if best else None


@lru_cache(maxsize=1)
def _face_cascade():
    return cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


def detect_face(rgb: np.ndarray, scale_factor: float, min_neighbors: int, min_size_ratio: float):
    """가장 큰 정면 얼굴 상자 (x, y, w, h)."""
    cascade = _face_cascade()
    side = int(rgb.shape[1] * min_size_ratio)
    faces = cascade.detectMultiScale(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), scaleFactor=scale_factor,
                                     minNeighbors=min_neighbors, minSize=(side, side))
    if len(faces) == 0:
        return None
    return tuple(int(v) for v in max(faces, key=lambda f: f[2] * f[3]))


def disc_for_face(face, diameter_per_face: float) -> tuple[float, float, float]:
    x, y, w, h = face
    return x + w / 2, y + h / 2, max(w, h) * diameter_per_face / 2


def off_face_disc(disc, size) -> tuple[float, float, float] | None:
    """같은 크기의 원을 얼굴과 겹치지 않게 같은 높이에 둔다. 좌우 대칭 위치를 먼저 시도한다."""
    x, y, r = disc
    width, height = size
    for cx in (width - x, x + 3 * r, x - 3 * r):
        if abs(cx - x) >= 2 * r and r <= cx <= width - r and r <= y <= height - r:
            return cx, y, r
    return None


def paint_disc(image: Image.Image, disc, fill: int) -> Image.Image:
    x, y, r = disc
    painted = image.convert('RGB')
    ImageDraw.Draw(painted).ellipse((x - r, y - r, x + r, y + r), fill=(fill,) * 3)
    return painted


class EditedDataset(Dataset):
    """지정한 index만 원을 그린 뒤 원래 평가 전처리를 적용한다."""

    def __init__(self, base: MetadataDataset, edits: dict[int, tuple]):
        self.base, self.edits = base, edits

    def __len__(self):
        return len(self.base)

    def __getitem__(self, index):
        with Image.open(self.base.image_path(index)) as handle:
            image = handle.convert('RGB')
        if index in self.edits:
            image = paint_disc(image, *self.edits[index])
        return self.base.transform(image), float(self.base.rows[index].label)


def _edit_for(spec, detection, size, diameter_per_face):
    if spec['position'] == 'detected_disc':
        if detection['disc'] is None:
            return None
        x, y, r = detection['disc']
        return (x, y, r + 3), spec['fill']  # JPEG 경계 번짐까지 덮는다
    if detection['face'] is None:
        return None
    disc = disc_for_face(detection['face'], diameter_per_face)
    if spec['position'] == 'off_face':
        disc = off_face_disc(disc, size)
    return (disc, spec['fill']) if disc else None


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='P06-02b face mask dependence')
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    settings = yaml.safe_load(Path(args.config).read_text())
    artifact = load_calibration(settings['calibration'])
    temperature, threshold = artifact['temperature'], artifact['threshold_probability']
    model, config = load_model(artifact['checkpoint'], settings['device'])
    mc = config['model']
    base = MetadataDataset(config['data']['metadata_csv'], mc['image_size'], False, False,
                           image_root=config['data'].get('image_root'), normalization=mc.get('normalization'))
    rows = base.rows
    standard, unseen = evaluation_indices(rows)
    targets = sorted(set(standard) | set(unseen))

    detections, sizes = {}, {}
    for i in range(len(rows)):
        with Image.open(base.image_path(i)) as handle:
            rgb = np.asarray(handle.convert('RGB'))
        sizes[i] = (rgb.shape[1], rgb.shape[0])
        detections[i] = dict(disc=detect_disc(rgb, **settings['disc_detector']),
                             face=detect_face(rgb, **settings['face_detector']) if rows[i].label == 0 else None)
    output = Path(settings['output_dir'])
    output.mkdir(parents=True, exist_ok=True)
    with (output/'detections.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'disc_x', 'disc_y', 'disc_r', 'face_x', 'face_y', 'face_w', 'face_h'])
        for i, found in detections.items():
            writer.writerow([rows[i].image_id, *(found['disc'] or ('',) * 3), *(found['face'] or ('',) * 4)])

    def predict(data, indices):
        return dict(zip(indices, predict_logits(model, data, indices, settings['device'], config['training'])[0]))

    logits = {'original': predict(base, targets)}
    edited = {}
    for name, spec in settings['conditions'].items():
        edits = {}
        for i in targets:
            if rows[i].label in spec['labels'] and (
                    edit := _edit_for(spec, detections[i], sizes[i], settings['disc_diameter_per_face'])):
                edits[i] = edit
        edited[name] = sorted(edits)
        logits[name] = predict(EditedDataset(base, edits), edited[name]) if edits else {}
    with (output/'predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'condition', 'logit'])
        for name, values in logits.items():
            writer.writerows((rows[i].image_id, name, float(v)) for i, v in sorted(values.items()))

    def probability(values, indices):
        return apply_temperature([values[i] for i in indices], temperature)

    has_disc = {i: detections[i]['disc'] is not None for i in range(len(rows))}
    prevalence = {}
    for i, row in enumerate(rows):
        key = f"{'real' if row.label else 'generated'}/{row.split}"
        counts = prevalence.setdefault(key, dict(count=0, disc=0))
        counts['count'] += 1
        counts['disc'] += has_disc[i]
    sets = dict(standard=standard, unseen=unseen)
    shortcut = {name: binary_metrics([rows[i].label for i in indices], [float(has_disc[i]) for i in indices])
                for name, indices in sets.items()}
    by_disc = {}
    for name, indices in sets.items():
        generated = [i for i in indices if rows[i].label == 0]
        for flag in (True, False):
            real = [i for i in indices if rows[i].label == 1 and has_disc[i] == flag]
            scores = probability(logits['original'], real)
            subset = real + generated
            by_disc[f'{name}/real_disc_{str(flag).lower()}'] = dict(
                real_count=len(real), real_mean_score=float(100 * scores.mean()) if real else None,
                false_negatives=int((scores < threshold).sum()),
                auc_vs_generated=binary_metrics([rows[i].label for i in subset],
                                                probability(logits['original'], subset))['roc_auc']
                if real else None)

    conditions = {}
    for name, spec in settings['conditions'].items():
        indices = edited[name]
        before, after = probability(logits['original'], indices), probability(logits[name], indices)
        crossed = (after >= threshold) != (before >= threshold)
        combined = logits['original'] | logits[name]
        conditions[name] = dict(
            spec=spec, edited_count=len(indices),
            edited_mean_score=dict(before=float(100 * before.mean()), after=float(100 * after.mean()))
            if indices else None,
            edited_mean_shift=float(100 * (after - before).mean()) if indices else None,
            edited_decision_flips=int(crossed.sum()),
            sets={set_name: _condition_metrics([rows[i] for i in s], [rows[i].label for i in s],
                                               probability(combined, s), probability(logits['original'], s),
                                               threshold) for set_name, s in sets.items()})

    main_condition = conditions['gen_white_face']
    controls = [conditions[name]['edited_mean_shift'] for name in ('gen_gray_face', 'gen_white_offface')]
    rule = settings['dependence_rule']
    dependence = (main_condition['edited_count'] > 0 and None not in controls
                  and all(main_condition['edited_mean_shift'] > c for c in controls)
                  and main_condition['edited_decision_flips'] / main_condition['edited_count']
                  >= rule['min_gen_flip_fraction'])
    report = dict(calibration=settings['calibration'], checkpoint_sha256=artifact['checkpoint_sha256'],
                  temperature=temperature, threshold_probability=threshold,
                  disc_prevalence=prevalence, shortcut_rule=shortcut, model_by_real_disc=by_disc,
                  conditions=conditions, dependence_evidence=bool(dependence))
    (output/'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps(dict(prevalence=prevalence, dependence_evidence=report['dependence_evidence']),
                     ensure_ascii=False))
    return report


if __name__ == '__main__':
    main()

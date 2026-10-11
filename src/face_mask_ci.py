"""P06-02c: 원형 얼굴 가림 의존을 대응표본·bootstrap 구간으로 재진단한다(P06-02b 표본 확장)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image

from src.calibrate import predict_logits
from src.calibration import apply_temperature
from src.dataset import MetadataDataset
from src.evaluate import load_model
from src.face_mask import EditedDataset, disc_for_face, off_face_disc
from src.score import load_calibration

CONDITIONS = ('white_face', 'gray_face', 'white_offface')


def pick_face(faces):
    """score 최대, 동점이면 넓이·위·왼쪽 순으로 하나를 고른다. faces 행: x, y, w, h, ..., score(마지막)."""
    return max(faces, key=lambda f: (f[-1], f[2] * f[3], -f[1], -f[0])) if len(faces) else None


def detect_face(rgb: np.ndarray, model: str, score_threshold: float, nms_threshold: float, top_k: int,
                min_size_ratio: float, **_):
    """YuNet 얼굴 상자 (x, y, w, h). 긴 변이 너비 × min_size_ratio 미만인 상자는 버린다."""
    height, width = rgb.shape[:2]
    detector = cv2.FaceDetectorYN.create(model, '', (width, height), score_threshold, nms_threshold, top_k)
    _, faces = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    faces = [] if faces is None else [f for f in faces if max(f[2], f[3]) >= width * min_size_ratio]
    best = pick_face(faces)
    return None if best is None else tuple(float(v) for v in best[:4])


def condition_edits(face, size, diameter_per_face, conditions) -> dict[str, tuple] | None:
    """세 조건의 (원, fill). 얼굴 밖 원을 둘 자리가 없으면 None(대응표본에서 제외)."""
    disc = disc_for_face(face, diameter_per_face)
    off = off_face_disc(disc, size)
    if off is None:
        return None
    return {name: (off if spec['position'] == 'off_face' else disc, spec['fill']) for name, spec in conditions.items()}


def per_image(original, edited, threshold) -> dict[str, np.ndarray]:
    """표본별 score 변화(0~100 단위)·흰 원 전환과 사전 정의 차이 D1~D3."""
    before = np.asarray(original)
    shift = {name: 100 * (np.asarray(edited[name]) - before) for name in CONDITIONS}
    return dict(shift_white=shift['white_face'], shift_gray=shift['gray_face'], shift_offface=shift['white_offface'],
                d1_white_minus_gray=shift['white_face'] - shift['gray_face'],
                d2_white_minus_offface=shift['white_face'] - shift['white_offface'],
                d3_gray_minus_offface=shift['gray_face'] - shift['white_offface'],
                flip_white=((before < threshold) & (np.asarray(edited['white_face']) >= threshold)).astype(float),
                flip_gray=((before < threshold) & (np.asarray(edited['gray_face']) >= threshold)).astype(float),
                flip_offface=((before < threshold) & (np.asarray(edited['white_offface']) >= threshold)).astype(float))


def bootstrap_summary(values: dict[str, np.ndarray], resamples: int, seed: int, interval: float) -> dict:
    """모든 통계량에 같은 이미지 재추출 표본을 쓰는 평균의 백분위 구간."""
    n = len(next(iter(values.values())))
    draws = np.random.default_rng(seed).integers(0, n, (resamples, n))
    tail = 100 * (1 - interval) / 2
    summary = {}
    for name, array in values.items():
        means = np.asarray(array)[draws].mean(axis=1)
        low, high = np.percentile(means, [tail, 100 - tail])
        summary[name] = dict(mean=float(np.mean(array)), low=float(low), high=float(high))
    return dict(count=n, **summary)


def decide(summary: dict, min_flip_fraction: float) -> dict[str, str]:
    """사전 규칙: 흰 원 의존(D1·D2·흰 원 전환율)과 얼굴 가림 일반 의존(D3)."""
    d1, d2, flip, d3 = (summary[k] for k in ('d1_white_minus_gray', 'd2_white_minus_offface', 'flip_white',
                                             'd3_gray_minus_offface'))
    if d1['low'] > 0 and d2['low'] > 0 and flip['low'] >= min_flip_fraction:
        white = 'confirmed'
    elif d1['mean'] > 0 and d2['mean'] > 0 and flip['mean'] >= min_flip_fraction:
        white = 'suggestive'
    else:
        white = 'insufficient'
    occlusion = 'confirmed' if d3['low'] > 0 else 'suggestive' if d3['mean'] > 0 else 'insufficient'
    return dict(white_disc_dependence=white, face_occlusion_dependence=occlusion)


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='P06-02c face mask resampling diagnostic')
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    settings = yaml.safe_load(Path(args.config).read_text())
    face_settings = settings['face_detector']
    digest = hashlib.sha256(Path(face_settings['model']).read_bytes()).hexdigest()
    if digest != face_settings['model_sha256']:
        raise ValueError(f'face detector model sha256 mismatch: {digest}')
    artifact = load_calibration(settings['calibration'])
    temperature, threshold = artifact['temperature'], artifact['threshold_probability']
    model, config = load_model(artifact['checkpoint'], settings['device'])
    mc = config['model']
    base = MetadataDataset(config['data']['metadata_csv'], mc['image_size'], False, False,
                           image_root=config['data'].get('image_root'), normalization=mc.get('normalization'))
    rows = base.rows
    candidates = [i for i, row in enumerate(rows) if row.label == 0 and row.split in settings['splits']]

    faces, edits, excluded = {}, {}, dict(no_face=0, no_offface_room=0)
    for i in candidates:
        with Image.open(base.image_path(i)) as handle:
            rgb = np.asarray(handle.convert('RGB'))
        faces[i] = detect_face(rgb, **face_settings)
        if faces[i] is None:
            excluded['no_face'] += 1
            continue
        edit = condition_edits(faces[i], (rgb.shape[1], rgb.shape[0]), settings['disc_diameter_per_face'],
                               settings['conditions'])
        if edit is None:
            excluded['no_offface_room'] += 1
            continue
        edits[i] = edit
    targets = sorted(edits)

    output = Path(settings['output_dir'])
    output.mkdir(parents=True, exist_ok=True)
    with (output/'detections.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'face_x', 'face_y', 'face_w', 'face_h', 'in_target'])
        for i in candidates:
            writer.writerow([rows[i].image_id, *(faces[i] or ('',) * 4), int(i in edits)])

    def predict(data):
        return predict_logits(model, data, targets, settings['device'], config['training'])[0]

    logits = {'original': predict(base)}
    for name in CONDITIONS:
        logits[name] = predict(EditedDataset(base, {i: edits[i][name] for i in targets}))
    with (output/'predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'condition', 'logit'])
        for name, values in logits.items():
            writer.writerows((rows[i].image_id, name, float(v)) for i, v in zip(targets, values))

    probabilities = {name: apply_temperature(values, temperature) for name, values in logits.items()}
    values = per_image(probabilities['original'], probabilities, threshold)
    boot = settings['bootstrap']

    def summarize(mask):
        if not mask.any():
            return dict(count=0)
        return bootstrap_summary({k: v[mask] for k, v in values.items()}, boot['resamples'], boot['seed'],
                                 boot['interval'])
    splits = np.array([rows[i].split for i in targets])
    generators = np.array([rows[i].generator for i in targets])
    pooled = summarize(np.ones(len(targets), dtype=bool))
    subsets = dict(test=summarize(np.isin(splits, ['test', 'test_unseen'])), val=summarize(splits == 'val'))
    subsets.update({f'generator/{g}': summarize(generators == g) for g in sorted(set(generators))})
    report = dict(calibration=settings['calibration'], checkpoint_sha256=artifact['checkpoint_sha256'],
                  face_model_sha256=digest, temperature=temperature, threshold_probability=threshold,
                  candidates=len(candidates), excluded=excluded, targets=len(targets),
                  pooled=pooled, subsets=subsets, decision=decide(pooled, settings['decision']['min_flip_fraction']))
    (output/'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps(dict(targets=len(targets), excluded=excluded, decision=report['decision']), ensure_ascii=False))
    return report


if __name__ == '__main__':
    main()

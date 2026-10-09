"""P06: 고정 P05 artifact로 오류 사례를 저장하고 데이터 제작 조건을 통제 진단한다."""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import statistics
from functools import lru_cache, partial
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from torchvision import transforms

from src.calibrate import predict_logits
from src.calibration import apply_temperature
from src.dataset import MetadataDataset
from src.evaluate import binary_metrics, evaluation_indices, grouped_metrics, load_model
from src.score import load_calibration

CASE_TYPES = ('false_positive', 'false_negative', 'low_confidence')


def case_type(label: int, probability: float, threshold: float, low_score: float, high_score: float):
    """REAL=1. 오분류가 low_confidence보다 우선하며 score 경계는 양끝 포함."""
    predicted_real = probability >= threshold
    if label == 0 and predicted_real:
        return 'false_positive'
    if label == 1 and not predicted_real:
        return 'false_negative'
    return 'low_confidence' if low_score / 100 <= probability <= high_score / 100 else None


@lru_cache(maxsize=1)
def _reference_luma_tables() -> dict[int, tuple[int, ...]]:
    # 표본과 같은 Pillow 인코더로 만든 table과 비교해 coefficient 순서 차이를 피한다.
    tables = {}
    for quality in range(1, 101):
        buffer = io.BytesIO()
        Image.new('RGB', (8, 8)).save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        with Image.open(buffer) as image:
            tables[quality] = tuple(image.quantization[0])
    return tables


def estimate_jpeg_quality(image: Image.Image) -> int | None:
    """luminance 양자화 table이 가장 가까운 IJG quality. JPEG가 아니면 None."""
    tables = getattr(image, 'quantization', None)
    if not tables:
        return None
    luma = np.asarray(tables[0], dtype=float)
    return min(_reference_luma_tables().items(),
               key=lambda item: (np.abs(np.asarray(item[1]) - luma).sum(), -item[0]))[0]


def apply_condition(image: Image.Image, spec: dict) -> Image.Image:
    kind = spec['type']
    if kind == 'jpeg':
        buffer = io.BytesIO()
        image.convert('RGB').save(buffer, format='JPEG', quality=int(spec['quality']))
        buffer.seek(0)
        with Image.open(buffer) as encoded:
            return encoded.convert('RGB')
    if kind == 'downscale':
        scale = spec['long_side'] / max(image.size)
        size = (round(image.width * scale), round(image.height * scale))
        return image.resize(size, Image.Resampling.BICUBIC)
    if kind == 'center_square':
        side = min(image.size)
        left, top = (image.width - side) // 2, (image.height - side) // 2
        return image.crop((left, top, left + side, top + side))
    raise ValueError(f'unknown condition type: {kind}')


def _condition_metrics(rows, labels, probabilities, original, threshold):
    result = grouped_metrics(rows, labels, probabilities)
    result['calibrated_classification'] = binary_metrics(labels, probabilities, threshold)
    labels, probabilities, original = map(np.asarray, (labels, probabilities, original))
    flipped = (probabilities >= threshold) != (original >= threshold)
    for name, label in (('real', 1), ('generated', 0)):
        mask = labels == label
        result.setdefault('mean_score', {})[name] = float(100 * probabilities[mask].mean()) if mask.any() else None
        result.setdefault('mean_score_shift', {})[name] = (
            float(100 * (probabilities[mask] - original[mask]).mean()) if mask.any() else None)
        result.setdefault('decision_flips', {})[name] = int(flipped[mask].sum())
    return result


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='P06 failure analysis')
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    settings = yaml.safe_load(Path(args.config).read_text())
    artifact = load_calibration(settings['calibration'])
    temperature, threshold = artifact['temperature'], artifact['threshold_probability']
    low_score, high_score = settings['low_confidence_score']
    model, config = load_model(artifact['checkpoint'], settings['device'])
    mc = config['model']

    def dataset(spec=None):
        data = MetadataDataset(config['data']['metadata_csv'], mc['image_size'], False, False,
                               image_root=config['data'].get('image_root'),
                               normalization=mc.get('normalization'))
        if spec is not None:
            data.transform = transforms.Compose([partial(apply_condition, spec=spec), data.transform])
        return data

    base = dataset()
    rows = base.rows
    standard, unseen = evaluation_indices(rows)
    targets = sorted(set(standard) | set(unseen))
    val = [i for i, row in enumerate(rows) if row.split == 'val']
    sizes, qualities = {}, []
    for i in targets:
        with Image.open(base.image_path(i)) as image:
            sizes[i] = image.size
            if rows[i].label == 1 and (quality := estimate_jpeg_quality(image)) is not None:
                qualities.append(quality)
    real_quality = int(statistics.median(qualities)) if qualities else None

    def predict(data, indices):
        return dict(zip(indices, predict_logits(model, data, indices, settings['device'], config['training'])[0]))

    logits = {'original': predict(base, targets + val)}
    specs = {}
    for name, spec in settings['conditions'].items():
        spec = dict(spec)
        if spec.get('quality') == 'estimated_real':
            if real_quality is None:
                raise ValueError('estimated_real requires JPEG REAL test images')
            spec['quality'] = real_quality
        specs[name] = spec
        indices = [i for i in targets if 'labels' not in spec or rows[i].label in spec['labels']]
        logits[name] = predict(dataset(spec), indices)

    output = Path(settings['output_dir'])
    output.mkdir(parents=True, exist_ok=True)
    with (output/'predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'condition', 'logit'])
        for name, values in logits.items():
            writer.writerows((rows[i].image_id, name, float(v)) for i, v in sorted(values.items()))

    membership = {i: '|'.join(name for name, group in (('A', standard), ('B', unseen)) if i in group)
                  for i in targets}
    errors = Path(settings['errors_dir'])
    cases = {kind: [] for kind in CASE_TYPES}
    for i, logit in logits['original'].items():
        probability = float(apply_temperature([logit], temperature)[0])
        row = rows[i]
        kind = case_type(row.label, probability, threshold, low_score, high_score)
        if kind:
            cases[kind].append(dict(image_id=row.image_id, score=100*probability, label=row.label,
                                    category=row.category, source_domain=row.source_domain,
                                    generator=row.generator, split=row.split,
                                    evaluation=membership.get(i, 'val'), source_path=base.image_path(i)))
    for kind, items in cases.items():
        folder = errors/kind
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        with (folder/'manifest.csv').open('w', newline='') as handle:
            fields = ['image_id', 'score', 'label', 'category', 'source_domain', 'generator', 'split', 'evaluation']
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for item in sorted(items, key=lambda x: x['score']):
                writer.writerow(item)
                shutil.copyfile(item['source_path'], folder/item['image_id'])

    evaluation_sets = dict(standard=standard, unseen=unseen,
                           standard_square=[i for i in standard if sizes[i][0] == sizes[i][1]],
                           unseen_square=[i for i in unseen if sizes[i][0] == sizes[i][1]])
    report = dict(calibration=settings['calibration'], checkpoint_sha256=artifact['checkpoint_sha256'],
                  temperature=temperature, threshold_probability=threshold,
                  estimated_real_jpeg_quality=real_quality, condition_specs=specs,
                  low_confidence_score=[low_score, high_score],
                  case_counts={kind: {s: sum(s in c['evaluation'].split('|') for c in items)
                                      for s in ('A', 'B', 'val')} | dict(unique=len(items))
                               for kind, items in cases.items()},
                  conditions={})
    for name, values in logits.items():
        combined = logits['original'] | values  # labels 한정 조건은 나머지 클래스에 원본 logit 사용
        report['conditions'][name] = {}
        for set_name, indices in evaluation_sets.items():
            if not indices:
                report['conditions'][name][set_name] = None
                continue
            original = apply_temperature([logits['original'][i] for i in indices], temperature)
            probabilities = apply_temperature([combined[i] for i in indices], temperature)
            report['conditions'][name][set_name] = _condition_metrics(
                [rows[i] for i in indices], [rows[i].label for i in indices], probabilities, original, threshold)
    (output/'diagnostics.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps(report['case_counts'], ensure_ascii=False))
    return report


if __name__ == '__main__':
    main()

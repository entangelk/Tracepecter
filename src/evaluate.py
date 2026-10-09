"""§19: checkpoint에서 Standard 및 unseen generator test를 평가한다."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

from src.dataset import MetadataDataset, MetadataRow
from src.model import RealismScorer, build_encoder, set_encoder_frozen


def binary_metrics(labels, probabilities, threshold: float = 0.5) -> dict:
    """REAL=1, threshold=0.5. PR-AUC는 PR 곡선의 trapezoidal 면적이다.

    단일 클래스 집합은 ROC/PR-AUC를 null로 기록한다.
    """
    y = np.asarray(labels, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if len(y) == 0:
        raise ValueError('cannot evaluate an empty dataset')
    predicted = p >= threshold
    tp = int(((y == 1) & predicted).sum())
    fp = int(((y == 0) & predicted).sum())
    fn = int(((y == 1) & ~predicted).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    result = dict(count=len(y), accuracy=float((predicted == y).mean()),
                  precision=precision, recall=recall,
                  f1=2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                  roc_auc=None, pr_auc=None)
    positives = int(y.sum())
    negatives = len(y) - positives
    if positives and negatives:
        order = np.argsort(-p, kind='stable')
        sorted_y, sorted_p = y[order], p[order]
        ends = np.r_[np.flatnonzero(np.diff(sorted_p)), len(y) - 1]
        tps = np.cumsum(sorted_y)[ends]
        fps = ends + 1 - tps
        tpr, fpr = np.r_[0, tps / positives], np.r_[0, fps / negatives]
        def integrate(y_values, x_values):
            return np.sum(np.diff(x_values) * (y_values[1:] + y_values[:-1]) / 2)
        result['roc_auc'] = float(integrate(tpr, fpr))
        result['pr_auc'] = float(integrate(np.r_[1, tps / (tps + fps)], tpr))
    return result


def evaluation_indices(rows: list[MetadataRow]) -> tuple[list[int], list[int]]:
    standard = [i for i, row in enumerate(rows) if row.split == 'test']
    real = [i for i in standard if rows[i].label == 1]
    unseen = [i for i, row in enumerate(rows) if row.split == 'test_unseen']
    if any(rows[i].label != 0 for i in unseen):
        raise ValueError('test_unseen must contain generated images only (DB-04)')
    return standard, real + unseen


def predict(model, loader, device) -> tuple[list[int], list[float]]:
    model.eval()
    labels, probabilities = [], []
    with torch.inference_mode():
        for images, batch_labels in loader:
            probabilities.extend(model(images.to(device)).cpu().tolist())
            labels.extend(batch_labels.int().tolist())
    return labels, probabilities


def grouped_metrics(rows, labels, probabilities) -> dict:
    result = binary_metrics(labels, probabilities)
    for field, output in [('category', 'category_wise'), ('generator', 'generator_wise'),
                          ('source_domain', 'source_wise')]:
        groups = sorted({getattr(row, field) for row in rows} - {''})
        metrics = {}
        for group in groups:
            # generator별: 해당 GEN + 전체 REAL. source별: 해당 REAL + 전체 GEN.
            indices = [i for i, row in enumerate(rows)
                       if getattr(row, field) == group
                       or (field == 'generator' and row.label == 1)
                       or (field == 'source_domain' and row.label == 0)]
            metrics[group] = binary_metrics([labels[i] for i in indices],
                                           [probabilities[i] for i in indices])
        result[output] = metrics
    return result


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_model(checkpoint, device):
    """학습 checkpoint의 config가 모델 구조를 소유한다."""
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    mc = saved['config']['model']
    encoder = build_encoder(mc['encoder'], mc.get('embedding_dim', 64), mc.get('model_id'), mc.get('revision'))
    model = RealismScorer(encoder, encoder.embedding_dim)
    model.load_state_dict(saved['model_state'])
    set_encoder_frozen(model, mc['freeze_encoder'])
    return model.to(device).eval(), saved['config']


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='Tracepecter test evaluation')
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args(argv)
    model, config = load_model(args.checkpoint, args.device)
    mc = config['model']
    dataset = MetadataDataset(config['data']['metadata_csv'], mc['image_size'], False, False,
                              image_root=config['data'].get('image_root'), normalization=mc.get('normalization'))
    standard, unseen = evaluation_indices(dataset.rows)
    result = dict(shared_real_count=sum(dataset.rows[i].label == 1 for i in standard),
                  unseen_real_policy='standard_test_real_reuse', pr_auc_method='trapezoidal')
    for name, indices in [('standard', standard), ('unseen', unseen)]:
        loader = DataLoader(Subset(dataset, indices), batch_size=config['training']['batch_size'],
                            num_workers=config['training'].get('num_workers', 0),
                            pin_memory=args.device.startswith('cuda'),
                            multiprocessing_context='spawn' if config['training'].get('num_workers', 0) else None)
        labels, probabilities = predict(model, loader, args.device)
        result[name] = grouped_metrics([dataset.rows[i] for i in indices], labels, probabilities)
    output = Path(args.checkpoint).parent / 'test_metrics.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    experiment_path = output.parent / 'experiment.json'
    if experiment_path.exists():
        experiment = json.loads(experiment_path.read_text())
        experiment.update(test_sample_count=len(standard), unseen_sample_count=len(unseen),
                          test_metrics=result)
        temporary = experiment_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(experiment, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        temporary.replace(experiment_path)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return result


if __name__ == '__main__':
    main()

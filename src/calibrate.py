"""P05 entrypoint: validation fitting과 고정 Test A/B calibration 평가."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader, Subset

from src.calibration import apply_temperature, fit_temperature, choose_threshold, calibration_metrics
from src.dataset import MetadataDataset
from src.evaluate import load_model, evaluation_indices, binary_metrics, file_sha256


def predict_logits(model, dataset, indices, device, training):
    loader = DataLoader(Subset(dataset, indices), batch_size=training['batch_size'],
                        num_workers=training.get('num_workers', 0), pin_memory=device.startswith('cuda'),
                        multiprocessing_context='spawn' if training.get('num_workers', 0) else None)
    logits, labels = [], []
    model.eval()
    with torch.inference_mode():
        for images, batch_labels in loader:
            logits.extend(model.forward_logits(images.to(device)).cpu().tolist())
            labels.extend(batch_labels.int().tolist())
    return np.asarray(logits), np.asarray(labels)


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='validation 기반 score calibration')
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    settings = yaml.safe_load(Path(args.config).read_text())
    checkpoint = settings['checkpoint']
    model, config = load_model(checkpoint, settings['device'])
    mc = config['model']
    dataset = MetadataDataset(config['data']['metadata_csv'], mc['image_size'], False, False,
                              image_root=config['data'].get('image_root'), normalization=mc.get('normalization'))
    val = [i for i, row in enumerate(dataset.rows) if row.split == 'val']
    logits, labels = predict_logits(model, dataset, val, settings['device'], config['training'])
    output = Path(settings['output_dir'])
    output.mkdir(parents=True, exist_ok=True)
    with (output/'validation_predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'logit'])
        writer.writerows((dataset.rows[i].image_id, float(logit)) for i, logit in zip(val, logits))
    fit = settings['fit']
    temperature = fit_temperature(logits, labels, fit['temperature_min'], fit['temperature_max'], fit['iterations'])
    threshold = choose_threshold(labels, apply_temperature(logits, temperature))
    artifact = dict(version=1, method='temperature_scaling', checkpoint=checkpoint,
                    checkpoint_sha256=file_sha256(checkpoint),
                    metadata_sha256=file_sha256(config['data']['metadata_csv']),
                    temperature=temperature, threshold_probability=threshold, fit_split='val',
                    validation_count=len(val), config=settings, git_commit=os.environ.get('GIT_COMMIT'))
    temporary = output/'calibration.tmp'
    temporary.write_text(json.dumps(artifact, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    temporary.replace(output/'calibration.json')
    bins = settings['metrics']['ece_bins']
    def metrics(logits, labels):
        return dict(raw=calibration_metrics(logits, labels, 1, bins),
                    calibrated=calibration_metrics(logits, labels, temperature, bins),
                    raw_classification=binary_metrics(labels, apply_temperature(logits, 1)),
                    calibrated_classification=binary_metrics(labels, apply_temperature(logits, temperature), threshold))
    report = dict(validation=metrics(logits, labels), shared_real_policy='standard_test_real_reuse',
                  ece_definition='equal_width_real_class_probability', ece_bins=bins)
    standard, unseen = evaluation_indices(dataset.rows)
    for name, indices in [('standard', standard), ('unseen', unseen)]:
        test_logits, test_labels = predict_logits(model, dataset, indices, settings['device'], config['training'])
        report[name] = metrics(test_logits, test_labels)
    (output/'metrics.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    print(f'temperature={temperature:.6f} probability_threshold={threshold:.6f}')
    return artifact


if __name__ == '__main__':
    main()

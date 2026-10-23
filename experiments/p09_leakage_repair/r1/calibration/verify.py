"""Recompute val-only fitting and verify the fixed evaluation/artifact lineage."""
import csv
import json
from pathlib import Path

import numpy as np
import yaml

from src.anonymize import file_hash
from src.calibration import apply_temperature, fit_temperature, choose_threshold, calibration_metrics
from src.dataset import read_metadata
from src.evaluate import binary_metrics, evaluation_indices

ROOT = Path('experiments/p09_leakage_repair/r1/calibration')


def main():
    artifact = json.loads((ROOT/'calibration.json').read_text())
    metrics = json.loads((ROOT/'metrics.json').read_text())
    config = yaml.safe_load(Path('configs/p09_r1_calibration.yaml').read_text())
    training = json.loads((ROOT.parent/'training/result.json').read_text())
    metadata = Path('data/versions/p09_r1/metadata.csv')
    assert artifact['config'] == config and artifact['fit_split'] == 'val'
    assert artifact['metadata_sha256'] == file_hash(metadata)
    assert artifact['checkpoint_sha256'] == training['artifact_sha256'][artifact['checkpoint']] == file_hash(artifact['checkpoint'])
    rows = read_metadata(metadata)
    by_id = {r.image_id: r for r in rows}
    assert len(by_id) == len(rows) == 6000
    with (ROOT/'validation_predictions.csv').open() as handle:
        predictions = list(csv.DictReader(handle))
    ids = [r['image_id'] for r in predictions]
    assert len(ids) == len(set(ids)) == artifact['validation_count'] == 820
    assert set(ids) == {r.image_id for r in rows if r.split == 'val'}
    logits = np.array([float(r['logit']) for r in predictions])
    labels = np.array([by_id[i].label for i in ids])
    fit = config['fit']
    temperature = fit_temperature(logits, labels, fit['temperature_min'], fit['temperature_max'], fit['iterations'])
    threshold = choose_threshold(labels, apply_temperature(logits, temperature))
    assert temperature == artifact['temperature'] and threshold == artifact['threshold_probability']
    expected = dict(raw=calibration_metrics(logits, labels, 1, 10),
                    calibrated=calibration_metrics(logits, labels, temperature, 10),
                    raw_classification=binary_metrics(labels, apply_temperature(logits, 1)),
                    calibrated_classification=binary_metrics(labels, apply_temperature(logits, temperature), threshold))
    assert expected == metrics['validation']
    standard, unseen = evaluation_indices(rows)
    shared = set(standard) & set(unseen)
    assert (len(standard), len(unseen), len(shared)) == (800, 1048, 448)
    assert all(rows[i].label == 1 and rows[i].split == 'test' for i in shared)
    assert all(rows[i].split in ('test', 'test_unseen') for i in set(standard)|set(unseen))
    assert metrics['standard']['calibrated_classification']['count'] == len(standard)
    assert metrics['unseen']['calibrated_classification']['count'] == len(unseen)
    protected = json.loads((ROOT.parent/'training/preserved_artifacts.json').read_text())
    for path, digest in protected.items():
        assert file_hash(path) == digest, path
    with (ROOT/'evaluation_ids.csv').open('w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['cohort', 'image_id'])
        for name, indices in [('standard', standard), ('unseen', unseen)]:
            writer.writerows((name, rows[i].image_id) for i in indices)
    inputs = ['configs/p09_r1_calibration.yaml', str(metadata), str(ROOT.parent/'training/result.json'),
              str(ROOT.parent/'training/preserved_artifacts.json'), 'src/calibrate.py', 'src/calibration.py',
              'src/evaluate.py', 'src/dataset.py', 'src/anonymize.py', str(Path(__file__)), artifact['checkpoint']]
    outputs = [ROOT/name for name in ('calibration.json', 'metrics.json', 'validation_predictions.csv', 'evaluation_ids.csv', 'execution.json', 'calibration.log')]
    result = dict(val_only_recomputed=True, validation_count=len(ids), standard_count=len(standard), unseen_count=len(unseen),
                  shared_test_real=len(shared), preserved_artifacts=len(protected),
                  test_metrics_recomputed=False, test_metrics_evidence='src.calibrate execution; test logits not persisted',
                  inputs_sha256={p:file_hash(p) for p in inputs}, outputs_sha256={str(p):file_hash(p) for p in outputs})
    (ROOT/'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print('val fitting/metrics reproduced; fixed cohort IDs and 11 preserved artifacts verified')


if __name__ == '__main__':
    main()

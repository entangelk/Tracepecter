"""Verify completed P09 training artifacts and preserved inputs on CPU."""
import csv
import json
from pathlib import Path

import torch

from src.anonymize import file_hash, training_config
from src.dataset import MetadataDataset
from src.train import load_config

ROOT = Path('experiments/p09_leakage_repair/r1/training')


def read(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main():
    config = training_config(load_config('configs/p09_r1_train.yaml'))
    directory = Path(config['output']['checkpoint_dir'])
    lock = json.loads((ROOT/'input_lock.json').read_text())
    for name, expected in lock['inputs_sha256'].items():
        assert file_hash(name) == expected, name
    preserved = json.loads((ROOT/'preserved_artifacts.json').read_text())
    for name, expected in preserved.items():
        assert file_hash(name) == expected, name
    best = torch.load(directory/'best.pt', map_location='cpu', weights_only=True)
    last = torch.load(directory/'last.pt', map_location='cpu', weights_only=True)
    experiment = json.loads((directory/'experiment.json').read_text())
    assert best['config'] == last['config'] == experiment['config'] == config
    assert last['epochs_done'] == config['training']['epochs'] == 10
    history = last['history']
    assert [r['epoch'] for r in history] == list(range(1, 11))
    assert experiment['history'] == history
    selected = min(history, key=lambda r: r['val_loss'])
    assert best['epochs_done'] == selected['epoch']
    assert best['val_loss'] == last['best_loss'] == selected['val_loss']
    assert best['validation_metrics'] == selected['validation_metrics']
    assert 'optimizer_state' in last and 'torch_rng' in last and 'random_rng' in last and last['cuda_rng']
    assert experiment['dataset_version'] == file_hash(config['data']['metadata_csv'])
    manifest = read(ROOT/'sample_ids.csv')
    for split, key in [('train', 'train_sample_count'), ('val', 'validation_sample_count')]:
        dataset = MetadataDataset(config['data']['metadata_csv'], config['model']['image_size'], False, False,
                                  split=split, image_root=config['data']['image_root'])
        expected = [r for r in manifest if r['split'] == split]
        assert [r.image_id for r in dataset.rows] == [r['image_id'] for r in expected]
        assert [r.path for r in dataset.rows] == [r['path'] for r in expected]
        assert [r.label for r in dataset.rows] == [int(r['label']) for r in expected]
        assert experiment[key] == len(dataset) == len(expected)
    for saved in (best, last):
        assert all(torch.isfinite(t).all().item() for t in saved['model_state'].values())
    prior = torch.load('checkpoints/anonymized/best.pt', map_location='cpu', weights_only=True)
    encoder = [k for k in best['model_state'] if k.startswith('encoder.')]
    head = [k for k in best['model_state'] if k.startswith('head.')]
    assert encoder and head
    assert all(torch.equal(best['model_state'][k], prior['model_state'][k]) for k in encoder)
    assert all(torch.equal(last['model_state'][k], prior['model_state'][k]) for k in encoder)
    assert any(not torch.equal(best['model_state'][k], prior['model_state'][k]) for k in head)
    result = dict(training_commit=experiment['git_commit'], metadata_sha256=experiment['dataset_version'],
                  config_sha256=file_hash('configs/p09_r1_train.yaml'),
                  anonymization_sha256=config['anonymization']['sha256'], epochs_done=10,
                  best_epoch=best['epochs_done'], best_val_loss=best['val_loss'],
                  best_validation_metrics=best['validation_metrics'], history=history,
                  train_images=experiment['train_sample_count'], validation_images=experiment['validation_sample_count'],
                  sample_manifest_sha256=file_hash(ROOT/'sample_ids.csv'),
                  encoder_equal_to_preserved_p08=True, head_differs_from_p08=True,
                  all_model_tensors_finite=True, preserved_artifacts_verified=len(preserved),
                  artifact_sha256={str(directory/name):file_hash(directory/name)
                                   for name in ('best.pt', 'last.pt', 'experiment.json')})
    output = ROOT/'result.json'
    encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n'
    if output.exists() and output.read_text() != encoded:
        raise ValueError('training result differs; never overwrite')
    output.write_text(encoded)
    print(json.dumps({k:v for k,v in result.items() if k != 'history'}, ensure_ascii=False))


if __name__ == '__main__':
    main()

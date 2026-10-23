"""P09 diagnostic: evaluate a new cohort while retaining each artifact's fit lineage."""
import csv
import json
from pathlib import Path

import pytest
import torch
import yaml

from scripts import p08_diagnostic as shared
from scripts import p09_diagnostic as runner
from scripts.p08_preregister import prepare
from src.anonymize import bind_spec, file_hash
from test_p08_diagnostic_runner import fixture


@pytest.fixture
def changed_cohort(fixture, monkeypatch):
    path, output, calls, settings = fixture
    baseline = Path(settings['inputs']['baseline_calibration'])
    artifact = json.loads(baseline.read_text())
    checkpoint = Path(artifact['checkpoint'])
    saved = torch.load(checkpoint, weights_only=True)
    current = Path(settings['inputs']['metadata'])
    rows = shared.read_csv(current)
    old = path.parent/'old_metadata.csv'
    for row in rows:
        if row['image_id'] == 'train_0.png':
            row['split'] = 'test'
        elif row['image_id'] == 'test_0.png':
            row['split'] = 'train'
    with old.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    saved['config']['data']['metadata_csv'] = str(old)
    torch.save(saved, checkpoint)
    artifact.update(checkpoint_sha256=file_hash(checkpoint), metadata_sha256=file_hash(old))
    baseline.write_text(json.dumps(artifact))
    (output/'preregistration.json').unlink()
    prepare(path)
    candidate = json.loads(Path(settings['candidate_calibration']).read_text())
    training = output.parent/'training'
    training.mkdir()
    (training/'result.json').write_text(json.dumps(dict(artifact_sha256={candidate['checkpoint']: candidate['checkpoint_sha256']})))
    original_load = shared.load_model
    def load(checkpoint, device):
        model, _ = original_load(checkpoint, device)
        return model, torch.load(checkpoint, weights_only=True)['config']
    monkeypatch.setattr(shared, 'load_model', load)
    return path, output, calls, settings, old


def test_cross_split_evaluation_keeps_original_bindings(changed_cohort):
    """Under: baseline fit lineage rewritten; over: valid old baseline rejected for new cohort."""
    path, output, calls, settings, old = changed_cohort
    with pytest.raises(ValueError, match='calibration metadata hash mismatch'):
        shared.preflight(path)
    before = {p: Path(p).read_bytes() for p in (settings['inputs']['baseline_calibration'], settings['candidate_calibration'], str(old))}
    state = runner.preflight(path)
    assert state['configs']['baseline']['data']['metadata_csv'] == str(old)
    assert state['configs']['candidate']['data']['metadata_csv'] == settings['inputs']['metadata']
    assert 'test_0.png' in state['eval_ids'] and 'train_0.png' not in state['eval_ids']
    result = runner.run(path, 'cpu')
    assert result['evaluation']['baseline']['anonymized']['cohorts']['standard']['count'] == 2
    assert result['evaluation']['baseline']['original']['temperature'] == 2.
    assert result['evaluation']['candidate']['original']['temperature'] == 3.
    assert result['evaluation']['candidate']['original']['threshold_probability'] == .53
    assert not result['adoption']['adopt']
    assert before == {p: Path(p).read_bytes() for p in before}
    count = len(calls)
    assert runner.run(path, 'cpu') == result
    assert len(calls) == count


@pytest.mark.parametrize('damage', ['baseline_metadata', 'baseline_identity', 'baseline_duplicate', 'baseline_columns', 'baseline_immutable', 'evaluation_duplicate', 'candidate_metadata', 'candidate_checkpoint', 'candidate_binding'])
def test_artifact_loader_rejects_mixed_lineage(changed_cohort, damage):
    """Under: mixed artifact/data accepted; over: unchanged cross-split pair allowed above."""
    path, output, _, settings, old = changed_cohort
    registration = json.loads((output/'preregistration.json').read_text())
    spec = yaml.safe_load(Path(settings['inputs']['anonymization']).read_text())
    if damage == 'baseline_metadata':
        old.write_text(old.read_text()+'\n')
    elif damage.startswith('baseline_'):
        rows = shared.read_csv(old)
        fields = list(rows[0])
        if damage == 'baseline_identity':
            rows[0]['image_id'] = 'foreign.png'
        elif damage == 'baseline_duplicate':
            rows.append(rows[0].copy())
        elif damage == 'baseline_columns':
            fields.remove('category')
            for row in rows:
                del row['category']
        else:
            rows[0]['category'] = 'changed'
        with old.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fields)
            writer.writeheader(); writer.writerows(rows)
        p = Path(settings['inputs']['baseline_calibration'])
        artifact = json.loads(p.read_text()); artifact['metadata_sha256'] = file_hash(old)
        p.write_text(json.dumps(artifact))
    elif damage == 'evaluation_duplicate':
        current = Path(settings['inputs']['metadata'])
        current.write_text(current.read_text()+current.read_text().splitlines()[1]+'\n')
    else:
        p = Path(settings['candidate_calibration'])
        artifact = json.loads(p.read_text())
        if damage == 'candidate_metadata':
            checkpoint = Path(artifact['checkpoint'])
            saved = torch.load(checkpoint, weights_only=True)
            saved['config']['data']['metadata_csv'] = str(old)
            torch.save(saved, checkpoint)
            artifact['metadata_sha256'] = file_hash(old)
            artifact['checkpoint_sha256'] = file_hash(checkpoint)
        elif damage == 'candidate_checkpoint':
            result = output.parent/'training/result.json'
            result.write_text(json.dumps(dict(artifact_sha256={artifact['checkpoint']: 'wrong'})))
        else:
            checkpoint = Path(artifact['checkpoint'])
            saved = torch.load(checkpoint, weights_only=True)
            other_spec = dict(spec, edge_sigma=spec['edge_sigma']+1)
            saved['config']['anonymization'] = bind_spec(other_spec)
            torch.save(saved, checkpoint)
            artifact['checkpoint_sha256'] = file_hash(checkpoint)
            result = output.parent/'training/result.json'
            result.write_text(json.dumps(dict(artifact_sha256={artifact['checkpoint']: artifact['checkpoint_sha256']})))
        p.write_text(json.dumps(artifact))
    with pytest.raises(ValueError):
        runner.load_artifacts(settings, registration, spec)

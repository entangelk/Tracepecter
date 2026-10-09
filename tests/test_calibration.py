"""P05: calibration 무시·순서 반전·과도한 거부와 데이터 누출을 막는다."""
import numpy as np
import pytest
import torch

from src.calibration import apply_temperature, fit_temperature, choose_threshold, calibration_metrics
from src.model import RealismScorer, StubEncoder


def test_logits_preserve_probability_and_saturation():
    model = RealismScorer(StubEncoder(8), 8).eval()
    images = torch.randn(2, 3, 16, 16)
    with torch.no_grad():
        expected = model.head(model.encoder(images)).squeeze(-1)
        assert torch.equal(model(images), expected)
        assert torch.equal(model.forward_logits(images).sigmoid(), expected)
        model.head[-2].weight.zero_()
        model.head[-2].bias.fill_(80)
        assert torch.equal(model.forward_logits(images), torch.full((2,), 80.0))
        assert torch.equal(model(images), torch.ones(2))


def test_temperature_improves_overconfidence_and_preserves_order():
    logits = np.array([5.] * 10 + [-5.] * 10)
    labels = np.array([1] * 9 + [0] + [0] * 9 + [1])
    temperature = fit_temperature(logits, labels, 0.05, 20, 100)
    assert temperature == pytest.approx(5 / np.log(9), rel=1e-5)
    before = calibration_metrics(logits, labels, 1, 10)
    after = calibration_metrics(logits, labels, temperature, 10)
    assert after['nll'] < before['nll']
    assert after['brier'] < before['brier']
    scores = apply_temperature([-80, -2, 0, 2, 80], temperature) * 100
    assert np.all(np.diff(scores) > 0)
    assert np.all((scores >= 0) & (scores <= 100))
    assert scores[2] == 50
    with pytest.raises(ValueError):
        apply_temperature([0], 0)
    with pytest.raises(ValueError):
        fit_temperature([1, 2], [1, 1], 0.05, 20, 100)


def test_threshold_prefers_balanced_accuracy_and_handles_ties():
    # 고정 0.5로 REAL을 전부 거부하는 변경과 정상 낮은 threshold의 거부를 검출.
    assert choose_threshold([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4]) == 0.3
    assert choose_threshold([0, 1], [0.5, 0.5]) == 0.5
    assert calibration_metrics([0, 0], [0, 1], 1, 10)['ece'] == 0


def test_calibration_cli_uses_only_validation_and_scores_deterministically(tmp_path):
    """test 변경은 fitting에 영향 없고, 정상 scoring·artifact hash 거부를 확인한다."""
    import csv
    import json
    import yaml
    from test_baseline import make_data
    from src.train import run_training
    from src.calibrate import main as calibrate
    from src.score import main as score, load_calibration

    metadata = make_data(tmp_path)
    config = dict(model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=1, device='cpu'),
                  augmentation=dict(horizontal_flip=False, jpeg_aug=False),
                  data=dict(metadata_csv=str(metadata)))
    checkpoint = run_training(config, str(metadata), 1, tmp_path/'checkpoints')
    settings = dict(checkpoint=str(checkpoint), device='cpu', output_dir=str(tmp_path/'calibration'),
                    fit=dict(temperature_min=0.05, temperature_max=20.0, iterations=100),
                    metrics=dict(ece_bins=10))
    settings_path = tmp_path/'calibration.yaml'
    settings_path.write_text(yaml.safe_dump(settings))
    artifact = calibrate(['--config', str(settings_path)])
    prediction_path = tmp_path/'calibration/validation_predictions.csv'
    with prediction_path.open() as handle:
        predictions = list(csv.DictReader(handle))
    assert {r['image_id'] for r in predictions} == {'val_0.png', 'val_1.png'}
    assert set(predictions[0]) == {'image_id', 'logit'}
    assert artifact['validation_count'] == 2
    metrics = json.loads((tmp_path/'calibration/metrics.json').read_text())
    assert metrics['validation']['calibrated']['nll'] <= metrics['validation']['raw']['nll']
    assert metrics['standard']['calibrated_classification']['count'] == 2
    assert metrics['unseen']['calibrated_classification']['count'] == 2
    # Test 이미지를 바꾸어도 temperature/threshold는 같아야 한다.
    from PIL import Image
    Image.new('RGB', (32, 40), 'white').save(tmp_path/'test_0.png')
    Image.new('RGB', (32, 40), 'black').save(tmp_path/'test_1.png')
    again = calibrate(['--config', str(settings_path)])
    assert again['temperature'] == artifact['temperature']
    assert again['threshold_probability'] == artifact['threshold_probability']
    artifact_path = tmp_path/'calibration/calibration.json'
    arguments = ['--image', str(tmp_path/'val_1.png'), '--calibration', str(artifact_path)]
    first, second = score(arguments), score(arguments)
    assert first == second
    assert set(first) == {'realism_score', 'classification'}
    assert 0 <= first['realism_score'] <= 100
    assert first['classification'] in {'photographic_like', 'synthetic_like'}
    damaged = dict(artifact, temperature=-1)
    artifact_path.write_text(json.dumps(damaged))
    with pytest.raises(ValueError, match='temperature'):
        load_calibration(artifact_path)
    artifact_path.write_text(json.dumps(artifact))
    with checkpoint.open('ab') as handle:
        handle.write(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        load_calibration(artifact_path)


def test_single_class_metrics_allowed_but_fitting_requires_both():
    """단일 클래스 지표의 과도한 거부는 막고 fitting의 양 클래스 조건은 유지한다."""
    metrics = calibration_metrics([-2, -1], [0, 0], 1, 10)
    assert metrics['nll'] > 0 and metrics['brier'] > 0 and metrics['ece'] > 0
    with pytest.raises(ValueError):
        fit_temperature([-2, -1], [0, 0], 0.05, 20, 100)
    with pytest.raises(ValueError):
        choose_threshold([0, 0], [0.1, 0.2])

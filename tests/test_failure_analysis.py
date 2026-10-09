"""P06: 오류 분류 경계·통제 변환·오류 저장이 P05 artifact와 일관되는지 고정한다."""
import csv
import io
import json

import numpy as np
import yaml
from PIL import Image

from src.failure_analysis import apply_condition, case_type, estimate_jpeg_quality


def test_case_type_boundaries():
    """threshold 이상은 photographic이므로 경계 REAL을 오류로 세는 과잉 판정도,
    threshold 미만 REAL을 놓치는 과소 판정도 막는다. 오류는 low_confidence보다 우선한다."""
    def kind(label, probability):
        return case_type(label, probability, 0.7, 10, 90)
    assert case_type(1, 0.7, 0.7, 10, 60) is None
    assert kind(1, 0.7) == 'low_confidence'
    assert kind(1, 0.69) == 'false_negative'
    assert kind(0, 0.7) == 'false_positive'
    assert kind(0, 0.5) == 'low_confidence'
    assert kind(1, 0.9) == 'low_confidence'
    assert kind(1, 0.95) is None
    assert kind(0, 0.05) is None
    assert kind(0, 0.1) == 'low_confidence'


def _noise(size=(64, 48)):
    rng = np.random.default_rng(0)
    return Image.fromarray(rng.integers(0, 256, (*size[::-1], 3), dtype=np.uint8))


def test_jpeg_quality_estimate_matches_encoder_quality():
    for quality in (60, 75, 90):
        buffer = io.BytesIO()
        _noise().save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        with Image.open(buffer) as image:
            assert estimate_jpeg_quality(image) == quality
    buffer = io.BytesIO()
    _noise().save(buffer, format='PNG')
    buffer.seek(0)
    with Image.open(buffer) as image:
        assert estimate_jpeg_quality(image) is None


def test_conditions_geometry_and_determinism():
    wide = _noise((80, 40))
    assert apply_condition(wide, dict(type='center_square')).size == (40, 40)
    assert apply_condition(_noise((1000, 500)), dict(type='downscale', long_side=512)).size == (512, 256)
    jpeg = dict(type='jpeg', quality=75)
    first, second = apply_condition(wide, jpeg), apply_condition(wide, jpeg)
    assert first.mode == 'RGB' and first.size == wide.size
    assert first.tobytes() == second.tobytes() != wide.tobytes()


def test_failure_analysis_cli_saves_errors_and_condition_predictions(tmp_path):
    from test_baseline import make_data
    from src.calibrate import main as calibrate
    from src.calibration import apply_temperature
    from src.failure_analysis import main as analyze
    from src.train import run_training

    metadata = make_data(tmp_path)
    for name in ('train_1.png', 'val_1.png', 'test_1.png'):  # REAL은 실제 데이터처럼 JPEG 내용
        with Image.open(tmp_path/name) as image:
            image.convert('RGB').save(tmp_path/name, format='JPEG', quality=80)
    config = dict(model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=1, device='cpu'),
                  augmentation=dict(horizontal_flip=False, jpeg_aug=False),
                  data=dict(metadata_csv=str(metadata)))
    checkpoint = run_training(config, str(metadata), 1, tmp_path/'checkpoints')
    calibration = dict(checkpoint=str(checkpoint), device='cpu', output_dir=str(tmp_path/'calibration'),
                       fit=dict(temperature_min=0.05, temperature_max=20.0, iterations=100),
                       metrics=dict(ece_bins=10))
    (tmp_path/'calibration.yaml').write_text(yaml.safe_dump(calibration))
    artifact = calibrate(['--config', str(tmp_path/'calibration.yaml')])
    # 모든 표본이 오류/경계로 저장되도록 low_confidence 구간을 전체로 둔다.
    settings = dict(calibration=str(tmp_path/'calibration/calibration.json'), device='cpu',
                    output_dir=str(tmp_path/'p06'), errors_dir=str(tmp_path/'errors'),
                    low_confidence_score=[0, 100],
                    conditions=dict(jpeg_q75=dict(type='jpeg', quality=75),
                                    gen_jpeg=dict(type='jpeg', quality='estimated_real', labels=[0])))
    (tmp_path/'p06.yaml').write_text(yaml.safe_dump(settings))
    stale = tmp_path/'errors/false_positive/stale.png'
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b'old')
    report = analyze(['--config', str(tmp_path/'p06.yaml')])

    with (tmp_path/'p06/predictions.csv').open() as handle:
        predictions = list(csv.DictReader(handle))
    assert set(predictions[0]) == {'image_id', 'condition', 'logit'}
    by_condition = {}
    for row in predictions:
        by_condition.setdefault(row['condition'], set()).add(row['image_id'])
    targets = {'test_0.png', 'test_1.png', 'test_unseen_0.png'}
    assert by_condition['original'] == targets | {'val_0.png', 'val_1.png'}
    assert by_condition['jpeg_q75'] == targets
    assert by_condition['gen_jpeg'] == {'test_0.png', 'test_unseen_0.png'}

    assert not stale.exists()
    saved = {}
    for kind in ('false_positive', 'false_negative', 'low_confidence'):
        with (tmp_path/f'errors/{kind}/manifest.csv').open() as handle:
            for row in csv.DictReader(handle):
                assert (tmp_path/f'errors/{kind}'/row['image_id']).exists()  # 원본 파일명(확장자 포함)
                saved[row['image_id']] = (kind, row)
    assert set(saved) == targets | {'val_0.png', 'val_1.png'}
    labels = {r['image_id']: int(r['label']) for r in csv.DictReader(metadata.open())}
    for row in predictions:
        if row['condition'] != 'original':
            continue
        probability = float(apply_temperature([float(row['logit'])], artifact['temperature'])[0])
        expected = case_type(labels[row['image_id']], probability, artifact['threshold_probability'], 0, 100)
        kind, manifest = saved[row['image_id']]
        assert kind == expected
        assert float(manifest['score']) == 100 * probability
        assert {'label', 'category', 'source_domain', 'generator', 'split', 'evaluation'} <= set(manifest)
    assert saved['test_1.png'][1]['evaluation'] == 'A|B'

    metrics = json.loads((tmp_path/'p06/diagnostics.json').read_text())
    assert metrics == report
    assert metrics['estimated_real_jpeg_quality'] == 80
    assert metrics['conditions']['original']['standard']['count'] == 2
    assert metrics['conditions']['original']['unseen']['count'] == 2
    assert metrics['conditions']['original']['standard']['decision_flips'] == dict(real=0, generated=0)

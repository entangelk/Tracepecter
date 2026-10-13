"""P08-02: 누락/완화된 가림·무결성 검사를 잡고 정상 무얼굴·legacy 입력은 허용한다."""
import copy
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
import yaml
from PIL import Image

from src.anonymize import (Anonymizer, bind_spec, checkpoint_anonymizer,
                           spec_hash, training_config, write_face_cache)
from src.dataset import MetadataDataset


@pytest.fixture
def spec(tmp_path):
    model = tmp_path / 'yunet.onnx'
    model.write_bytes(b'test detector')
    settings = yaml.safe_load(Path('configs/anonymize.yaml').read_text())
    settings['face_detector']['model'] = str(model)
    settings['face_detector']['model_sha256'] = hashlib.sha256(model.read_bytes()).hexdigest()
    return settings


def test_all_faces_filter_and_paint_deterministically(spec, monkeypatch):
    """대표 1개만 가리는 완화를 잡고 무얼굴/최소크기 경계/배경 보존을 허용한다."""
    boxes = [[10, 10, 20, 20], [45, 10, 20, 20], [60, 60, 4, 3], [70, 70, 3.99, 3]]
    class Detector:
        def detect(self, bgr):
            assert tuple(bgr[0, 0]) == (30, 20, 10)
            return None, np.array([b + [0] * 10 + [0.95] for b in boxes])
    monkeypatch.setattr(cv2.FaceDetectorYN, 'create', lambda *args: Detector())
    worker = Anonymizer(bind_spec(spec))
    image = Image.new('RGB', (100, 100), (10, 20, 30))
    result, count = worker(image)
    assert count == 3
    pixels = np.asarray(result)
    assert all(tuple(pixels[y, x]) == (255, 255, 255) for x, y in [(20, 20), (55, 20), (62, 62)])
    assert tuple(pixels[90, 90]) == (10, 20, 30)
    assert np.array_equal(result, worker(image)[0])
    boxes.clear()
    unchanged, count = worker(image)
    assert count == 0 and np.array_equal(unchanged, image)


def test_cache_matches_live_and_rejects_missing_stale_rows(spec, tmp_path, monkeypatch):
    """캐시 무시·누락 허용을 잡고 빈 목록 행과 동일한 즉시 경로를 허용한다."""
    faces = [[10., 10., 20., 20.], [20., 10., 20., 20.]]
    monkeypatch.setattr(Anonymizer, 'detect', lambda self, image: faces)
    image_path = tmp_path / 'image.png'
    Image.new('RGB', (80, 80), (80, 90, 100)).save(image_path)
    binding = bind_spec(spec)
    live = Anonymizer(binding)
    cache = tmp_path / 'face_boxes.csv'
    write_face_cache([('a', image_path)], binding, cache)
    before = cache.read_bytes()
    write_face_cache([('a', image_path)], binding, cache)
    assert cache.read_bytes() == before and b'\r' not in before
    cached = Anonymizer(binding, cache)
    with Image.open(image_path) as image:
        assert np.array_equal(cached(image, 'a', image_path)[0], live(image)[0])
        # overlapping/pre-existing white discs use the same painting rule
        painted = live(image)[0]
        assert np.array_equal(cached(painted, 'a', image_path)[0], live(painted)[0])
        with pytest.raises(ValueError, match='missing'):
            cached(image, 'absent', image_path)
    image_path.write_bytes(image_path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='image.*hash'):
        cached(Image.new('RGB', (80, 80)), 'a', image_path)
    with pytest.raises(ValueError, match='image.*hash'):
        write_face_cache([('a', image_path)], binding, cache)
    image_path.write_bytes(image_path.read_bytes()[:-7])
    for field in ['detector_sha256', 'parameters_sha256']:
        records = list(csv.DictReader(cache.open()))
        records[0][field] = 'bad'
        with cache.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=records[0], lineterminator='\n')
            writer.writeheader()
            writer.writerows(records)
        with pytest.raises(ValueError, match='hash'):
            Anonymizer(binding, cache)
        cache.write_bytes(before)
    faces.clear()
    cache.unlink()
    write_face_cache([('a', image_path)], binding, cache)
    with Image.open(image_path) as image:
        result, count = Anonymizer(binding, cache)(image, 'a', image_path)
        assert count == 0 and np.array_equal(result, image)


@pytest.mark.parametrize('config', [{}, {'anonymization': None}])
def test_legacy_and_null_allowed_for_evaluation_but_not_score(config):
    """원본 평가를 과도하게 거부하지 않고 익명화 없는 추론은 반드시 거부한다."""
    assert checkpoint_anonymizer(config) is None
    with pytest.raises(ValueError, match='requires anonymization'):
        checkpoint_anonymizer(config, required=True)


def test_binding_training_and_fail_closed(spec, tmp_path):
    """규격 변조·누락을 거부하고 올바른 snapshot과 명시적 null 학습을 허용한다."""
    path = tmp_path / 'spec.yaml'
    path.write_text(yaml.safe_dump(spec))
    config = training_config({'anonymization': str(path)})
    assert config['anonymization'] == bind_spec(spec)
    assert config['anonymization']['sha256'] == spec_hash(spec)
    assert training_config(config) == config
    assert training_config({'anonymization': None}) == {'anonymization': None}
    with pytest.raises(ValueError, match='explicit'):
        training_config({})
    assert checkpoint_anonymizer(config) is not None
    altered = copy.deepcopy(config)
    altered['anonymization']['spec']['diameter_per_face'] = 1.6
    with pytest.raises(ValueError, match='sha256'):
        checkpoint_anonymizer(altered)
    for bad in [True, {}, {'spec': spec, 'sha256': 'bad'}]:
        with pytest.raises(ValueError):
            checkpoint_anonymizer({'anonymization': bad})
    unsupported = dict(spec, shape='triangle')
    with pytest.raises(ValueError, match='spec'):
        checkpoint_anonymizer({'anonymization': {'spec': unsupported, 'sha256': spec_hash(unsupported)}})
    model = tmp_path / 'yunet.onnx'
    model.write_bytes(b'wrong')
    with pytest.raises(ValueError, match='detector.*sha256'):
        checkpoint_anonymizer(config)
    model.unlink()
    with pytest.raises(ValueError, match='detector'):
        checkpoint_anonymizer(config)


def test_dataset_anonymizes_before_transform(spec, tmp_path, monkeypatch):
    """resize/augmentation 뒤 가림을 잡고 원본 이미지에서 모든 얼굴을 처리한다."""
    image = tmp_path / 'a.png'
    Image.new('RGB', (80, 100), 'black').save(image)
    metadata = tmp_path / 'metadata.csv'
    metadata.write_text('image_id,path,label,category,source_type\na,a.png,1,top,real\n')
    seen = []
    def detect(self, image):
        seen.append(image.size)
        return [[10, 10, 20, 20]]
    monkeypatch.setattr(Anonymizer, 'detect', detect)
    dataset = MetadataDataset(metadata, 16, False, False, anonymizer=Anonymizer(bind_spec(spec)))
    dataset.transform = lambda image: (image.size, tuple(np.asarray(image)[20, 20]))
    result, label = dataset[0]
    assert seen == [(80, 100)] and result == ((80, 100), (255, 255, 255)) and label == 1


def test_anonymized_training_evaluation_calibration_and_score(spec, tmp_path, monkeypatch):
    """각 entrypoint의 전처리 누락을 잡고 올바른 snapshot·cache·score 경로를 허용한다."""
    from test_baseline import make_data
    from src.train import run_training
    from src.evaluate import main as evaluate, load_model
    from src.calibrate import main as calibrate
    from src.score import main as score

    metadata = make_data(tmp_path)
    calls = []
    def detect(self, image):
        calls.append(image.size)
        return [[4., 4., 8., 8.], [16., 16., 8., 8.]]
    monkeypatch.setattr(Anonymizer, 'detect', detect)
    spec_path = tmp_path / 'spec.yaml'
    spec_path.write_text(yaml.safe_dump(spec))
    cache = tmp_path / 'face_boxes.csv'
    base = MetadataDataset(metadata, 16, False, False)
    write_face_cache([(r.image_id, base.image_path(i)) for i, r in enumerate(base.rows)], bind_spec(spec), cache)
    config = dict(anonymization=str(spec_path),
                  model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=1, device='cpu'),
                  augmentation=dict(horizontal_flip=False, jpeg_aug=False),
                  data=dict(metadata_csv=str(metadata), face_cache=str(cache)))
    calls.clear()
    checkpoint = run_training(config, str(metadata), 1, tmp_path / 'checkpoints')
    assert not calls  # 학습과 validation은 cache를 쓴다
    saved = torch.load(checkpoint, weights_only=True)
    assert saved['config']['anonymization'] == bind_spec(spec)
    evaluate(['--checkpoint', str(checkpoint), '--face-cache', str(cache)])
    assert not calls
    settings = dict(checkpoint=str(checkpoint), device='cpu', output_dir=str(tmp_path / 'calibration'),
                    face_cache=str(cache), fit=dict(temperature_min=0.05, temperature_max=20., iterations=100),
                    metrics=dict(ece_bins=10))
    settings_path = tmp_path / 'calibration.yaml'
    settings_path.write_text(yaml.safe_dump(settings))
    calibrate(['--config', str(settings_path)])
    assert not calls
    # 학습 원본 YAML이 없어도 하류는 checkpoint 규격으로 동작한다.
    spec_path.unlink()
    args = ['--image', str(tmp_path / 'val_1.png'), '--calibration', str(tmp_path / 'calibration/calibration.json')]
    first = score(args)
    assert first == score(args) and len(calls) == 2
    assert set(first) == {'realism_score', 'classification'} and 0 <= first['realism_score'] <= 100
    # 즉시 검출 평가도 같은 지표. 캐시 누락을 원본 입력으로 숨기지 않는다.
    cached = evaluate(['--checkpoint', str(checkpoint), '--face-cache', str(cache)])
    direct = evaluate(['--checkpoint', str(checkpoint)])
    assert cached == direct
    legacy = copy.deepcopy(saved)
    del legacy['config']['anonymization']
    legacy_path = tmp_path / 'legacy.pt'
    torch.save(legacy, legacy_path)
    _, legacy_config = load_model(legacy_path, 'cpu')
    assert 'anonymization' not in legacy_config
    assert checkpoint_anonymizer(legacy_config) is None
    saved['config']['anonymization']['sha256'] = 'bad'
    torch.save(saved, checkpoint)
    with pytest.raises(ValueError, match='sha256'):
        load_model(checkpoint, 'cpu')


def test_legacy_override_uses_explicit_spec(spec, tmp_path, monkeypatch):
    """legacy를 항상 무처리로 두는 변경을 잡고 결합된 규격의 덮어쓰기는 거부한다."""
    path = tmp_path / 'spec.yaml'
    path.write_text(yaml.safe_dump(spec))
    monkeypatch.setattr(Anonymizer, 'detect', lambda self, image: [[2., 2., 8., 8.]])
    worker = checkpoint_anonymizer({}, override=path)
    result, count = worker(Image.new('RGB', (20, 20), 'black'))
    assert count == 1 and tuple(np.asarray(result)[6, 6]) == (255, 255, 255)
    with pytest.raises(ValueError, match='override'):
        checkpoint_anonymizer({'anonymization': bind_spec(spec)}, override=path)


def test_paint_matches_measured_kernel_exactly(spec, monkeypatch):
    """경계 처리·반올림 drift를 잡고 P08-01 실측과 동일한 단일 원을 허용한다."""
    from scripts.p08_measure import paint_synthetic
    rgb = np.random.default_rng(42).integers(0, 256, (100, 80, 3), dtype=np.uint8)
    face = [5.25, 12.75, 20.5, 30.5]
    monkeypatch.setattr(Anonymizer, 'detect', lambda self, image: [face])
    expected, _ = paint_synthetic(rgb, face, spec['diameter_per_face'], False, spec['edge_sigma'])
    actual, count = Anonymizer(bind_spec(spec))(Image.fromarray(rgb))
    assert count == 1 and np.array_equal(actual, expected)


@pytest.mark.parametrize('field,value', [('shape', 'ellipse'), ('diameter_per_face', 0.9),
                                         ('edge_sigma', float('nan')), ('fill', [0, 0, 0])])
def test_invalid_spec_rejected(spec, field, value):
    """미채택 모양·범위 밖 설정을 거부한다. 정상 경계는 다른 셀이 허용한다."""
    spec[field] = value
    with pytest.raises(ValueError, match='spec'):
        bind_spec(spec)


@pytest.mark.parametrize('binding', ['missing', None])
def test_score_rejects_before_encoder_loading(binding, tmp_path, monkeypatch):
    """무익명화 score의 늦은 거부를 잡고 원본 평가 허용은 별도 셀로 보장한다."""
    from src.evaluate import file_sha256
    from src.score import main as score
    config = {} if binding == 'missing' else {'anonymization': None}
    path = tmp_path / 'legacy.pt'
    torch.save({'config': config}, path)
    artifact = tmp_path / 'calibration.json'
    artifact.write_text(json.dumps(dict(version=1, method='temperature_scaling', checkpoint=str(path),
                                        checkpoint_sha256=file_sha256(path), temperature=1., threshold_probability=0.5)))
    def forbidden(*args, **kwargs):
        pytest.fail('encoder loaded before rejecting unanonymized score')
    monkeypatch.setattr('src.evaluate.build_encoder', forbidden)
    with pytest.raises(ValueError, match='requires anonymization'):
        score(['--image', str(tmp_path / 'unused.png'), '--calibration', str(artifact)])


def test_detect_sorts_unordered_overlapping_faces(spec, monkeypatch):
    """정렬 누락을 잡고 역순 검출도 모든 겹침 얼굴을 좌표순으로 보존한다."""
    faces = [[12., 12., 18., 24.], [8., 8., 18., 24.]]
    class Detector:
        def detect(self, bgr):
            return None, np.array([box + [0] * 10 + [0.95] for box in faces])
    monkeypatch.setattr(cv2.FaceDetectorYN, 'create', lambda *args: Detector())
    worker = Anonymizer(bind_spec(spec))
    image = Image.new('RGB', (60, 60), 'black')
    expected = [faces[1], faces[0]]
    assert worker.detect(image) == expected
    faces.reverse()
    assert worker.detect(image) == expected


def test_paint_sorts_unordered_overlapping_faces(spec, monkeypatch):
    """칠하기 정렬 누락을 픽셀로 잡고 같은 얼굴 집합의 양 순서를 모두 허용한다."""
    from scripts.p08_measure import paint_synthetic
    faces = [[12., 12., 18., 24.], [8., 8., 18., 24.]]
    rgb = np.random.default_rng(42).integers(0, 256, (60, 60, 3), dtype=np.uint8)
    expected = rgb.copy()
    for face in sorted(faces):
        expected, _ = paint_synthetic(expected, face, spec['diameter_per_face'], False, spec['edge_sigma'])
    monkeypatch.setattr(Anonymizer, 'detect', lambda self, image: faces)
    worker = Anonymizer(bind_spec(spec))
    image = Image.fromarray(rgb)
    first, count = worker(image)
    assert count == 2 and np.array_equal(first, expected)
    faces.reverse()
    second, count = worker(image)
    assert count == 2 and np.array_equal(second, expected)
    assert tuple(np.asarray(second)[20, 20]) == (255, 255, 255)
    assert np.array_equal(np.asarray(second)[55, 55], rgb[55, 55])


@pytest.mark.parametrize('config', [{}, {'anonymization': None}], ids=['legacy', 'null'])
def test_evaluate_rejects_face_cache_without_anonymization(config, monkeypatch):
    """캐시만 지정한 무익명화 평가를 거부하고 캐시 없는 원본 평가는 허용한다."""
    from src.evaluate import main as evaluate
    assert checkpoint_anonymizer(config) is None
    monkeypatch.setattr('src.evaluate.load_model', lambda *args: (None, config))
    with pytest.raises(ValueError, match='face cache requires anonymization'):
        evaluate(['--checkpoint', 'unused.pt', '--face-cache', 'unused.csv'])

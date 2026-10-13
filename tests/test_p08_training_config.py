"""P08-04: 비교 학습 설정의 drift를 막고 익명화·별도 artifact 경로만 허용한다."""
from pathlib import Path
import os

import pytest

import yaml


def test_anonymized_training_matches_primary_except_preprocessing_and_output():
    baseline = yaml.safe_load(Path('configs/primary.yaml').read_text())
    candidate = yaml.safe_load(Path('configs/anonymized.yaml').read_text())
    assert candidate['anonymization'] == 'configs/anonymize.yaml'
    assert candidate['data'].pop('face_cache') == 'experiments/p08_anonymized/face_boxes.csv'
    assert candidate['output']['checkpoint_dir'] == 'checkpoints/anonymized'
    candidate['anonymization'] = baseline['anonymization']
    candidate['output'] = baseline['output']
    assert candidate == baseline


def test_smoke_uses_model_resolution_and_preserves_default_fixture(tmp_path, monkeypatch):
    """작은 원본의 YuNet smoke 실패를 막고 기존 기본 32px fixture는 허용한다."""
    from PIL import Image
    from src.dataset import read_metadata
    from src.train import build_smoke_dataset, main
    import shutil

    legacy = build_smoke_dataset(tmp_path/'legacy')
    with Image.open(legacy.parent/read_metadata(legacy)[0].path) as image:
        assert image.size == (32, 32)
    seen = []
    def training(config, train_csv, epochs, checkpoint_dir):
        for row in read_metadata(train_csv):
            with Image.open(Path(train_csv).parent/row.path) as image:
                seen.append(image.size)
                assert image.size == (config['model']['image_size'],) * 2
        return checkpoint_dir/'best.pt'
    monkeypatch.setattr('src.train.run_training', training)
    result = main(['--config','configs/anonymized.yaml','--smoke'])
    try:
        assert len(seen) == 8
    finally:
        shutil.rmtree(result.parent.parent)


@pytest.mark.skipif(os.environ.get('TRACEPECTER_REAL_YUNET_SMOKE') != '1',
                    reason='실제 YuNet 모델이 준비된 환경에서 명시적으로 실행하는 CPU smoke')
def test_real_yunet_anonymized_cpu_smoke_completes(monkeypatch):
    """실제 검출을 우회하지 않고 CPU smoke를 완료하며 모델 없는 기본 CI는 opt-in을 기다린다."""
    import shutil
    import torch
    from src.anonymize import Anonymizer
    from src.train import main

    detect = Anonymizer.detect
    observed = []
    def inspect_detection(self, image):
        observed.append(image.size)
        return detect(self, image)
    monkeypatch.setattr(Anonymizer, 'detect', inspect_detection)
    checkpoint = main(['--config','configs/anonymized.yaml','--smoke'])
    try:
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        assert saved['epochs_done'] == 1
        assert saved['validation_metrics']['count'] == 8
        assert saved['config']['training']['device'] == 'cpu'
        assert saved['config']['model']['encoder'] == 'stub'
        assert saved['config']['anonymization']['spec'] == yaml.safe_load(Path('configs/anonymize.yaml').read_text())
        assert observed == [(224,224)] * 16
    finally:
        shutil.rmtree(checkpoint.parent.parent)

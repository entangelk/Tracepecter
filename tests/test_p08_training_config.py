"""P08-04: 비교 학습 설정의 drift를 막고 익명화·별도 artifact 경로만 허용한다."""
from pathlib import Path

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

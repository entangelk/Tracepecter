"""P02: stub 대체·freeze·split·평가의 양방향 회귀 가드.

under-strict: encoder 학습/잘못된 pooling/학습 REAL의 Test B 유입을 잡는다.
over-strict: freeze 해제·정상 양 클래스 평가·단일 클래스 기록도 허용한다.
"""
import csv
import json
import random

import pytest
import torch
from PIL import Image
from transformers import SiglipVisionConfig, SiglipVisionModel

from src.dataset import MetadataDataset, build_transform
from src.model import RealismScorer, SiglipEncoder, build_encoder, set_encoder_frozen
from src.evaluate import binary_metrics, evaluation_indices
from src.train import run_training


def test_siglip_pooling_and_freeze(monkeypatch):
    vision = SiglipVisionModel(SiglipVisionConfig(
        hidden_size=16, intermediate_size=32, num_hidden_layers=1,
        num_attention_heads=2, image_size=16, patch_size=8,
    ))
    monkeypatch.setattr(SiglipVisionModel, 'from_pretrained', lambda *a, **k: vision)
    encoder = build_encoder('siglip', model_id='tiny')
    assert isinstance(encoder, SiglipEncoder)
    assert encoder.embedding_dim == 16
    model = RealismScorer(encoder, encoder.embedding_dim)
    set_encoder_frozen(model, True)
    model.train()
    assert not encoder.training
    assert model.head.training
    images = torch.randn(2, 3, 16, 16)
    with torch.no_grad():
        assert torch.allclose(encoder(images), vision(pixel_values=images).pooler_output)
    before = {k: v.clone() for k, v in encoder.state_dict().items()}
    head_before = {k: v.clone() for k, v in model.head.state_dict().items()}
    loss = model(images).sum()
    loss.backward()
    assert all(p.grad is None for p in encoder.parameters())
    assert any(p.grad is not None for p in model.head.parameters())
    optimizer = torch.optim.Adam(model.head.parameters())
    optimizer.step()
    assert any(not torch.equal(head_before[k], v) for k, v in model.head.state_dict().items())
    assert all(torch.equal(before[k], v) for k, v in encoder.state_dict().items())
    set_encoder_frozen(model, False)
    model.train()
    assert encoder.training
    model(images).sum().backward()
    assert any(p.grad is not None for p in encoder.parameters())


def make_data(root):
    rows = []
    for split in ('train', 'val', 'test', 'test_unseen'):
        for label in (0, 1):
            if split == 'test_unseen' and label == 1:
                continue
            name = f'{split}_{label}.png'
            Image.new('RGB', (32, 40), (label * 255, 100, 100)).save(root / name)
            rows.append(dict(image_id=name, path=name, label=label, category='상의',
                             source_type='real' if label else 'generated',
                             source_domain='kfashion' if label else '',
                             generator='' if label else ('unseen' if split == 'test_unseen' else 'seen'),
                             split=split))
    path = root / 'metadata.csv'
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_split_and_test_b_real_reuse(tmp_path):
    path = make_data(tmp_path)
    dataset = MetadataDataset(path, 16, False, False, split='train')
    assert {r.image_id for r in dataset.rows} == {'train_0.png', 'train_1.png'}
    all_rows = MetadataDataset(path, 16, False, False).rows
    standard, unseen = evaluation_indices(all_rows)
    assert {all_rows[i].image_id for i in standard} == {'test_0.png', 'test_1.png'}
    assert {all_rows[i].image_id for i in unseen} == {'test_1.png', 'test_unseen_0.png'}
    image1, _ = dataset[0]
    image2, _ = dataset[0]
    assert torch.equal(image1, image2)


def test_metrics_two_classes_and_single_class():
    perfect = binary_metrics([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8])
    assert perfect['roc_auc'] == perfect['pr_auc'] == perfect['f1'] == 1.0
    inverted = binary_metrics([0, 1], [0.9, 0.1])
    assert inverted['roc_auc'] == inverted['accuracy'] == 0.0
    assert binary_metrics([0, 0], [0.1, 0.2])['roc_auc'] is None
    assert binary_metrics([0, 1], [0.5, 0.5])['roc_auc'] == 0.5
    tied = binary_metrics([0, 1, 0, 1], [0.8, 0.8, 0.3, 0.1])
    assert tied['roc_auc'] == 0.375
    assert tied['pr_auc'] == pytest.approx(7 / 12)


def test_training_validation_checkpoint_and_evaluation(tmp_path, monkeypatch):
    from src.evaluate import main as evaluate
    path = make_data(tmp_path)
    normalization = dict(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    seen = []
    def dataset_factory(*args, **kwargs):
        seen.append(kwargs.get('normalization'))
        return MetadataDataset(*args, **kwargs)
    monkeypatch.setattr('src.train.MetadataDataset', dataset_factory)
    monkeypatch.setattr('src.evaluate.MetadataDataset', dataset_factory)
    config = dict(model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True,
                            normalization=normalization),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=3, device='cpu'),
                  augmentation=dict(horizontal_flip=False, jpeg_aug=False),
                  data=dict(metadata_csv=str(path)),
                  output=dict(checkpoint_dir=str(tmp_path / 'checkpoints')))
    checkpoint = run_training(config, str(path), 2, tmp_path / 'checkpoints')
    assert checkpoint.name == 'best.pt'
    saved = torch.load(checkpoint, weights_only=True)
    assert 1 <= saved['epochs_done'] <= 2
    assert saved['validation_metrics']['roc_auc'] is not None
    history = json.loads((checkpoint.parent / 'experiment.json').read_text())['history']
    assert saved['val_loss'] == min(h['val_loss'] for h in history)
    # under-strict: 재개 시 epoch/optimizer 상태를 버리는 변경을 검출한다.
    # over-strict: 동일 config의 정상 재개를 허용한다.
    run_training(config, str(path), 3, checkpoint.parent, resume=True)
    last = torch.load(checkpoint.parent / 'last.pt', weights_only=True)
    assert last['epochs_done'] == 3
    assert last['history'][:2] == history
    assert len(last['history']) == 3
    result = evaluate(['--checkpoint', str(checkpoint)])
    assert result['standard']['count'] == 2
    assert result['unseen']['count'] == 2
    assert result['shared_real_count'] == 1
    assert result['standard']['generator_wise']['seen']['roc_auc'] is not None
    assert seen and all(n == normalization for n in seen)


def test_image_root_mount_and_invalid_unseen(tmp_path):
    root = tmp_path / 'mounted'
    root.mkdir()
    Image.new('RGB', (20, 20)).save(root / 'sample.png')
    path = tmp_path / 'metadata.csv'
    path.write_text('image_id,path,label,category,source_type,split\n'
                    'a,images/sample.png,1,상의,real,test_unseen\n')
    dataset = MetadataDataset(path, 16, False, False, image_root=root)
    assert dataset[0][0].shape == (3, 16, 16)
    with pytest.raises(ValueError, match='generated images only'):
        evaluation_indices(dataset.rows)


def test_resume_matches_uninterrupted_training(tmp_path):
    """중단 시 optimizer/RNG 누락을 잡고 정상 재개는 연속 실행과 같은 결과를 낸다."""
    path = make_data(tmp_path)
    config = dict(model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=3, device='cpu', num_workers=2),
                  augmentation=dict(horizontal_flip=True, jpeg_aug=True,
                                    minor_crop=True, color_jitter=True),
                  data=dict(metadata_csv=str(path)))
    torch.manual_seed(42)
    random.seed(42)
    run_training(config, str(path), 3, tmp_path / 'full')
    torch.manual_seed(42)
    random.seed(42)
    run_training(config, str(path), 2, tmp_path / 'resumed')
    torch.manual_seed(123)
    random.seed(123)
    run_training(config, str(path), 3, tmp_path / 'resumed', resume=True)
    full = torch.load(tmp_path / 'full/last.pt', weights_only=True)
    resumed = torch.load(tmp_path / 'resumed/last.pt', weights_only=True)
    assert full['history'] == resumed['history']
    assert all(torch.equal(v, resumed['model_state'][k]) for k, v in full['model_state'].items())
    changed = dict(config, training=dict(config['training'], learning_rate=0.02))
    with pytest.raises(ValueError, match='same config'):
        run_training(changed, str(path), 3, tmp_path / 'resumed', resume=True)


def test_minor_crop_resizes_before_sampling():
    """세로 착용컷의 과도한 중앙 crop을 막고 정상 약한 crop은 유지한다."""
    from torchvision import transforms
    transform = build_transform(224, False, False, minor_crop=True)
    assert isinstance(transform.transforms[0], transforms.Resize)
    assert isinstance(transform.transforms[1], transforms.RandomResizedCrop)
    resized = transform.transforms[0](Image.new('RGB', (400, 900)))
    assert resized.size == (224, 224)
    assert transform.transforms[1].scale == (0.95, 1.0)

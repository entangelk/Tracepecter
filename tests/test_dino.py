"""P03: pooled feature/정규화 오연결을 막고 기존 SigLIP 기본값은 유지한다."""
import pytest
import torch
from PIL import Image
from transformers import Dinov2Config, Dinov2Model

from src.dataset import build_transform
from src.model import build_encoder, RealismScorer, set_encoder_frozen


def test_dino_pooling_dimension_and_freeze(monkeypatch):
    """잘못된 pooling·차원을 거부하고 head 학습과 freeze 해제는 허용한다."""
    vision = Dinov2Model(Dinov2Config(hidden_size=16, intermediate_size=32,
                                    num_hidden_layers=1, num_attention_heads=2,
                                    image_size=16, patch_size=8))
    monkeypatch.setattr(Dinov2Model, 'from_pretrained', lambda *a, **k: vision)
    encoder = build_encoder('dino', model_id='tiny', revision='test')
    assert encoder.embedding_dim == 16
    model = RealismScorer(encoder, encoder.embedding_dim)
    set_encoder_frozen(model, True)
    model.train()
    assert not encoder.training and model.head.training
    images = torch.randn(2, 3, 16, 16)
    with torch.no_grad():
        assert torch.equal(encoder(images), vision(pixel_values=images).pooler_output)
    model(images).sum().backward()
    assert all(p.grad is None for p in encoder.parameters())
    assert any(p.grad is not None for p in model.head.parameters())
    set_encoder_frozen(model, False)
    model.train()
    model(images).sum().backward()
    assert any(p.grad is not None for p in encoder.parameters())


def test_normalization_config_and_old_checkpoint_default():
    """DINO 정규화 무시와 기존 SigLIP의 0.5 기본값 변경을 함께 검출한다."""
    image = Image.new('RGB', (32, 32), (128, 128, 128))
    normalization = dict(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    tensor = build_transform(16, False, False, normalization=normalization)(image)
    for c in range(3):
        expected = (128 / 255 - normalization['mean'][c]) / normalization['std'][c]
        assert tensor[c].mean().item() == pytest.approx(expected, abs=1e-6)
    with pytest.raises(KeyError):
        build_transform(16, False, False, normalization={})
    old = build_transform(16, False, False)(image)
    assert old.mean().item() == pytest.approx((128 / 255 - 0.5) / 0.5, abs=1e-6)


def test_primary_selection_uses_validation_then_latency():
    """실질적 val 차이를 무시하거나 근접 점수에서 속도를 무시하는 변경을 막는다."""
    from scripts.compare_baselines import select_primary
    siglip = dict(encoder='siglip', validation_roc_auc=0.99, latency_median_ms=10, parameter_count=100)
    dino = dict(encoder='dino', validation_roc_auc=0.992, latency_median_ms=20, parameter_count=100)
    assert select_primary([siglip, dino], 0.001) == 'dino'
    dino['validation_roc_auc'] = 0.9901
    assert select_primary([siglip, dino], 0.001) == 'siglip'
    dino['latency_median_ms'] = 5
    assert select_primary([siglip, dino], 0.001) == 'dino'

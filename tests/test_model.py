"""§16 모델 구조 회귀 가드.

가드 방향:
- under-strict: Sigmoid 가 제거되면 test_output_is_probability 재실패.
- over-strict:  freeze 정책이 반전되거나 head 스택 순서가 바뀌면
  test_encoder_grad_flags / test_head_structure_matches_spec 재실패.
"""
import pytest
import torch

from src.model import RealismScorer, StubEncoder, build_encoder, set_encoder_frozen

EMBEDDING_DIM = 32


def _model() -> RealismScorer:
    return RealismScorer(StubEncoder(EMBEDDING_DIM), EMBEDDING_DIM)


def test_output_is_probability():
    """forward 출력은 [B] shape 이고 모든 값이 [0,1] 범위 (§16 Sigmoid).

    결정성(검증 H1): seed 고정 + 입력 100배 스케일로 로짓을 극단화해,
    Sigmoid 가 없으면 반드시 [0,1] 밖 값이 관측된다."""
    torch.manual_seed(0)
    model = _model().eval()
    images = torch.randn(8, 3, 64, 64) * 100
    with torch.no_grad():
        output = model(images)
    assert output.shape == (8,)
    assert torch.all(output >= 0.0)
    assert torch.all(output <= 1.0)


def test_encoder_grad_flags():
    """freeze=true → encoder 파라미터 requires_grad=False, head 는 True. 해제 시 반전 (§16/§17)."""
    model = _model()
    set_encoder_frozen(model, frozen=True)
    assert all(not p.requires_grad for p in model.encoder.parameters())
    assert all(p.requires_grad for p in model.head.parameters())

    set_encoder_frozen(model, frozen=False)
    assert all(p.requires_grad for p in model.encoder.parameters())


def test_unknown_encoder_rejected():
    """알 수 없는 encoder 이름을 거부한다(정상 stub·siglip은 별도 검증)."""
    with pytest.raises(ValueError):
        build_encoder("unknown", EMBEDDING_DIM)


def test_head_structure_matches_spec():
    """head 스택은 §16 순서 그대로: Linear → GELU → Dropout → Linear(1) → Sigmoid."""
    model = _model()
    kinds = [type(layer) for layer in model.head]
    assert kinds == [torch.nn.Linear, torch.nn.GELU, torch.nn.Dropout, torch.nn.Linear, torch.nn.Sigmoid]
    assert model.head[-2].out_features == 1

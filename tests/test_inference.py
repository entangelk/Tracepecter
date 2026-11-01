"""P07-01: 공유 추론 코어의 응답 계약·model_version·threshold 경계를 잡는다."""
import hashlib
import json
from pathlib import Path

import pytest
import torch
import yaml
from PIL import Image

from src.anonymize import Anonymizer, bind_spec
from src.evaluate import file_sha256
from src.inference import Scorer, model_version
from src.model import RealismScorer, build_encoder
from src.score import main as score

HASHES = ('a' * 64, 'b' * 64, 'c' * 64)


@pytest.fixture
def artifact(tmp_path, monkeypatch):
    """stub checkpoint + 익명화 규격 + calibration JSON. 검출기는 얼굴 2개를 돌려준다."""
    detector = tmp_path / 'yunet.onnx'
    detector.write_bytes(b'test detector')
    spec = yaml.safe_load(Path('configs/anonymize.yaml').read_text())
    spec['face_detector'].update(model=str(detector), model_sha256=hashlib.sha256(detector.read_bytes()).hexdigest())
    monkeypatch.setattr(Anonymizer, 'detect', lambda self, image: [[4., 4., 8., 8.], [16., 16., 8., 8.]])
    torch.manual_seed(0)
    config = dict(anonymization=bind_spec(spec),
                  model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True))
    checkpoint = tmp_path / 'best.pt'
    torch.save(dict(config=config, model_state=RealismScorer(build_encoder('stub', 8), 8).state_dict()), checkpoint)
    calibration = tmp_path / 'calibration.json'
    calibration.write_text(json.dumps(dict(version=1, method='temperature_scaling', checkpoint=str(checkpoint),
                                           checkpoint_sha256=file_sha256(checkpoint),
                                           temperature=1.5, threshold_probability=0.5)))
    image = tmp_path / 'image.png'
    Image.new('RGB', (40, 32), (120, 60, 30)).save(image)
    return dict(calibration=calibration, checkpoint=checkpoint, image=image, spec_sha256=config['anonymization']['sha256'])


def test_model_version_is_stable_and_deterministic():
    """같은 세 hash는 같은 값(과잉 엄격 가드)이고 형식은 소문자 hex 12자리다."""
    first = model_version(*HASHES)
    assert first == model_version(*HASHES)
    assert len(first) == 12 and all(c in '0123456789abcdef' for c in first)


@pytest.mark.parametrize('position', [0, 1, 2])
def test_model_version_changes_when_any_component_changes(position):
    """checkpoint·calibration·익명화 규격 중 하나만 바뀌어도 값이 달라진다(과소 엄격 가드)."""
    changed = list(HASHES)
    changed[position] = 'd' * 64
    assert model_version(*changed) != model_version(*HASHES)


def test_model_version_depends_on_component_order():
    """세 hash를 정렬·집합으로 합치는 변형을 잡는다. 순서가 바뀌면 다른 artifact 조합이다."""
    a, b, c = HASHES
    assert model_version(b, a, c) != model_version(a, b, c)


def test_scorer_response_contract_and_cli_agree(artifact, capsys):
    """응답은 DB-08 네 필드뿐이고(confidence 없음) CLI는 같은 코어로 같은 값을 출력한다."""
    scorer = Scorer(artifact['calibration'])
    with Image.open(artifact['image']) as handle:
        result = scorer(handle)
    assert set(result) == {'realism_score', 'classification', 'faces_anonymized', 'model_version'}
    assert 0 <= result['realism_score'] <= 100
    assert result['classification'] in ('photographic_like', 'synthetic_like')
    assert result['faces_anonymized'] == 2
    assert result['model_version'] == model_version(file_sha256(artifact['checkpoint']),
                                                    file_sha256(artifact['calibration']), artifact['spec_sha256'])
    cli = score(['--image', str(artifact['image']), '--calibration', str(artifact['calibration'])])
    assert cli == result and json.loads(capsys.readouterr().out) == result


def test_scorer_loads_once_and_repeats_identically(artifact, monkeypatch):
    """요청마다 다시 로드하는 변형을 잡고, 같은 입력의 반복 호출은 같은 응답이다."""
    import src.inference as inference
    loads = []
    original = inference.load_model
    monkeypatch.setattr(inference, 'load_model', lambda *a, **k: loads.append(1) or original(*a, **k))
    scorer = Scorer(artifact['calibration'])
    with Image.open(artifact['image']) as handle:
        first, second = scorer(handle), scorer(handle)
    assert first == second and len(loads) == 1


def test_scorer_converts_non_rgb_input(artifact):
    """RGBA·L 입력도 RGB 변환 후 점수를 낸다. 같은 RGB 내용이면 같은 점수다."""
    scorer = Scorer(artifact['calibration'])
    rgb = Image.new('RGB', (40, 32), (120, 60, 30))
    assert scorer(rgb.convert('RGBA')) == scorer(rgb)
    assert scorer(Image.new('L', (40, 32), 90))['faces_anonymized'] == 2


def test_classification_boundary_belongs_to_photographic(artifact):
    """확률이 threshold와 같으면 photographic_like, 바로 아래면 synthetic_like다(양방향 경계)."""
    scorer = Scorer(artifact['calibration'])
    image = Image.new('RGB', (40, 32), (120, 60, 30))
    probability = scorer(image)['realism_score'] / 100
    scorer.threshold = probability
    assert scorer(image)['classification'] == 'photographic_like'
    scorer.threshold = probability + 1e-9
    assert scorer(image)['classification'] == 'synthetic_like'


def test_model_version_follows_calibration_file(artifact):
    """같은 checkpoint라도 calibration 파일 내용이 바뀌면 model_version이 달라진다."""
    before = Scorer(artifact['calibration']).model_version
    data = json.loads(artifact['calibration'].read_text())
    data['temperature'] = 2.0
    artifact['calibration'].write_text(json.dumps(data))
    after = Scorer(artifact['calibration']).model_version
    assert before != after


def test_non_finite_score_rejected(artifact, monkeypatch):
    """NaN 확률을 응답으로 내보내지 않는다."""
    scorer = Scorer(artifact['calibration'])
    monkeypatch.setattr(scorer.model, 'forward_logits', lambda batch: torch.tensor([[float('nan')]]))
    with pytest.raises(ValueError, match='non-finite'):
        scorer(Image.new('RGB', (40, 32)))

"""P07-01: 공유 추론 코어의 응답 계약·model_version·threshold 경계를 잡는다."""
import hashlib
import json
import math
from pathlib import Path

import pytest
import torch
import yaml
from PIL import Image

from src.anonymize import Anonymizer, bind_spec
from src.evaluate import file_sha256
from src.inference import Scorer, load_calibration, model_version
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
                                           temperature=1.5, threshold_probability=0.37)))
    image = tmp_path / 'image.png'
    Image.new('RGB', (40, 32), (120, 60, 30)).save(image)
    return dict(calibration=calibration, checkpoint=checkpoint, image=image, detector=detector,
                spec_sha256=config['anonymization']['sha256'])


def rewrite(path, **fields):
    data = json.loads(path.read_text())
    data.update(fields)
    path.write_text(json.dumps(data))


def test_model_version_is_stable_and_deterministic():
    """같은 세 hash는 같은 값(과잉 엄격 가드)이고 형식은 소문자 hex 12자리다."""
    first = model_version(*HASHES)
    assert first == model_version(*HASHES)
    assert len(first) == 12 and all(c in '0123456789abcdef' for c in first)


def test_model_version_formula_is_literal():
    """해시 함수·순서·구분자·앞 12자리를 같은 함수 없이 독립 계산값과 고정 문자열로 잠근다."""
    assert model_version(*HASHES) == hashlib.sha256(':'.join(HASHES).encode()).hexdigest()[:12] == '30b19c9cb857'


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
    expected = ':'.join([file_sha256(artifact['checkpoint']), file_sha256(artifact['calibration']), artifact['spec_sha256']])
    assert result['model_version'] == hashlib.sha256(expected.encode()).hexdigest()[:12]
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


def fixed_logit_scorer(artifact, monkeypatch, logit=0.625):
    scorer = Scorer(artifact['calibration'])
    monkeypatch.setattr(scorer.model, 'forward_logits', lambda batch: torch.tensor([[logit]]))
    return scorer


def test_score_uses_artifact_temperature(artifact, monkeypatch):
    """realism_score = 100*sigmoid(logit/T), T는 artifact 값(1.5). logit은 float32에서 정확한 0.625. T 무시·고정 변형을 잡는다."""
    result = fixed_logit_scorer(artifact, monkeypatch)(Image.new('RGB', (40, 32)))
    assert result['realism_score'] == pytest.approx(100 / (1 + math.exp(-0.625 / 1.5)), abs=1e-9)
    assert result['realism_score'] != pytest.approx(100 / (1 + math.exp(-0.625)), abs=1e-3)


@pytest.mark.parametrize('offset,expected', [(0., 'photographic_like'), (1e-9, 'synthetic_like'),
                                             (-1e-9, 'photographic_like')])
def test_classification_uses_artifact_threshold(artifact, monkeypatch, offset, expected):
    """artifact threshold와 같은 확률은 photographic_like, 바로 위 threshold면 synthetic_like다.
    threshold를 artifact 파일로만 바꾸므로 고정 0.5·인스턴스 우회 변형도 잡는다."""
    probability = 1 / (1 + math.exp(-0.625 / 1.5))
    rewrite(artifact['calibration'], threshold_probability=probability + offset)
    result = fixed_logit_scorer(artifact, monkeypatch)(Image.new('RGB', (40, 32)))
    assert result['classification'] == expected


def test_fixture_threshold_separates_from_default(artifact, monkeypatch):
    """확률 0.4~0.5 구간을 artifact threshold 0.37은 photographic_like로, 고정 0.5는 synthetic_like로 나눈다."""
    result = fixed_logit_scorer(artifact, monkeypatch, logit=-0.375)(Image.new('RGB', (40, 32)))
    assert 37 <= result['realism_score'] < 50 and result['classification'] == 'photographic_like'


@pytest.mark.parametrize('field,value,message', [
    ('version', 2, 'unsupported'), ('method', 'platt', 'unsupported'),
    ('temperature', 0., 'temperature'), ('temperature', -1., 'temperature'),
    ('temperature', float('nan'), 'temperature'), ('temperature', float('inf'), 'temperature'),
    ('threshold_probability', -1e-9, 'threshold'), ('threshold_probability', 1 + 1e-9, 'threshold'),
    ('threshold_probability', float('nan'), 'threshold'), ('checkpoint_sha256', '0' * 64, 'hash mismatch')])
def test_invalid_calibration_rejected_at_startup(artifact, field, value, message):
    """artifact 검증 분기마다 load_calibration과 Scorer 생성이 모두 거부한다(요청 전 기동 거부)."""
    rewrite(artifact['calibration'], **{field: value})
    with pytest.raises(ValueError, match=message):
        load_calibration(artifact['calibration'])
    with pytest.raises(ValueError, match=message):
        Scorer(artifact['calibration'])


@pytest.mark.parametrize('threshold', [0., 1.])
def test_threshold_range_endpoints_accepted(artifact, threshold):
    """threshold 범위 검증의 과잉 엄격 변형(0·1 거부)을 잡는다."""
    rewrite(artifact['calibration'], threshold_probability=threshold)
    assert Scorer(artifact['calibration']).threshold == threshold


def test_detector_mismatch_rejected_by_scorer(artifact):
    """checkpoint에 결합된 YuNet hash와 실제 파일이 다르면 Scorer 생성이 거부된다."""
    artifact['detector'].write_bytes(b'other detector')
    with pytest.raises(ValueError, match='face detector model sha256 mismatch'):
        Scorer(artifact['calibration'])


def test_model_version_follows_calibration_file(artifact):
    """같은 checkpoint라도 calibration 파일 내용이 바뀌면 model_version이 달라진다."""
    before = Scorer(artifact['calibration']).model_version
    rewrite(artifact['calibration'], temperature=2.0)
    after = Scorer(artifact['calibration']).model_version
    assert before != after


def test_non_finite_score_rejected(artifact, monkeypatch):
    """NaN 확률을 응답으로 내보내지 않는다."""
    scorer = Scorer(artifact['calibration'])
    monkeypatch.setattr(scorer.model, 'forward_logits', lambda batch: torch.tensor([[float('nan')]]))
    with pytest.raises(ValueError, match='non-finite'):
        scorer(Image.new('RGB', (40, 32)))

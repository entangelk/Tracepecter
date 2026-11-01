"""P07-02: POST /score의 응답 schema·거부 경로·기동 거부를 stub artifact로 잡는다."""
import io

import pytest
import yaml
from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from src.inference import Scorer
from test_inference import artifact, rewrite  # noqa: F401  stub checkpoint·calibration fixture 공유


def encode(fmt, size=(40, 32), mode='RGB'):
    buffer = io.BytesIO()
    Image.new(mode, size, 90).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def settings(artifact, tmp_path):
    def write(**overrides):
        values = dict(calibration=str(artifact['calibration']), device='cpu',
                      max_upload_bytes=4096, formats=['JPEG', 'PNG', 'WEBP'])
        values.update(overrides)
        path = tmp_path / 'inference.yaml'
        path.write_text(yaml.safe_dump(values))
        return path
    return write


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings()))


def post(client, data, name='image.png', field='image'):
    return client.post('/score', files={field: (name, data, 'application/octet-stream')})


@pytest.mark.parametrize('fmt', ['JPEG', 'PNG', 'WEBP'])
def test_accepted_formats_return_contract(client, artifact, fmt):
    """세 형식 모두 DB-08 네 필드만 돌려주고 값은 CLI와 같은 코어 결과와 같다."""
    response = post(client, encode(fmt))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {'realism_score', 'classification', 'faces_anonymized', 'model_version'}
    with Image.open(io.BytesIO(encode(fmt))) as handle:
        expected = Scorer(artifact['calibration'])(handle)
    assert body == pytest.approx(expected) and body['faces_anonymized'] == 2


def test_same_input_same_output(client):
    """같은 바이트를 두 번 보내면 같은 응답이다."""
    data = encode('PNG')
    assert post(client, data).json() == post(client, data).json()


@pytest.mark.parametrize('fmt', ['GIF', 'BMP', 'TIFF'])
def test_decodable_but_unsupported_format_is_415(client, fmt):
    """PIL이 읽을 수 있어도 설정에 없는 형식은 점수 없이 415다."""
    response = post(client, encode(fmt))
    assert response.status_code == 415 and 'realism_score' not in response.json()


@pytest.mark.parametrize('data', [b'not an image', b'', encode('PNG')[:60], encode('JPEG')[:200]])
def test_undecodable_bytes_are_400(client, data):
    """이미지가 아닌 바이트·빈 파일·잘린 PNG/JPEG는 400이다."""
    response = post(client, data)
    assert response.status_code == 400 and 'realism_score' not in response.json()


def test_size_limit_boundary(settings, artifact):
    """정확히 한도인 업로드는 받고 1바이트 초과는 413이다(양방향 경계)."""
    data = encode('PNG')
    at_limit = TestClient(create_app(settings(max_upload_bytes=len(data))))
    assert post(at_limit, data).status_code == 200
    below = TestClient(create_app(settings(max_upload_bytes=len(data) - 1)))
    response = post(below, data)
    assert response.status_code == 413 and 'realism_score' not in response.json()


def test_decompression_bomb_is_413(client, monkeypatch):
    """선언 픽셀 수가 PIL 폭탄 한도를 넘는 이미지는 디코딩 전에 413으로 거부한다."""
    monkeypatch.setattr(Image, 'MAX_IMAGE_PIXELS', 100)
    assert post(client, encode('PNG', size=(40, 32))).status_code == 413


def test_missing_or_misnamed_field_is_rejected(client):
    """필드 `image`가 없으면 점수를 내지 않는다(FastAPI 검증 422)."""
    assert post(client, encode('PNG'), field='file').status_code == 422


def test_format_is_read_from_bytes_not_filename(client):
    """파일 이름 확장자는 형식 판정에 쓰지 않는다. GIF 내용에 .png 이름이어도 415다."""
    assert post(client, encode('GIF'), name='photo.png').status_code == 415
    assert post(client, encode('PNG'), name='photo.gif').status_code == 200


def test_non_rgb_png_is_scored(client):
    """RGBA·팔레트 PNG도 RGB 변환 후 점수를 낸다."""
    assert post(client, encode('PNG', mode='RGBA')).status_code == 200
    assert post(client, encode('PNG', mode='P')).status_code == 200


def test_non_finite_score_is_not_serialized(settings, artifact, monkeypatch):
    """NaN 점수는 200 응답으로 나가지 않는다."""
    scorer = Scorer(artifact['calibration'])
    monkeypatch.setattr(scorer, 'temperature', float('nan'))
    client = TestClient(create_app(settings(), scorer=scorer), raise_server_exceptions=False)
    response = post(client, encode('PNG'))
    assert response.status_code == 500
    assert 'NaN' not in response.text


@pytest.mark.parametrize('field,value', [('temperature', 0.), ('threshold_probability', 1.5),
                                         ('checkpoint_sha256', '0' * 64)])
def test_invalid_artifact_blocks_startup(settings, artifact, field, value):
    """artifact 검증에 실패하면 앱을 만들지 않는다(기동 거부)."""
    rewrite(artifact['calibration'], **{field: value})
    with pytest.raises(ValueError):
        create_app(settings())


def test_model_loaded_once_at_startup(settings, monkeypatch):
    """요청마다 Scorer를 다시 만드는 변형을 잡는다."""
    import api.main as main
    built = []
    monkeypatch.setattr(main, 'Scorer', lambda *a, **k: built.append(1) or Scorer(*a, **k))
    client = TestClient(create_app(settings()))
    for _ in range(3):
        assert post(client, encode('PNG')).status_code == 200
    assert len(built) == 1


def test_openapi_schema_matches_contract(client):
    """OpenAPI 응답 schema가 네 필드와 분류 어휘 두 개를 그대로 노출한다."""
    schema = client.get('/openapi.json').json()['components']['schemas']['ScoreResponse']
    assert set(schema['properties']) == {'realism_score', 'classification', 'faces_anonymized', 'model_version'}
    assert set(schema['properties']['classification']['enum']) == {'photographic_like', 'synthetic_like'}
    assert set(schema['required']) == set(schema['properties'])

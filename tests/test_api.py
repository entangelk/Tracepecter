"""P07-02: POST /score의 응답 schema·거부 경로·기동 거부를 stub artifact로 잡는다."""
import io
import threading
import time
from pathlib import Path

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
                      max_upload_bytes=4096, formats=['JPEG', 'MPO', 'PNG', 'WEBP'])
        values.update(overrides)
        path = tmp_path / 'inference.yaml'
        path.write_text(yaml.safe_dump(values))
        return path
    return write


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings()))


def post(client, data, name='image.png', field='image', content_type='application/octet-stream'):
    return client.post('/score', files={field: (name, data, content_type)})


def truncated(fmt):
    """헤더는 온전해 format 식별은 되지만 픽셀 데이터가 잘린 파일."""
    data = encode(fmt, size=(32, 32))
    return data[:len(data) // 2]


def mpo():
    buffer = io.BytesIO()
    first, second = Image.new('RGB', (40, 32), 90), Image.new('RGB', (40, 32), 200)
    first.save(buffer, format='MPO', save_all=True, append_images=[second])
    return buffer.getvalue()


@pytest.mark.parametrize('fmt', ['JPEG', 'PNG', 'WEBP', 'MPO'])
def test_accepted_formats_return_contract(client, artifact, fmt):
    """세 형식 모두 DB-08 네 필드만 돌려주고 값은 CLI와 같은 코어 결과와 같다."""
    data = mpo() if fmt == 'MPO' else encode(fmt)
    response = post(client, data)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {'realism_score', 'classification', 'faces_anonymized', 'model_version'}
    with Image.open(io.BytesIO(data)) as handle:
        assert handle.format == fmt
        expected = Scorer(artifact['calibration'])(handle)  # MPO는 첫 프레임, CLI와 같다
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
    types = {name: field.get('type') for name, field in schema['properties'].items()}
    assert types == dict(realism_score='number', classification='string', faces_anonymized='integer',
                         model_version='string')


def test_size_checked_before_decoding(settings):
    """이미지가 아닌 대용량 바이트도 400이 아니라 413이다(크기 판정이 디코딩보다 먼저)."""
    client = TestClient(create_app(settings(max_upload_bytes=100)))
    assert post(client, b'x' * 101).status_code == 413


@pytest.mark.parametrize('fmt', ['GIF', 'BMP'])
def test_format_checked_before_full_decoding(client, fmt):
    """허용 목록 밖 형식은 잘린 파일이어도 400이 아니라 415다(format 판정이 디코딩보다 먼저)."""
    assert post(client, truncated(fmt)).status_code == 415


@pytest.mark.parametrize('fmt', ['PNG', 'JPEG'])
def test_truncated_allowed_format_is_400(client, fmt):
    """허용 형식의 잘린 파일은 format 판정을 통과한 뒤 디코딩에서 400이다."""
    assert post(client, truncated(fmt)).status_code == 400


def test_formats_come_from_config(settings):
    """허용 형식을 코드에 고정하는 변형을 잡는다. 설정에서 PNG만 허용하면 JPEG는 415다."""
    client = TestClient(create_app(settings(formats=['PNG'])))
    assert post(client, encode('PNG')).status_code == 200
    assert post(client, encode('JPEG')).status_code == 415


def test_device_comes_from_config(settings, monkeypatch):
    """설정의 device를 Scorer에 그대로 넘긴다."""
    import api.main as main
    seen = []
    monkeypatch.setattr(main, 'Scorer', lambda calibration, device: seen.append(device) or Scorer(calibration))
    create_app(settings(device='cuda:1'))
    assert seen == ['cuda:1']


def test_shipped_config_values():
    """배포 설정의 계약 값: 채택 artifact 경로·CPU·10 MiB·JPEG/MPO/PNG/WEBP. threshold·temperature는 두지 않는다."""
    settings = yaml.safe_load(Path('configs/inference.yaml').read_text())
    assert settings == dict(calibration='experiments/p09_leakage_repair/r1/calibration/calibration.json',
                            device='cpu', max_upload_bytes=10 * 1024 * 1024, formats=['JPEG', 'MPO', 'PNG', 'WEBP'])


def test_content_type_is_ignored(client):
    """Content-Type 헤더도 형식 판정에 쓰지 않는다."""
    assert post(client, encode('PNG'), content_type='image/gif').status_code == 200
    assert post(client, encode('GIF'), content_type='image/png').status_code == 415


def test_duplicate_image_field_uses_last(client):
    """`image` 필드가 두 개면 마지막 것을 쓴다(FastAPI 단일 UploadFile 규칙)."""
    response = client.post('/score', files=[('image', ('a.gif', encode('GIF'), 'image/gif')),
                                            ('image', ('b.png', encode('PNG'), 'image/png'))])
    assert response.status_code == 200


def test_requests_are_serialized(settings, artifact):
    """동시 요청이 점수 계산 구간에 겹쳐 들어가지 않는다."""
    real = Scorer(artifact['calibration'])
    state = dict(active=0, peak=0)
    def scorer(image):
        state['active'] += 1
        state['peak'] = max(state['peak'], state['active'])
        time.sleep(0.05)
        state['active'] -= 1
        return real(image)
    client = TestClient(create_app(settings(), scorer=scorer))
    data = encode('PNG')
    threads = [threading.Thread(target=post, args=(client, data)) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert state['peak'] == 1


def test_mpo_follows_config(settings):
    """MPO를 설정과 무관하게 JPEG로 취급하는 변형을 잡는다. JPEG만 허용하면 MPO는 415다."""
    client = TestClient(create_app(settings(formats=['JPEG'])))
    assert post(client, encode('JPEG')).status_code == 200
    assert post(client, mpo()).status_code == 415


def test_config_path_from_environment(settings, monkeypatch):
    """인자가 없으면 TRACEPECTER_INFERENCE_CONFIG가 가리키는 설정을 쓴다."""
    import api.main as main
    seen = []
    monkeypatch.setattr(main, 'Scorer', lambda calibration, device: seen.append(device) or Scorer(calibration))
    monkeypatch.setenv('TRACEPECTER_INFERENCE_CONFIG', str(settings(device='cuda')))
    create_app()
    assert seen == ['cuda']


def test_upload_is_not_written_to_named_file(client, monkeypatch):
    """요청 처리 중 서버가 쓰기 모드로 파일을 열지 않는다(업로드 비저장)."""
    import builtins
    writes = []
    original = builtins.open
    def guarded(file, mode='r', *args, **kwargs):
        if any(flag in mode for flag in 'wax+'):
            writes.append(file)
        return original(file, mode, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', guarded)
    assert post(client, encode('PNG')).status_code == 200
    assert writes == []

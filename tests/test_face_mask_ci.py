"""P06-02c: 대응표본 구성·표본별 값·bootstrap 구간·사전 판정 규칙과 CLI 연결을 고정한다."""
import csv
import hashlib
import json

import cv2
import numpy as np
import pytest
import yaml

from src.face_mask import EditedDataset, disc_for_face, off_face_disc
from src.face_mask_ci import bootstrap_summary, condition_edits, decide, detect_face, per_image, pick_face

SETTINGS = yaml.safe_load(open('configs/face_mask_ci.yaml'))
RULE = SETTINGS['decision']['min_flip_fraction']


def test_pick_face_prefers_score_then_area_then_top_left():
    """score가 높으면 작은 상자라도 고른다. 동점이면 넓이, 그다음 위·왼쪽. 검출 순서와 무관하다."""
    small_sure, big_unsure = (0, 0, 10, 10, 0.95), (50, 50, 40, 40, 0.91)
    assert pick_face([big_unsure, small_sure]) == small_sure
    a, b = (50, 10, 20, 20, 0.9), (10, 40, 20, 20, 0.9)
    assert pick_face([a, b]) == pick_face([b, a]) == a
    assert pick_face([(0, 0, 10, 10, 0.9), (9, 9, 11, 11, 0.9)]) == (9, 9, 11, 11, 0.9)
    left, right = (10, 10, 20, 20, 0.9), (40, 10, 20, 20, 0.9)  # score·넓이·y가 같으면 왼쪽
    assert pick_face([left, right]) == pick_face([right, left]) == left
    assert pick_face([]) is None


def test_detect_face_filters_small_boxes_by_width_inclusive_and_passes_yunet_settings(monkeypatch):
    """min_size_ratio는 이미지 너비 기준이고 경계 포함. 너비 100이면 긴 변 4 이상만 남는다(높이 200 기준이면 8).
    YuNet 생성 인자는 (모델, '', (너비, 높이), score, nms, top_k) 순서다."""
    calls = []

    class Detector:
        def detect(self, image):
            return 1, np.asarray([[0, 0, 3.9, 3.9, *[0] * 10, 0.99],   # 너비 × 0.04 미만: 제외
                                  [50, 50, 3, 6, *[0] * 10, 0.95],     # 긴 변 6: 너비 기준이면 통과
                                  [20, 20, 4, 4, *[0] * 10, 0.92]], dtype=np.float32)
    monkeypatch.setattr(cv2.FaceDetectorYN, 'create', lambda *args: calls.append(args) or Detector())
    settings = dict(SETTINGS['face_detector'], model='m.onnx')
    rgb = np.zeros((200, 100, 3), dtype=np.uint8)
    assert detect_face(rgb, **settings) == (50, 50, 3, 6)
    assert calls == [('m.onnx', '', (100, 200), settings['score_threshold'], settings['nms_threshold'],
                      settings['top_k'])]
    Detector.detect = lambda self, image: (1, np.asarray([[20, 20, 4, 4, *[0] * 10, 0.92]], dtype=np.float32))
    assert detect_face(rgb, **settings) == (20, 20, 4, 4)  # 긴 변 = 너비 × 0.04 정확히: 포함
    Detector.detect = lambda self, image: (1, None)
    assert detect_face(rgb, **settings) is None


def test_condition_edits_share_face_disc_and_drop_samples_without_offface_room():
    """세 조건은 같은 표본에 적용된다: 흰·회색은 같은 얼굴 원, 얼굴 밖은 같은 반지름의 다른 위치. 자리가 없으면 제외."""
    ratio = SETTINGS['disc_diameter_per_face']
    face = (40, 40, 20, 30)
    disc = disc_for_face(face, ratio)
    assert disc == pytest.approx((50, 55, 18))
    edits = condition_edits(face, (300, 200), ratio, SETTINGS['conditions'])
    assert edits == dict(white_face=(disc, 255), gray_face=(disc, 128),
                         white_offface=(off_face_disc(disc, (300, 200)), 255))
    assert condition_edits((100, 10, 100, 100), (300, 200), ratio, SETTINGS['conditions']) is None


def test_per_image_shifts_differences_and_one_directional_flips():
    """과소: threshold 이상이 되면(경계 포함) 전환. 과잉: 원래 REAL 판정이던 표본·threshold 미만 이동은 전환이 아니다."""
    threshold = 0.7
    original = [0.1, 0.1, 0.8, 0.1]
    edited = dict(white_face=[0.7, 0.69, 0.9, 0.3], gray_face=[0.5, 0.6, 0.9, 0.2], white_offface=[0.2, 0.1, 0.8, 0.1])
    values = per_image(original, edited, threshold)
    assert values['flip_white'].tolist() == [1, 0, 0, 0]
    assert values['flip_gray'].tolist() == [0, 0, 0, 0]
    at = per_image([threshold, threshold - 0.01], dict(white_face=[0.9, 0.9], gray_face=[0.9, 0.9],
                                                       white_offface=[0.9, 0.9]), threshold)
    assert at['flip_white'].tolist() == [0, 1]  # 원본이 threshold와 같으면 이미 REAL 판정: 전환 아님
    assert values['shift_white'] == pytest.approx([60, 59, 10, 20])
    assert values['d1_white_minus_gray'] == pytest.approx([20, 9, 0, 10])
    assert values['d2_white_minus_offface'] == pytest.approx([50, 59, 10, 20])
    assert values['d3_gray_minus_offface'] == pytest.approx([30, 50, 10, 10])


def test_bootstrap_summary_is_seeded_and_shares_resamples_across_statistics():
    rng = np.random.default_rng(0)
    a = rng.normal(size=200)
    first = bootstrap_summary(dict(a=a, doubled=2 * a, constant=np.full(200, 3.0)), 500, 7, 0.95)
    again = bootstrap_summary(dict(a=a, doubled=2 * a, constant=np.full(200, 3.0)), 500, 7, 0.95)
    assert first == again and first['count'] == 200
    assert first['doubled']['low'] == pytest.approx(2 * first['a']['low'])  # 같은 재추출 표본
    assert first['constant'] == dict(mean=3.0, low=3.0, high=3.0)
    assert first['a']['low'] < first['a']['mean'] < first['a']['high']
    other = bootstrap_summary(dict(a=a), 500, 8, 0.95)
    assert other['a']['low'] != first['a']['low']
    means = a[np.random.default_rng(7).integers(0, 200, (500, 200))].mean(axis=1)
    assert [first['a']['low'], first['a']['high']] == pytest.approx(np.percentile(means, [2.5, 97.5]), abs=1e-12)
    narrow = bootstrap_summary(dict(a=a), 500, 7, 0.9)
    assert [narrow['a']['low'], narrow['a']['high']] == pytest.approx(np.percentile(means, [5, 95]), abs=1e-12)


def _summary(d1=(5, 1), d2=(5, 1), flip=(0.1, 0.06), d3=(5, 1)):
    def stat(pair):
        return dict(mean=pair[0], low=pair[1], high=pair[0] + 1)
    return dict(d1_white_minus_gray=stat(d1), d2_white_minus_offface=stat(d2), flip_white=stat(flip),
                d3_gray_minus_offface=stat(d3))


@pytest.mark.parametrize('summary, expected', [
    (_summary(), 'confirmed'),
    (_summary(flip=(0.1, 0.05)), 'confirmed'),          # 전환율 하한 = 기준(포함)
    (_summary(d1=(5, 0)), 'suggestive'),                 # D1 하한 0은 확정 아님(엄격히 커야 함)
    (_summary(d2=(5, -1)), 'suggestive'),
    (_summary(flip=(0.06, 0.049)), 'suggestive'),
    (_summary(d2=(5, 0)), 'suggestive'),                 # D2 하한 0은 확정 아님
    (_summary(flip=(0.05, 0.01)), 'suggestive'),          # 전환율 점추정 = 기준(포함)
    (_summary(d1=(0, -1)), 'insufficient'),              # 점추정도 엄격히 커야 함
    (_summary(d2=(-1, -2)), 'insufficient'),
    (_summary(d2=(0, -1)), 'insufficient'),               # D2 점추정 0은 시사 아님
    (_summary(flip=(0.049, 0.01)), 'insufficient'),
])
def test_white_disc_rule_three_levels(summary, expected):
    assert decide(summary, RULE)['white_disc_dependence'] == expected


@pytest.mark.parametrize('d3, expected', [((5, 0.1), 'confirmed'), ((5, 0), 'suggestive'), ((0, -1), 'insufficient')])
def test_occlusion_rule_three_levels(d3, expected):
    assert decide(_summary(d3=d3), RULE)['face_occlusion_dependence'] == expected


def _prepare_cli(tmp_path, monkeypatch, threshold):
    """stub 모델·calibration(threshold 고정)·더미 YuNet 모델 파일·고정 얼굴 검출로 CLI 설정을 만든다.
    대상 후보(GEN val/test/test_unseen) 순서대로: val 얼굴 있음, test 얼굴 없음, test_unseen 얼굴 있음."""
    import src.face_mask_ci as ci
    from src.calibrate import main as calibrate
    from src.train import run_training
    from test_baseline import make_data

    metadata = make_data(tmp_path)
    config = dict(anonymization=None, model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=1, device='cpu'),
                  augmentation=dict(horizontal_flip=False, jpeg_aug=False),
                  data=dict(metadata_csv=str(metadata)))
    checkpoint = run_training(config, str(metadata), 1, tmp_path/'checkpoints')
    (tmp_path/'calibration.yaml').write_text(yaml.safe_dump(dict(
        checkpoint=str(checkpoint), device='cpu', output_dir=str(tmp_path/'calibration'),
        fit=dict(temperature_min=0.05, temperature_max=20.0, iterations=100), metrics=dict(ece_bins=10))))
    calibrate(['--config', str(tmp_path/'calibration.yaml')])
    load_calibration = ci.load_calibration
    monkeypatch.setattr(ci, 'load_calibration', lambda path: {**load_calibration(path),
                                                              'threshold_probability': threshold})
    faces = iter([(12, 5, 6, 6), None, (12, 5, 6, 6)])
    monkeypatch.setattr(ci, 'detect_face', lambda rgb, **_: next(faces))
    model = tmp_path/'yunet.onnx'
    model.write_bytes(b'stub')
    settings = json.loads(json.dumps(SETTINGS))
    settings['face_detector'].update(model=str(model), model_sha256=hashlib.sha256(b'stub').hexdigest())
    settings.update(calibration=str(tmp_path/'calibration/calibration.json'), device='cpu',
                    output_dir=str(tmp_path/'out'))
    (tmp_path/'ci.yaml').write_text(yaml.safe_dump(settings))
    return ci, str(tmp_path/'ci.yaml'), settings


def _fake_predict(ci, temperature, white, gray, offface):
    def logit(p):
        return temperature * np.log(p / (1 - p))

    def predict(model, data, indices, device, training):
        if not isinstance(data, EditedDataset):
            return np.asarray([logit(0.01)] * len(indices)), None
        out = []
        for i in indices:
            (x, _, _), fill = data.edits[i]
            out.append(logit(gray if fill == 128 else white if x == 15 else offface))
        return np.asarray(out), None
    return predict


@pytest.mark.parametrize('white, gray, expected_white, expected_flip', [
    (0.75, 0.69, 'confirmed', 1.0),       # 흰 > 회색 > 얼굴 밖, 전부 전환
    (0.75, 0.80, 'insufficient', 1.0),    # 회색이 더 크면 D1 < 0
    (0.65, 0.60, 'insufficient', 0.0),    # threshold(0.7) 미만: 0.5 기준이면 전환으로 세어 확정이 된다
])
def test_cli_builds_matched_targets_and_wires_rule_inputs(tmp_path, monkeypatch, white, gray, expected_white,
                                                          expected_flip):
    ci, config_path, _ = _prepare_cli(tmp_path, monkeypatch, threshold=0.7)
    temperature = json.loads((tmp_path/'calibration/calibration.json').read_text())['temperature']
    monkeypatch.setattr(ci, 'predict_logits', _fake_predict(ci, temperature, white, gray, offface=0.02))
    report = ci.main(['--config', config_path])

    assert report['candidates'] == 3 and report['targets'] == 2
    assert report['excluded'] == dict(no_face=1, no_offface_room=0)
    assert report['subsets']['test']['count'] == 1 and report['subsets']['val']['count'] == 1
    assert report['pooled']['flip_white']['mean'] == expected_flip
    assert report['pooled']['shift_offface']['mean'] == pytest.approx(1.0)
    assert report['pooled']['d1_white_minus_gray']['mean'] == pytest.approx(100 * (white - gray))
    assert report['decision'] == dict(white_disc_dependence=expected_white, face_occlusion_dependence='confirmed')
    with (tmp_path/'out/predictions.csv').open() as handle:
        rows = list(csv.DictReader(handle))
    assert {r['condition'] for r in rows} == {'original', *ci.CONDITIONS}
    assert {r['image_id'] for r in rows} == {'val_0.png', 'test_unseen_0.png'}
    with (tmp_path/'out/detections.csv').open() as handle:
        in_target = {r['image_id']: r['in_target'] for r in csv.DictReader(handle)}
    assert in_target == {'val_0.png': '1', 'test_0.png': '0', 'test_unseen_0.png': '1'}
    assert json.loads((tmp_path/'out/report.json').read_text()) == report


def test_cli_excludes_faces_without_offface_room_and_rejects_wrong_model_hash(tmp_path, monkeypatch):
    ci, config_path, settings = _prepare_cli(tmp_path, monkeypatch, threshold=0.7)
    faces = iter([(12, 5, 6, 6), (0, 0, 30, 30), None])
    monkeypatch.setattr(ci, 'detect_face', lambda rgb, **_: next(faces))
    temperature = json.loads((tmp_path/'calibration/calibration.json').read_text())['temperature']
    monkeypatch.setattr(ci, 'predict_logits', _fake_predict(ci, temperature, 0.75, 0.69, 0.02))
    report = ci.main(['--config', config_path])
    assert report['excluded'] == dict(no_face=1, no_offface_room=1) and report['targets'] == 1
    assert report['subsets']['test'] == dict(count=0)

    settings['face_detector']['model_sha256'] = '0' * 64
    (tmp_path/'bad.yaml').write_text(yaml.safe_dump(settings))
    with pytest.raises(ValueError, match='sha256'):
        ci.main(['--config', str(tmp_path/'bad.yaml')])


def test_cli_decides_on_pooled_targets_with_configured_bootstrap(tmp_path, monkeypatch):
    """판정은 합산 대상으로 내린다(하위 집합과 판정이 달라도). bootstrap에는 config의 재추출 수·seed·구간을 넘긴다.
    report에는 config와 GIT_COMMIT이 남는다."""
    ci, config_path, _ = _prepare_cli(tmp_path, monkeypatch, threshold=0.7)
    temperature = json.loads((tmp_path/'calibration/calibration.json').read_text())['temperature']

    def logit(p):
        return temperature * np.log(p / (1 - p))

    def predict(model, data, indices, device, training):
        if not isinstance(data, EditedDataset):
            return np.asarray([logit(0.01)] * len(indices)), None
        out = []
        for i in indices:
            (x, _, _), fill = data.edits[i]
            val = data.base.rows[i].split == 'val'  # val은 흰 > 회색 > 얼굴 밖, test_unseen은 반대
            out.append(logit((0.69 if val else 0.03) if fill == 128 else (0.75 if val else 0.02) if x == 15
                             else (0.02 if val else 0.04)))
        return np.asarray(out), None
    monkeypatch.setattr(ci, 'predict_logits', predict)
    calls = []
    summary = ci.bootstrap_summary
    monkeypatch.setattr(ci, 'bootstrap_summary', lambda values, *args: calls.append(args) or summary(values, *args))
    monkeypatch.setenv('GIT_COMMIT', 'abc123')
    report = ci.main(['--config', config_path])

    boot = SETTINGS['bootstrap']
    assert calls and set(calls) == {(boot['resamples'], boot['seed'], boot['interval'])}
    assert decide(report['subsets']['val'], RULE)['white_disc_dependence'] == 'confirmed'
    assert decide(report['subsets']['test'], RULE)['white_disc_dependence'] == 'insufficient'
    assert report['decision'] == decide(report['pooled'], RULE)
    assert report['decision']['white_disc_dependence'] == 'suggestive'
    assert report['git_commit'] == 'abc123' and report['config']['bootstrap'] == boot

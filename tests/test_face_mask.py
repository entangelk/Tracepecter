"""P06-02b: 흰 원 검출·원 덧씌우기·진단 CLI가 사전 고정 규칙대로 동작하는지 고정한다."""
import csv
import json

import numpy as np
import yaml
from PIL import Image, ImageDraw

import pytest

from src.face_mask import (EditedDataset, decision_flips, dependence_evidence, detect_disc, disc_for_face,
                           largest_face, off_face_disc, paint_disc, select_edits)

SETTINGS = yaml.safe_load(open('configs/face_mask_diagnostic.yaml'))
DETECTOR = SETTINGS['disc_detector']
CONDITIONS = SETTINGS['conditions']


def _noise(width=300, height=200, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 200, (height, width, 3), dtype=np.uint8)


def _with_disc(array, x, y, r):
    image = Image.fromarray(array)
    ImageDraw.Draw(image).ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255))
    return np.asarray(image)


def test_detects_disc_even_when_merged_with_white_background():
    """과소 검출 방지: 원 둘레 절반이 흰 배경과 붙어 있어도 잡는다(실제 K-Fashion 사례)."""
    found = detect_disc(_with_disc(_noise(), 150, 100, 30), **DETECTOR)
    assert found is not None and abs(found[0] - 150) <= 2 and abs(found[1] - 100) <= 2 and abs(found[2] - 30) <= 3
    merged = _noise()
    merged[:, :150] = 255
    found = detect_disc(_with_disc(merged, 150, 100, 30), **DETECTOR)
    assert found is not None and abs(found[0] - 150) <= 3


def test_rejects_white_regions_that_are_not_discs():
    """과잉 검출 방지: 흰 사각형·넓은 흰 영역·잡음만 있는 이미지는 원이 아니다."""
    square = Image.fromarray(_noise())
    ImageDraw.Draw(square).rectangle((120, 70, 180, 130), fill=(255, 255, 255))
    assert detect_disc(np.asarray(square), **DETECTOR) is None
    wall = _noise()
    wall[:, :200] = 255
    assert detect_disc(wall, **DETECTOR) is None
    assert detect_disc(_noise(), **DETECTOR) is None


def test_disc_detector_requires_dark_edge_even_when_filled():
    """edge 단독 잠금: 꽉 찬 흰 원이라도 둘레 바깥이 outside_max보다 밝으면(240) 원이 아니다."""
    light = np.full((200, 300, 3), 240, dtype=np.uint8)
    assert detect_disc(_with_disc(light, 150, 100, 30), **DETECTOR) is None


def test_disc_detector_requires_filled_inside_even_with_edge():
    """fill 단독 잠금: 둘레 경계가 뚜렷해도 안쪽에 어두운 점(순백 비율 < min_fill)이 있으면 원이 아니다."""
    spotted = Image.fromarray(_with_disc(_noise(), 150, 100, 30))
    ImageDraw.Draw(spotted).ellipse((155, 93, 169, 107), fill=(0, 0, 0))
    assert detect_disc(np.asarray(spotted), **DETECTOR) is None


def test_largest_face_breaks_area_ties_deterministically():
    """넓이가 같으면 검출 순서와 무관하게 위·왼쪽 상자. 넓이가 크면 위치와 무관하게 큰 상자."""
    a, b = (50, 10, 20, 20), (10, 40, 20, 20)
    assert largest_face([a, b]) == largest_face([b, a]) == a
    assert largest_face([(10, 10, 20, 20), (90, 90, 21, 21)]) == (90, 90, 21, 21)


def test_disc_for_face_uses_long_side_times_diameter_ratio():
    assert disc_for_face((10, 20, 40, 30), SETTINGS['disc_diameter_per_face']) == pytest.approx((30, 35, 28))


def test_select_edits_follows_condition_labels_position_and_fill():
    """labels 필터(GEN 원 오검출은 real_disc_gray 대상 아님), spec fill, REAL 원 r+3, off_face 자리 없음 제외."""
    labels = [1, 0, 0, 1]
    detections = [dict(disc=(50, 50, 10), face=None), dict(disc=(60, 60, 10), face=(40, 40, 20, 20)),
                  dict(disc=None, face=(10, 10, 100, 100)), dict(disc=None, face=None)]
    sizes = [(300, 200)] * 4
    ratio = SETTINGS['disc_diameter_per_face']

    def edits(name):
        return select_edits(CONDITIONS[name], labels, range(4), detections, sizes, ratio)
    assert edits('real_disc_gray') == {0: ((50, 50, 13), 128)}
    face = disc_for_face((40, 40, 20, 20), ratio)
    big = disc_for_face((10, 10, 100, 100), ratio)
    assert edits('gen_white_face') == {1: (face, 255), 2: (big, 255)}
    assert edits('gen_gray_face') == {1: (face, 128), 2: (big, 128)}
    assert edits('gen_white_offface') == {1: (off_face_disc(face, (300, 200)), 255)}  # 2번은 자리가 없어 제외


def test_decision_flips_counts_only_correct_to_wrong_at_calibrated_threshold():
    """과소: threshold(0.7) 기준 GEN→REAL 판정, REAL→FN만 센다. 과잉: 0.5~0.7 이동·역방향 전환은 세지 않는다."""
    threshold = 0.7
    assert decision_flips([0.1, 0.1, 0.4], [0.75, 0.69, 0.6], [0, 0, 0], threshold) == 1
    assert decision_flips([0.9, 0.9, 0.8], [0.65, 0.71, 0.4], [1, 1, 1], threshold) == 2
    assert decision_flips([0.8, 0.3], [0.2, 0.9], [0, 1], threshold) == 0  # 틀렸던 판정이 맞게 바뀐 경우
    assert decision_flips([0.1], [threshold], [0], threshold) == 1  # 경계값은 REAL 판정(≥): GEN은 전환
    assert decision_flips([0.9], [threshold], [1], threshold) == 0  # REAL은 경계값이면 FN 아님


@pytest.mark.parametrize('flips, count, shifts, expected', [
    (1, 20, (5.0, 4.0), True),     # 비율 정확히 0.05(경계 포함)
    (49, 1000, (5.0, 4.0), False),  # 0.049
    (36, 581, (10.0, 10.0), False),  # 회색 대조와 같으면 미발동(엄격히 커야 함)
    (36, 581, (5.0, 11.0), False),  # 위치 대조보다 작으면 미발동
    (36, 581, (11.0, 5.0), False),  # 회색 대조보다 작으면 미발동
    (36, 581, (None, 5.0), False),
    (0, 0, (5.0, 4.0), False),
])
def test_dependence_rule_fires_only_when_both_conditions_hold(flips, count, shifts, expected):
    main = dict(edited_count=count, edited_mean_shift=10.0, edited_decision_flips=flips)
    assert dependence_evidence(main, list(shifts), SETTINGS['dependence_rule']['min_gen_flip_fraction']) is expected


def test_off_face_disc_keeps_size_and_avoids_face():
    x, y, r = off_face_disc((100, 60, 20), (300, 200))
    assert (y, r) == (60, 20) and abs(x - 100) >= 40 and 20 <= x <= 280
    assert off_face_disc((150, 60, 20), (300, 200)) == (210, 60, 20)  # 대칭 위치가 겹치면 옆으로
    assert off_face_disc((50, 60, 40), (120, 200)) is None


def test_paint_disc_only_changes_inside(tmp_path):
    image = Image.fromarray(_noise())
    painted = np.asarray(paint_disc(image, (150, 100, 20), 128))
    original = np.asarray(image)
    assert (painted[100, 150] == 128).all()
    assert (painted[100, 175] == original[100, 175]).all() and (painted[10, 10] == original[10, 10]).all()


def test_edited_dataset_edits_only_listed_indices(tmp_path):
    from src.dataset import MetadataDataset
    from test_baseline import make_data
    data = MetadataDataset(make_data(tmp_path), 16, False, False)
    edited = EditedDataset(data, {0: ((16, 20, 10), 128)})
    assert not np.array_equal(edited[0][0].numpy(), data[0][0].numpy())
    assert np.array_equal(edited[1][0].numpy(), data[1][0].numpy())
    assert edited[0][1] == data[0][1]


def _prepare_cli(tmp_path, monkeypatch):
    """stub 모델·calibration·이미지(REAL 1장에만 흰 원)·고정 얼굴 상자로 CLI 설정 파일을 만든다."""
    import src.face_mask as face_mask
    from src.calibrate import main as calibrate
    from src.train import run_training
    from test_baseline import make_data

    metadata = make_data(tmp_path)
    for name, seed in (('test_1.png', 1), ('test_0.png', 2), ('test_unseen_0.png', 3)):
        array = _noise(seed=seed)
        Image.fromarray(_with_disc(array, 150, 100, 30) if name == 'test_1.png' else array).save(tmp_path/name)
    monkeypatch.setattr(face_mask, 'detect_face', lambda rgb, **_: (130, 80, 40, 40))
    config = dict(model=dict(encoder='stub', embedding_dim=8, image_size=16, freeze_encoder=True),
                  training=dict(batch_size=2, learning_rate=0.01, epochs=1, device='cpu'),
                  augmentation=dict(horizontal_flip=False, jpeg_aug=False),
                  data=dict(metadata_csv=str(metadata)))
    checkpoint = run_training(config, str(metadata), 1, tmp_path/'checkpoints')
    (tmp_path/'calibration.yaml').write_text(yaml.safe_dump(dict(
        checkpoint=str(checkpoint), device='cpu', output_dir=str(tmp_path/'calibration'),
        fit=dict(temperature_min=0.05, temperature_max=20.0, iterations=100), metrics=dict(ece_bins=10))))
    calibrate(['--config', str(tmp_path/'calibration.yaml')])
    settings = dict(SETTINGS)
    settings.update(calibration=str(tmp_path/'calibration/calibration.json'), device='cpu',
                    output_dir=str(tmp_path/'out'))
    (tmp_path/'face.yaml').write_text(yaml.safe_dump(settings))
    return face_mask, str(tmp_path/'face.yaml')


def test_face_mask_cli_reports_prevalence_shortcut_and_conditions(tmp_path, monkeypatch):
    face_mask, config_path = _prepare_cli(tmp_path, monkeypatch)
    report = face_mask.main(['--config', config_path])

    with (tmp_path/'out/detections.csv').open() as handle:
        discs = {r['image_id']: r['disc_r'] for r in csv.DictReader(handle)}
    assert {k for k, v in discs.items() if v} == {'test_1.png'}
    assert report['disc_prevalence']['real/test'] == dict(count=1, disc=1)
    assert report['disc_prevalence']['generated/test'] == dict(count=1, disc=0)
    assert report['shortcut_rule']['standard']['roc_auc'] == 1.0
    with (tmp_path/'out/predictions.csv').open() as handle:
        by_condition = {}
        for row in csv.DictReader(handle):
            by_condition.setdefault(row['condition'], set()).add(row['image_id'])
    assert by_condition['real_disc_gray'] == {'test_1.png'}
    assert by_condition['gen_white_face'] == by_condition['gen_gray_face'] == {'test_0.png', 'test_unseen_0.png'}
    assert report['conditions']['gen_white_face']['edited_count'] == 2
    assert report['model_by_real_disc']['standard/real_disc_false']['real_count'] == 0
    assert isinstance(report['dependence_evidence'], bool)
    gray = report['conditions']['real_disc_gray']
    assert gray['sets']['standard']['mean_score_shift']['generated'] == 0  # 미처리 표본은 원본 logit
    assert gray['sets']['standard']['mean_score_shift']['real'] == pytest.approx(gray['edited_mean_shift'])
    assert json.loads((tmp_path/'out/report.json').read_text()) == report


@pytest.mark.parametrize('offface_largest', [True, False])
def test_face_mask_cli_wires_calibrated_threshold_labels_and_both_controls(tmp_path, monkeypatch, offface_largest):
    """main() 연결 잠금: 전환은 calibration threshold·실제 label로, 판정은 주 조건을 두 대조 모두와 비교한다.
    확률을 threshold와 0.5 사이에 두어 0.5로 바꾸면 전환 수가 달라지고, REAL 전환(FN)은 label을 GEN으로 바꾸면
    세지 않게 된다. 미발동: 얼굴 밖 대조의 상승이 가장 크면 False(대조 하나를 빼면 True로 뒤집힘).
    발동: 흰 원 > 회색 원 > 얼굴 밖이고 전환 비율이 기준 이상이면 True(주 조건·기준·결과 연결이 틀리면 False)."""
    face_mask, config_path = _prepare_cli(tmp_path, monkeypatch)
    calibration = json.loads((tmp_path/'calibration/calibration.json').read_text())
    temperature, threshold = calibration['temperature'], 0.7  # stub 적합 threshold는 0.5일 수 있어 고정한다
    load_calibration = face_mask.load_calibration
    monkeypatch.setattr(face_mask, 'load_calibration',
                        lambda path: {**load_calibration(path), 'threshold_probability': threshold})
    middle = (threshold + 0.5) / 2  # 0.5 이상·threshold 미만: 0.5로 바꾸면 전환으로 세진다

    def logit(probability):
        return temperature * np.log(probability / (1 - probability))

    def fake_predict(model, data, indices, device, training):
        values = []
        for i in indices:
            label = (data.base if isinstance(data, face_mask.EditedDataset) else data).rows[i].label
            if not isinstance(data, face_mask.EditedDataset):
                values.append(logit(0.99 if label else 0.01))
                continue
            (x, _, _), fill = data.edits[i]
            if label:
                values.append(logit(0.49))  # REAL → FN
            elif x != 150:
                values.append(logit(0.999 if offface_largest else 0.02))
            elif fill == 255:
                values.append(logit(threshold + 0.01 if data.base.rows[i].image_id == 'test_0.png'
                                    else middle))
            else:
                values.append(logit(middle))
        return np.asarray(values), None
    monkeypatch.setattr(face_mask, 'predict_logits', fake_predict)
    report = face_mask.main(['--config', config_path])

    with (tmp_path/'out/predictions.csv').open() as handle:
        logits = {}
        for row in csv.DictReader(handle):
            logits.setdefault(row['condition'], {})[row['image_id']] = float(row['logit'])
    labels = {'test_1.png': 1, 'test_0.png': 0, 'test_unseen_0.png': 0}

    def probability(value):
        return 1 / (1 + np.exp(-value / temperature))
    for name, values in logits.items():
        if name == 'original':
            continue
        expected = sum((probability(logits['original'][k]) >= threshold) == (labels[k] == 1)
                       and (probability(v) >= threshold) != (labels[k] == 1) for k, v in values.items())
        assert report['conditions'][name]['edited_decision_flips'] == expected, name
    assert report['conditions']['real_disc_gray']['edited_decision_flips'] == 1
    assert report['conditions']['gen_white_face']['edited_decision_flips'] == 1
    assert report['conditions']['gen_gray_face']['edited_decision_flips'] == 0
    shifts = {name: report['conditions'][name]['edited_mean_shift']
              for name in ('gen_white_face', 'gen_gray_face', 'gen_white_offface')}
    if offface_largest:
        assert shifts['gen_gray_face'] < shifts['gen_white_face'] < shifts['gen_white_offface']
        assert report['dependence_evidence'] is False
    else:
        assert shifts['gen_white_offface'] < shifts['gen_gray_face'] < shifts['gen_white_face']
        assert report['dependence_evidence'] is True

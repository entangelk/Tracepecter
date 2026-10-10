"""P06-02b: 흰 원 검출·원 덧씌우기·진단 CLI가 사전 고정 규칙대로 동작하는지 고정한다."""
import csv
import json

import numpy as np
import yaml
from PIL import Image, ImageDraw

from src.face_mask import EditedDataset, detect_disc, off_face_disc, paint_disc

DETECTOR = dict(white_min=245, outside_max=235, min_edge_fraction=0.35, min_fill=0.97,
                radius_ratio=[0.015, 0.15], hough_param2=12)


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


def test_face_mask_cli_reports_prevalence_shortcut_and_conditions(tmp_path, monkeypatch):
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
    settings = yaml.safe_load(open('configs/face_mask_diagnostic.yaml'))
    settings.update(calibration=str(tmp_path/'calibration/calibration.json'), device='cpu',
                    output_dir=str(tmp_path/'out'))
    (tmp_path/'face.yaml').write_text(yaml.safe_dump(settings))
    report = face_mask.main(['--config', str(tmp_path/'face.yaml')])

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
    assert json.loads((tmp_path/'out/report.json').read_text()) == report

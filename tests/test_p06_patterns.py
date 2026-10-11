"""P06-04: 얼굴 상태 분류·오류 판정·Wilson 구간·한쪽 Fisher 검정·crop 얼굴 보존·집계를 고정한다."""
import csv
import hashlib
import json
import math

import pytest
import yaml
from PIL import Image

import scripts.p06_patterns as patterns
from scripts.p06_patterns import (crop_keeps_face, face_state, fisher_greater, is_error, is_low_confidence, summarize,
                                  wilson)


def test_face_state_uses_disc_only_for_real():
    """REAL 흰 원은 'disc'가 얼굴 검출보다 우선한다. GEN의 원 검출은 오검출이므로 무시한다."""
    assert face_state(1, True, (0, 0, 5, 5)) == 'disc'
    assert face_state(1, False, (0, 0, 5, 5)) == 'visible'
    assert face_state(1, False, None) == 'none'
    assert face_state(0, True, None) == 'none'
    assert face_state(0, True, (0, 0, 5, 5)) == 'visible'


def test_is_error_at_threshold_boundary():
    """threshold와 같은 확률은 REAL 판정(P06-01 정의): REAL은 정답, GEN은 FP."""
    assert is_error(1, 0.7, 0.7) is False and is_error(0, 0.7, 0.7) is True
    assert is_error(1, 0.69, 0.7) is True and is_error(0, 0.69, 0.7) is False


def test_low_confidence_excludes_errors_and_uses_inclusive_score_band():
    assert is_low_confidence(1, 0.8, 0.7) is True
    assert is_low_confidence(0, 0.6, 0.7) is True
    assert is_low_confidence(0, 0.8, 0.7) is False     # 오분류(FP)는 low_confidence가 아니다
    assert is_low_confidence(1, 0.9, 0.7) is True and is_low_confidence(1, 0.9001, 0.7) is False
    assert is_low_confidence(0, 0.1, 0.7) is True and is_low_confidence(0, 0.0999, 0.7) is False


def test_wilson_matches_known_values():
    assert wilson(40, 40) == pytest.approx([0.9124, 1.0], abs=1e-4)
    assert wilson(0, 10) == pytest.approx([0.0, 0.2775], abs=1e-4)
    assert wilson(0, 0) is None


def test_fisher_greater_is_hypergeometric_upper_tail():
    """3/3 대 0/3: 위쪽 꼬리는 C(3,3)C(3,0)/C(6,3) = 1/20. 반대 방향(0/3 대 3/3)은 1이다."""
    assert fisher_greater(3, 3, 0, 3) == pytest.approx(1 / 20)
    assert fisher_greater(0, 3, 3, 3) == pytest.approx(1.0)
    expected = sum(math.comb(5, k) * math.comb(15, 10 - k) for k in range(4, 6)) / math.comb(20, 10)
    assert fisher_greater(4, 10, 1, 10) == pytest.approx(expected)


def test_crop_keeps_face_checks_face_centre_inside_centre_square():
    """세로 832×1216은 crop 범위가 y ∈ [192, 1024)다(src/failure_analysis.py와 같은 정수 기하, 반열린 구간)."""
    assert crop_keeps_face((400, 150, 40, 80), (832, 1216)) is False    # 중심 y 190
    assert crop_keeps_face((400, 100, 40, 80), (832, 1216)) is False    # 중심 y 140
    assert crop_keeps_face((400, 152, 40, 80), (832, 1216)) is True     # 중심 y 192(경계)
    assert crop_keeps_face((10, 10, 20, 20), (500, 500)) is True        # 정사각 원본은 잘리지 않음
    assert crop_keeps_face((400, 984, 40, 79), (832, 1216)) is True     # 중심 y 1023.5
    assert crop_keeps_face((400, 984, 40, 80), (832, 1216)) is False    # 중심 y 1024(아래 끝, 배타)
    assert crop_keeps_face((40, 40, 20, 20.4), (100, 201)) is True      # top = 101 // 2 = 50, 중심 y 50.2


def _row(label, state, error, generator='g', category='상의', aspect=1.0, crop_keeps=None, crop_error=None,
         low_confidence=False):
    return dict(label=label, face_state=state, error=error, low_confidence=low_confidence,
                generator=generator if not label else '',
                category=category, aspect=aspect, crop_keeps_face=crop_keeps, center_square_error=crop_error)


def test_summarize_counts_by_face_state_and_tests_concentration():
    rows = ([_row(0, 'none', True)] * 3 + [_row(0, 'none', False)] + [_row(0, 'visible', False, crop_keeps=False,
                                                                           crop_error=True)] * 4
            + [_row(1, 'disc', False)] * 2 + [_row(1, 'none', True)])
    report = summarize(rows)
    assert report['face_state']['generated/none'] == dict(n=4, errors=3, rate=0.75, ci95=wilson(3, 4), low_confidence=0)
    assert report['face_state']['generated/all']['n'] == 8 and report['face_state']['real/visible']['n'] == 0
    test = report['concentration_tests']['generated: none > visible']
    assert test['p_one_sided'] == pytest.approx(fisher_greater(3, 4, 0, 4), rel=1e-2)
    assert report['generator_by_face']['g']['none']['errors'] == 3
    assert report['center_crop']['gen_face_removed_by_crop'] == dict(n=4, errors_original=0, errors_center_square=4,
                                                                     originally_correct=4, new_errors=4)
    assert report['center_crop']['gen_face_kept_by_crop']['n'] == 0


def test_summarize_real_tests_low_confidence_and_crop_new_errors():
    """REAL 검정은 none을 a로 둔다(방향 고정). low_confidence는 상태별로 센다. crop 새 오류는 원래 정답이던 표본만 센다."""
    rows = ([_row(1, 'none', True)] * 2 + [_row(1, 'none', False, low_confidence=True)] + [_row(1, 'disc', False)] * 3
            + [_row(0, 'none', True, crop_error=True), _row(0, 'none', False, crop_error=True),
               _row(0, 'none', False, crop_error=False, low_confidence=True)])
    report = summarize(rows)
    test = report['concentration_tests']['real: none > disc']
    assert (test['a']['n'], test['a']['errors'], test['b']['n']) == (3, 2, 3)
    assert test['p_one_sided'] == pytest.approx(fisher_greater(2, 3, 0, 3), rel=1e-2)
    assert report['face_state']['real/none']['low_confidence'] == 1
    assert report['face_state']['generated/none']['low_confidence'] == 1
    assert report['center_crop']['gen_no_face_before_crop'] == dict(
        n=3, errors_original=1, errors_center_square=2, originally_correct=2, new_errors=1)


def _main_fixture(tmp_path, monkeypatch, sha=None):
    rows = [('r_train', 1, 'train', ''), ('g_train', 0, 'train', 'g'), ('r_test', 1, 'test', ''),
            ('r_disc', 1, 'test', ''), ('g_test', 0, 'test', 'g'), ('g_low', 0, 'test_unseen', 'u')]
    (tmp_path/'images').mkdir()
    with (tmp_path/'metadata.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'path', 'label', 'category', 'split', 'generator'])
        for image_id, label, split, generator in rows:
            Image.new('RGB', (20, 30)).save(tmp_path/'images'/f'{image_id}.png')
            writer.writerow([image_id, f'images/{image_id}.png', label, '상의', split, generator])
    probabilities = dict(r_test=0.6, r_disc=0.95, g_test=0.6, g_low=0.2)  # threshold 0.5: g_test는 FP
    with (tmp_path/'predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'condition', 'logit'])
        for image_id, p in probabilities.items():
            writer.writerow([image_id, 'original', math.log(p / (1 - p))])
            writer.writerow([image_id, 'center_square', math.log(p / (1 - p))])
    (tmp_path/'discs.csv').write_text('image_id,disc_r\nr_disc,10\nr_train,10\ng_test,10\n')
    (tmp_path/'yunet.onnx').write_bytes(b'stub')
    (tmp_path/'face.yaml').write_text(yaml.safe_dump(dict(face_detector=dict(
        model=str(tmp_path/'yunet.onnx'), model_sha256=sha or hashlib.sha256(b'stub').hexdigest()))))
    for name, value in dict(METADATA=tmp_path/'metadata.csv', PREDICTIONS=tmp_path/'predictions.csv',
                            DISCS=tmp_path/'discs.csv', FACE_CONFIG=tmp_path/'face.yaml', IMAGE_ROOT=tmp_path/'images',
                            OUTPUT=tmp_path/'out').items():
        monkeypatch.setattr(patterns, name, value)
    monkeypatch.setattr(patterns, 'load_calibration', lambda path: dict(temperature=1.0, threshold_probability=0.5))
    monkeypatch.setattr(patterns, 'detect_face', lambda rgb, **_: (5, 5, 4, 4))


def test_main_writes_features_and_counts_train_faces_separately(tmp_path, monkeypatch):
    _main_fixture(tmp_path, monkeypatch)
    report = patterns.main()
    with (tmp_path/'out/features.csv').open() as handle:
        features = {r['image_id']: r for r in csv.DictReader(handle)}
    assert set(features) == {'r_test', 'r_disc', 'g_test', 'g_low'}  # 오류 집계는 평가 split만
    assert features['g_test']['error'] == 'True' and features['g_test']['low_confidence'] == 'False'
    assert features['r_test']['low_confidence'] == 'True' and features['g_low']['low_confidence'] == 'True'
    assert features['r_disc']['face_state'] == 'disc' and features['g_test']['face_state'] == 'visible'
    assert report['train_face_state'] == dict(generated=dict(visible=1), real=dict(disc=1))
    assert json.loads((tmp_path/'out/patterns.json').read_text()) == report


def test_main_rejects_wrong_face_model_hash(tmp_path, monkeypatch):
    _main_fixture(tmp_path, monkeypatch, sha='0' * 64)
    with pytest.raises(ValueError, match='sha256'):
        patterns.main()

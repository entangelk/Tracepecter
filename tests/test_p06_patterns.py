"""P06-04: 얼굴 상태 분류·오류 판정·Wilson 구간·한쪽 Fisher 검정·crop 얼굴 보존·집계를 고정한다."""
import math

import pytest

from scripts.p06_patterns import crop_keeps_face, face_state, fisher_greater, is_error, summarize, wilson


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
    """세로 832×1216은 위아래 192px씩 잘린다: 얼굴 중심 y가 192 미만이면 잘린다(경계 포함 유지)."""
    assert crop_keeps_face((400, 150, 40, 80), (832, 1216)) is False    # 중심 y 190
    assert crop_keeps_face((400, 100, 40, 80), (832, 1216)) is False    # 중심 y 140
    assert crop_keeps_face((400, 152, 40, 80), (832, 1216)) is True     # 중심 y 192(경계)
    assert crop_keeps_face((10, 10, 20, 20), (500, 500)) is True        # 정사각 원본은 잘리지 않음


def _row(label, state, error, generator='g', category='상의', aspect=1.0, crop_keeps=None, crop_error=None):
    return dict(label=label, face_state=state, error=error, low_confidence=False, generator=generator if not label else '',
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
    assert report['center_crop']['gen_face_removed_by_crop'] == dict(n=4, errors_original=0, errors_center_square=4)
    assert report['center_crop']['gen_face_kept_by_crop']['n'] == 0

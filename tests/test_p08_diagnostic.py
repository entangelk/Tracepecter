"""P08-06: 느슨한 통과와 정상 경계의 과도한 거부를 함께 잠근다."""
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pytest
import yaml

from src.diagnostic import (adoption, concentration, intervention, newcombe, wilson)


@pytest.fixture
def settings():
    return yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())


def test_wilson_and_newcombe_keep_zero_events_uncertainty():
    """0건을 위험 0으로 확정하지 않고, 대칭·정상 양끝을 허용한다."""
    z = NormalDist().inv_cdf(0.975)
    assert wilson(0, 80) == pytest.approx((0, z*z/(80+z*z)))
    assert wilson(80, 80) == pytest.approx((80/(80+z*z), 1))
    lo, hi = newcombe(2, 50, 10, 50)
    reverse = newcombe(10, 50, 2, 50)
    assert reverse == pytest.approx((-hi, -lo))
    l1, u1 = wilson(2, 50); l2, u2 = wilson(10, 50)
    assert (lo, hi) == pytest.approx((-.16-np.hypot(.04-l1, u2-.2),
                                     -.16+np.hypot(u1-.04, .2-l2)))


def test_intervention_bootstrap_is_paired_absolute_with_replacement(settings):
    """절댓값 상쇄·무복원추출을 잡고 양방향 이동·경계 포함을 허용한다."""
    ids = [f'g{i:03}' for i in range(100)]
    ref = {i: 0.1 for i in ids}
    var = {i: .1 + (-1 if n % 2 else 1)*.02 for n, i in enumerate(ids)}
    result = intervention(ids[::-1], ref, var, {i: 0 for i in ids}, .5, settings)
    assert result['status'] == 'pass'
    assert result['mean_signed_shift'] == pytest.approx(0)
    assert result['mean_absolute_shift'] == pytest.approx(2)
    # 동일 표본·seed의 실제 PCG64 추출을 독립 계산한다.
    var = {i: .1 + n/1000 for n, i in enumerate(ids)}
    result = intervention(ids, ref, var, {i: 0 for i in ids}, .5, settings)
    delta = np.arange(100)/10
    indices = np.random.Generator(np.random.PCG64(settings['seed'])).integers(0, 100, size=(20000, 100))
    expected = np.percentile(delta[indices].mean(axis=1), [2.5, 97.5], method='linear')
    assert result['absolute_shift_ci'] == pytest.approx(expected)
    assert expected[0] != expected[1]
    constant = {i: .15 for i in ids}
    boundary = intervention(ids, ref, constant, {i: 0 for i in ids}, .5, settings)
    settings['intervention_rules']['score']['max_upper'] = boundary['absolute_shift_ci'][1]
    assert intervention(ids, ref, constant, {i: 0 for i in ids}, .5, settings)['status'] == 'pass'
    settings['intervention_rules']['score']['max_upper'] -= 1e-8
    assert intervention(ids, ref, constant, {i: 0 for i in ids}, .5, settings)['status'] == 'fail'


def test_error_gate_uses_all_images_and_does_not_cancel_reverse_flips(settings):
    """역전환 상쇄·맞은 표본만 분모 사용을 잡고 고정 threshold의 >=를 허용한다."""
    ids = [str(i) for i in range(100)]
    ref = {i: .2 for i in ids}; var = ref.copy(); labels = {i: 0 for i in ids}
    ref['0'], var['0'] = .49, .5
    ref['1'], var['1'] = .5, .49
    result = intervention(ids, ref, var, labels, .5, settings)
    assert result['correct_to_wrong'] == result['wrong_to_correct'] == 1
    assert result['error_risk'] == .01
    assert result['error_ci'] == pytest.approx(wilson(1, 100))
    assert result['status'] == 'fail'  # Wilson 상한 >5%
    assert intervention(ids, ref, ref, labels, .5, settings)['status'] == 'pass'


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'nan', 'infinite', 'insufficient'])
def test_invalid_interventions_are_indeterminate_not_partial_pass(settings, damage):
    ids = [str(i) for i in range(80)]
    ref = {i: .2 for i in ids}; var = ref.copy(); labels = {i: 0 for i in ids}
    if damage == 'missing': del var['0']
    if damage == 'duplicate': ids[-1] = ids[0]
    if damage == 'nan': var['0'] = float('nan')
    if damage == 'infinite': var['0'] = float('inf')
    if damage == 'insufficient': ids = ids[:79]
    assert intervention(ids, ref, var, labels, .5, settings)['status'] == 'indeterminate'


def test_concentration_counts_all_states_and_generators(settings):
    """검출 유무 대체·generator 합치기를 잡고 얼굴 없음·부분 누락 우선순위를 허용한다."""
    annotations = {}; probabilities = {}; generators = {}
    for state, counts in [('anonymized', (1, 0)), ('no_visible_face', (0, 0)), ('missed_visible_face', (2, 1))]:
        for n in range(200):
            image_id = f'{state}{n}'
            annotations[image_id] = counts
            probabilities[image_id] = .2
            generators[image_id] = 'g1' if n % 2 else 'g2'
    result = concentration(annotations, probabilities, generators, .5, settings)
    assert result['status'] == 'pass'
    assert all(s['count'] == 200 and s['false_positives'] == 0 for s in result['states'].values())
    assert result['generators']['g1']['missed_visible_face']['count'] == 100
    for i in probabilities:
        if i.startswith('missed'): probabilities[i] = .5
    assert concentration(annotations, probabilities, generators, .5, settings)['status'] == 'fail'
    annotations = {i: c for i, c in annotations.items() if not i.startswith('missed')}
    assert concentration(annotations, probabilities, generators, .5, settings)['status'] == 'indeterminate'
    annotations['bad'] = (0, 1)
    assert concentration(annotations, probabilities, generators, .5, settings)['status'] == 'indeterminate'


def test_adoption_requires_both_aucs_and_every_cue_gate(settings):
    """AUC만으로 채택하는 완화를 잡고 정확한 AUC 경계·전 관문 통과를 허용한다."""
    gates = {k: {'status': 'pass'} for k in settings['adoption']['required_cue_gates']}
    assert adoption(.90, .80, gates, settings)['adopt']
    for a, b in [(.8999, .8), (.9, .7999), (None, .8), (float('nan'), .8)]:
        assert not adoption(a, b, gates, settings)['adopt']
    for name in gates:
        for status in ('fail', 'indeterminate'):
            changed = dict(gates, **{name: {'status': status}})
            assert not adoption(.99, .99, changed, settings)['adopt']
    assert not adoption(.99, .99, {}, settings)['adopt']


def test_concentration_minimum_interval_boundaries_and_bad_predictions(settings):
    """최소 표본·닫힌 구간을 잠그고 NaN·누락을 부분 통과로 처리하지 않는다."""
    annotations = {f'{s}{n}': counts for s,counts in [('a',(1,0)),('b',(0,0)),('c',(1,1))] for n in range(20)}
    p = {i:.1 for i in annotations}; g = {i:'g' for i in annotations}
    settings['face_concentration']['max_absolute_rate_difference'] = newcombe(0,20,0,20)[1]
    assert concentration(annotations,p,g,.5,settings)['status'] == 'pass'
    settings['face_concentration']['max_absolute_rate_difference'] -= 1e-8
    assert concentration(annotations,p,g,.5,settings)['status'] == 'fail'
    del annotations['a0']
    assert concentration(annotations,p,g,.5,settings)['status'] == 'indeterminate'
    annotations['a0'] = (1,0)
    p['a0'] = float('nan')
    assert concentration(annotations,p,g,.5,settings)['status'] == 'indeterminate'
    del p['a0']
    assert concentration(annotations,p,g,.5,settings)['status'] == 'indeterminate'

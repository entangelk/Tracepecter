"""P08-01: 사전 크기 실패를 보존하고 미완료 소유자 확인을 최종 통과로 만들지 않는다."""
import csv
import json

import numpy as np
import pytest

from scripts import p08_measure as measure


def test_size_match_preserves_failure_and_reports_owner_selected_diameter():
    """과소 원을 통과시키지 않으며, 소유자 선택 k=1.2도 사전 분포 통과로 바꾸지 않는다."""
    original = measure.size_match([0.07, 0.09, 0.11], [0.11, 0.14, 0.18], 0.15, 1.0, 1.6)
    selected = measure.size_match([0.07, 0.09, 0.11], [0.11, 0.14, 0.18], 0.15, 1.0, 1.6, k=1.2)
    assert original['passed'] is False and original['k'] < 1.0
    assert selected['k'] == 1.2 and selected['k_in_range'] is True and selected['passed'] is False
    assert measure.size_match([0.1, 0.12, 0.14], [0.1, 0.12, 0.14], 0.15, 1.0, 1.6)['passed'] is True


def test_recall_gate_reports_wilson_and_rejects_low_recall_or_small_sample():
    """높은 재현율도 양성 부족이면 실패하며, 80/100은 구간 하한과 무관하게 점추정으로 통과한다."""
    result = measure.recall_gate([1] * 100, [True] * 80 + [False] * 20, 0.8, 80)
    assert result['passed'] is True
    assert result['ci95'] == pytest.approx([0.7112, 0.8666], abs=1e-4)
    assert measure.recall_gate([1] * 100, [True] * 79 + [False] * 21, 0.8, 80)['passed'] is False
    assert measure.recall_gate([1] * 79, [True] * 79, 0.8, 80)['passed'] is False
    assert measure.recall_gate([], [], 0.8, 80)['ci95'] is None


def test_owner_review_requires_every_selected_id_and_keeps_test_reporting_only():
    """일부 확인을 최종으로 오인하지 않고, 필요한 확인만 전부 끝나면 나머지 1차 표시를 유지한다."""
    rows = [dict(image_id='a', agent_face_visible='1'), dict(image_id='b', agent_face_visible='1')]
    partial = measure.recall_summary(rows, [True, True], {'a': 1}, ['a', 'b'], 0.8, 2, True)
    assert partial['passed'] is None and partial['labels'] == 'owner_partial'
    assert partial['owner_review_missing'] == ['b'] and partial['point_gate_passed'] is True
    complete = measure.recall_summary(rows, [True, True], {'a': 1}, ['a'], 0.8, 2, True)
    assert complete['passed'] is True and complete['labels'] == 'owner_final'
    corrected = measure.recall_summary(rows, [True, True], {'a': 0}, ['a'], 0.8, 2, True)
    assert corrected['passed'] is False and corrected['positives'] == 1
    test = measure.recall_summary(rows, [True, True], {}, [], 0.8, 80, False)
    assert test['passed'] is None and test['gate_applies'] is False
    test_partial = measure.recall_summary(rows, [True, True], {'a': 1}, ['a', 'b'], 0.8, 80, False)
    assert test_partial['labels'] == 'owner_partial' and test_partial['owner_review_missing'] == ['b']
    test_final = measure.recall_summary(rows, [True, True], {'a': 1, 'b': 0}, ['a', 'b'], 0.8, 80, False)
    assert test_final['labels'] == 'owner_final' and test_final['passed'] is None
    assert test_final['positives'] == 1 and test_final['gate_applies'] is False


def test_owner_labels_reject_duplicates_invalid_values_and_unknown_ids(tmp_path):
    path = tmp_path / 'owner.csv'
    assert measure.read_owner_labels(path, {'a'}) == {}
    for body in ('a,1\na,0\n', 'a,\n', 'a,2\n', 'b,1\n'):
        path.write_text('image_id,owner_face_visible\n' + body)
        with pytest.raises(ValueError):
            measure.read_owner_labels(path, {'a'})
    path.write_text('image_id,owner_face_visible\na,0\n')
    assert measure.read_owner_labels(path, {'a'}) == {'a': 0}


@pytest.mark.parametrize('pool, suffix', [('train_gen', ''), ('test_gen_sd35', '_sd35')])
def test_owner_stage_builds_blind_page_and_blank_export_template(tmp_path, monkeypatch, pool, suffix):
    """브라우저 자료에는 정답·검출·선정 사유를 넣지 않고 원본과 동일 ID로 소유자 CSV를 만든다."""
    output = tmp_path / 'measure'
    output.mkdir()
    (output / 'recall_labels_agent.csv').write_text(
        f'pool,image_id,agent_face_visible\n{pool},gen_1,1\n')
    (output / 'recall_detections.csv').write_text(f'pool,image_id,yunet_detected\n{pool},gen_1,0\n')
    owner = output / 'recall_labels_owner.csv'
    owner.write_text('image_id,owner_face_visible\nprevious,1\n')
    monkeypatch.setattr(measure, 'load_rgb', lambda row: np.zeros((20, 20, 3), dtype=np.uint8))
    settings = {'recall_gate': {'seed': 1, 'owner_random_fraction': .2}}
    measure.owner_stage(settings, {'gen_1': {}}, output, tmp_path / 'review', 0, pool=pool)
    html = (tmp_path / 'review/index.html').read_text()
    assert 'data:image/jpeg;base64,' in html and 'gen_1' in html
    assert 'disagreement' not in html and 'yunet_detected' not in html and 'agent_face_visible' not in html
    assert f'recall_labels_owner{suffix}.csv' in html
    with (output / f'recall_labels_owner_template{suffix}.csv').open() as handle:
        assert list(csv.DictReader(handle)) == [{'image_id': 'gen_1', 'owner_face_visible': ''}]
    assert owner.read_text() == 'image_id,owner_face_visible\nprevious,1\n'
    if suffix:
        assert not (output / f'recall_labels_owner{suffix}.csv').exists()


def test_owner_selection_includes_all_disagreements_and_seeded_random_agreements():
    """불일치를 빠뜨리지 않고, 나머지는 전수가 아닌 사전 seed의 20%만 뽑는다."""
    rows = [dict(image_id=str(i), agent_face_visible='1') for i in range(12)]
    selected = measure.owner_check_rows(rows, [False] * 2 + [True] * 10,
                                        {'seed': 1, 'owner_random_fraction': .2})
    assert selected == [dict(image_id='0', reason='disagreement'),
                        dict(image_id='1', reason='disagreement'),
                        dict(image_id='4', reason='random'), dict(image_id='3', reason='random')]


@pytest.mark.parametrize('selected_update, rejected', [
    ({'diameter_per_face': 1.2}, False),
    ({'diameter_per_face': 1.0}, False),
    ({'diameter_per_face': 1.6}, False),
    ({'face_detector': {'model_sha256': 'wrong'}}, True),
    ({'shape': 'ellipse'}, True),
    ({'fill': [128, 128, 128]}, True),
    ({'diameter_per_face': .99}, True),
    ({'diameter_per_face': 1.61}, True),
])
def test_measure_report_keeps_original_failure_and_waits_for_owner(tmp_path, monkeypatch, selected_update, rejected):
    """선택 규격 불일치는 거부하되 지름 경계 1.0/1.6은 허용하고, 원래 실패·잠정 관문을 보존한다."""
    (tmp_path / 'real_disc_candidates.csv').write_text(
        'candidate_id,image_id,cx,cy,axis_a,axis_b,major,minor,angle\nd,real,10,10,10,10,10,10,0\n')
    (tmp_path / 'real_disc_review.csv').write_text('candidate_id,confirmed\nd,1\n')
    (tmp_path / 'recall_labels_agent.csv').write_text(
        'pool,image_id,agent_face_visible\ntrain_gen,gen,1\ntest_gen_sd35,sd35,1\ntest_gen_sd35,sd35_2,1\n')
    config = tmp_path / 'config.yaml'
    config.write_text('fixed inputs')
    monkeypatch.setattr(measure, 'CONFIG', str(config))
    monkeypatch.setattr(measure, 'METADATA', str(config))
    monkeypatch.setattr(measure, 'load_rgb', lambda row: np.zeros((100, 100, 3), dtype=np.uint8))
    monkeypatch.setattr(measure, 'detect_face', lambda rgb, **kw: (0, 0, 20, 20))
    monkeypatch.setattr(measure, 'disc_edge_width', lambda *args: 2.0)
    diameter_calls = []
    def paint(rgb, face, k, ellipse, sigma):
        diameter_calls.append(k)
        return rgb, {}
    monkeypatch.setattr(measure, 'paint_synthetic', paint)
    settings = dict(face_detector={'model_sha256': 'abc'}, real_discs={'seed': 1},
                    size_match={'tolerance': .15, 'k_min': 1., 'k_max': 1.6},
                    edge_match={'angles': 72, 'sigma_grid': [.5], 'tolerance_px': 1},
                    recall_gate={'seed': 1, 'owner_random_fraction': 1., 'min_recall': .8, 'min_positives': 1},
                    ellipse_ratio=.85, ellipse_fraction_gate=.2,
                    selected_anonymization={'diameter_per_face': 1.2, 'face_detector': {'model_sha256': 'abc'},
                                            'shape': 'circle', 'fill': [255, 255, 255]})
    meta = {'real': {'label': '1', 'split': 'train'}, 'gen': {'label': '0', 'split': 'train'},
            'sd35': {'label': '0', 'split': 'test_unseen'}, 'sd35_2': {'label': '0', 'split': 'test_unseen'}}
    settings['selected_anonymization'].update(selected_update)
    if rejected:
        with pytest.raises(ValueError, match='selected anonymization'):
            measure.measure_stage(settings, meta, tmp_path, tmp_path, 0)
        assert diameter_calls == [] and not (tmp_path / 'report.json').exists()
        return
    measure.measure_stage(settings, meta, tmp_path, tmp_path, 0)
    report = json.loads((tmp_path / 'report.json').read_text())
    assert diameter_calls == [selected_update['diameter_per_face']]
    assert report['synthetic']['size_match']['k'] == .5
    assert report['synthetic']['size_match']['passed'] is False
    assert report['synthetic']['selected_size']['passed'] is False
    assert report['recall']['train_gen']['passed'] is None
    assert report['recall']['train_gen']['owner_review_missing'] == ['gen']
    assert report['recall']['test_gen_sd35']['gate_applies'] is False
    assert report['recall']['test_gen_sd35']['labels'] == 'agent_only'
    assert report['recall']['test_gen_sd35']['owner_review_missing'] == ['sd35', 'sd35_2']
    assert report['owner_check'] == 1
    (tmp_path / 'recall_labels_owner.csv').write_text('image_id,owner_face_visible\ngen,1\n')
    measure.measure_stage(settings, meta, tmp_path, tmp_path, 0)
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['recall']['train_gen']['passed'] is True
    (tmp_path / 'recall_labels_owner_sd35.csv').write_text(
        'image_id,owner_face_visible\nsd35,0\nsd35_2,1\n')
    measure.measure_stage(settings, meta, tmp_path, tmp_path, 0)
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['recall']['train_gen']['passed'] is True
    sd35 = report['recall']['test_gen_sd35']
    assert sd35['labels'] == 'owner_final' and sd35['owner_review_missing'] == []
    assert sd35['positives'] == 1 and sd35['passed'] is None and sd35['gate_applies'] is False

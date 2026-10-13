"""P08 보조 크기: 의복 rect 합집합과 화면에 보이는 사람 높이를 구별한다."""
import csv
import json
import zipfile

import numpy as np
import pytest
import yaml

from scripts import p08_person_size as person


def test_rect_height_unions_every_part_without_summing_overlap_or_clipping():
    """한 부위만 쓰거나 겹침을 합산하지 않으며, 원 좌표의 음수 시작점도 보존한다."""
    data = {'데이터셋 정보': {'데이터셋 상세설명': {'렉트좌표': {
        '상의': [{'Y좌표': -5, '가로': 10, '세로': 40}],
        '하의': [{'Y좌표': 20, '가로': 10, '세로': 60}], '아우터': [{}],
    }}}}
    assert person.rect_union_height(data) == 85
    assert person.rect_union_height({'데이터셋 정보': {'데이터셋 상세설명': {
        '렉트좌표': {'원피스': [{'Y좌표': 10, '가로': 20, '세로': 30}]}}}}) == 30


def test_missing_or_degenerate_rect_is_not_silently_measured():
    """없는 rect를 사람 전체 높이로 대체하지 않고, 정상 단일 rect는 위 테스트에서 허용한다."""
    with pytest.raises(ValueError, match='rect'):
        person.rect_union_height({})
    with pytest.raises(ValueError, match='rect'):
        person.rect_union_height({'데이터셋 정보': {'데이터셋 상세설명': {
            '렉트좌표': {'상의': [{'Y좌표': 10, '가로': 0, '세로': 20}]}}}})


def test_manual_height_allows_clipped_frame_but_rejects_invalid_extents():
    """프레임 경계 0/1은 허용하되 역전·범위 밖·NaN은 분모로 쓰지 않는다."""
    assert person.manual_height(0, 1, 832) == 832
    assert person.manual_height(.1, .9, 1000) == pytest.approx(800)
    for top, bottom in [(-.1, .9), (.1, 1.1), (.5, .5), (.9, .1), (float('nan'), 1)]:
        with pytest.raises(ValueError, match='extent'):
            person.manual_height(top, bottom, 832)


def test_sample_uses_owner_labels_and_only_detected_train_faces():
    """검출 없는 얼굴·sd35·소유자 음성은 제외하고, 정상 검출 양성은 seed 순서로 유지한다."""
    rows = [dict(pool='train_gen', image_id=str(i), agent_face_visible='1') for i in range(55)]
    rows.append(dict(pool='test_gen_sd35', image_id='sd35', agent_face_visible='1'))
    detected = {r['image_id']: True for r in rows}
    detected['0'] = False
    selected = person.gen_sample(rows, detected, {'1': 0}, 42)
    assert len(selected) == 50 and len(set(selected)) == 50
    assert not {'0', '1', 'sd35'} & set(selected)
    assert selected == person.gen_sample(rows, detected, {'1': 0}, 42)
    with pytest.raises(ValueError, match='50'):
        person.gen_sample(rows[:10], detected, {}, 42)


def test_report_uses_manual_height_and_selected_k_without_changing_main_gate(tmp_path, monkeypatch):
    """원 지름은 선택 k를 쓰며 의복/사람 분모를 구분하고, 원래 크기 관문 실패는 보존한다."""
    monkeypatch.chdir(tmp_path)
    output = tmp_path / 'measure'
    output.mkdir()
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'data').mkdir()
    model = tmp_path / 'detector.onnx'
    model.write_bytes(b'fixed detector')
    face = dict(model=str(model), model_sha256=person.file_hash(model))
    (tmp_path / 'configs/anonymize.yaml').write_text(yaml.safe_dump(dict(
        face_detector=face, diameter_per_face=1.2)))
    (tmp_path / 'configs/anonymize_measure.yaml').write_text(yaml.safe_dump(dict(
        output_dir=str(output), face_detector=face, real_discs={'seed': 42})))
    rows = [dict(pool='train_gen', image_id=f'gen_{i}', agent_face_visible=1) for i in range(50)]
    person.write_csv(output / 'recall_labels_agent.csv', rows)
    person.write_csv(output / 'recall_detections.csv', [dict(image_id=r['image_id'], yunet_detected=1) for r in rows])
    (output / 'recall_labels_owner.csv').write_text('image_id,owner_face_visible\n')
    sample = person.gen_sample(rows, {r['image_id']: True for r in rows}, {}, 42)
    person.write_csv(output / 'person_sample_gen.csv', [dict(image_id=i) for i in sample])
    person.write_csv(output / 'person_height_gen.csv', [dict(image_id=i, top_fraction=.1, bottom_fraction=.9) for i in sample])
    person.write_csv(output / 'real_disc_candidates.csv', [dict(candidate_id='disc', image_id='real', major=10)])
    person.write_csv(output / 'real_disc_review.csv', [dict(candidate_id='disc', confirmed=1)])
    person.write_csv(tmp_path / 'data/metadata.csv', [dict(image_id=i, style='style') for i in sample + ['real']])
    archive = tmp_path / 'labels.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('style/real.json', json.dumps({'데이터셋 정보': {'데이터셋 상세설명': {
            '렉트좌표': {'상의': [{'Y좌표': 10, '가로': 20, '세로': 50}]}}}}))
    original_report = '{"synthetic":{"size_match":{"passed":false}}}\n'
    (output / 'report.json').write_text(original_report)
    monkeypatch.setattr(person.measure, 'load_rgb', lambda row: np.zeros((100, 80, 3), dtype=np.uint8))
    monkeypatch.setattr(person.measure, 'detect_face', lambda *args, **kwargs: (0, 0, 10, 20))
    person.run(archive)
    report = json.loads((output / 'person_size_report.json').read_text())
    assert report['real']['ratio_quartiles'] == pytest.approx([.2] * 3)
    assert report['gen']['ratio_quartiles'] == pytest.approx([.3] * 3)
    assert report['gen']['n'] == 50 and report['gen']['frame_clipped'] == 0
    assert report['gate_applies'] is False and report['selected_k'] == 1.2
    assert b'\r' not in (output / 'person_size_gen.csv').read_bytes()
    assert (output / 'report.json').read_text() == original_report
    person.write_csv(output / 'person_height_gen.csv', [dict(image_id=sample[0], top_fraction=0, bottom_fraction=1)] * 50)
    with pytest.raises(ValueError, match='IDs'):
        person.run(archive)

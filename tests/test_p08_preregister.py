"""P08-03: 사전등록의 lineage·불변성을 잠그고 정상 재생성·빈 검출을 허용한다."""
import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.p08_preregister import prepare


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def registration(tmp_path):
    config = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    for key in config['inputs']:
        config['inputs'][key] = str(tmp_path / (key+'.dat'))
    paths = {k: Path(v) for k, v in config['inputs'].items()}
    spec = yaml.safe_load(Path('configs/anonymize.yaml').read_text())
    paths['anonymization'].write_text(yaml.safe_dump(spec))
    parameters = {k:v for k,v in spec['face_detector'].items() if k not in ('model', 'model_sha256')}
    digest = hashlib.sha256(json.dumps(parameters, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    metadata = [dict(image_id='r', label='1', split='train', generator=''),
                dict(image_id='g1', label='0', split='test', generator='g'),
                dict(image_id='g2', label='0', split='test_unseen', generator='g')]
    write_csv(paths['metadata'], metadata)
    write_csv(paths['face_cache'], [dict(image_id=r['image_id'], detector_sha256=spec['face_detector']['model_sha256'],
                                        parameters_sha256=digest, boxes='[[1,2,3,4]]' if r['image_id']=='g1' else '[]') for r in metadata])
    write_csv(paths['real_candidates'], [dict(candidate_id='c', image_id='r', width='100', cx='50', cy='20', major='10', minor='9', angle='0')])
    write_csv(paths['real_review'], [dict(candidate_id='c', image_id='r', confirmed='1')])
    paths['measurement'].write_text(json.dumps(dict(synthetic=dict(selected_size=dict(synthetic_quartiles=[0.1,0.2,0.3])))))
    paths['baseline_calibration'].write_text('{}')
    config['output_dir'] = str(tmp_path / 'output')
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(config))
    return path, paths, config


def test_registration_is_blind_deterministic_and_preserves_empty_faces(registration, monkeypatch):
    """예측 혼입·미검출 이미지 누락을 막고 같은 입력의 byte 동일 재생성을 허용한다."""
    path, inputs, config = registration
    def forbidden(*args, **kwargs):
        pytest.fail('preregistration performed inference')
    monkeypatch.setattr('src.anonymize.Anonymizer.detect', forbidden)
    result = prepare(path)
    output = Path(config['output_dir'])
    before = {p.name:p.read_bytes() for p in output.iterdir()}
    assert prepare(path) == result
    assert before == {p.name:p.read_bytes() for p in output.iterdir()}
    assert result['real_images'] == result['real_discs'] == 1
    assert result['face_review_images'] == 2
    assert result['gen_interventions_by_generator'] == {'g': {'eligible': 1, 'selected': 1}}
    assert result['size_target_diameter_over_width'] == 0.2
    assert set(result['inputs_sha256']) == set(inputs)
    assert all(b'\r' not in value for value in before.values())
    reviews = list(csv.DictReader((output/'face_review_template.csv').open()))
    assert [r['image_id'] for r in reviews] == ['g1','g2']
    assert all(r['confirmed'] == '' for r in reviews)


def test_registration_rejects_changed_inputs_without_partial_overwrite(registration):
    """입력 변경의 묵인을 막고 재등록 거부 시 기존 artifact를 보존한다."""
    path, inputs, config = registration
    prepare(path)
    output = Path(config['output_dir'])
    before = {p.name:p.read_bytes() for p in output.iterdir()}
    inputs['baseline_calibration'].write_text('{"changed":true}')
    with pytest.raises(ValueError, match='preregistration differs'):
        prepare(path)
    assert before == {p.name:p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize('field', ['detector_sha256','parameters_sha256'])
def test_registration_rejects_stale_cache_parameters(registration, field):
    path, inputs, config = registration
    rows = list(csv.DictReader(inputs['face_cache'].open()))
    rows[0][field] = 'bad'
    write_csv(inputs['face_cache'], rows)
    with pytest.raises(ValueError, match='mismatch'):
        prepare(path)
    assert not Path(config['output_dir']).exists()


def test_registration_rejects_duplicate_ids_and_wrong_real_split(registration):
    path, inputs, config = registration
    rows = list(csv.DictReader(inputs['metadata'].open()))
    write_csv(inputs['metadata'], rows + [rows[0]])
    with pytest.raises(ValueError, match='unique'):
        prepare(path)
    rows[0]['split'] = 'test'
    write_csv(inputs['metadata'], rows)
    with pytest.raises(ValueError, match='lineage'):
        prepare(path)


def test_preregistered_config_covers_all_adoption_gates():
    config = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    assert config['cue_model'] == 'candidate'
    assert config['evaluation']['models'] == ['baseline','candidate']
    assert config['evaluation']['inputs'] == ['original','anonymized']
    assert config['evaluation']['cohorts'] == ['val','standard','unseen']
    assert config['adoption']['required_cue_gates'] == ['face_concentration','real_shape','real_size','gen_gray','gen_restore']
    assert config['adoption']['all_required'] is True
    assert config['adoption']['standard_anonymized_roc_auc_min'] == 0.90
    assert config['adoption']['unseen_anonymized_roc_auc_min'] == 0.80
    assert config['adoption']['indeterminate'] == 'do_not_adopt'


@pytest.mark.parametrize('kind', ['missing_candidate', 'duplicate_candidate', 'incomplete_review', 'invalid_boxes', 'invalid_target'])
def test_registration_rejects_invalid_sources(registration, kind):
    """잘못된 주석·좌표·목표치를 거부하고 정상 source는 기본 셀에서 허용한다."""
    path, inputs, config = registration
    if kind == 'missing_candidate':
        rows = list(csv.DictReader(inputs['real_review'].open()))
        rows[0]['candidate_id'] = 'unknown'
        write_csv(inputs['real_review'], rows)
    elif kind == 'duplicate_candidate':
        rows = list(csv.DictReader(inputs['real_candidates'].open()))
        write_csv(inputs['real_candidates'], rows + rows)
    elif kind == 'incomplete_review':
        rows = list(csv.DictReader(inputs['real_review'].open()))
        rows[0]['confirmed'] = ''
        write_csv(inputs['real_review'], rows)
    elif kind == 'invalid_boxes':
        rows = list(csv.DictReader(inputs['face_cache'].open()))
        rows[0]['boxes'] = '[[1,2,-3,4]]'
        write_csv(inputs['face_cache'], rows)
    else:
        inputs['measurement'].write_text(json.dumps(dict(synthetic=dict(selected_size=dict(synthetic_quartiles=[0.1,0,0.3])))))
    with pytest.raises(ValueError):
        prepare(path)
    assert not Path(config['output_dir']).exists()

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


def test_face_state_and_annotation_contract():
    """놓친 얼굴을 없음으로 치환하거나 불완전 확인을 통과시키는 규격 변경을 잠근다."""
    config = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    annotations = config['annotations']
    assert annotations['timing'] == 'before_candidate_diagnostic_predictions'
    assert annotations['score_blind'] is True
    assert annotations['visible_definition'] == 'at_least_two_of_eyes_nose_mouth_including_partial_profile'
    assert annotations['fields'] == ['image_id','visible_faces','uncovered_visible_faces','confirmed']
    assert annotations['review'] == 'agent_all_owner_all_disagreements_and_seeded_20_percent'
    assert annotations['owner_random_fraction'] == 0.20
    assert annotations['final_owner_overrides_agent'] is True
    assert annotations['incomplete'] == 'indeterminate'
    face = config['face_concentration']
    assert face['cohort'] == 'all_gen_in_gen_splits'
    assert face['states'] == ['anonymized','no_visible_face','missed_visible_face']
    assert face['state_priority'] == 'missed_then_no_visible_then_anonymized'
    assert face['comparisons'] == [['anonymized','no_visible_face'],['anonymized','missed_visible_face'],['no_visible_face','missed_visible_face']]
    assert face['outcome'] == 'false_positive_rate'
    assert face['interval'] == 'newcombe_wilson_independent_difference_two_sided'
    assert face['confidence'] == 0.95
    assert face['max_absolute_rate_difference'] == 0.10
    assert face['min_images_per_state'] == 20
    assert face['missing_state'] == 'indeterminate'
    assert face['per_generator'] == 'report_only_no_causal_claim'


def test_intervention_construction_preserves_other_real_face_masks():
    """REAL 별도 얼굴 마스크의 복원을 막고 GEN 회색·제거 대조는 원본 기반을 허용한다."""
    config = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    edits = config['interventions']
    assert edits['real_shape'] == dict(cohort='real', reference='anonymized', construction_base='normal_anonymized',
                                      edit='white_circle_covering_existing_ellipse', radius='measured_major_half_plus_edge_guard')
    assert edits['real_size'] == dict(cohort='real', reference='anonymized', construction_base='normal_anonymized',
                                     edit='enlarge_existing_white_circle_only',
                                     target='measurement_synthetic_selected_size_median_diameter_over_width',
                                     radius='max_shape_radius_and_target_radius')
    assert edits['gen_gray'] == dict(cohort='detected_gen', reference='anonymized', construction_base='original',
                                    edit='paint_all_cached_face_discs_gray_from_original', fill=[128,128,128])
    assert edits['gen_restore'] == dict(cohort='detected_gen', reference='anonymized', construction_base='original',
                                       edit='original_image_without_synthetic_face_discs')
    assert edits['edge_guard_sigma_multiplier'] == 3.0 and edits['edge_guard_extra_px'] == 1.0
    assert edits['geometry_and_edge'] == 'checkpoint_anonymization'
    assert edits['resize_normalization'] == 'checkpoint_model'
    assert edits['augmentation'] is False


def test_intervention_equivalence_contract_uses_images_and_absolute_effects():
    """원별 중복 집계·signed 상쇄·작은 표본의 확신·허용폭 변경을 막는 계약을 잠근다."""
    config = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    rules = config['intervention_rules']
    assert rules['unit'] == 'image' and rules['min_images'] == 80
    assert rules['score'] == dict(statistic='mean_absolute_paired_score_shift', scale=[0,100],
                                  bootstrap='image_cluster_percentile_two_sided', rng='numpy_generator_pcg64',
                                  index_draw='integers_zero_to_n_exclusive_shape_resamples_by_n_with_replacement',
                                  percentile_method='linear', resamples=20000,
                                  confidence=0.95, max_upper=5.0,
                                  repeated_discs='jointly_edit_then_one_prediction_per_image')
    assert rules['error'] == dict(statistic='previously_correct_becomes_incorrect', denominator='all_selected_images',
                                  interval='wilson_two_sided', confidence=0.95, max_upper=0.05)
    assert rules['threshold'] == 'calibrated_probability_threshold_of_same_model'
    assert rules['signed_shift_and_reverse_flips'] == rules['generator_breakdown'] == 'report_only'
    assert rules['missing_nonfinite_or_insufficient'] == 'indeterminate'


def test_sampling_and_non_adoption_contract():
    """부족분 사후 충원·조건별 fitting·미확정 채택·P07 조기 진행을 막는 계약을 잠근다."""
    config = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    assert config['sampling'] == dict(real='all_confirmed_measurement_discs', real_split='train',
                                      gen_splits=['test','test_unseen'], gen_detected_per_generator=40,
                                      face_review='all_gen_in_gen_splits', undersized_generator='take_all_report_count')
    evaluation = config['evaluation']
    assert evaluation['standard_split'] == 'test'
    assert evaluation['unseen_real'] == 'standard_test_real_reuse'
    assert evaluation['unseen_generated_split'] == 'test_unseen'
    assert evaluation['calibration_per_model'] == 'fixed_for_both_inputs'
    assert evaluation['metrics'] == ['roc_auc','pr_auc','accuracy','precision','recall','f1','nll','brier','ece']
    assert evaluation['ece_bins'] == 10 and evaluation['grouping'] == ['generator','category','source_domain']
    adoption = config['adoption']
    assert adoption['failed'] == 'do_not_adopt'
    assert adoption['pass'] == 'replace_primary_and_report_owner'
    assert adoption['non_adoption'] == 'keep_baseline_artifacts_wait_p07_retry_p08'
    assert adoption['retry_failed'] == 'ask_owner'
    assert adoption['face_visible_real_holdout'] == 'limitation_not_p07_gate'


def test_stratified_cap_seed_undersized_generator_and_multi_disc_images(registration):
    """cap 축소·seed/순서 변경·부족분 충원·원별 이미지 부풀림을 잡고 정상 층화를 허용한다."""
    path, inputs, config = registration
    metadata = [dict(image_id='r',label='1',split='train',generator='')]
    for generator, prefix, n in [('alpha','a',45),('beta','b',43),('gamma','c',2)]:
        metadata.extend(dict(image_id=f'{prefix}{i:03}',label='0',split='test',generator=generator) for i in range(n))
    metadata.append(dict(image_id='z_empty',label='0',split='test_unseen',generator='gamma'))
    write_csv(inputs['metadata'], list(reversed(metadata)))
    row = list(csv.DictReader(inputs['face_cache'].open()))[0]
    write_csv(inputs['face_cache'], [dict(row,image_id=r['image_id'],boxes='[]' if r['image_id'] in ('r','z_empty') else '[[1,2,3,4]]') for r in metadata])
    candidates = list(csv.DictReader(inputs['real_candidates'].open()))
    candidates.append(dict(candidates[0], candidate_id='c2',cx='70'))
    write_csv(inputs['real_candidates'], candidates)
    write_csv(inputs['real_review'], [dict(candidate_id=r['candidate_id'],image_id='r',confirmed='1') for r in candidates])
    result = prepare(path)
    output = Path(config['output_dir'])
    selected = list(csv.DictReader((output/'gen_interventions.csv').open()))
    excluded = {'a012','a020','a029','a036','a039','b000','b009','b026','z_empty'}
    expected = {r['image_id'] for r in metadata if r['label']=='0'} - excluded
    assert {r['image_id'] for r in selected} == expected and len(selected) == 82
    assert result['gen_interventions_by_generator'] == {
        'alpha': {'eligible':45,'selected':40}, 'beta': {'eligible':43,'selected':40}, 'gamma': {'eligible':2,'selected':2}}
    assert result['real_discs'] == 2 and result['real_images'] == 1
    assert result['face_review_images'] == 91
    review = list(csv.DictReader((output/'face_review_template.csv').open()))
    assert 'z_empty' in {r['image_id'] for r in review}
    for name, digest in result['manifests_sha256'].items():
        assert hashlib.sha256((output/name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('kind', ['cache_duplicate','cache_missing','cache_extra','review_duplicate','review_image_mismatch','real_label_mismatch'])
def test_registration_rejects_all_id_and_real_lineage_mismatches(registration, kind):
    """ID/REAL 계보의 각 거부 분기를 잠그고 정상 source는 기본 셀이 허용한다."""
    path, inputs, config = registration
    if kind.startswith('cache_'):
        rows = list(csv.DictReader(inputs['face_cache'].open()))
        if kind == 'cache_duplicate': rows.append(rows[0])
        elif kind == 'cache_missing': rows.pop(0)
        else: rows.append(dict(rows[0],image_id='extra'))
        write_csv(inputs['face_cache'], rows)
    elif kind.startswith('review_'):
        rows = list(csv.DictReader(inputs['real_review'].open()))
        if kind == 'review_duplicate': rows.append(rows[0])
        else: rows[0]['image_id'] = 'g1'
        write_csv(inputs['real_review'], rows)
    else:
        rows = list(csv.DictReader(inputs['metadata'].open()))
        rows[0]['label'] = '0'
        write_csv(inputs['metadata'], rows)
    with pytest.raises(ValueError):
        prepare(path)
    assert not Path(config['output_dir']).exists()


@pytest.mark.parametrize('field,value', [('width','0'),('major','0'),('minor','0'),('major','8'),
                                        ('cx','nan'),('cy','inf'),('angle','-inf'),('width','bad')])
def test_registration_rejects_invalid_real_geometry(registration, field, value):
    """비유한·비숫자·비양수 너비/축·역전 축을 거부하고 음수 중심은 다음 셀에서 허용한다."""
    path, inputs, config = registration
    rows = list(csv.DictReader(inputs['real_candidates'].open()))
    rows[0][field] = value
    write_csv(inputs['real_candidates'], rows)
    with pytest.raises(ValueError):
        prepare(path)
    assert not Path(config['output_dir']).exists()


def test_registration_allows_finite_clipped_disc_geometry(registration):
    """화면 경계 원 중심의 과도한 거부를 막고 양수 등축·음수 중심을 허용한다."""
    path, inputs, config = registration
    rows = list(csv.DictReader(inputs['real_candidates'].open()))
    rows[0].update(cx='-0.5',cy='-1',major='10',minor='10')
    write_csv(inputs['real_candidates'], rows)
    assert prepare(path)['real_images'] == 1

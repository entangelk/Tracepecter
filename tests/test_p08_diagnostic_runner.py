"""진단 전용 원본 bypass·공통 커널·해시·재개를 stub으로 통합 검증한다."""
import csv
import json
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml
from PIL import Image

from scripts import p08_diagnostic as runner
from scripts.p08_preregister import csv_bytes, prepare
from src.anonymize import Anonymizer, bind_spec, file_hash, write_face_cache
from src.dataset import MetadataDataset


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    from test_baseline import make_data
    metadata = make_data(tmp_path)
    spec = yaml.safe_load(Path('configs/anonymize.yaml').read_text())
    detector = tmp_path/'detector.onnx'; detector.write_bytes(b'fixture')
    spec['face_detector'].update(model=str(detector), model_sha256=file_hash(detector))
    spec_path = tmp_path/'spec.yaml'; spec_path.write_text(yaml.safe_dump(spec))
    monkeypatch.setattr(Anonymizer, 'detect', lambda *a: [[2., 2., 8., 8.], [20., 2., 8., 8.]])
    cache = tmp_path/'cache.csv'
    dataset = MetadataDataset(metadata, 16, False, False)
    write_face_cache([(r.image_id, dataset.image_path(i)) for i,r in enumerate(dataset.rows)], bind_spec(spec), cache)
    settings = yaml.safe_load(Path('configs/anonymized_diagnostic.yaml').read_text())
    output = tmp_path/'diagnostic'; settings['output_dir'] = str(output)
    candidates = tmp_path/'candidates.csv'
    candidates.write_bytes(csv_bytes(('candidate_id','image_id','width','cx','cy','major','minor','angle'),
        [dict(candidate_id=f'c{n}', image_id='train_1.png', width=32, cx=x, cy=30, major=8, minor=6, angle=0)
         for n,x in enumerate([8, 24])]))
    review = tmp_path/'review.csv'
    review.write_bytes(csv_bytes(('candidate_id','image_id','confirmed'),
        [dict(candidate_id=f'c{n}', image_id='train_1.png', confirmed=1) for n in range(2)]))
    measurement = tmp_path/'measurement.json'
    measurement.write_text(json.dumps(dict(synthetic=dict(selected_size=dict(synthetic_quartiles=[.1, .7, .8])))))
    configs = {}; artifacts = {}
    for name, temp, threshold in [('baseline',2.,.37), ('candidate',3.,.61)]:
        config = dict(anonymization=None if name=='baseline' else bind_spec(spec),
                      model=dict(image_size=16), data=dict(metadata_csv=str(metadata)),
                      training=dict(batch_size=2, num_workers=0))
        checkpoint = tmp_path/(name+'.pt'); torch.save(dict(config=config), checkpoint)
        artifact = tmp_path/(name+'.json')
        artifact.write_text(json.dumps(dict(version=1,method='temperature_scaling',checkpoint=str(checkpoint),
            checkpoint_sha256=file_hash(checkpoint),metadata_sha256=file_hash(metadata),
            temperature=temp,threshold_probability=threshold)))
        configs[str(checkpoint)] = config; artifacts[name] = str(artifact)
    settings['inputs'].update(metadata=str(metadata),anonymization=str(spec_path),face_cache=str(cache),
                             real_candidates=str(candidates),real_review=str(review),measurement=str(measurement),
                             baseline_calibration=artifacts['baseline'])
    settings['candidate_calibration'] = artifacts['candidate']
    config_path = tmp_path/'diagnostic.yaml'; config_path.write_text(yaml.safe_dump(settings))
    prepare(config_path)
    annotations = [dict(image_id=r['image_id'],visible_faces=2,uncovered_visible_faces=0,confirmed=1)
                   for r in runner.read_csv(output/'face_review_template.csv')]
    (output/'face_review.csv').write_bytes(csv_bytes(('image_id','visible_faces','uncovered_visible_faces','confirmed'),annotations))
    (output/'face_review_lock.json').write_text(json.dumps(dict(sha256={'face_review.csv':file_hash(output/'face_review.csv')})))
    monkeypatch.setattr(runner, 'committed_annotations', lambda *a: 'fixture_commit')
    calls = []
    class Model:
        def eval(self): return self
        def forward_logits(self, images):
            calls.append(images.clone())
            return images.mean(dim=(1,2,3))
    monkeypatch.setattr(runner, 'load_model', lambda checkpoint, device: (Model(),configs[checkpoint]))
    return config_path, output, calls, settings


def test_stub_end_to_end_fixed_calibration_and_resume(fixture):
    """전 조건 실행·해시 결합을 강제하며 정상 재개에서는 예측을 반복하지 않는다."""
    path, output, calls, settings = fixture
    result = runner.run(path, 'cpu')
    assert set(result['evaluation']) == {'baseline','candidate'}
    for name, threshold in [('baseline',.37),('candidate',.61)]:
        for condition in ('original','anonymized'):
            value = result['evaluation'][name][condition]
            assert value['threshold_probability'] == threshold
            assert value['cohorts']['val']['count'] == 2
            assert value['cohorts']['standard']['count'] == 2
            assert value['cohorts']['unseen']['count'] == 2
            assert {'nll','brier','ece','roc_auc','pr_auc','f1'} <= value['cohorts']['val'].keys()
            assert value['cohorts']['standard']['generator_wise']['seen']['count'] == 2
    assert not result['adoption']['adopt']
    assert result['gates']['face_concentration']['status'] == 'indeterminate'
    assert all(v['count'] == 1 for k,v in result['gates'].items() if k.startswith('real_'))
    predictions = lambda n: {r['image_id']:float(r['logit']) for r in runner.read_csv(output/(n+'.csv'))}
    original = predictions('candidate_original')
    normal = predictions('candidate_anonymized')
    assert normal['test_0.png'] > original['test_0.png']
    assert predictions('candidate_gen_restore')['test_0.png'] == original['test_0.png']
    gray = predictions('candidate_gen_gray')['test_0.png']
    assert original['test_0.png'] < gray < normal['test_0.png']
    count = len(calls)
    assert runner.run(path, 'cpu') == result
    assert len(calls) == count
    # 다른 candidate artifact와 기존 예측을 섞을 수 없다.
    artifact = Path(settings['candidate_calibration'])
    value = json.loads(artifact.read_text()); value['temperature'] = 4.
    artifact.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='execution.*differs'):
        runner.run(path, 'cpu')


def test_variants_preserve_other_masks_all_discs_and_no_second_anonymization(fixture):
    """REAL 원본 기반·GEN 재가림을 잡고 모든 얼굴과 여러 원의 공동 처리를 허용한다."""
    path, output, calls, settings = fixture
    state = runner.preflight(path)
    config = state['configs']['candidate']
    ds = runner.Variants(state, config, ['train_1.png'], 'real_shape')
    image = ds.image('train_1.png')
    pixels = np.asarray(image)
    assert tuple(pixels[6,6]) == tuple(pixels[6,24]) == (255,255,255) # 다른 위치 YuNet 두 원 보존
    assert tuple(pixels[30,8]) == tuple(pixels[30,24]) == (255,255,255) # 기존 두 원 모두 덧칠
    geometry = runner.real_geometry(state, (32,40), 'train_1.png', 'real_size')
    assert len(geometry) == 2 and all(g['expansion_ratio'] > 1 for g in geometry)
    restore = runner.Variants(state, config, ['test_0.png'], 'gen_restore').image('test_0.png')
    assert np.array_equal(restore, Image.open(path.parent/'test_0.png').convert('RGB'))


@pytest.mark.parametrize('damage', ['registration','annotation','candidate_binding','metadata','image','missing_cache'])
def test_preflight_rejects_tampering_before_predictions(fixture, damage):
    """불일치를 원본 bypass로 숨기는 완화를 잡고 정상 입력은 위 통합 셀에서 허용한다."""
    path, output, calls, settings = fixture
    if damage=='registration':
        path.write_text(path.read_text()+'\n# changed\n')
    elif damage=='annotation':
        (output/'face_review.csv').write_text('broken')
    elif damage=='candidate_binding':
        artifact = json.loads(Path(settings['candidate_calibration']).read_text())
        checkpoint = Path(artifact['checkpoint']); saved = torch.load(checkpoint,weights_only=True)
        saved['config']['anonymization']['sha256'] = 'bad'; torch.save(saved,checkpoint)
        artifact['checkpoint_sha256'] = file_hash(checkpoint)
        Path(settings['candidate_calibration']).write_text(json.dumps(artifact))
    elif damage=='metadata':
        p=Path(settings['inputs']['metadata']);p.write_bytes(p.read_bytes()+b'\n')
    elif damage=='image':
        p=path.parent/'test_0.png';p.write_bytes(p.read_bytes()+b'changed')
    elif damage=='missing_cache':
        p=Path(settings['inputs']['face_cache']);p.write_text(p.read_text().replace('test_0.png,','absent.png,'))
    with pytest.raises(ValueError): runner.run(path,'cpu')
    assert not calls


def test_resume_rejects_duplicate_and_foreign_rows_and_repairs_only_torn_tail(tmp_path):
    """중복·다른 cohort를 거부하고 중단된 마지막 행만 안전하게 제거한다."""
    path = tmp_path/'predictions.csv'
    path.write_bytes(b'image_id,logit\na,1.0\nb,2.')
    assert runner.resume_predictions(path, {'a','b'}) == {'a':1.}
    assert path.read_bytes() == b'image_id,logit\na,1.0\n'
    for tail in (b'a,2\n', b'foreign,2\n', b'b,nan\n'):
        path.write_bytes(b'image_id,logit\na,1.0\n'+tail)
        with pytest.raises(ValueError): runner.resume_predictions(path, {'a','b'})


def test_committed_annotation_check_rejects_dirty_bytes_and_accepts_head(tmp_path, monkeypatch):
    """예측 전 주석 미커밋을 거부하고 HEAD와 동일한 정상 입력은 허용한다."""
    # 실제 Git이 없는 CPU 컨테이너에서도 동일한 subprocess 경계를 검증한다.
    output = Path('fixture_output')
    monkeypatch.chdir(tmp_path); output.mkdir()
    (output/'face_review.csv').write_bytes(b'csv')
    (output/'face_review_lock.json').write_bytes(b'lock')
    def git(args):
        if 'show' in args:
            return b'csv' if args[-1].endswith('face_review.csv') else b'lock'
        return b'fixed_commit\n'
    monkeypatch.setattr(runner.subprocess,'check_output',git)
    # fixture()의 preflight 대체와 무관한 원래 함수다.
    assert runner.committed_annotations(output) == 'fixed_commit'
    (output/'face_review.csv').write_bytes(b'changed')
    with pytest.raises(ValueError,match='uncommitted'):
        runner.committed_annotations(output)

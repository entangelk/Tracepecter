"""진단 전용 원본 bypass·공통 커널·해시·재개를 stub으로 통합 검증한다."""
import csv
import json
import math
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
    # T=1/고정 T 및 threshold=.5/모델별 threshold의 분류가 실제로 갈리는 값.
    for name, temp, threshold in [('baseline',2.,.42), ('candidate',3.,.53)]:
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


def manual_metrics(logits, labels, temperature, threshold):
    """stub logit의 독립 수식. 실제 calibration/evaluate 함수는 호출하지 않는다."""
    scaled = [v/temperature for v in logits]
    probabilities = [1/(1+math.exp(-v)) for v in scaled]
    predicted = [p >= threshold for p in probabilities]
    n = len(labels)
    tp = sum(p and y == 1 for p,y in zip(predicted,labels))
    fp = sum(p and y == 0 for p,y in zip(predicted,labels))
    fn = sum(not p and y == 1 for p,y in zip(predicted,labels))
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    ece = 0.
    for b in range(10):
        indices = [i for i,p in enumerate(probabilities) if min(int(p*10),9) == b]
        if indices:
            ece += abs(sum(probabilities[i]-labels[i] for i in indices))/n
    return dict(accuracy=sum(p == y for p,y in zip(predicted,labels))/n,
                precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0,
                nll=sum(math.log1p(math.exp(v))-y*v for v,y in zip(scaled,labels))/n,
                brier=sum((p-y)**2 for p,y in zip(probabilities,labels))/n,ece=ece)


def test_stub_end_to_end_fixed_calibration_and_resume(fixture):
    """실제 계산의 T/threshold 무시를 잡고 모델별 정상 보정·모든 입력·재개를 허용한다."""
    path, output, calls, settings = fixture
    result = runner.run(path, 'cpu')
    assert set(result['evaluation']) == {'baseline','candidate'}
    metadata = runner.read_csv(settings['inputs']['metadata'])
    cohorts = {name:[r for r in metadata if r['split'] == split]
               for name,split in [('val','val'),('standard','test')]}
    cohorts['unseen'] = [r for r in metadata if r['split']=='test_unseen' or (r['split']=='test' and r['label']=='1')]
    for name, temperature, threshold in [('baseline',2.,.42),('candidate',3.,.53)]:
        for condition in ('original','anonymized'):
            value = result['evaluation'][name][condition]
            assert value['temperature'] == temperature
            assert value['threshold_probability'] == threshold
            assert value['cohorts']['val']['count'] == 2
            assert value['cohorts']['standard']['count'] == 2
            assert value['cohorts']['unseen']['count'] == 2
            assert {'nll','brier','ece','roc_auc','pr_auc','f1'} <= value['cohorts']['val'].keys()
            assert value['cohorts']['standard']['generator_wise']['seen']['count'] == 2
            logits = {r['image_id']:float(r['logit']) for r in runner.read_csv(output/f'{name}_{condition}.csv')}
            for cohort, rows in cohorts.items():
                values = [logits[r['image_id']] for r in rows]
                labels = [int(r['label']) for r in rows]
                expected = manual_metrics(values,labels,temperature,threshold)
                for field, wanted in expected.items():
                    assert value['cohorts'][cohort][field] == pytest.approx(wanted,abs=1e-12), (name,condition,cohort,field)
            if condition == 'original':
                values = [logits[r['image_id']] for r in cohorts['val']]
                labels = [int(r['label']) for r in cohorts['val']]
                # fixture 자체가 두 결함을 관측할 수 있는지 먼저 잠근다.
                expected = manual_metrics(values,labels,temperature,threshold)['accuracy']
                assert expected != manual_metrics(values,labels,1.,threshold)['accuracy']
                assert expected != manual_metrics(values,labels,temperature,.5)['accuracy']
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


def test_cue_boundary_uses_candidate_temperature_threshold_and_all_predictions(fixture, monkeypatch):
    """단서 입력의 T=1·threshold=.5 강제를 잡고 올바른 모델별 보정 연결을 허용한다."""
    path, output, _, _ = fixture
    actual_concentration, actual_intervention = runner.concentration, runner.intervention
    seen = []
    def check_probabilities(values, condition):
        rows = runner.read_csv(output/f'candidate_{condition}.csv')
        expected = {r['image_id']:1/(1+math.exp(-float(r['logit'])/3.)) for r in rows}
        assert values == pytest.approx(expected,abs=1e-12)
        uncalibrated = {r['image_id']:1/(1+math.exp(-float(r['logit']))) for r in rows}
        assert any(abs(expected[i]-uncalibrated[i]) > .01 for i in expected)
    def face_gate(annotations, probabilities, generators, threshold, settings):
        assert threshold == .53
        check_probabilities(probabilities,'anonymized')
        seen.append('face_concentration')
        return actual_concentration(annotations,probabilities,generators,threshold,settings)
    def edit_gate(ids, reference, variant, labels, threshold, settings):
        assert threshold == .53
        condition = ['real_shape','real_size','gen_gray','gen_restore'][len(seen)-1]
        check_probabilities(reference,'anonymized')
        check_probabilities(variant,condition)
        seen.append(condition)
        return actual_intervention(ids,reference,variant,labels,threshold,settings)
    monkeypatch.setattr(runner,'concentration',face_gate)
    monkeypatch.setattr(runner,'intervention',edit_gate)
    runner.run(path,'cpu')
    assert seen == ['face_concentration','real_shape','real_size','gen_gray','gen_restore']


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
    gray = runner.Variants(state, config, ['test_0.png'], 'gen_gray').image('test_0.png')
    assert tuple(np.asarray(gray)[6,6]) == tuple(np.asarray(gray)[6,24]) == (128,128,128)
    restore = runner.Variants(state, config, ['test_0.png'], 'gen_restore').image('test_0.png')
    assert np.array_equal(restore, Image.open(path.parent/'test_0.png').convert('RGB'))
    # 이미 큰 원은 크기 목표 때문에 축소하지 않는다. 경계 clipping도 보고한다.
    state['real']['train_1.png'][0].update(major='100', minor='100', cx='-2')
    geometry = runner.real_geometry(state, (32,40), 'train_1.png', 'real_size')
    assert geometry[0]['expansion_ratio'] == 1 and not geometry[0]['expanded'] and geometry[0]['clipped']
    normal = runner.Variants(state, config, ['train_1.png'], 'anonymized').image('train_1.png')
    expanded = runner.Variants(state, config, ['train_1.png'], 'real_size').image('train_1.png')
    assert np.all(np.asarray(expanded) >= np.asarray(normal))


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

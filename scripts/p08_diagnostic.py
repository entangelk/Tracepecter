"""P08-06 offline 진단: 사전등록·주석 고정 → 2×2/개입 예측 → 고정 판정.

기존 checkpoint/calibration/P06 결과를 덮어쓰지 않고 output_dir에만 기록한다.
원본 bypass는 이 실행기에만 존재하며 score/API 계약은 변경하지 않는다.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from scripts.p08_preregister import read_csv
from src.anonymize import Anonymizer, bind_spec, checkpoint_anonymizer, file_hash, paint_circles
from src.calibration import apply_temperature, calibration_metrics
from src.dataset import MetadataDataset, build_transform
from src.diagnostic import adoption, concentration, intervention
from src.evaluate import binary_metrics, evaluation_indices, load_model
from src.score import load_calibration


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def committed_annotations(output):
    """주석과 해시 고정 파일이 현재 HEAD에도 같은 바이트로 존재해야 한다."""
    prefix = ['git', '-c', f'safe.directory={Path.cwd()}']
    for name in ('face_review.csv', 'face_review_lock.json'):
        path = output/name
        committed = subprocess.check_output(prefix+['show', f'HEAD:{path.as_posix()}'])
        if committed != path.read_bytes():
            raise ValueError(f'uncommitted annotation: {path}')
    return subprocess.check_output(prefix+['log', '-1', '--format=%H', '--', str(output/'face_review.csv')]).decode().strip()


def load_artifacts(settings, registration, spec):
    """P08 requires both fitted artifacts to belong to the evaluation metadata."""
    artifacts, configs = {}, {}
    for name, path in [('baseline', settings['inputs']['baseline_calibration']),
                       ('candidate', settings['candidate_calibration'])]:
        artifact = load_calibration(path)
        if artifact['metadata_sha256'] != registration['inputs_sha256']['metadata']:
            raise ValueError('calibration metadata hash mismatch')
        saved = torch.load(artifact['checkpoint'], map_location='cpu', weights_only=True)
        config = saved['config']
        checkpoint_anonymizer(config, required=name == 'candidate')
        if (file_hash(config['data']['metadata_csv']) != artifact['metadata_sha256']
                or (name == 'candidate' and config['anonymization'] != bind_spec(spec))):
            raise ValueError('checkpoint metadata/anonymization mismatch')
        artifacts[name], configs[name] = artifact, config
    return artifacts, configs


def preflight(config_path, *, artifact_loader=None):
    settings = yaml.safe_load(Path(config_path).read_text())
    output = Path(settings['output_dir'])
    registration = json.loads((output/'preregistration.json').read_text())
    if file_hash(config_path) != registration['config_sha256']:
        raise ValueError('preregistration config hash mismatch')
    for key, digest in registration['inputs_sha256'].items():
        if file_hash(settings['inputs'][key]) != digest:
            raise ValueError(f'preregistration input hash mismatch: {key}')
    for name, digest in registration['manifests_sha256'].items():
        if file_hash(output/name) != digest:
            raise ValueError(f'preregistration manifest hash mismatch: {name}')
    lock = json.loads((output/'face_review_lock.json').read_text())
    for name, digest in lock['sha256'].items():
        if file_hash(output/name) != digest:
            raise ValueError(f'annotation hash mismatch: {name}')
    annotation_commit = committed_annotations(output)
    annotations = {}
    for row in read_csv(output/settings['annotations']['output']):
        i = row['image_id']
        v, u = int(row['visible_faces']), int(row['uncovered_visible_faces'])
        if i in annotations or row['confirmed'] != '1' or not 0 <= u <= v:
            raise ValueError('incomplete or duplicate face annotation')
        annotations[i] = (v, u)
    template_ids = {r['image_id'] for r in read_csv(output/'face_review_template.csv')}
    if set(annotations) != template_ids:
        raise ValueError('face annotation IDs mismatch')
    spec = yaml.safe_load(Path(settings['inputs']['anonymization']).read_text())
    worker = Anonymizer(bind_spec(spec), settings['inputs']['face_cache'])
    artifacts, configs = (artifact_loader or load_artifacts)(settings, registration, spec)
    dataset = MetadataDataset(settings['inputs']['metadata'], 224, False, False,
                              image_root=configs['candidate']['data'].get('image_root'))
    rows = {r.image_id:r for r in dataset.rows}
    if len(rows) != len(dataset.rows) or set(worker.cache) != set(rows):
        raise ValueError('metadata/cache IDs mismatch')
    gen_ids = {r.image_id for r in dataset.rows if r.label == 0 and r.split in settings['sampling']['gen_splits']}
    if gen_ids != template_ids:
        raise ValueError('face annotation cohort mismatch')
    real = defaultdict(list)
    for row in read_csv(output/'real_interventions.csv'):
        real[row['image_id']].append(row)
    gen = [r['image_id'] for r in read_csv(output/'gen_interventions.csv')]
    eval_ids = sorted(r.image_id for r in dataset.rows if r.split in ('val', 'test', 'test_unseen'))
    needed = set(eval_ids) | set(real) | set(gen)
    paths = {r.image_id:dataset.image_path(i) for i,r in enumerate(dataset.rows) if r.image_id in needed}
    # 원본 비교·복원 조건에서도 같은 이미지/cache 계보 검증을 선행한다.
    for n, i in enumerate(sorted(needed)):
        worker.boxes(None, i, paths[i])
        if (n+1) % 200 == 0:
            print(f'preflight images {n+1}/{len(needed)}', flush=True)
    identity = dict(config_sha256=file_hash(config_path), registration_sha256=file_hash(output/'preregistration.json'),
                    annotation_lock_sha256=file_hash(output/'face_review_lock.json'), annotation_commit=annotation_commit,
                    candidate_calibration_sha256=file_hash(settings['candidate_calibration']),
                    source_sha256={p:file_hash(p) for p in [str(Path(__file__)), 'src/diagnostic.py',
                        'src/anonymize.py', 'src/calibration.py', 'src/dataset.py', 'src/evaluate.py',
                        'src/score.py', 'src/model.py']},
                    checkpoints={k:a['checkpoint_sha256'] for k,a in artifacts.items()})
    return dict(settings=settings, output=output, registration=registration, annotations=annotations,
                worker=worker, artifacts=artifacts, configs=configs, rows=rows, paths=paths,
                real=real, gen=gen, eval_ids=eval_ids, identity=identity)


def real_geometry(state, size, image_id, variant):
    settings, spec = state['settings'], state['worker'].spec
    guard = settings['interventions']['edge_guard_sigma_multiplier']*spec['edge_sigma'] + settings['interventions']['edge_guard_extra_px']
    target_ratio = state['registration']['size_target_diameter_over_width']
    width, height = size
    geometry = []
    for row in sorted(state['real'][image_id], key=lambda r:r['candidate_id']):
        if float(row['width']) != width:
            raise ValueError('real geometry width mismatch')
        cx, cy, major = (float(row[k]) for k in ('cx','cy','major'))
        shape_radius = major/2+guard
        radius = max(shape_radius, width*target_ratio/2+guard) if variant == 'real_size' else shape_radius
        x, y, r = round(cx), round(cy), round(radius)
        geometry.append(dict(candidate_id=row['candidate_id'], image_id=image_id, variant=variant,
                             cx=cx, cy=cy, radius=radius, target_diameter=width*target_ratio,
                             shape_radius=shape_radius, measured_major=major, raster_radius=r,
                             expansion_ratio=radius/shape_radius, expansion_over_measured_major=2*r/major,
                             expanded=radius>shape_radius,
                             clipped=x-r<0 or y-r<0 or x+r>=width or y+r>=height))
    return geometry


class Variants(Dataset):
    def __init__(self, state, config, ids, condition):
        self.state, self.ids, self.condition = state, ids, condition
        mc = config['model']
        self.transform = build_transform(mc['image_size'], False, False, normalization=mc.get('normalization'))

    def image(self, image_id):
        state, condition = self.state, self.condition
        path = state['paths'][image_id]
        with Image.open(path) as handle:
            original = handle.convert('RGB')
        worker = state['worker']
        boxes = worker.boxes(original, image_id, path)
        if condition in ('original','gen_restore'):
            return original
        if condition == 'gen_gray':
            circles = [(x+w/2, y+h/2, worker.spec['diameter_per_face']*max(w,h)/2) for x,y,w,h in sorted(boxes)]
            return paint_circles(original, circles, state['settings']['interventions']['gen_gray']['fill'], worker.spec['edge_sigma'])
        normal, _ = worker(original, image_id, path)
        if condition == 'anonymized':
            return normal
        if condition not in ('real_shape','real_size'):
            raise ValueError(f'unknown diagnostic condition: {condition}')
        geometry = real_geometry(state, original.size, image_id, condition)
        return paint_circles(normal, [(g['cx'],g['cy'],g['radius']) for g in geometry], worker.spec['fill'], worker.spec['edge_sigma'])

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, index):
        return self.transform(self.image(self.ids[index]))


def resume_predictions(path, ids):
    if not path.exists():
        return {}
    data = path.read_bytes()
    if data and not data.endswith(b'\n'):
        # fsync 이전 전원 단절로 생긴 마지막 불완전 행만 제거한다.
        data = data[:data.rfind(b'\n')+1]
        path.write_bytes(data)
    if not data:
        return {}
    if data.splitlines()[0] != b'image_id,logit':
        raise ValueError(f'invalid resumed prediction columns: {path}')
    result = {}
    for row in read_csv(path):
        i, logit = row['image_id'], float(row['logit'])
        if i not in ids or i in result or not math.isfinite(logit):
            raise ValueError(f'invalid resumed prediction: {path}')
        result[i] = logit
    return result


def predictions(state, model, config, model_name, condition, ids, device):
    path = state['output']/f'{model_name}_{condition}.csv'
    result = resume_predictions(path, set(ids))
    todo = sorted(set(ids)-set(result))
    if not todo:
        return result
    dataset = Variants(state, config, todo, condition)
    training = config['training']
    workers = training.get('num_workers',0)
    loader = DataLoader(dataset, batch_size=training['batch_size'], num_workers=workers,
                        multiprocessing_context='spawn' if workers else None, pin_memory=device.startswith('cuda'))
    with path.open('a', newline='') as handle, torch.inference_mode():
        writer = csv.writer(handle, lineterminator='\n')
        if handle.tell() == 0:
            writer.writerow(['image_id','logit'])
        offset = 0
        for images in loader:
            logits = model.forward_logits(images.to(device)).cpu().tolist()
            if not all(math.isfinite(v) for v in logits):
                raise ValueError('nonfinite diagnostic logits')
            for i, logit in zip(todo[offset:offset+len(logits)], logits):
                result[i] = logit
                writer.writerow([i,logit])
            offset += len(logits)
            handle.flush(); os.fsync(handle.fileno())
            print(f'{model_name}/{condition}: {len(result)}/{len(ids)}', flush=True)
    return result


def evaluation_report(state, logits, artifact):
    settings = state['settings']
    all_rows = list(state['rows'].values())
    standard, unseen = evaluation_indices(all_rows)
    val = [i for i,r in enumerate(all_rows) if r.split == 'val']
    def metrics(rows):
        values = [logits[r.image_id] for r in rows]
        labels = [r.label for r in rows]
        p = apply_temperature(values, artifact['temperature'])
        return dict(binary_metrics(labels,p,artifact['threshold_probability']),
                    **calibration_metrics(values,labels,artifact['temperature'],settings['evaluation']['ece_bins']))
    cohorts = {}
    for name, indices in [('val',val),('standard',standard),('unseen',unseen)]:
        rows = [all_rows[i] for i in indices]
        result = metrics(rows)
        for field, key in [('generator','generator_wise'),('category','category_wise'),('source_domain','source_wise')]:
            result[key] = {g:metrics([r for r in rows if getattr(r,field)==g
                                     or (field=='generator' and r.label==1)
                                     or (field=='source_domain' and r.label==0)])
                           for g in sorted({getattr(r,field) for r in rows}-{''})}
        cohorts[name] = result
    return dict(temperature=artifact['temperature'], threshold_probability=artifact['threshold_probability'], cohorts=cohorts)


def run(config_path, device, *, preflight_fn=None):
    state = (preflight_fn or preflight)(config_path)
    state['identity'].update(device=device, torch_version=str(torch.__version__), numpy_version=np.__version__)
    output = state['output']
    identity_path = output/'execution.json'
    if identity_path.exists() and json.loads(identity_path.read_text()) != state['identity']:
        raise ValueError('execution identity differs; do not mix diagnostic predictions')
    write_json(identity_path,state['identity'])
    evaluation, candidate = {}, {}
    for name in state['settings']['evaluation']['models']:
        artifact, config = state['artifacts'][name], state['configs'][name]
        model, loaded_config = load_model(artifact['checkpoint'], device)
        if loaded_config != config:
            raise ValueError('checkpoint config changed during preflight')
        model.eval()
        evaluation[name] = {}
        for condition in state['settings']['evaluation']['inputs']:
            ids = state['eval_ids']
            if name == 'candidate' and condition == 'anonymized':
                ids = sorted(set(ids)|set(state['real']))
            logits = predictions(state,model,config,name,condition,ids,device)
            evaluation[name][condition] = evaluation_report(state,logits,artifact)
            if name == 'candidate' and condition == 'anonymized':
                candidate[condition] = logits
        if name == 'candidate':
            for condition in state['settings']['interventions']:
                if condition not in ('real_shape','real_size','gen_gray','gen_restore'):
                    continue
                ids = sorted(state['real']) if condition.startswith('real_') else state['gen']
                candidate[condition] = predictions(state,model,config,name,condition,ids,device)
        del model
        if device.startswith('cuda'):
            torch.cuda.empty_cache()
    artifact = state['artifacts']['candidate']
    probabilities = {k:dict(zip(v,apply_temperature(list(v.values()),artifact['temperature']).tolist())) for k,v in candidate.items()}
    reference = probabilities['anonymized']
    labels = {i:r.label for i,r in state['rows'].items()}
    generators = {i:r.generator for i,r in state['rows'].items()}
    threshold = artifact['threshold_probability']
    gates = dict(face_concentration=concentration(state['annotations'],reference,generators,threshold,state['settings']))
    for condition in ('real_shape','real_size','gen_gray','gen_restore'):
        ids = sorted(state['real']) if condition.startswith('real_') else state['gen']
        variant = probabilities[condition]
        result = intervention(ids,reference,variant,labels,threshold,state['settings'])
        result['generators'] = {}
        for g in sorted({generators[i] for i in ids}):
            group = [i for i in ids if generators[i] == g]
            delta = np.array([(variant[i]-reference[i])*100 for i in group])
            result['generators'][g] = dict(count=len(group), mean_signed_shift=float(delta.mean()),
                mean_absolute_shift=float(np.abs(delta).mean()),
                correct_to_wrong=sum((reference[i]>=threshold)==labels[i] and (variant[i]>=threshold)!=labels[i] for i in group),
                wrong_to_correct=sum((reference[i]>=threshold)!=labels[i] and (variant[i]>=threshold)==labels[i] for i in group))
        gates[condition] = result
    geometry = []
    for i in sorted(state['real']):
        with Image.open(state['paths'][i]) as image:
            for variant in ('real_shape','real_size'):
                geometry.extend(real_geometry(state,image.size,i,variant))
    expanded_ids = {g['image_id'] for g in geometry if g['variant']=='real_size' and g['expanded']}
    geometry_report = dict(discs=geometry, no_expansion_images=len(set(state['real'])-expanded_ids))
    normal = evaluation['candidate']['anonymized']['cohorts']
    report = dict(evaluation=evaluation,gates=gates,
                  adoption=adoption(normal['standard']['roc_auc'],normal['unseen']['roc_auc'],gates,state['settings']),
                  geometry=geometry_report,shared_real_policy='standard_test_real_reuse',
                  prediction_sha256={p.name:file_hash(p) for p in sorted(output.glob('candidate_*.csv'))+sorted(output.glob('baseline_*.csv'))})
    write_json(output/'result.json',report)
    print(json.dumps(report['adoption'],ensure_ascii=False),flush=True)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='P08-06 preregistered offline diagnostic (no fitting)')
    parser.add_argument('--config',default='configs/anonymized_diagnostic.yaml')
    parser.add_argument('--device',default='cpu')
    args = parser.parse_args(argv)
    run(args.config,args.device)


if __name__ == '__main__':
    main()

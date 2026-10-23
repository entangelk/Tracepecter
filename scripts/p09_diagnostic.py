"""P09 diagnostic adapter: retain training/fit lineage while evaluating the repaired cohort."""
import argparse
import json
from pathlib import Path

import torch

from scripts import p08_diagnostic as shared
from src.anonymize import bind_spec, checkpoint_anonymizer, file_hash
from src.score import load_calibration


def load_artifacts(settings, registration, spec):
    current = shared.read_csv(settings['inputs']['metadata'])
    current_by_id = {r['image_id']: r for r in current}
    if len(current_by_id) != len(current):
        raise ValueError('duplicate evaluation metadata ID')
    training_result = json.loads((Path(settings['output_dir']).parent/'training/result.json').read_text())
    artifacts, configs = {}, {}
    for name, path in [('baseline', settings['inputs']['baseline_calibration']),
                       ('candidate', settings['candidate_calibration'])]:
        artifact = load_calibration(path)
        saved = torch.load(artifact['checkpoint'], map_location='cpu', weights_only=True)
        config = saved['config']
        if file_hash(config['data']['metadata_csv']) != artifact['metadata_sha256']:
            raise ValueError('checkpoint fitting metadata hash mismatch')
        checkpoint_anonymizer(config, required=name == 'candidate')
        if name == 'candidate':
            if artifact['metadata_sha256'] != registration['inputs_sha256']['metadata']:
                raise ValueError('candidate calibration metadata hash mismatch')
            if config['anonymization'] != bind_spec(spec):
                raise ValueError('candidate anonymization mismatch')
            if training_result['artifact_sha256'].get(artifact['checkpoint']) != artifact['checkpoint_sha256']:
                raise ValueError('candidate checkpoint differs from fixed training result')
        else:
            original = shared.read_csv(config['data']['metadata_csv'])
            by_id = {r['image_id']: r for r in original}
            if len(by_id) != len(original) or set(by_id) != set(current_by_id):
                raise ValueError('baseline/evaluation metadata identity mismatch')
            for image_id, row in current_by_id.items():
                source = by_id[image_id]
                if set(row) != set(source):
                    raise ValueError('baseline/evaluation metadata columns mismatch')
                for key, value in source.items():
                    if key == 'split' or (key == 'look_group' and source['source_type'] == 'real'):
                        continue
                    if row[key] != value:
                        raise ValueError(f'baseline/evaluation immutable metadata changed: {image_id}:{key}')
        artifacts[name], configs[name] = artifact, config
    return artifacts, configs


def preflight(config_path):
    state = shared.preflight(config_path, artifact_loader=load_artifacts)
    identity = state['identity']
    identity['source_sha256'][str(Path(__file__))] = file_hash(__file__)
    identity['evaluation_metadata_sha256'] = state['registration']['inputs_sha256']['metadata']
    identity['fitting_metadata_sha256'] = {name: value['metadata_sha256'] for name, value in state['artifacts'].items()}
    identity['training_result_sha256'] = file_hash(Path(state['settings']['output_dir']).parent/'training/result.json')
    return state


def run(config_path, device):
    return shared.run(config_path, device, preflight_fn=preflight)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/p09_r1_diagnostic.yaml')
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    run(args.config, args.device)


if __name__ == '__main__':
    main()

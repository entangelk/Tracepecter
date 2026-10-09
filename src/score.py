"""학습된 checkpoint + calibration artifact로 이미지의 0~100 score를 출력한다."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
from PIL import Image

from src.calibration import apply_temperature
from src.dataset import build_transform
from src.evaluate import load_model, file_sha256


def load_calibration(path) -> dict:
    artifact = json.loads(Path(path).read_text())
    if artifact['version'] != 1 or artifact['method'] != 'temperature_scaling':
        raise ValueError('unsupported calibration artifact')
    if file_sha256(artifact['checkpoint']) != artifact['checkpoint_sha256']:
        raise ValueError('calibration checkpoint hash mismatch')
    if not math.isfinite(artifact['temperature']) or artifact['temperature'] <= 0:
        raise ValueError('invalid calibration temperature')
    if not math.isfinite(artifact['threshold_probability']) or not 0 <= artifact['threshold_probability'] <= 1:
        raise ValueError('invalid probability threshold')
    return artifact


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='Photographic Realism Score')
    parser.add_argument('--image', required=True)
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args(argv)
    artifact = load_calibration(args.calibration)
    model, config = load_model(artifact['checkpoint'], args.device)
    mc = config['model']
    transform = build_transform(mc['image_size'], False, False, normalization=mc.get('normalization'))
    with Image.open(args.image) as handle:
        image = transform(handle.convert('RGB')).unsqueeze(0).to(args.device)
    with torch.inference_mode():
        logit = model.forward_logits(image).item()
    probability = float(apply_temperature([logit], artifact['temperature'])[0])
    result = dict(realism_score=100*probability,
                  classification='photographic_like' if probability >= artifact['threshold_probability'] else 'synthetic_like')
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return result


if __name__ == '__main__':
    main()

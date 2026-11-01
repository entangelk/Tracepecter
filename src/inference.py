"""P07-01: score CLI와 API가 공유하는 추론 코어. artifact·모델·익명화기는 생성 시 준비하고 요청마다 다시 읽지 않는다."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import torch

from src.anonymize import checkpoint_anonymizer
from src.calibration import apply_temperature
from src.dataset import build_transform
from src.evaluate import load_model, file_sha256


def load_calibration(path) -> dict:
    return validate_calibration(json.loads(Path(path).read_text()))


def validate_calibration(artifact) -> dict:
    if artifact['version'] != 1 or artifact['method'] != 'temperature_scaling':
        raise ValueError('unsupported calibration artifact')
    if file_sha256(artifact['checkpoint']) != artifact['checkpoint_sha256']:
        raise ValueError('calibration checkpoint hash mismatch')
    if not math.isfinite(artifact['temperature']) or artifact['temperature'] <= 0:
        raise ValueError('invalid calibration temperature')
    if not math.isfinite(artifact['threshold_probability']) or not 0 <= artifact['threshold_probability'] <= 1:
        raise ValueError('invalid probability threshold')
    return artifact


def model_version(checkpoint_sha256: str, calibration_sha256: str, anonymization_sha256: str) -> str:
    """checkpoint·calibration 파일·익명화 규격 sha256(hex)을 이 순서로 ':'로 이은 문자열의 sha256 hex 앞 12자리."""
    joined = ':'.join([checkpoint_sha256, calibration_sha256, anonymization_sha256])
    return hashlib.sha256(joined.encode()).hexdigest()[:12]


class Scorer:
    def __init__(self, calibration, device='cpu'):
        raw = Path(calibration).read_bytes()  # 검증한 내용과 model_version의 hash가 같은 바이트를 가리킨다
        artifact = validate_calibration(json.loads(raw))
        model, config = load_model(artifact['checkpoint'], device, require_anonymization=True)
        self.model, self.device = model, device
        self.anonymizer = checkpoint_anonymizer(config, required=True)
        mc = config['model']
        self.transform = build_transform(mc['image_size'], False, False, normalization=mc.get('normalization'))
        self.temperature = artifact['temperature']
        self.threshold = artifact['threshold_probability']
        self.model_version = model_version(artifact['checkpoint_sha256'], hashlib.sha256(raw).hexdigest(),
                                           config['anonymization']['sha256'])

    def __call__(self, image) -> dict:
        anonymized, faces = self.anonymizer(image.convert('RGB'))
        batch = self.transform(anonymized).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            logit = self.model.forward_logits(batch).item()
        probability = float(apply_temperature([logit], self.temperature)[0])
        if not math.isfinite(probability):
            raise ValueError('non-finite score')
        return dict(realism_score=100*probability,
                    classification='photographic_like' if probability >= self.threshold else 'synthetic_like',
                    faces_anonymized=faces, model_version=self.model_version)

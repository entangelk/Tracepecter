"""P08 공통 전처리: config snapshot·YuNet 전체 얼굴·검증된 좌표 캐시.

규격 정본은 configs/anonymize.yaml. checkpoint의 anonymization은
{spec: 전체 규격, sha256: canonical JSON 해시} 또는 명시적 null이다.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image

CACHE_FIELDS = ('image_id', 'image_sha256', 'detector_sha256', 'parameters_sha256', 'boxes')


def spec_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_spec(spec):
    """현재 측정·채택 규격의 필드와 범위를 검증한다(타원은 미채택)."""
    try:
        if set(spec) != {'face_detector', 'shape', 'diameter_per_face', 'fill', 'edge_sigma'}:
            raise ValueError
        face = spec['face_detector']
        if set(face) != {'model', 'model_sha256', 'score_threshold', 'nms_threshold', 'top_k', 'min_size_ratio'}:
            raise ValueError
        if not isinstance(face['model'], str) or not face['model']:
            raise ValueError
        digest = face['model_sha256']
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError
        for key, low, high in [('score_threshold', 0, 1), ('nms_threshold', 0, 1), ('min_size_ratio', 0, 1)]:
            value = face[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError
        if type(face['top_k']) is not int or face['top_k'] <= 0:
            raise ValueError
        if spec['shape'] != 'circle' or spec['fill'] != [255, 255, 255]:
            raise ValueError
        for key, low, high in [('diameter_per_face', 1.0, 1.6), ('edge_sigma', 0, math.inf)]:
            value = spec[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError
    except (TypeError, KeyError, ValueError):
        raise ValueError('invalid anonymization spec') from None


def bind_spec(spec) -> dict:
    validate_spec(spec)
    return dict(spec=copy.deepcopy(spec), sha256=spec_hash(spec))


def training_config(config) -> dict:
    """새 학습은 명시 설정 필수. 외부 YAML을 checkpoint snapshot으로 한 번 변환한다."""
    if 'anonymization' not in config:
        raise ValueError('training requires explicit anonymization (spec path or null)')
    result = copy.deepcopy(config)
    value = result['anonymization']
    if isinstance(value, str):
        result['anonymization'] = bind_spec(yaml.safe_load(Path(value).read_text()))
    checkpoint_anonymizer(result)
    return result


def checkpoint_anonymizer(config, *, required=False, cache_path=None, override=None):
    """legacy/null은 평가만 허용. override는 원본 checkpoint의 비교 평가 전용."""
    binding = config.get('anonymization')
    if binding is None:
        if required:
            raise ValueError('score requires anonymization in checkpoint')
        if override is None:
            if cache_path is not None:
                raise ValueError('face cache requires anonymization')
            return None
        binding = bind_spec(yaml.safe_load(Path(override).read_text()))
    elif override is not None:
        raise ValueError('cannot override checkpoint anonymization')
    return Anonymizer(binding, cache_path)


def validate_boxes(boxes):
    if not isinstance(boxes, list):
        raise ValueError('invalid cached face boxes')
    for box in boxes:
        if (not isinstance(box, list) or len(box) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
                or box[2] <= 0 or box[3] <= 0):
            raise ValueError('invalid cached face boxes')
    return boxes


def paint_circles(image, circles, fill, edge_sigma):
    """입력 순서의 (cx, cy, radius)를 공통 rasterization·Gaussian 커널로 덧칠한다."""
    rgb = np.asarray(image).copy()
    for cx, cy, radius in circles:
        mask = np.zeros(rgb.shape[:2], dtype=np.float32)
        cv2.ellipse(mask, (round(cx), round(cy)), (round(radius), round(radius)), 0, 0, 360, 1.0, -1)
        if edge_sigma > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), edge_sigma)
        rgb = (rgb * (1 - mask[..., None]) + np.asarray(fill, dtype=np.float32) * mask[..., None]).round().astype(np.uint8)
    return Image.fromarray(rgb)


class Anonymizer:
    def __init__(self, binding, cache_path=None):
        if not isinstance(binding, dict) or set(binding) != {'spec', 'sha256'}:
            raise ValueError('invalid anonymization binding')
        validate_spec(binding['spec'])
        if spec_hash(binding['spec']) != binding['sha256']:
            raise ValueError('anonymization sha256 mismatch')
        self.spec = copy.deepcopy(binding['spec'])
        face = self.spec['face_detector']
        try:
            digest = file_hash(face['model'])
        except OSError as exc:
            raise ValueError('face detector model unavailable') from exc
        if digest != face['model_sha256']:
            raise ValueError('face detector model sha256 mismatch')
        self.detector_hash = digest
        # 경로는 배포 위치이고 모델 identity는 별도 키다. 검출 파라미터만 해시한다.
        self.parameters_hash = spec_hash({k: v for k, v in face.items() if k not in ('model', 'model_sha256')})
        self.cache = None
        if cache_path is not None:
            self.cache = {}
            with open(cache_path, newline='', encoding='utf-8') as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != list(CACHE_FIELDS):
                    raise ValueError('invalid face cache columns')
                for row in reader:
                    if not row['image_id'] or row['image_id'] in self.cache:
                        raise ValueError('duplicate or empty face cache image_id')
                    if row['detector_sha256'] != digest or row['parameters_sha256'] != self.parameters_hash:
                        raise ValueError('face cache detector/parameters hash mismatch')
                    row['boxes'] = validate_boxes(json.loads(row['boxes']))
                    self.cache[row['image_id']] = row

    def detect(self, image):
        rgb = np.asarray(image)
        height, width = rgb.shape[:2]
        settings = self.spec['face_detector']
        detector = cv2.FaceDetectorYN.create(settings['model'], '', (width, height),
                                            settings['score_threshold'], settings['nms_threshold'], settings['top_k'])
        _, faces = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        boxes = [] if faces is None else [list(map(float, f[:4])) for f in faces
                                         if max(f[2], f[3]) >= width * settings['min_size_ratio']]
        # 같은 얼굴 집합의 순서가 바뀌어도 겹침 영역의 반올림 결과를 고정한다.
        return sorted(validate_boxes(boxes))

    def boxes(self, image, image_id=None, image_path=None):
        if self.cache is None:
            return self.detect(image)
        if image_id not in self.cache:
            raise ValueError(f'face cache row missing: {image_id}')
        row = self.cache[image_id]
        if image_path is None or file_hash(image_path) != row['image_sha256']:
            raise ValueError(f'face cache image hash mismatch: {image_id}')
        return row['boxes']

    def __call__(self, image, image_id=None, image_path=None):
        boxes = self.boxes(image, image_id, image_path)
        if not boxes:
            return image, 0
        circles = [(x+w/2, y+h/2, self.spec['diameter_per_face']*max(w, h)/2) for x, y, w, h in sorted(boxes)]
        return paint_circles(image, circles, self.spec['fill'], self.spec['edge_sigma']), len(boxes)


def write_face_cache(images, binding, output):
    """metadata 전체 좌표를 LF CSV에 저장. 기존 행은 해시 확인 후 건너뛰어 재개한다."""
    output = Path(output)
    worker = Anonymizer(binding, output if output.exists() else None)
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = worker.cache or {}
    seen = set()
    with output.open('a', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=CACHE_FIELDS, lineterminator='\n')
        if handle.tell() == 0:
            writer.writeheader()
        for image_id, path in images:
            if image_id in seen:
                raise ValueError('duplicate metadata image_id')
            seen.add(image_id)
            if image_id in existing:
                worker.boxes(None, image_id, path)
                continue
            with Image.open(path) as handle_image:
                image = handle_image.convert('RGB')
            boxes = worker.detect(image)
            writer.writerow(dict(image_id=image_id, image_sha256=file_hash(path),
                                 detector_sha256=worker.detector_hash, parameters_sha256=worker.parameters_hash,
                                 boxes=json.dumps(boxes, separators=(',', ':'), allow_nan=False)))
            handle.flush()
        if set(existing) - seen:
            raise ValueError('face cache contains images outside metadata')


def main(argv=None):
    from src.dataset import MetadataDataset
    parser = argparse.ArgumentParser(description='P08 all-face coordinate cache (CPU)')
    parser.add_argument('--config', default='configs/anonymize.yaml')
    parser.add_argument('--metadata', default='data/metadata.csv')
    parser.add_argument('--image-root', default='/images')
    parser.add_argument('--output', default='experiments/p08_anonymized/face_boxes.csv')
    args = parser.parse_args(argv)
    binding = bind_spec(yaml.safe_load(Path(args.config).read_text()))
    dataset = MetadataDataset(args.metadata, 224, False, False, image_root=args.image_root)
    write_face_cache(((row.image_id, dataset.image_path(i)) for i, row in enumerate(dataset.rows)), binding, args.output)
    print(f'face cache: {len(dataset)} images → {args.output}')


if __name__ == '__main__':
    main()

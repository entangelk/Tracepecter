"""학습된 checkpoint + calibration artifact로 이미지의 0~100 score를 출력한다."""
from __future__ import annotations

import argparse
import json

from PIL import Image

from src.inference import Scorer, load_calibration  # noqa: F401  load_calibration은 기존 import 경로 유지


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='Photographic Realism Score')
    parser.add_argument('--image', required=True)
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args(argv)
    scorer = Scorer(args.calibration, args.device)
    with Image.open(args.image) as handle:
        result = scorer(handle)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return result


if __name__ == '__main__':
    main()

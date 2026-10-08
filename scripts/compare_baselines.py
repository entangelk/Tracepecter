"""P03: 고정된 두 checkpoint의 GPU forward latency와 크기를 비교한다."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import torch

from src.model import RealismScorer, build_encoder, set_encoder_frozen


def select_primary(results: list[dict], auc_margin: float) -> str:
    """실험 전 기록한 validation/latency 규칙만 사용한다(test metric은 입력 아님)."""
    high = max(results, key=lambda r: r['validation_roc_auc'])
    low = min(results, key=lambda r: r['validation_roc_auc'])
    if high['validation_roc_auc'] - low['validation_roc_auc'] >= auc_margin:
        return high['encoder']
    return min(results, key=lambda r: (r['latency_median_ms'], r['parameter_count']))['encoder']


def benchmark(checkpoint: str, device: str, warmup: int, repeats: int) -> dict:
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    mc = saved['config']['model']
    encoder = build_encoder(mc['encoder'], mc.get('embedding_dim', 64), mc.get('model_id'), mc.get('revision'))
    model = RealismScorer(encoder, encoder.embedding_dim)
    model.load_state_dict(saved['model_state'])
    set_encoder_frozen(model, True)
    model.to(device).eval()
    torch.manual_seed(0)
    images = torch.randn(1, 3, mc['image_size'], mc['image_size'], device=device)
    synchronize = (lambda: torch.cuda.synchronize(device)) if device.startswith('cuda') else (lambda: None)
    samples = []
    with torch.inference_mode():
        for _ in range(warmup):
            model(images)
        synchronize()
        for _ in range(repeats):
            synchronize()
            start = time.perf_counter_ns()
            model(images)
            synchronize()
            samples.append((time.perf_counter_ns() - start) / 1_000_000)
    result = dict(encoder=mc['encoder'], checkpoint=checkpoint, config=saved['config'],
                  best_epoch=saved['epochs_done'], validation_roc_auc=saved['validation_metrics']['roc_auc'],
                  parameter_count=sum(p.numel() for p in model.parameters()),
                  checkpoint_bytes=Path(checkpoint).stat().st_size,
                  latency_median_ms=statistics.median(samples), latency_samples_ms=samples)
    del model, encoder, saved
    if device.startswith('cuda'):
        torch.cuda.empty_cache()
    return result


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description='P03 baseline comparison')
    parser.add_argument('--checkpoints', nargs=2, required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--warmup', type=int, default=10)
    parser.add_argument('--repeats', type=int, default=100)
    parser.add_argument('--auc-margin', type=float, default=0.001)
    args = parser.parse_args(argv)
    if args.repeats < 1 or args.warmup < 0:
        parser.error('repeats must be positive and warmup nonnegative')
    results = [benchmark(path, args.device, args.warmup, args.repeats) for path in args.checkpoints]
    result = dict(device=args.device, warmup=args.warmup, repeats=args.repeats,
                  dtype='float32', batch_size=1, includes_preprocessing=False,
                  auc_margin=args.auc_margin, primary_encoder=select_primary(results, args.auc_margin),
                  models=results)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print('primary encoder:', result['primary_encoder'])
    return result


if __name__ == '__main__':
    main()

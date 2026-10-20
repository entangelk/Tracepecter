"""Create hash-checked contact sheets for a bounded P09 REAL review batch."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from scripts.p09_group_candidates import read_csv, sha256, verify_audit_lock, write_csv
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--image-root', type=Path, required=True)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int, default=48)
    args = parser.parse_args()
    if args.out.exists() or args.start < 0 or args.count < 1:
        raise ValueError('output exists or invalid review range')
    audit_root = Path('experiments/p08_anonymized/leakage_audit')
    verify_audit_lock(audit_root/'audit_lock.json')
    lock = json.loads((args.run/'input_lock.json').read_text())
    for name, expected in lock['outputs_sha256'].items():
        if sha256(args.run/name) != expected:
            raise ValueError(f'candidate artifact hash mismatch: {name}')
    meta = {r['image_id']: r for r in read_csv('data/metadata.csv')}
    images = {r['image_id']: r for r in map(json.loads, (audit_root/'image_audit.jsonl').read_text().splitlines())}
    seeds = {tuple(sorted((r['a'], r['b']))) for r in read_csv(args.run/'seed_review.csv')}
    eligible = [r for r in read_csv(args.run/'priority_candidates.csv')
                if all(meta[r[k]]['label'] == '1' for k in ('a', 'b'))
                and meta[r['a']]['look_group'] != meta[r['b']]['look_group']
                and (r['a'], r['b']) not in seeds]
    pairs = eligible[args.start:args.start+args.count]
    if not pairs:
        raise ValueError('empty review batch')
    args.out.mkdir(parents=True)
    write_csv(args.out/'pairs.csv', pairs, list(pairs[0]))
    font = ImageFont.load_default(size=16)
    for start in range(0, len(pairs), 8):
        canvas = Image.new('RGB', (1200, 1240), '#ddd')
        draw = ImageDraw.Draw(canvas)
        for n, pair in enumerate(pairs[start:start+8]):
            x, y = (n % 2)*600, (n // 2)*310
            title = f"{args.start+start+n+1}. {pair['a']} / {pair['b']} cos={float(pair['cosine']):.4f} d={pair['phash_distance']}"
            draw.text((x+6, y+2), title, font=font, fill='black')
            for side, key in enumerate(('a', 'b')):
                image_id = pair[key]
                path = args.image_root/Path(meta[image_id]['path']).relative_to('images')
                if sha256(path) != images[image_id]['sha256']:
                    raise ValueError(f'original image hash mismatch: {image_id}')
                with Image.open(path) as image:
                    thumb = ImageOps.contain(image.convert('RGB'), (285, 278))
                    canvas.paste(thumb, (x+side*300+(300-thumb.width)//2, y+28))
        canvas.save(args.out/f'{start:03}.jpg', quality=95)
    print(f'{len(pairs)} pairs from {len(eligible)} eligible REAL candidates: {args.out}')


if __name__ == '__main__':
    main()

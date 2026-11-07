"""P10-02: render hash-checked side-by-side sheets for the P10 selection (P09 layout)."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from scripts.p09_group_candidates import read_csv, sha256, write_json

AUDIT = Path('experiments/p08_anonymized/leakage_audit/image_audit.jsonl')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--image-root', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists; use a new directory, never overwrite')
    lock = json.loads((args.selection/'input_lock.json').read_text())
    for name, expected in lock['outputs_sha256'].items():
        if sha256(args.selection/name) != expected:
            raise ValueError(f'selection hash mismatch: {name}')
    meta = {r['image_id']: r for r in read_csv('data/versions/p09_r1/metadata.csv')}
    images = {r['image_id']: r for r in map(json.loads, AUDIT.read_text().splitlines())}
    pairs = read_csv(args.selection/'pairs.csv')
    args.out.mkdir(parents=True)
    font = ImageFont.load_default(size=16)
    for start in range(0, len(pairs), 8):
        canvas = Image.new('RGB', (1200, 1240), '#ddd')
        draw = ImageDraw.Draw(canvas)
        for n, pair in enumerate(pairs[start:start+8]):
            x, y = (n % 2)*600, (n // 2)*310
            title = f"{start+n+1}. {pair['a']} / {pair['b']} cos={float(pair['cosine']):.4f} {pair['stratum']}"
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
    write_json(args.out/'sheets_lock.json', dict(selection_lock_sha256=sha256(args.selection/'input_lock.json'),
                                                source_sha256=sha256(__file__),
                                                sheets_sha256={p.name: sha256(p) for p in sorted(args.out.glob('*.jpg'))}))
    print(f'{len(pairs)} pairs, {len(list(args.out.glob("*.jpg")))} sheets: {args.out}')


if __name__ == '__main__':
    main()

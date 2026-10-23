"""Render score-blind P09 review sheets; preserve original/anonymous pairs for zooming."""
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from scripts.p08_face_review import load, pair_image, read_csv, template_ids

ROOT = Path('experiments/p09_leakage_repair/r1/diagnostic')
OUTPUT = Path('reports/errors/review/p09_leakage_repair/r1/face_review')


def main():
    settings, meta, worker = load('configs/p09_r1_diagnostic.yaml')
    prior = {r['image_id'] for r in read_csv(ROOT/'prior_face_review.csv')}
    ids = sorted(set(template_ids(settings))-prior)
    if OUTPUT.exists():
        raise ValueError('review output exists; preserve rendered evidence')
    OUTPUT.mkdir(parents=True)
    (OUTPUT/'pairs').mkdir()
    font = ImageFont.load_default(size=19)
    catalog = []
    for start in range(0, len(ids), 8):
        sheet = Image.new('RGB', (1440, 1760), 'white')
        draw = ImageDraw.Draw(sheet)
        for n, image_id in enumerate(ids[start:start+8]):
            row = meta[image_id]
            path = Path('/images')/Path(row['path']).relative_to('images')
            with Image.open(path) as handle:
                original = handle.convert('RGB')
            masked, _ = worker(original, image_id, path)
            pair_image(row, worker).save(OUTPUT/'pairs'/f'{image_id}.jpg', quality=95)
            x, y = (n%2)*720, (n//2)*440
            draw.text((x+6, y+4), f'{start+n:03} {image_id} {row["generator"]}', fill='black', font=font)
            for column, image in enumerate((original, masked)):
                view = ImageOps.contain(image, (236, 385))
                sheet.paste(view, (x+column*240, y+35))
                crop = image.crop((0, 0, image.width, round(image.height*.45)))
                crop = ImageOps.contain(crop, (236, 185))
                sheet.paste(crop, (x+480, y+35+column*195))
            catalog.append(dict(image_id=image_id, sheet=f'{start//8:03}.jpg', position=n, generator=row['generator']))
        sheet.save(OUTPUT/f'{start//8:03}.jpg', quality=95)
    with (OUTPUT/'catalog.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, ['image_id', 'sheet', 'position', 'generator'])
        writer.writeheader()
        writer.writerows(catalog)
    print(f'{len(ids)} images, {(len(ids)+7)//8} sheets; model scores excluded')


if __name__ == '__main__':
    main()

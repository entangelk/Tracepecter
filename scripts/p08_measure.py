"""P08-01: K-Fashion 흰 원 규격과 YuNet 재현율 관문을 잰다(이미지만 사용, 모델 결과 없음).

설정은 configs/anonymize_measure.yaml(측정 전 고정). 단계:
  candidates : REAL train 무작위 순서로 흰 원 후보를 만들고 확인용 시트를 그린다.
  missed     : 후보가 없던 이미지에서 무작위로 골라 누락 원 확인용 시트를 그린다.
  measure    : 사람 확인 결과로 원 규격과 재현율 관문을 계산하고 소유자 확인 목록을 만든다.
  recall     : 재현율 표본 목록과 블라인드 시트(검출 상자 없음)를 만든다.
  owner      : 소유자 확인 대상의 블라인드 검토 페이지와 빈 CSV 양식을 만든다.
실행: docker compose --profile training run --rm -T train python -m scripts.p08_measure <단계> [--sheets DIR]
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import random
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw

from src.face_mask_ci import detect_face
from scripts.p06_patterns import wilson

CONFIG = 'configs/anonymize_measure.yaml'
METADATA = 'data/metadata.csv'
IMAGE_ROOT = Path('/images')
REVIEW_SET = 'reports/errors/review_set.csv'
OWNER_SUFFIX = {'train_gen': '', 'test_gen_sd35': '_sd35'}


def white_mask(rgb: np.ndarray, white_min: int) -> np.ndarray:
    return (rgb.min(axis=2) >= white_min).astype(np.uint8)


def disc_candidates(rgb: np.ndarray, white_min: int, min_area_ratio: float, min_fill: float) -> list[dict]:
    """순백 연결 성분 중 면적·타원 채움률을 만족하는 것. 타원은 (cx, cy, 장축, 단축, 각도)."""
    width = rgb.shape[1]
    count, labels, stats, _ = cv2.connectedComponentsWithStats(white_mask(rgb, white_min), 8)
    found = []
    for k in range(1, count):
        if stats[k, cv2.CC_STAT_AREA] < min_area_ratio * width * width:
            continue
        contours, _ = cv2.findContours((labels == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contour = max(contours, key=cv2.contourArea)
        if len(contour) < 5:
            continue
        (cx, cy), (a, b), angle = cv2.fitEllipse(contour)
        fill = cv2.contourArea(contour) / (math.pi * a * b / 4) if a and b else 0.0
        if fill >= min_fill:
            found.append(dict(cx=cx, cy=cy, axis_a=a, axis_b=b, major=max(a, b), minor=min(a, b), angle=angle, fill=fill))
    return found


def ellipse_radius(major: float, minor: float, angle_deg: float, theta: float) -> float:
    """중심에서 방향 theta(라디안)로 갔을 때 타원 경계까지의 거리. angle_deg는 major 축의 방향."""
    a, b = major / 2, minor / 2
    phi = theta - math.radians(angle_deg)
    return a * b / math.hypot(b * math.cos(phi), a * math.sin(phi))


def major_angle(disc: dict) -> float:
    """cv2.fitEllipse 각도는 첫 번째 축(axis_a) 방향이다. major 축 방향으로 바꾼다."""
    return disc['angle'] if disc.get('axis_a', disc['major']) >= disc.get('axis_b', disc['minor']) else disc['angle'] + 90


def transition_width(profile: np.ndarray, min_contrast: float = 30.0) -> float | None:
    """10–90% 전이 폭(px, 1px 간격 단면). 안쪽·바깥 수준은 양 끝 3점 중앙값. 대비가 작으면 None."""
    inner, outer = float(np.median(profile[:3])), float(np.median(profile[-3:]))
    delta = inner - outer
    if delta < min_contrast:
        return None
    low, high = outer + 0.1 * delta, inner - 0.1 * delta
    return float(((profile > low) & (profile < high)).sum())


def disc_edge_width(rgb: np.ndarray, disc: dict, angles: int) -> float | None:
    """원 경계의 10–90% 전이 폭: 방향별 값의 중앙값. 유효 방향이 4분의 1 미만이면 None."""
    darkest = rgb.min(axis=2).astype(float)
    height, width = darkest.shape
    widths = []
    for theta in np.linspace(0, 2 * math.pi, angles, endpoint=False):
        r = ellipse_radius(disc['major'], disc['minor'], major_angle(disc), theta)
        steps = np.arange(0.8 * r, 1.2 * r + 1e-9, 1.0)
        xs = np.clip(np.round(disc['cx'] + steps * math.cos(theta)).astype(int), 0, width - 1)
        ys = np.clip(np.round(disc['cy'] + steps * math.sin(theta)).astype(int), 0, height - 1)
        value = transition_width(darkest[ys, xs])
        if value is not None:
            widths.append(value)
    return float(np.median(widths)) if len(widths) >= angles / 4 else None


def paint_synthetic(rgb: np.ndarray, face, k: float, ellipse: bool, sigma: float) -> tuple[np.ndarray, dict]:
    """얼굴 상자 중심에 흰 원(또는 상자 비례 타원)을 Gaussian blur 알파로 칠한다."""
    x, y, w, h = face
    major = k * max(w, h)
    axes = (k * w / 2, k * h / 2) if ellipse else (major / 2, major / 2)
    mask = np.zeros(rgb.shape[:2], dtype=np.float32)
    cv2.ellipse(mask, (round(x + w / 2), round(y + h / 2)), (round(axes[0]), round(axes[1])), 0, 0, 360, 1.0, -1)
    if sigma > 0:
        mask = cv2.GaussianBlur(mask, (0, 0), sigma)
    painted = (rgb * (1 - mask[..., None]) + 255 * mask[..., None]).round().astype(np.uint8)
    disc = dict(cx=x + w / 2, cy=y + h / 2, major=2 * max(axes), minor=2 * min(axes),
                angle=0.0 if axes[0] >= axes[1] else 90.0)
    return painted, disc


def quartiles(values) -> list[float]:
    return [float(v) for v in np.percentile(values, [25, 50, 75])]


def size_match(real_ratios, face_ratios, tolerance: float, k_min: float, k_max: float, k=None) -> dict:
    """기본 k는 중앙값 비율이며 명시적 k도 같은 사전 분포·허용 범위 기준으로 판정한다."""
    real_q, face_q = quartiles(real_ratios), quartiles(face_ratios)
    k = real_q[1] / face_q[1] if k is None else k
    synthetic_q = [k * q for q in face_q]
    within = [abs(s - r) / r <= tolerance for s, r in zip(synthetic_q, real_q)]
    return dict(k=k, real_quartiles=real_q, synthetic_quartiles=synthetic_q, within=within,
                k_in_range=k_min <= k <= k_max, passed=all(within) and k_min <= k <= k_max)


def recall_gate(labels: list[int], detected: list[bool], min_recall: float, min_positives: int) -> dict:
    positives = [d for label, d in zip(labels, detected) if label]
    hits = sum(positives)
    n = len(positives)
    recall = hits / n if n else None
    return dict(positives=n, detected=hits, recall=recall, ci95=wilson(hits, n),
                passed=bool(n >= min_positives and recall >= min_recall))


def read_owner_labels(path: Path, allowed_ids: set[str]) -> dict[str, int]:
    if not path.exists():
        return {}
    owner = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            image_id, value = row['image_id'], row['owner_face_visible']
            if image_id not in allowed_ids or image_id in owner or value not in ('0', '1'):
                raise ValueError(f'invalid owner label: {image_id}={value!r}')
            owner[image_id] = int(value)
    return owner


def recall_summary(rows, detected, owner, required_ids, min_recall, min_positives, gate_applies):
    final = [owner.get(r['image_id'], int(r['agent_face_visible'])) for r in rows]
    result = recall_gate(final, detected, min_recall, min_positives)
    missing = sorted(set(required_ids) - owner.keys())
    reviewed = any(r['image_id'] in owner for r in rows)
    labels = 'owner_final' if not missing and (gate_applies or reviewed) else 'owner_partial' if reviewed else 'agent_only'
    return dict(result, point_gate_passed=result['passed'],
                passed=result['passed'] if gate_applies and not missing else None,
                gate_applies=gate_applies, labels=labels, owner_review_missing=missing, n=len(rows))


def owner_check_rows(rows, detected, gate):
    disagree = [r['image_id'] for r, d in zip(rows, detected) if int(r['agent_face_visible']) != d]
    disagree_ids = set(disagree)
    rest = [r['image_id'] for r in rows if r['image_id'] not in disagree_ids]
    extra = random.Random(gate['seed']).sample(rest, round(gate['owner_random_fraction'] * len(rest)))
    return [dict(image_id=i, reason='disagreement') for i in disagree] + \
           [dict(image_id=i, reason='random') for i in extra]


def owner_stage(settings, meta, output: Path, sheets: Path, max_images: int, pool='train_gen'):
    """검출·에이전트 표시를 숨긴 원본 검토 페이지와 빈 소유자 CSV 양식을 만든다."""
    suffix = OWNER_SUFFIX[pool]
    labels = [r for r in csv.DictReader(open(output / 'recall_labels_agent.csv')) if r['pool'] == pool]
    detected = {r['image_id']: bool(int(r['yunet_detected']))
                for r in csv.DictReader(open(output / 'recall_detections.csv')) if r['pool'] == pool}
    rows = owner_check_rows(labels, [detected[r['image_id']] for r in labels], settings['recall_gate'])
    with (output / f'recall_owner_check{suffix}.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['image_id', 'reason'])
        writer.writeheader()
        writer.writerows(rows)
    cases = []
    for row in rows:
        buffer = io.BytesIO()
        Image.fromarray(load_rgb(meta[row['image_id']])).save(buffer, format='JPEG', quality=95)
        cases.append(dict(image_id=row['image_id'], image=base64.b64encode(buffer.getvalue()).decode('ascii')))
    template = Path(__file__).with_name('p08_owner_review.html').read_text()
    sheets.mkdir(parents=True, exist_ok=True)
    page = sheets / 'index.html'
    page.write_text(template.replace('/*CASES*/null', json.dumps(cases).replace('</', '<\\/'))
                   .replace('/*DOWNLOAD_NAME*/"recall_labels_owner.csv"',
                            json.dumps(f'recall_labels_owner{suffix}.csv')))
    with (output / f'recall_labels_owner_template{suffix}.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['image_id', 'owner_face_visible'])
        writer.writeheader()
        writer.writerows(dict(image_id=r['image_id'], owner_face_visible='') for r in rows)
    print(f'{page}: {len(rows)} images')


def seeded_order(ids, seed: int) -> list[str]:
    order = sorted(ids)
    random.Random(seed).shuffle(order)
    return order


def load_rgb(row) -> np.ndarray:
    with Image.open(IMAGE_ROOT / Path(row['path']).relative_to('images')) as handle:
        return np.asarray(handle.convert('RGB'))


def _sheet(tiles, path, columns=6, size=260):
    rows = max(1, math.ceil(len(tiles) / columns))
    sheet = Image.new('RGB', (columns * size, rows * (size + 20)), 'white')
    for i, (image, label) in enumerate(tiles):
        image.thumbnail((size, size))
        x, y = (i % columns) * size, (i // columns) * (size + 20)
        sheet.paste(image, (x, y))
        ImageDraw.Draw(sheet).text((x + 4, y + size + 2), label, fill=(0, 0, 0))
    sheet.save(path, quality=85)


def candidates_stage(settings, meta, output: Path, sheets: Path, max_images: int):
    spec = settings['real_discs']
    review = {r['image_id'] for r in csv.DictReader(open(REVIEW_SET))}
    ids = [i for i, r in meta.items() if r['label'] == '1' and r['split'] == spec['split'] and i not in review]
    order = seeded_order(ids, spec['seed'])
    rows, tiles, batch = [], [], 0
    for rank, image_id in enumerate(order):
        rgb = load_rgb(meta[image_id])
        found = disc_candidates(rgb, spec['white_min'], spec['min_area_ratio'], spec['min_fill'])
        for j, d in enumerate(found):
            cid = f'{rank:04d}_{j}'
            rows.append(dict(candidate_id=cid, rank=rank, image_id=image_id, width=rgb.shape[1], **{
                k: round(v, 3) for k, v in d.items()}))
            view = rgb.copy()
            cv2.ellipse(view, ((d['cx'], d['cy']), (d['axis_a'], d['axis_b']), d['angle']), (255, 0, 0), 1)
            half = int(1.6 * d['major'])
            box = (max(0, int(d['cx']) - half), max(0, int(d['cy']) - half),
                   min(rgb.shape[1], int(d['cx']) + half), min(rgb.shape[0], int(d['cy']) + half))
            crop = Image.fromarray(view).crop(box)
            tiles.append((crop, f"{cid} {image_id} r{d['minor'] / d['major']:.2f}"))
        if len(tiles) >= 36:
            _sheet(tiles, sheets / f'disc_candidates_{batch:02d}.jpg')
            tiles, batch = [], batch + 1
        if rank + 1 >= max_images:
            break
    if tiles:
        _sheet(tiles, sheets / f'disc_candidates_{batch:02d}.jpg')
    with (output / 'real_disc_candidates.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / 'real_disc_order.json').write_text(json.dumps(order[:rank + 1]) + '\n')
    print(f'images {rank + 1}, candidates {len(rows)}, sheets {batch + 1}')


def missed_stage(settings, meta, output: Path, sheets: Path, max_images: int):
    """확인이 끝난 순위까지 처리한 이미지 중 후보가 없던 것에서 무작위로 골라 누락 원을 사람이 센다."""
    spec = settings['real_discs']
    order = json.loads((output / 'real_disc_order.json').read_text())
    reviewed = list(csv.DictReader(open(output / 'real_disc_review.csv')))
    last = max(order.index(r['image_id']) for r in reviewed)
    with_candidates = {r['image_id'] for r in csv.DictReader(open(output / 'real_disc_candidates.csv'))}
    pool = [i for i in order[:last + 1] if i not in with_candidates]
    picked = random.Random(spec['seed']).sample(pool, spec['missed_check'])
    _sheet([(Image.fromarray(load_rgb(meta[i])), i) for i in picked], sheets / 'disc_missed_check.jpg', columns=10, size=200)
    (output / 'real_disc_missed_sample.json').write_text(json.dumps(dict(pool=len(pool), picked=picked), indent=1) + '\n')
    print(f'pool {len(pool)}, picked {len(picked)}')


def recall_stage(settings, meta, output: Path, sheets: Path, max_images: int):
    spec = settings['recall_gate']
    pools = dict(train_gen=[i for i, r in meta.items() if r['label'] == '0' and r['split'] == 'train'],
                 test_gen_sd35=[i for i, r in meta.items() if r['generator'] == 'sd35_medium'])
    sample = {}
    for name, ids in pools.items():
        order = seeded_order(ids, spec['seed'])
        size = spec['train_gen']['max'] if name == 'train_gen' else spec['test_gen_sd35']
        sample[name] = order[:size]
        for batch in range(0, size, 30):
            _sheet([(Image.fromarray(load_rgb(meta[i])), i) for i in sample[name][batch:batch + 30]],
                   sheets / f'recall_{name}_{batch // 30:02d}.jpg', columns=6, size=300)
    (output / 'recall_sample.json').write_text(json.dumps(sample, indent=1) + '\n')
    print({k: len(v) for k, v in sample.items()})


def measure_stage(settings, meta, output: Path, sheets: Path, max_images: int):
    """사람 확인 결과로 원 규격(크기·모양·경계)과 YuNet 재현율 관문을 계산해 report.json에 쓴다."""
    face = settings['face_detector']
    spec, size_spec, edge_spec, gate = (settings[k] for k in ('real_discs', 'size_match', 'edge_match', 'recall_gate'))
    candidates = {r['candidate_id']: r for r in csv.DictReader(open(output / 'real_disc_candidates.csv'))}
    confirmed = [candidates[r['candidate_id']] for r in csv.DictReader(open(output / 'real_disc_review.csv'))
                 if r['confirmed'] == '1']
    discs, real_ratio, real_edges, on_disc = [], [], [], 0
    for row in confirmed:
        disc = {k: float(row[k]) for k in ('cx', 'cy', 'axis_a', 'axis_b', 'major', 'minor', 'angle')}
        rgb = load_rgb(meta[row['image_id']])
        real_ratio.append(disc['major'] / rgb.shape[1])
        edge = disc_edge_width(rgb, disc, edge_spec['angles'])
        if edge is not None:
            real_edges.append(edge)
        found = detect_face(rgb, **face)
        if found is not None:
            x, y, w, h = found
            on_disc += math.hypot(x + w / 2 - disc['cx'], y + h / 2 - disc['cy']) <= 1.5 * disc['major'] / 2
        discs.append(disc)
    ellipse_fraction = float(np.mean([d['minor'] / d['major'] < settings['ellipse_ratio'] for d in discs]))
    use_ellipse = ellipse_fraction >= settings['ellipse_fraction_gate']

    gen_train = sorted(i for i, r in meta.items() if r['label'] == '0' and r['split'] == 'train')
    faces = {}
    for image_id in gen_train:
        rgb = load_rgb(meta[image_id])
        found = detect_face(rgb, **face)
        if found is not None:
            faces[image_id] = (found, rgb.shape[1])
    face_ratio = [max(f[2], f[3]) / width for f, width in faces.values()]
    size = size_match(real_ratio, face_ratio, size_spec['tolerance'], size_spec['k_min'], size_spec['k_max'])
    selected = settings.get('selected_anonymization')
    if selected and (selected['face_detector'] != face or selected['shape'] != ('ellipse' if use_ellipse else 'circle')
                     or selected['fill'] != [255, 255, 255]
                     or not size_spec['k_min'] <= selected['diameter_per_face'] <= size_spec['k_max']):
        raise ValueError('selected anonymization does not match measured detector/shape/fill or allowed diameter')
    selected_size = size_match(real_ratio, face_ratio, size_spec['tolerance'], size_spec['k_min'], size_spec['k_max'],
                               k=selected['diameter_per_face']) if selected else size

    edge_sample = seeded_order(list(faces), edge_spec.get('seed', spec['seed']))[:100]
    real_edge = float(np.median(real_edges))
    sigma_widths, chosen = {}, None
    for sigma in edge_spec['sigma_grid']:
        widths = []
        for image_id in edge_sample:
            painted, disc = paint_synthetic(load_rgb(meta[image_id]), faces[image_id][0], selected_size['k'], use_ellipse, sigma)
            value = disc_edge_width(painted, disc, edge_spec['angles'])
            if value is not None:
                widths.append(value)
        sigma_widths[str(sigma)] = float(np.median(widths))
        if chosen is None and abs(sigma_widths[str(sigma)] - real_edge) <= edge_spec['tolerance_px']:
            chosen = sigma

    labels = list(csv.DictReader(open(output / 'recall_labels_agent.csv')))
    recall, checks, detections = {}, {}, []
    for pool in ('train_gen', 'test_gen_sd35'):
        rows = [r for r in labels if r['pool'] == pool]
        detected = []
        for r in rows:
            hit = detect_face(load_rgb(meta[r['image_id']]), **face) is not None
            detected.append(hit)
            detections.append(dict(pool=pool, image_id=r['image_id'], yunet_detected=int(hit)))
        owner = read_owner_labels(output / f'recall_labels_owner{OWNER_SUFFIX[pool]}.csv',
                                  {r['image_id'] for r in rows})
        checks[pool] = owner_check_rows(rows, detected, gate)
        recall[pool] = recall_summary(rows, detected, owner,
                                      [r['image_id'] for r in checks[pool]],
                                      gate['min_recall'], gate['min_positives'], pool == 'train_gen')
    with (output / 'recall_detections.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['pool', 'image_id', 'yunet_detected'])
        writer.writeheader()
        writer.writerows(detections)
    for pool, to_check in checks.items():
        with (output / f'recall_owner_check{OWNER_SUFFIX[pool]}.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['image_id', 'reason'])
            writer.writeheader()
            writer.writerows(to_check)

    report = dict(
        real_discs=dict(confirmed=len(discs), size_ratio_quartiles=quartiles(real_ratio),
                        ellipse_fraction=ellipse_fraction, use_ellipse=use_ellipse,
                        edge_width_median_px=real_edge, edge_measured=len(real_edges),
                        yunet_face_on_disc=dict(count=int(on_disc), of=len(discs))),
        synthetic=dict(gen_train_faces=len(faces), face_ratio_quartiles=quartiles(face_ratio), size_match=size,
                       selected_size=selected_size,
                       edge_sample=len(edge_sample), edge_width_by_sigma=sigma_widths, sigma=chosen,
                       edge_passed=chosen is not None),
        recall=recall, owner_check=len(checks['train_gen']),
        provenance=dict(measurement_config_sha256=hashlib.sha256(Path(CONFIG).read_bytes()).hexdigest(),
                        metadata_sha256=hashlib.sha256(Path(METADATA).read_bytes()).hexdigest(),
                        detector_sha256=face['model_sha256'], selected_anonymization=selected))
    (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=1))


def main(argv=None):
    parser = argparse.ArgumentParser(description='P08-01 measurement')
    parser.add_argument('stage', choices=['candidates', 'missed', 'recall', 'measure', 'owner'])
    parser.add_argument('--anonymization-config', type=Path, help='소유자 결정 후 규격(사전 측정 기준은 유지)')
    parser.add_argument('--sheets', default='/tmp/p08_sheets')
    parser.add_argument('--pool', choices=list(OWNER_SUFFIX), default='train_gen',
                        help='owner: 블라인드 검토 대상 (기본 train_gen)')
    parser.add_argument('--max-images', type=int, default=1200,
                        help='candidates: 후보를 만들 REAL 이미지 수 상한(앞에서부터 확인된 원 min_discs개를 쓰므로 결과에 영향 없음)')
    args = parser.parse_args(argv)
    settings = yaml.safe_load(Path(CONFIG).read_text())
    if args.anonymization_config:
        settings['selected_anonymization'] = yaml.safe_load(args.anonymization_config.read_text())
    face = settings['face_detector']
    if hashlib.sha256(Path(face['model']).read_bytes()).hexdigest() != face['model_sha256']:
        raise ValueError('face detector model sha256 mismatch')
    meta = {r['image_id']: r for r in csv.DictReader(open(METADATA))}
    output, sheets = Path(settings['output_dir']), Path(args.sheets)
    output.mkdir(parents=True, exist_ok=True)
    sheets.mkdir(parents=True, exist_ok=True)
    if args.stage == 'owner':
        owner_stage(settings, meta, output, sheets, args.max_images, pool=args.pool)
    else:
        dict(candidates=candidates_stage, missed=missed_stage, recall=recall_stage,
             measure=measure_stage)[args.stage](settings, meta, output, sheets, args.max_images)


if __name__ == '__main__':
    main()

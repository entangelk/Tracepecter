"""P08 누출 적대적 감사: 원본 지문·PNG 생성 계보·split 간 후보·단서 대조.

현재 metadata와 이미지만 읽고 별도 감사 artifact를 만든다. split은 변경하지 않는다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.deduplicate import compute_phash


def read_metadata():
    with open('data/metadata.csv',newline='') as handle:
        return list(csv.DictReader(handle))


def image_path(root,row):
    return root/Path(row['path']).relative_to('images')


def scan_images(rows,root,output):
    def scan(row):
        raw = image_path(root,row).read_bytes()
        with Image.open(io.BytesIO(raw)) as image:
            fmt,size = image.format,image.size
            rgb = image.convert('RGB')
            tiny = np.asarray(rgb.resize((224,224),Image.Resampling.BICUBIC),dtype=np.float64)/255
            gray = tiny.mean(2)
            gx,gy = np.abs(np.diff(gray,axis=1)),np.abs(np.diff(gray,axis=0))
            features = [*tiny.mean((0,1)).tolist(),*tiny.std((0,1)).tolist(),float(gx.mean()),float(gy.mean()),float((gx**2).mean()),float((gy**2).mean())]
            return dict(image_id=row['image_id'],sha256=hashlib.sha256(raw).hexdigest(),
                        rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),phash=f'{compute_phash(rgb):016x}',
                        width=size[0],height=size[1],format=fmt,bytes=len(raw),pixel_features=features)
    temporary = output/'image_audit.tmp'
    with temporary.open('w') as handle,ThreadPoolExecutor(max_workers=6) as pool:
        for n,row in enumerate(pool.map(scan,rows),1):
            handle.write(json.dumps(row)+'\n');handle.flush()
            if n%200==0:print(f'images {n}/{len(rows)}',flush=True)
    temporary.replace(output/'image_audit.jsonl')


def generation_provenance(rows,root,output):
    def scan(row):
        with Image.open(image_path(root,row)) as image:
            graph = json.loads(image.info['prompt'])
        texts,seeds = [],[]
        for node in graph.values():
            for key,value in node.get('inputs',{}).items():
                if key in ('text','prompt') and isinstance(value,str) and value.startswith('a person '):texts.append(value)
                if key in ('seed','noise_seed') and isinstance(value,int):seeds.append(value)
        if len(texts)!=1 or len(seeds)!=1:
            raise ValueError(f'unknown generation provenance: {row["image_id"]}')
        return dict(image_id=row['image_id'],generator=row['generator'],split=row['split'],prompt=texts[0],noise_seed=seeds[0])
    with ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(scan,[r for r in rows if r['label']=='0']))
    (output/'generation_provenance.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')


def cross_split_groups(rows,key):
    groups = defaultdict(list)
    for row in rows:groups[row[key]].append(row)
    return [v for v in groups.values() if len({r['split'] for r in v})>1]


def rank_auc(labels,scores):
    """감사 표본 최대1048장의 pairwise rank oracle. sigmoid/threshold에 의존하지 않는다."""
    y,s = np.asarray(labels),np.asarray(scores)
    real,gen = s[y==1,None],s[y==0][None,:]
    return float(((real>gen)+.5*(real==gen)).mean())


def nuisance_baseline(rows,features,shuffle=False):
    x = np.asarray(features,dtype=float)
    labels = np.array([int(r['label']) for r in rows])
    train = np.array([r['split']=='train' for r in rows])
    mean,std = x[train].mean(0),x[train].std(0)
    std[std<1e-12] = 1
    x = np.c_[np.ones(len(x)),(x-mean)/std]
    target = labels[train].copy()
    if shuffle:np.random.default_rng(20261020).shuffle(target)
    penalty = np.eye(x.shape[1])*.001;penalty[0,0] = 0
    beta = np.linalg.solve(x[train].T@x[train]+penalty,x[train].T@target)
    score = x@beta
    result = {}
    for cohort in ('val','standard','unseen'):
        indices = np.array([r['split']==('test' if cohort=='standard' else 'val') if cohort!='unseen'
                            else r['split']=='test_unseen' or (r['split']=='test' and r['label']=='1') for r in rows])
        result[cohort] = dict(count=int(indices.sum()),roc_auc=rank_auc(labels[indices],score[indices]),
                             accuracy=float(((score[indices]>=.5)==labels[indices]).mean()))
    return result


def summarize(metadata,output):
    audit = [json.loads(line) for line in (output/'image_audit.jsonl').read_text().splitlines()]
    images = {r['image_id']:r for r in audit}
    if len(images)!=len(audit) or set(images)!={r['image_id'] for r in metadata}:
        raise ValueError('audit image ID mismatch')
    rows = [dict(r,**images[r['image_id']]) for r in metadata]
    report = dict(metadata_sha256=hashlib.sha256(Path('data/metadata.csv').read_bytes()).hexdigest())
    for key in ('sha256','rgb_sha256'):
        groups = Counter(r[key] for r in rows)
        cross = cross_split_groups(rows,key)
        report[key] = dict(duplicate_groups=sum(n>1 for n in groups.values()),cross_split_groups=len(cross),
                           examples=[[r['image_id'] for r in group] for group in cross[:10]])
    hashes = [int(r['phash'],16) for r in rows]
    train = [i for i,r in enumerate(rows) if r['split']=='train']
    nearest,pairs = [],[]
    # 6000장으로 고정된 전수 O(N²) 64-bit 비교. 이미지 decode는 이중 루프 밖이다.
    for i,row in enumerate(rows):
        if row['split']!='train':
            distance,j = min(((hashes[i]^hashes[j]).bit_count(),j) for j in train)
            nearest.append(dict(image_id=row['image_id'],nearest_train=rows[j]['image_id'],distance=distance,label=row['label'],split=row['split']))
        for j in range(i):
            if row['split']!=rows[j]['split']:
                distance = (hashes[i]^hashes[j]).bit_count()
                if distance<=10:
                    pairs.append(dict(a=row['image_id'],b=rows[j]['image_id'],distance=distance,a_split=row['split'],b_split=rows[j]['split'],a_label=row['label'],b_label=rows[j]['label']))
    (output/'cross_split_phash.json').write_text(json.dumps(sorted(pairs,key=lambda r:r['distance']),indent=2)+'\n')
    (output/'nearest_train_phash.json').write_text(json.dumps(nearest,indent=2)+'\n')
    report['phash'] = dict(threshold=10,cross_split_pairs=len(pairs),by_label=dict(Counter(r['a_label']+'-'+r['b_label'] for r in pairs)),
        train_touching_pairs=sum('train' in (r['a_split'],r['b_split']) for r in pairs),
        nearest_train_test_within10=sum(r['distance']<=10 and r['split'] in ('test','test_unseen') for r in nearest))
    report['formats'] = dict(Counter(r['label']+':'+r['format'] for r in rows))
    report['dimensions'] = {label:Counter(str((r['width'],r['height'])) for r in rows if r['label']==label).most_common(12) for label in ('0','1')}
    report['nuisance_baselines'] = dict(
        header_dimensions_bytes=nuisance_baseline(rows,[[r['width'],r['height'],math.log(r['bytes'])] for r in rows]),
        resized_pixel_statistics=nuisance_baseline(rows,[r['pixel_features'] for r in rows]),
        resized_pixel_statistics_shuffled_train_labels=nuisance_baseline(rows,[r['pixel_features'] for r in rows],True))
    provenance = json.loads((output/'generation_provenance.json').read_text())
    report['generation_overlap'] = {}
    for keys in [('prompt',),('prompt','noise_seed'),('generator','prompt','noise_seed')]:
        known = {tuple(r[k] for k in keys) for r in provenance if r['split']=='train'}
        report['generation_overlap']['+'.join(keys)] = {
            split:dict(count=len(sample:=[r for r in provenance if r['split']==split]),
                       overlaps=sum(tuple(r[k] for k in keys) in known for r in sample))
            for split in ('val','test','test_unseen')}
    (output/'audit_summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,indent=2,ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image-root',type=Path,default=Path('/images'))
    parser.add_argument('--stage',choices=['all','scan','provenance','summary'],default='all')
    args = parser.parse_args()
    output = Path('experiments/p08_anonymized/leakage_audit');output.mkdir(exist_ok=True)
    rows = read_metadata()
    if args.stage in ('all','scan'):scan_images(rows,args.image_root,output)
    if args.stage in ('all','provenance'):generation_provenance(rows,args.image_root,output)
    if args.stage in ('all','summary'):summarize(rows,output)


if __name__ == '__main__':
    main()

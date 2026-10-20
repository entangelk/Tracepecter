"""누출 적대적 점검: 동결 embedding 최근접, 균일 재압축, 상수/셔플 대조.

모델·split·calibration은 읽기 전용이다. 임베딩 청크는 비추적 reports/에 보존한다.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from src.anonymize import checkpoint_anonymizer, file_hash
from src.calibration import apply_temperature
from src.dataset import MetadataDataset, build_transform
from src.evaluate import binary_metrics, evaluation_indices, load_model
from src.score import load_calibration

OUTPUT = Path('experiments/p08_anonymized/leakage_audit')
CACHE = Path('reports/errors/review/p08_leakage_probe')


class ProbeImages(Dataset):
    def __init__(self, base, indices, quality=None):
        self.base, self.indices, self.quality = base, indices, quality

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        i = self.indices[index]
        row = self.base.rows[i]
        path = self.base.image_path(i)
        with Image.open(path) as handle:
            image = handle.convert('RGB')
        image, _ = self.base.anonymizer(image,row.image_id,path)
        if self.quality is not None:
            image = image.resize((224,224),Image.Resampling.BICUBIC)
            buffer = io.BytesIO()
            image.save(buffer,format='JPEG',quality=self.quality,subsampling=2)
            buffer.seek(0)
            with Image.open(buffer) as handle:
                image = handle.convert('RGB')
        return self.base.transform(image)


def main():
    OUTPUT.mkdir(exist_ok=True)
    CACHE.mkdir(parents=True,exist_ok=True)
    artifact_path = Path('experiments/p08_anonymized/calibration/calibration.json')
    artifact = load_calibration(artifact_path)
    model,config = load_model(artifact['checkpoint'],'cuda',require_anonymization=True)
    assert file_hash(config['data']['metadata_csv']) == artifact['metadata_sha256']
    mc = config['model']
    worker = checkpoint_anonymizer(config,required=True,cache_path=config['data']['face_cache'])
    base = MetadataDataset(config['data']['metadata_csv'],mc['image_size'],False,False,
                           image_root=config['data']['image_root'],normalization=mc.get('normalization'),anonymizer=worker)
    identity = dict(checkpoint=artifact['checkpoint_sha256'],calibration=file_hash(artifact_path),
                    metadata=artifact['metadata_sha256'],cache=file_hash(config['data']['face_cache']),source=file_hash(__file__))
    lock = CACHE/'identity.json'
    if lock.exists() and json.loads(lock.read_text()) != identity:
        raise ValueError('probe cache identity mismatch')
    lock.write_text(json.dumps(identity,indent=2)+'\n')
    chunks = []
    with torch.inference_mode():
        for start in range(0,len(base),128):
            path = CACHE/f'{start:05}.npz'
            if not path.exists():
                indices = list(range(start,min(start+128,len(base))))
                loader = DataLoader(ProbeImages(base,indices),batch_size=32,num_workers=2,multiprocessing_context='spawn')
                features,logits = [],[]
                for images in loader:
                    f = model.encoder(images.to('cuda'))
                    z = model.head[:-1](f).squeeze(-1)
                    features.append(f.cpu().numpy());logits.extend(z.cpu().tolist())
                temporary = path.with_suffix('.tmp.npz')
                np.savez(temporary,features=np.concatenate(features),logits=logits)
                temporary.replace(path)
            with np.load(path) as chunk:
                chunks.append((chunk['features'],chunk['logits']))
            print(f'embeddings {min(start+128,len(base))}/{len(base)}',flush=True)
    embeddings = np.concatenate([c[0] for c in chunks]);logits = np.concatenate([c[1] for c in chunks])
    normalized = torch.tensor(embeddings,device='cuda')
    normalized = torch.nn.functional.normalize(normalized,dim=1)
    train = [i for i,r in enumerate(base.rows) if r.split=='train']
    heldout = [i for i,r in enumerate(base.rows) if r.split!='train']
    similarity = normalized[heldout]@normalized[train].T
    best,indices = similarity.max(dim=1)
    pairs = [dict(image_id=base.rows[i].image_id,split=base.rows[i].split,label=base.rows[i].label,
                  nearest_train=base.rows[train[j]].image_id,train_label=base.rows[train[j]].label,cosine=float(s))
             for i,j,s in zip(heldout,indices.cpu().tolist(),best.cpu().tolist())]
    (OUTPUT/'embedding_nearest_train.json').write_text(json.dumps(sorted(pairs,key=lambda r:-r['cosine']),indent=2)+'\n')
    standard,unseen = evaluation_indices(base.rows)
    cohorts = dict(standard=standard,unseen=unseen)
    def metrics(values):
        return {name:binary_metrics([base.rows[i].label for i in ids],apply_temperature([values[i] for i in ids],artifact['temperature']),artifact['threshold_probability'])
                for name,ids in cohorts.items()}
    result = dict(identity=identity,normal=metrics(dict(enumerate(logits))),
                  constant_input=metrics({i:0. for i in range(len(base))}),perturbations={})
    evaluation = sorted(set(standard)|set(unseen))
    for quality in [95,70]:
        path = OUTPUT/f'jpeg_q{quality}.csv'
        existing = {}
        if path.exists():
            existing = {r['image_id']:float(r['logit']) for r in csv.DictReader(path.open())}
        todo = [i for i in evaluation if base.rows[i].image_id not in existing]
        loader = DataLoader(ProbeImages(base,todo,quality),batch_size=32,num_workers=2,multiprocessing_context='spawn')
        with path.open('a',newline='') as handle,torch.inference_mode():
            writer = csv.writer(handle,lineterminator='\n')
            if handle.tell()==0:writer.writerow(['image_id','logit'])
            offset = 0
            for images in loader:
                values = model.forward_logits(images.to('cuda')).cpu().tolist()
                for i,z in zip(todo[offset:offset+len(values)],values):
                    existing[base.rows[i].image_id] = z
                    writer.writerow([base.rows[i].image_id,z])
                offset += len(values);handle.flush()
                print(f'jpeg{quality} {len(existing)}/{len(evaluation)}',flush=True)
        result['perturbations'][f'jpeg_q{quality}'] = metrics({i:existing[base.rows[i].image_id] for i in evaluation})
    rng = np.random.default_rng(20261020)
    for name,ids in cohorts.items():
        labels = np.array([base.rows[i].label for i in ids]);p = apply_temperature(logits[ids],artifact['temperature'])
        aucs = [binary_metrics(rng.permutation(labels),p)['roc_auc'] for _ in range(100)]
        result.setdefault('shuffled_evaluation_labels',{})[name] = dict(mean_auc=float(np.mean(aucs)),quantiles=np.percentile(aucs,[2.5,97.5]).tolist())
    # 한 상수 tensor를 직접 예측해 이미지 외 label/ID를 모델 입력으로 받지 않는 대조.
    with torch.inference_mode():
        z = model.forward_logits(torch.zeros(4,3,mc['image_size'],mc['image_size'],device='cuda')).cpu().tolist()
    assert max(z)-min(z)<1e-5
    result['constant_tensor_logits'] = z
    (OUTPUT/'probe_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    main()

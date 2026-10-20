"""감사 도구의 양성/음성 대조. 실제 split이나 checkpoint를 변경하지 않는다."""
import json

from PIL import Image, PngImagePlugin

from scripts.p08_leakage_audit import cross_split_groups, generation_provenance, nuisance_baseline, rank_auc


def test_cross_split_fingerprints_find_duplicates_without_flagging_unrelated_images():
    """동일 지문 교차를 놓치지 않고 split 내부 중복·다른 지문의 교차는 구분한다."""
    rows = [dict(image_id='a',sha256='same',split='train'),dict(image_id='b',sha256='same',split='test'),
            dict(image_id='c',sha256='other',split='val')]
    assert [[r['image_id'] for r in group] for group in cross_split_groups(rows,'sha256')] == [['a','b']]
    rows[1]['split'] = 'train'
    assert cross_split_groups(rows,'sha256') == []
    rows[1].update(split='test',sha256='different')
    assert cross_split_groups(rows,'sha256') == []


def test_rank_auc_handles_inversion_and_constant_negative_control():
    assert rank_auc([0,1],[0.,1.]) == 1
    assert rank_auc([0,1],[1.,0.]) == 0
    assert rank_auc([0,1],[.5,.5]) == .5


def test_nuisance_fit_does_not_use_heldout_labels_or_normalization():
    """평가 labels를 학습에 넣는 결함을 잡고 정상 train-only 고정 fit을 허용한다."""
    rows = [dict(image_id=f'{split}{n}',label=str(n%2),split=split)
            for split,count in [('train',20),('val',200),('test',200),('test_unseen',200)] for n in range(count)]
    x = [[int(r['label'])] for r in rows]
    result = nuisance_baseline(rows,x)
    assert all(v['roc_auc'] == 1 and v['accuracy'] == 1 for v in result.values())
    # train에 비해 매우 많은 평가 labels를 뒤집어도 fit은 이동하지 않아야 한다.
    changed = [dict(r,label=str(1-int(r['label']))) if r['split']!='train' else r for r in rows]
    result = nuisance_baseline(changed,x)
    assert all(v['roc_auc'] == 0 and v['accuracy'] == 0 for v in result.values())


def test_png_provenance_uses_embedded_full_prompt_and_seed(tmp_path):
    """짧은 prompt_id의 과잉 중복 판정을 막고 실제 렌더 계보를 보존한다."""
    (tmp_path/'generated').mkdir()
    graph = {'a':dict(class_type='CLIPTextEncode',inputs=dict(text='a person wearing a coat, street')),
             'b':dict(class_type='KSampler',inputs=dict(seed=123))}
    info = PngImagePlugin.PngInfo();info.add_text('prompt',json.dumps(graph))
    Image.new('RGB',(10,10)).save(tmp_path/'generated/a.png',pnginfo=info)
    rows = [dict(image_id='a',label='0',path='images/generated/a.png',generator='g',split='test',prompt_id='coarse')]
    generation_provenance(rows,tmp_path,tmp_path)
    result = json.loads((tmp_path/'generation_provenance.json').read_text())
    assert result[0]['prompt'] == graph['a']['inputs']['text'] and result[0]['noise_seed'] == 123


def test_real_training_configuration_reads_only_train_and_validation_rows(tmp_path, monkeypatch):
    """train 전체행 혼입을 잡고 test/test_unseen 없는 정상 두 loader를 허용한다."""
    from test_baseline import make_data
    from src.dataset import MetadataDataset
    from src.train import run_training
    metadata = make_data(tmp_path)
    observed = []
    def dataset(*args,**kwargs):
        result = MetadataDataset(*args,**kwargs)
        observed.append({r.image_id for r in result.rows})
        return result
    monkeypatch.setattr('src.train.MetadataDataset',dataset)
    config = dict(anonymization=None,model=dict(encoder='stub',embedding_dim=8,image_size=16,freeze_encoder=True),
                  training=dict(batch_size=2,learning_rate=.01,device='cpu'),
                  data=dict(metadata_csv=str(metadata)),augmentation=dict(horizontal_flip=False,jpeg_aug=False))
    run_training(config,str(metadata),1,tmp_path/'checkpoints')
    assert observed == [{'train_0.png','train_1.png'},{'val_0.png','val_1.png'}]

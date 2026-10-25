"""P09 채택 projection이 진단·checkpoint·calibration 정본과 연결되는지 잠근다."""
import json
from pathlib import Path

import yaml

from src.diagnostic import adoption


def test_primary_uses_adopted_p09_artifacts_and_preserves_p08():
    """관문 없이 primary 변경·P08 artifact 덮어쓰기를 잡고 채택된 P09 artifact 연결을 허용한다."""
    settings = yaml.safe_load(Path('configs/p09_r1_diagnostic.yaml').read_text())
    report = json.loads((Path(settings['output_dir'])/'result.json').read_text())
    metrics = report['evaluation']['candidate']['anonymized']['cohorts']
    expected = adoption(metrics['standard']['roc_auc'], metrics['unseen']['roc_auc'], report['gates'], settings)
    assert expected == report['adoption'] and expected['adopt']
    primary = yaml.safe_load(Path('configs/primary.yaml').read_text())
    assert primary == yaml.safe_load(Path('configs/p09_r1_train.yaml').read_text())
    artifact = json.loads(Path(settings['candidate_calibration']).read_text())
    assert artifact['checkpoint'] == primary['output']['checkpoint_dir']+'/best.pt'
    assert primary['data']['metadata_csv'] == settings['inputs']['metadata']
    assert primary['anonymization'] == settings['inputs']['anonymization']
    assert primary['data']['face_cache'] == settings['inputs']['face_cache']
    previous = yaml.safe_load(Path('configs/anonymized.yaml').read_text())
    assert previous['output']['checkpoint_dir'] == 'checkpoints/anonymized'
    assert previous['data']['metadata_csv'] == 'data/metadata.csv'

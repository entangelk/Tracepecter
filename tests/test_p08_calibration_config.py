"""P08-05: 재calibration 설정이 P05 절차에서 벗어나거나 P05 artifact를 덮어쓰는 것을 막는다."""
from pathlib import Path

import yaml


def test_anonymized_calibration_matches_p05_except_checkpoint_cache_and_output():
    """fit/metric drift·P05 출력 재사용은 실패하고, checkpoint·캐시·출력 경로 차이만 허용한다."""
    baseline = yaml.safe_load(Path('configs/calibration.yaml').read_text())
    candidate = yaml.safe_load(Path('configs/calibration_anonymized.yaml').read_text())
    training = yaml.safe_load(Path('configs/anonymized.yaml').read_text())
    assert candidate.pop('checkpoint') == training['output']['checkpoint_dir'] + '/best.pt'
    assert candidate.pop('face_cache') == training['data']['face_cache']
    assert candidate.pop('output_dir') == 'experiments/p08_anonymized/calibration'
    assert 'anonymize' not in candidate  # 규격은 checkpoint 결합본만 사용한다
    del baseline['checkpoint'], baseline['output_dir']
    assert candidate == baseline

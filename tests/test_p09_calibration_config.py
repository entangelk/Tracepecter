"""P09 calibration keeps the fitting procedure and separates all artifacts."""
from pathlib import Path

import yaml


def test_p09_calibration_keeps_fit_and_uses_new_checkpoint_output():
    """Under: old checkpoint/output reused; over: fitting or anonymization override drifts."""
    prior = yaml.safe_load(Path('configs/calibration_anonymized.yaml').read_text())
    candidate = yaml.safe_load(Path('configs/p09_r1_calibration.yaml').read_text())
    training = yaml.safe_load(Path('configs/p09_r1_train.yaml').read_text())
    assert candidate['checkpoint'] == training['output']['checkpoint_dir']+'/best.pt'
    assert candidate['output_dir'] == 'experiments/p09_leakage_repair/r1/calibration'
    candidate['checkpoint'] = prior['checkpoint']
    candidate['output_dir'] = prior['output_dir']
    assert candidate == prior

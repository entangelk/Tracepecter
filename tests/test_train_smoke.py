"""P00-03 완료 확인 가드 — CLI smoke 실행 (phase_0_initialization.md).

가드 방향:
- under-strict: 학습 루프·checkpoint 저장이 깨지면 두 테스트 모두 재실패.
- over-strict: 정상 config 로 smoke 가 실패하게 만드는 변경(예: 인자 검증 과잉)도
  test_train_cli_command_runs_clean 에서 잡힌다.
"""
import shutil
import subprocess
import sys

import torch

from src.train import build_loss, main


def test_loss_is_binary_cross_entropy():
    """§16 Loss 리터럴 잠금(검증 H4) — BCELoss 가 아닌 loss 로 교체 시 재실패."""
    assert isinstance(build_loss(), torch.nn.BCELoss)


def test_train_smoke_creates_checkpoint(capsys):
    """train.main --smoke: 1 epoch 종료 + checkpoint 파일 생성 + 'smoke ok' 출력."""
    checkpoint_path = main(["--config", "configs/baseline.yaml", "--smoke"])
    try:
        assert checkpoint_path.exists()
        out = capsys.readouterr().out
        assert "train_loss=" in out
        assert "smoke ok" in out
    finally:
        # smoke_root(=checkpoint 경로의 조상) 임시 디렉터리 정리.
        shutil.rmtree(checkpoint_path.parent.parent, ignore_errors=True)


def test_train_cli_command_runs_clean():
    """phase 문서의 완료 확인 명령이 에러 없이 종료한다: python -m src.train --config configs/baseline.yaml --smoke."""
    result = subprocess.run(
        [sys.executable, "-m", "src.train", "--config", "configs/baseline.yaml", "--smoke"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "smoke ok" in result.stdout

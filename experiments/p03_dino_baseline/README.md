# P03 — DINOv2 baseline

동일 P01 split의 10 epoch frozen DINOv2-base 실험. 전체 설정/학습/평가는 [experiment.json](experiment.json), 실행 설정은 [config.yaml](config.yaml), 비교와 선정 근거는 [P03 report](../p03_comparison/README.md)를 따른다.

Checkpoint는 `checkpoints/dino/best.pt`, 재개용은 `last.pt`, 로그는 같은 디렉터리에 보관한다. 바이너리는 Git 비추적이며 checkpoint SHA256은 실험 스냅샷에 기록한다.

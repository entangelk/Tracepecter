"""§12 메타데이터 스키마·§15 전처리 회귀 가드.

가드 방향:
- under-strict: label 파싱/경로 해석이 깨지면 test_read_metadata_parses_all_rows /
  test_dataset_returns_image_and_float_label 재실패.
- over-strict: transform 이 스펙과 다른 크기·정규화를 내면 test_transform_resizes_and_normalizes 재실패.
"""
from PIL import Image

from src.dataset import MetadataDataset, build_transform, read_metadata

HEADER = (
    "image_id,path,label,category,source_type,source_domain,generator,product_id,split\n"
)


def _write_dataset(root, count=4):
    """§12 스키마를 따르는 tiny dataset 을 만들고 metadata.csv 경로를 반환한다."""
    images_dir = root / "images"
    images_dir.mkdir(parents=True)
    lines = [HEADER]
    for i in range(count):
        image_id = f"img_{i:06d}"
        Image.new("RGB", (16, 16), color=(i * 40 % 255, 90, 150)).save(
            images_dir / f"{image_id}.png"
        )
        source_type = "real" if i % 2 else "generated"
        generator = "" if i % 2 else "gen_a"
        lines.append(
            f"{image_id},images/{image_id}.png,{i % 2},smoke,{source_type},src,{generator},,train\n"
        )
    csv_path = root / "metadata.csv"
    csv_path.write_text("".join(lines), encoding="utf-8")
    return csv_path


def test_read_metadata_parses_all_rows(tmp_path):
    csv_path = _write_dataset(tmp_path)
    rows = read_metadata(csv_path)
    assert len(rows) == 4
    assert rows[0].image_id == "img_000000"
    assert rows[0].label == 0
    assert rows[1].label == 1
    assert rows[1].source_type == "real"
    assert rows[0].source_type == "generated"


def test_dataset_returns_image_and_float_label(tmp_path):
    csv_path = _write_dataset(tmp_path)
    dataset = MetadataDataset(
        csv_path, image_size=32, horizontal_flip=False, jpeg_aug=False
    )
    assert len(dataset) == 4
    image, label = dataset[0]
    assert image.shape == (3, 32, 32)
    assert isinstance(label, float)
    assert label == 0.0


def test_transform_resizes_and_normalizes():
    """§15 Resize(shape) + Normalization(mean=0.5, std=0.5) 값 검증(검증 H2).

    균일 회색(128)은 Normalize 후 ≈0.0078. Normalize 가 제거되면 ≈0.502 가 나와
    재실패한다."""
    transform = build_transform(image_size=64, horizontal_flip=False, jpeg_aug=False)
    image = Image.new("RGB", (100, 40), color=(128, 128, 128))
    tensor = transform(image)
    assert tensor.shape == (3, 64, 64)
    assert abs(float(tensor.mean())) < 0.05

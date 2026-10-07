"""§12 메타데이터 스키마·§15 전처리 회귀 가드.

가드 방향:
- under-strict: label 파싱/경로 해석이 깨지면 test_read_metadata_parses_all_rows /
  test_dataset_returns_image_and_float_label 재실패.
- over-strict: transform 이 스펙과 다른 크기·정규화를 내면 test_transform_resizes_and_normalizes 재실패.
- schema: §12 v1.2 12열 헤더·행 리터럴이 깨지면(열 제거·추가·순서 변경)
  test_metadata_fixture_locks_schema_v12_columns 재실패(독립검증 H1 — 기존 셀은
  read_metadata 가 소비하는 5열만 잠금).
"""
import csv

from PIL import Image

from src.dataset import MetadataDataset, build_transform, read_metadata

# project.md §12 v1.2 전체 컬럼(순서 포함) — 스키마 리터럴 잠금용.
SCHEMA_V1_2_COLUMNS = [
    "image_id", "path", "label", "category", "parts", "source_type",
    "source_domain", "generator", "style", "look_group", "prompt_id", "split",
]

HEADER = (
    "image_id,path,label,category,parts,source_type,source_domain,generator,"
    "style,look_group,prompt_id,split\n"
)


def _write_dataset(root, count=4):
    """§12 v1.2 스키마를 따르는 tiny dataset 을 만들고 metadata.csv 경로를 반환한다.

    값은 §12 값 규약을 따른다(독립검증 H3): REAL 행은 source_domain=kfashion·
    대표 부위·style·look_group 을 갖고, Generated 행은 generator·prompt_id 를 갖는다.
    """
    images_dir = root / "images"
    images_dir.mkdir(parents=True)
    lines = [HEADER]
    for i in range(count):
        image_id = f"img_{i:06d}"
        Image.new("RGB", (16, 16), color=(i * 40 % 255, 90, 150)).save(
            images_dir / f"{image_id}.png"
        )
        if i % 2:  # REAL 행
            row = (
                f"{image_id},images/{image_id}.png,1,상의,상의|하의,real,kfashion,,"
                f"스트리트,look_{i // 2},,train\n"
            )
        else:  # Generated 행
            row = (
                f"{image_id},images/{image_id}.png,0,원피스,원피스,generated,,gen_a,"
                f",,p01,train\n"
            )
        lines.append(row)
    csv_path = root / "metadata.csv"
    csv_path.write_text("".join(lines), encoding="utf-8")
    return csv_path


def test_metadata_fixture_locks_schema_v12_columns(tmp_path):
    """§12 v1.2 전체 12열 리터럴 잠금 — 헤더·행 모두(독립검증 H1 보강 셀).

    under-strict: 헤더나 행에서 아무 열이나 빠지면 재실패(MU1 — 기존 3셀은
    read_metadata 가 소비하는 5열만 잠금하고 style 등 7열은 잡지 못했다).
    over-strict: 열 추가·순서 변경·행 필드 수 불일치도 재실패(§12 는 12열을
    규정하므로 정당한 확장이 아닌 이상 고정).
    """
    csv_path = _write_dataset(tmp_path)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == SCHEMA_V1_2_COLUMNS
    assert len(rows) == 5
    assert all(len(row) == len(SCHEMA_V1_2_COLUMNS) for row in rows[1:])


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

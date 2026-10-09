"""P06-03 정적 검토 페이지 생성: Windows 브라우저에서 파일로 여는 HTML + 원본 이미지 사본.

  docker compose run --rm dev python -m scripts.build_review_page   # DATA_DIR=원본 이미지 루트
  → reports/errors/review/index.html (Git 비추적, F:\\devel\\Tracepecter\\reports\\errors\\review\\index.html)

판정은 페이지에서 reports/errors/review_owner.csv로 저장한다. 에이전트 1차 검토(review_agent.csv)나
소유자 CSV가 바뀌면 다시 생성해 페이지에 반영한다.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = Path(__file__).with_name('review_page.html')
PLACEHOLDER = '/*REVIEW_DATA*/null'


def read_reviews(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(newline='', encoding='utf-8') as handle:
        return {row['image_id']: row for row in csv.DictReader(handle)}


def load_cases(review_set: Path, metadata: Path, agent: Path, owner: Path) -> list[dict]:
    paths = {r['image_id']: r['path'] for r in csv.DictReader(metadata.open(encoding='utf-8'))}
    agents, owners = read_reviews(agent), read_reviews(owner)
    return [dict(row, order=order, label=int(row['label']), owner_check=row['owner_check'] == 'True',
                 scores=json.loads(row['scores']), path=paths[row['image_id']], file=Path(paths[row['image_id']]).name,
                 agent=agents.get(row['image_id']), review=owners.get(row['image_id']))
            for order, row in enumerate(csv.DictReader(review_set.open(encoding='utf-8')))]


def build(cases: list[dict], image_root: Path, output: Path) -> Path:
    images = output/'img'
    images.mkdir(parents=True, exist_ok=True)
    for case in cases:
        target = images/case['file']
        if not target.exists():
            shutil.copyfile(image_root/Path(case['path']).relative_to('images'), target)
    data = dict(generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'), cases=cases)
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    template = TEMPLATE.read_text(encoding='utf-8')
    if template.count(PLACEHOLDER) != 1:
        raise ValueError('review page template must contain exactly one data placeholder')
    page = output/'index.html'
    page.write_text(template.replace(PLACEHOLDER, payload), encoding='utf-8')
    return page


def main(argv=None) -> Path:
    parser = argparse.ArgumentParser(description='P06-03 static review page')
    parser.add_argument('--image-root', type=Path, default=Path('/data'))
    parser.add_argument('--review-set', type=Path, default=Path('reports/errors/review_set.csv'))
    parser.add_argument('--metadata', type=Path, default=Path('data/metadata.csv'))
    parser.add_argument('--agent', type=Path, default=Path('reports/errors/review_agent.csv'))
    parser.add_argument('--owner', type=Path, default=Path('reports/errors/review_owner.csv'))
    parser.add_argument('--output', type=Path, default=Path('reports/errors/review'))
    args = parser.parse_args(argv)
    page = build(load_cases(args.review_set, args.metadata, args.agent, args.owner), args.image_root, args.output)
    print(page)
    return page


if __name__ == '__main__':
    main()

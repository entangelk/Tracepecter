"""P06-03 로컬 검토 페이지: 검토군 사진을 보여 주고 소유자 판정을 CSV로 저장한다.

실행(원본 이미지는 재압축 없이 그대로 표시):
  DATA_DIR="$HOME/data/tracepector/images" docker compose run --rm -p 8765:8765 dev \
      python -m scripts.review_server --image-root /data
  → http://localhost:8765
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

REVIEW_FIELDS = ['image_id', 'perceived', 'cues', 'agent_agreement', 'note', 'updated_at']
PERCEIVED = {'', 'photo_like', 'ambiguous', 'synthetic_like'}
AGREEMENT = {'', 'agree', 'disagree'}
CUES = ('full_body', 'partial_frame', 'studio_plain_bg', 'busy_bg', 'face_visible', 'face_hidden',
        'smooth_retouch', 'lighting', 'body_defect', 'garment_defect', 'text_logo', 'photo_noise')
PAGE = Path(__file__).with_name('review_page.html')
_lock = Lock()


def read_reviews(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(newline='', encoding='utf-8') as handle:
        return {row['image_id']: row for row in csv.DictReader(handle)}


def save_review(path: Path, image_id: str, patch: dict, valid_ids: set[str]) -> dict:
    """한 행을 병합해 원자적으로 다시 쓴다. cues는 '|' 구분, 알 수 없는 값은 거부."""
    if image_id not in valid_ids:
        raise ValueError(f'unknown image_id: {image_id}')
    unknown = set(patch) - {'perceived', 'cues', 'agent_agreement', 'note'}
    if unknown:
        raise ValueError(f'unknown fields: {sorted(unknown)}')
    if patch.get('perceived', '') not in PERCEIVED or patch.get('agent_agreement', '') not in AGREEMENT:
        raise ValueError('invalid perceived/agent_agreement')
    if 'cues' in patch:
        if not set(patch['cues']) <= set(CUES):
            raise ValueError('invalid cues')
        patch = dict(patch, cues='|'.join(c for c in CUES if c in patch['cues']))
    with _lock:
        reviews = read_reviews(path)
        row = {field: '' for field in REVIEW_FIELDS} | reviews.get(image_id, {}) | patch
        row.update(image_id=image_id, updated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        reviews[image_id] = row
        temporary = path.with_suffix('.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            writer.writerows(sorted(reviews.values(), key=lambda r: r['image_id']))
        os.replace(temporary, path)
    return row


def load_cases(review_set: Path, metadata: Path, agent: Path, owner: Path) -> list[dict]:
    paths = {r['image_id']: r['path'] for r in csv.DictReader(metadata.open(encoding='utf-8'))}
    agents, owners = read_reviews(agent), read_reviews(owner)
    cases = []
    for order, row in enumerate(csv.DictReader(review_set.open(encoding='utf-8'))):
        cases.append(dict(row, order=order, label=int(row['label']), owner_check=row['owner_check'] == 'True',
                          scores=json.loads(row['scores']), path=paths[row['image_id']],
                          agent=agents.get(row['image_id']), review=owners.get(row['image_id'])))
    return cases


def make_handler(args):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, value):
            self._send(status, json.dumps(value, ensure_ascii=False).encode(), 'application/json; charset=utf-8')

        def _cases(self):
            return load_cases(args.review_set, args.metadata, args.agent, args.owner)

        def do_GET(self):
            if self.path in ('/', '/index.html'):
                return self._send(200, PAGE.read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/api/cases':
                return self._json(200, self._cases())
            if self.path.startswith('/img/'):
                image_id = self.path.removeprefix('/img/')
                case = next((c for c in self._cases() if c['image_id'] == image_id), None)
                if case is None:
                    return self._json(404, dict(error='unknown image'))
                file = args.image_root / Path(case['path']).relative_to('images')
                kind = 'image/png' if file.suffix.lower() == '.png' else 'image/jpeg'
                return self._send(200, file.read_bytes(), kind)
            self._json(404, dict(error='not found'))

        def do_POST(self):
            if not self.path.startswith('/api/review/'):
                return self._json(404, dict(error='not found'))
            image_id = self.path.removeprefix('/api/review/')
            try:
                patch = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                valid = {c['image_id'] for c in self._cases()}
                self._json(200, save_review(args.owner, image_id, patch, valid))
            except (ValueError, json.JSONDecodeError) as error:
                self._json(400, dict(error=str(error)))

        def log_message(self, *_):
            pass
    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description='P06-03 review page')
    parser.add_argument('--image-root', type=Path, required=True)
    parser.add_argument('--review-set', type=Path, default=Path('reports/errors/review_set.csv'))
    parser.add_argument('--metadata', type=Path, default=Path('data/metadata.csv'))
    parser.add_argument('--agent', type=Path, default=Path('reports/errors/review_agent.csv'))
    parser.add_argument('--owner', type=Path, default=Path('reports/errors/review_owner.csv'))
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    print(f'review page: http://localhost:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(args)).serve_forever()


if __name__ == '__main__':
    main()

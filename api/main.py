"""P07-02·03: POST /score와 정적 데모(GET /). 모델은 프로세스 시작 시 1회 로드하고, 업로드 원본은 저장하지 않는다.

실행: uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import io
import os
import threading
from pathlib import Path
from typing import Literal

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from src.inference import Scorer

DEMO = Path(__file__).resolve().parent.parent / 'demo' / 'index.html'


class ScoreResponse(BaseModel):
    realism_score: float
    classification: Literal['photographic_like', 'synthetic_like']
    faces_anonymized: int
    model_version: str


def create_app(config=None, scorer=None) -> FastAPI:
    # 설정 파일 선택만 환경변수로 바꿀 수 있다. 값은 설정 파일이 소유한다.
    config = config or os.environ.get('TRACEPECTER_INFERENCE_CONFIG', 'configs/inference.yaml')
    with open(config) as handle:
        settings = yaml.safe_load(handle)
    limit, formats = settings['max_upload_bytes'], set(settings['formats'])
    # artifact 검증 실패는 여기서 예외로 올라가 서버 기동을 막는다.
    scorer = scorer or Scorer(settings['calibration'], settings['device'])
    lock = threading.Lock()  # 모델 1개를 공유하므로 동시 요청이 CPU·메모리를 겹쳐 쓰지 않게 직렬화한다
    demo = DEMO.read_text(encoding='utf-8')
    app = FastAPI(title='Tracepecter')

    @app.get('/', response_class=HTMLResponse)
    def index():
        return demo

    @app.post('/score', response_model=ScoreResponse)
    def score(image: UploadFile = File(...)):
        data = image.file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, 'image too large')
        try:
            with Image.open(io.BytesIO(data)) as handle:
                if handle.format not in formats:
                    raise HTTPException(415, 'unsupported image format')
                picture = handle.convert('RGB')
        except Image.DecompressionBombError:
            raise HTTPException(413, 'image too large') from None
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise HTTPException(400, 'invalid image') from None
        with lock:
            return scorer(picture)

    return app

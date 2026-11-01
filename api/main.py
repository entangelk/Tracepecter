"""P07-02: POST /score. 모델은 프로세스 시작 시 1회 로드하고, 업로드 원본은 저장하지 않는다.

실행: uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import io
import threading
from typing import Literal

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from src.inference import Scorer


class ScoreResponse(BaseModel):
    realism_score: float
    classification: Literal['photographic_like', 'synthetic_like']
    faces_anonymized: int
    model_version: str


def create_app(config='configs/inference.yaml', scorer=None) -> FastAPI:
    with open(config) as handle:
        settings = yaml.safe_load(handle)
    limit, formats = settings['max_upload_bytes'], set(settings['formats'])
    # artifact 검증 실패는 여기서 예외로 올라가 서버 기동을 막는다.
    scorer = scorer or Scorer(settings['calibration'], settings['device'])
    lock = threading.Lock()  # 모델 1개를 공유하므로 동시 요청이 CPU·메모리를 겹쳐 쓰지 않게 직렬화한다
    app = FastAPI(title='Tracepecter')

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

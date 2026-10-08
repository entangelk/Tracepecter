# Tracepecter 실행 환경 — 의존성 canonical 은 requirements.txt (project.md §24).
# torch/torchvision 은 CPU wheel 을 먼저 설치해 레이어 캐시를 분리한다.
# CUDA 학습은 Dockerfile.training에서 기존 ComfyUI 기반 환경을 재사용한다.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir torch==2.9.0 torchvision==0.24.0 \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

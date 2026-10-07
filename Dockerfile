# Tracepecter 실행 환경 — 의존성 canonical 은 requirements.txt (project.md §24).
# torch/torchvision 은 CPU wheel 을 먼저 설치해 레이어 캐시를 분리한다.
# CUDA 빌드 전환은 P02 GPU 학습 시점에 build stage 또는 인덱스 교체로 처리한다.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

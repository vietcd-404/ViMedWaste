# Một container: build Angular → FastAPI phục vụ cả API lẫn giao diện (Render, Hugging Face, server trường).
#   docker build -t vimedwaste .
#   docker run -p 7860:7860 -e VIMEDWASTE_PASSWORD=doimatkhau vimedwaste
# Bỏ Grad-CAM (nhẹ hơn ~1 GB): docker build --build-arg GRADCAM=0 -t vimedwaste .

# ---------- 1. Build giao diện ----------
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npx ng build --configuration production

# ---------- 2. Backend + mô hình ----------
FROM python:3.11-slim
ARG GRADCAM=1

# Hugging Face chạy container bằng user id 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TORCH_HOME=/home/user/.cache/torch \
    VIMEDWASTE_ROOT=/home/user/app \
    VIMEDWASTE_DB=/home/user/app/runtime/vimedwaste.db \
    VIMEDWASTE_STATIC_DIR=/home/user/app/static \
    VIMEDWASTE_SIM_DATA=/home/user/app/data/demo \
    VIMEDWASTE_SEED_EVENTS=24
WORKDIR /home/user/app

# Thư viện trước, code sau → đổi code không phải cài lại thư viện
COPY pyproject.toml ./
COPY src ./src
RUN if [ "$GRADCAM" = "1" ]; then \
      pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    fi && pip install ".[api]"

COPY configs ./configs
COPY backend ./backend
COPY artifacts/models ./artifacts/models
COPY data/demo ./data/demo
COPY --from=frontend /fe/dist/frontend/browser ./static

RUN mkdir -p runtime && chown -R user:user /home/user
USER user

# Tải sẵn trọng số EfficientNet-B0 cho Grad-CAM để lúc chạy không phải tải
RUN if [ "$GRADCAM" = "1" ]; then python -c "from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights as W; efficientnet_b0(weights=W.IMAGENET1K_V1)"; fi

# Cổng: Render cấp qua biến PORT, Hugging Face dùng 7860
EXPOSE 7860
CMD ["sh", "-c", "exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]

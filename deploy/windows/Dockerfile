# Demo image for Windows 10 (Docker Desktop / WSL2 backend).
#
# Build context is the repository root:
#   docker build -f deploy/windows/Dockerfile -t photobase-demo .
#
# The image contains: built SPA, Python app, ffmpeg, CPU PyTorch and the
# YOLO-World billboard detector weights. PostgreSQL and Ollama stay outside.

# --- SPA ---------------------------------------------------------------------
FROM oven/bun:1 AS spa

WORKDIR /build

COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
RUN bun run build

# --- Runtime -----------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        fonts-dejavu-core \
        curl \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY schema ./schema
COPY scripts ./scripts
COPY deploy/windows/entrypoint.sh /entrypoint.sh

# CPU wheels keep the image smaller; if the CPU index does not carry the
# pinned version yet, fall back to the default index.
RUN pip install --upgrade pip \
    && (pip install "torch>=2.13,<2.14" "torchvision>=0.28,<0.29" \
            --index-url https://download.pytorch.org/whl/cpu \
        || pip install "torch>=2.13,<2.14" "torchvision>=0.28,<0.29") \
    && pip install ".[billboard]"

# Billboard detector weights are baked outside the data volume, so a fresh
# Windows data directory still works offline.
RUN mkdir -p /app/models \
    && cd /app/models \
    && python -c "from ultralytics import YOLOWorld; YOLOWorld('yolov8s-worldv2.pt')"

COPY --from=spa /build/dist ./frontend/dist

RUN chmod +x /entrypoint.sh && mkdir -p /app/data

EXPOSE 8010

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8010"]

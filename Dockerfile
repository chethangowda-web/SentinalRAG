# Single-container build: API + statically exported web UI.
#
# Used by the Railway deployment (service Root Directory = repo root, see railway.json) so the
# whole app runs as ONE service. docker-compose keeps using backend/Dockerfile and
# frontend/Dockerfile (separate containers behind nginx); keep the backend stages in sync.

# =============================================================================
# STAGE 1 — Web: export the Next.js app to plain static files
# =============================================================================
FROM node:22-alpine AS web

WORKDIR /web

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

# Empty API URL = same origin, because the API serves these files itself.
ENV STATIC_EXPORT=1 \
    NEXT_PUBLIC_API_URL="" \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# =============================================================================
# STAGE 2 — Python dependencies (CPU-only PyTorch)
# =============================================================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .

# CPU-only PyTorch first (avoids ~2 GB of CUDA libraries). Quoted: an unquoted `>=` is a shell redirect.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.0.0"

RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 3 — Runtime
# =============================================================================
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r sentinel && \
    useradd -r -g sentinel -d /app -s /bin/bash sentinel

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY backend/alembic.ini .
COPY backend/migrations/ migrations/
COPY backend/evaluation/ evaluation/
COPY backend/app/ app/

# The exported web UI, served by the API (see app/core/frontend.py)
COPY --from=web /web/out/ static/

RUN mkdir -p /data/uploads /data/processed && \
    chown -R sentinel:sentinel /app /data

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Run as the unprivileged user created above (owns /app and /data)
USER sentinel

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

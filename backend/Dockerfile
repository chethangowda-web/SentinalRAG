# =============================================================================
# STAGE 1 — Builder
#   Install all Python dependencies including CPU-only PyTorch
# =============================================================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install CPU-only PyTorch first (avoids downloading ~2 GB of CUDA/NVIDIA libs)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1

# Install all production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 2 — Runtime
#   Minimal image with only what is needed at runtime
# =============================================================================
FROM python:3.12-slim

# Install runtime OS packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r sentinel && \
    useradd -r -g sentinel -d /app -s /sbin/nologin sentinel

WORKDIR /app

# Copy installed Python packages from builder (avoids redundant downloads)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (only what is needed)
COPY alembic.ini .
COPY migrations/ migrations/
COPY evaluation/ evaluation/
COPY app/ app/

# Create data directories and fix permissions
RUN mkdir -p /data/uploads /data/processed && \
    chown -R sentinel:sentinel /app /data

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:8000/api/v1/health || exit 1

USER sentinel

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Deployment Guide

> **Audience:** DevOps engineers deploying SentinelRAG in production or demo environments.

---

## Architecture Overview (Deployment)

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  NGINX   │────►│ Backend  │────►│PostgreSQL│     │  Qdrant  │     │  Redis   │     │ Frontend │
│  :80     │     │  :8000   │     │  :5432   │     │  :6333   │     │  :6379   │     │  :3000   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │
     ▼                ▼
  Internet        /data/
  (optional)     (persistent volume)
```

All services run on a single Docker bridge network (`sentinelrag-network`). NGINX is the only service exposed to the host on port 80. Backend and Frontend are internal services accessed via reverse proxy.

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8 GB |
| Disk | 10 GB free | 50 GB+ SSD |
| Network | Broadband internet (for model downloads) | |

### Software Requirements

- **Docker Engine** ≥ 24.x
- **Docker Compose Plugin** ≥ 2.24.x (or standalone `docker-compose` v2)
- **Git** (for cloning the repository)

### API Requirements

- **LLM API Key**: DeepSeek, OpenAI-compatible, or Featherless account
- **Network access**: API provider endpoint must be reachable from the Docker host

---

## Docker Compose Deployment

### Step 1: Clone and Configure

```bash
git clone https://github.com/chethangowda-web/SentinalRAG.git
cd SentinalRAG
cp .env.example .env
```

### Step 2: Set Environment Variables

Edit `.env` with your configuration:

```bash
# Required: Set at least one LLM API key
DEEPSEEK_API_KEY=sk-your-key-here
# OR
FEATHERLESS_API_KEY=fk-your-key-here
FEATHERLESS_BASE_URL=https://api.featherless.ai/v1
FEATHERLESS_MODEL=deepseek-ai/DeepSeek-V4-Pro

# Optional: Override defaults
LLM_MODEL=deepseek-chat
LLM_TEMPERATURE=0.1
SECRET_KEY=generate-a-random-secret-here
LOG_LEVEL=INFO
```

### Step 3: Build and Start

```bash
# Build all images
docker compose build

# Start all services in detached mode
docker compose up -d

# Follow logs
docker compose logs -f
```

### Startup Sequence

On first startup, the backend runs the following sequence:
1. **Dependency health check** — Waits for PostgreSQL and Qdrant with exponential backoff (0.5s base, max 10 retries)
2. **Alembic migrations** — Runs `alembic upgrade head` to apply pending database schema migrations (creates `documents`, `chunks`, and `traces` tables)
3. **Fallback table creation** — If Alembic is unavailable, falls back to `init_db()` via `Base.metadata.create_all`
4. **Model lazy loading** — Sentence Transformer and Cross-Encoder models load on first request, not at startup

**First startup time:** 2–5 minutes (depends on network speed for model downloads):
- Sentence Transformer model: ~100MB
- Cross-Encoder model: ~80MB
- PyTorch: ~800MB (included in Docker image)

### Step 4: Verify Deployment

```bash
# Check all services are healthy
docker compose ps

# Test backend health
curl http://localhost/api/v1/health

# Test readiness (all dependencies)
curl http://localhost/api/v1/ready

# Access the application
open http://localhost
```

---

## Services Detail

### PostgreSQL 16 (Alpine)

| Detail | Value |
|---|---|
| Image | `postgres:16-alpine` |
| Port | 5432 (internal only) |
| User | `sentinel` |
| Password | `sentinel` (**change in production**) |
| Database | `sentinelrag` |
| Data Volume | `postgres_data` (persistent) |
| Health Check | `pg_isready -U sentinel -d sentinelrag` (5s interval) |

### Redis 7 (Alpine)

| Detail | Value |
|---|---|
| Image | `redis:7-alpine` |
| Port | 6379 (internal only) |
| Persistence | None (cache-only; currently reserved for future use) |
| Health Check | `redis-cli ping` (5s interval) |

### Qdrant v1.13.0

| Detail | Value |
|---|---|
| Image | `qdrant/qdrant:v1.13.0` |
| Ports | 6333 (REST), 6334 (gRPC) — internal only |
| Data Volume | `qdrant_data` (persistent) |
| Collection | `documents` (auto-created on first embed) |
| Health Check | `curl -sf http://localhost:6333/health` (10s interval) |

### Backend (FastAPI)

| Detail | Value |
|---|---|
| Build | `./backend/Dockerfile` (multi-stage, python:3.12-slim) |
| Port | 8000 (internal only) |
| Non-root user | `appuser` (UID 1000) |
| Data Volume | `app_data:/data` (uploads + processed files) |
| Health Check | `curl -sf http://localhost:8000/api/v1/health` (30s interval, 60s start period) |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info` |

### Frontend (Next.js)

| Detail | Value |
|---|---|
| Build | `./frontend/Dockerfile` (multi-stage, node:22-alpine) |
| Port | 3000 (internal only) |
| Build Mode | `output: "standalone"` |
| Health Check | `wget --spider http://localhost:3000` (30s interval) |
| Start Command | `node server.js` |

### NGINX Reverse Proxy

| Detail | Value |
|---|---|
| Image | `nginx:1.27-alpine` |
| Port | 80 (host-facing) |
| Config | `./nginx/nginx.conf` (mounted read-only) |
| Max Body Size | 50MB |
| Keepalive | 64 connections per upstream |
| Health Check | `nginx -t` (30s interval) |

---

## Environment Variables Reference

### Core Settings

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:sentinel@postgres:5432/sentinelrag` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant connection URL |
| `SECRET_KEY` | `""` (required) | Secret key for session signing. **Empty key causes fatal startup error.** Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000","http://localhost"]` | Allowed CORS origins |

### LLM Settings

| Variable | Default | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (required if Featherless not set) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | DeepSeek API base URL |
| `LLM_MODEL` | `deepseek-chat` | LLM model name |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature (0.0–1.0) |
| `FEATHERLESS_API_KEY` | — | Featherless API key (alternative provider) |
| `FEATHERLESS_BASE_URL` | — | Featherless API base URL |
| `FEATHERLESS_MODEL` | — | Featherless model name |

### Document Processing Settings

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_DIR` | `/data/uploads` | Upload directory (Docker: `app_data` volume) |
| `PROCESSED_DIR` | `/data/processed` | Processed text directory |
| `MAX_FILE_SIZE` | `52428800` | Max upload size in bytes (50MB) |
| `OCR_LANGUAGE` | `eng` | Tesseract OCR language |
| `CHUNK_SIZE` | `500` | Target chunk size in words |
| `CHUNK_OVERLAP` | `100` | Chunk overlap in words |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Sentence Transformer model |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimension |
| `EMBEDDING_BATCH_SIZE` | `32` | Embedding batch size |

### Rate Limiting

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_MAX_REQUESTS` | `100` | Max requests per window per IP |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window in seconds |

---

## Production Hardening

### Change Default Credentials

```bash
# In docker-compose.yml, update:
POSTGRES_USER: ${POSTGRES_USER:-sentinel}
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?error}  # Required, no default

# Update DATABASE_URL to match
DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/sentinelrag
```

### Generate a Strong SECRET_KEY

The application now **requires** a non-empty `SECRET_KEY`. An empty key causes a fatal startup error in production mode.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

Set in `.env`:
```bash
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

For development with SQLite, a warning is shown instead of a fatal error, but a strong key should still be configured.

### Enable HTTPS (SSL/TLS)

The NGINX configuration expects to terminate SSL. To enable HTTPS:

1. Place certificates at `./nginx/certs/`:
   ```
   nginx/
   ├── nginx.conf
   └── certs/
       ├── fullchain.pem
       └── privkey.pem
   ```

2. Update `docker-compose.yml` to mount certs:
   ```yaml
   nginx:
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
       - ./nginx/certs:/etc/nginx/certs:ro
     ports:
       - "443:443"
       - "80:80"
   ```

3. Update `nginx/nginx.conf` to add SSL listener (port 443) with redirect from HTTP.

### Resource Limits

Add resource constraints to prevent any single service from exhausting host resources:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

---

## Running Without Docker

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure external services are running:
# - PostgreSQL 16 on localhost:5432
# - Qdrant on localhost:6333
# - Redis on localhost:6379

# Set environment variables
export DEEPSEEK_API_KEY=sk-your-key-here
# Or create a .env file

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Dependencies (Local)

**PostgreSQL 16:**
```bash
# Ubuntu/Debian
sudo apt install postgresql-16
sudo -u postgres createuser sentinel -P
sudo -u postgres createdb sentinelrag -O sentinel

# macOS
brew install postgresql@16
createuser sentinel -P
createdb sentinelrag -O sentinel
```

**Qdrant:**
```bash
# Docker (recommended for local)
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.13.0
```

**Redis:**
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis
```

**Tesseract OCR:**
```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract
```

---

## Health Checks & Monitoring

### Docker Health Checks

Each service has a Docker health check:

| Service | Command | Interval | Start Period |
|---|---|---|---|
| PostgreSQL | `pg_isready` | 5s | 10s |
| Redis | `redis-cli ping` | 5s | 5s |
| Qdrant | `curl /health` | 10s | 10s |
| Backend | `curl /api/v1/health` | 30s | 60s |
| Frontend | `wget --spider` | 30s | 30s |
| NGINX | `nginx -t` | 30s | 30s |

### Application Health Endpoints

| Endpoint | Purpose | Frequency |
|---|---|---|
| `GET /api/v1/health` | Basic liveness (server is running) | Every 10s |
| `GET /api/v1/ready` | Readiness (all dependencies healthy) | Every 30s |
| `GET /api/v1/metrics` | Detailed system metrics | On demand |
| `GET /metrics/performance` | Latency percentiles | On demand |
| `GET /metrics/system` | CPU, memory, disk | On demand |
| `GET /metrics/errors` | Error counts | On demand |

### Logging

All services use JSON-file logging driver with rotation:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

Backend logs structured JSON with `request_id` for request tracing:
```json
{
  "timestamp": "2026-07-18T12:00:00.000Z",
  "level": "INFO",
  "logger": "sentinelrag.middleware",
  "message": "Request completed",
  "request_id": "uuid...",
  "method": "POST",
  "path": "/api/v1/chat",
  "status": 200,
  "latency_ms": 3205.4
}
```

---

## Troubleshooting

### Common Issues

| Symptom | Cause | Solution |
|---|---|---|
| Backend health check fails | Database not ready | Wait for PostgreSQL health check (10s start period) |
| LLM features return fallback | API key not configured | Set `DEEPSEEK_API_KEY` or `FEATHERLESS_API_KEY` |
| Upload fails with 400 | File too large or wrong type | Check file type (PDF/PNG/JPG) and size (max 50MB) |
| Chat returns "I don't know" | No documents ingested | Upload documents first via the upload page |
| Qdrant connection refused | Qdrant not started or wrong URL | Check `QDRANT_URL` environment variable |
| Frontend shows blank page | Backend not ready | Wait for backend health check to pass |
| Docker build slow | Model downloads | Pre-download models or use a cached Docker registry |
| Out of memory | Multiple services on low-RAM host | Reduce `EMBEDDING_BATCH_SIZE` or add swap |

### Checking Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines with timestamps
docker compose logs --tail=100 -t backend
```

### Restarting Services

```bash
# Restart a single service
docker compose restart backend

# Rebuild and recreate
docker compose up -d --build backend

# Full restart
docker compose down
docker compose up -d
```

### Debug Mode

Enable DEBUG-level logging for detailed pipeline tracing:
```bash
LOG_LEVEL=DEBUG docker compose up -d
```

---

## Performance Tuning

### Increasing Throughput

```yaml
# docker-compose.yml
backend:
  environment:
    # Increase connection pool for higher concurrency
    # (already in uvicorn — can add --workers N for multi-process)
```

For multi-worker deployment, change the start command:
```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
```

**Note:** Multi-worker deployment requires Redis-backed rate limiting (in-memory rate limiter is per-process).

### Reducing Memory Usage

```yaml
backend:
  environment:
    EMBEDDING_BATCH_SIZE: "16"  # Default: 32
```

### Storage

```yaml
volumes:
  app_data:
    driver: local
    driver_opts:
      type: none
      device: /path/to/host/directory
      o: bind
```

---

## Security Checklist

- [ ] Change PostgreSQL default password from `sentinel`
- [ ] Set a strong `SECRET_KEY`
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Restrict database access to backend only (internal Docker network)
- [ ] Add authentication middleware for API endpoints
- [ ] Set up regular log rotation and monitoring
- [ ] Keep Docker images updated with security patches
- [ ] Review and restrict CORS origins for production domain
- [ ] Implement network policies (Docker network segmentation)
- [ ] Set resource limits on all containers

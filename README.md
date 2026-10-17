# SentinelRAG — Self-Correcting Retrieval-Augmented Generation

**An enterprise-grade, self-correcting RAG platform powered by Google Gemini, LangGraph, and hybrid search that eliminates hallucinations through automatic detection and correction.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/next.js-15-black)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4-blueviolet)](https://langchain-ai.github.io/langgraph/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.16-red)](https://qdrant.tech)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/chethangowda-web/SentinalRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/chethangowda-web/SentinalRAG/actions)

**Running it for other people?** Read [OPERATIONS.md](./docs/OPERATIONS.md): capacity, settings to check, backups, and what to do when something breaks.

---

## Problem Statement

Standard RAG pipelines suffer from three critical failure modes that erode trust in production deployments:

1. **Hallucination** — LLMs generate confident-sounding but factually incorrect answers, citing sources that don't support the claim
2. **Missing Context** — Retrieved documents lack the information needed to answer the user's question, yet the LLM attempts an answer anyway
3. **Contradiction** — Retrieved context conflicts with itself or with the query, producing internally inconsistent answers

These failure modes are particularly dangerous in regulated industries — finance, healthcare, legal, and compliance — where incorrect answers carry real-world consequences.

### Why SentinelRAG

| Problem | Traditional RAG | SentinelRAG |
|---|---|---|
| Low-confidence retrieval | Answers anyway | Rewrites query and retries automatically |
| Contradictory context | Answers with contradictions | Detects and flags contradictions |
| Ambiguous questions | Guesses intent | Requests clarification |
| Missing context | Hallucinates | Returns fallback "I don't know" |
| No visibility | Black box | Full explainability panel |
| Evaluation | Manual spot-checking | Automated benchmark suite |

---

## Key Features

### Self-Correcting Pipeline
A 10-node LangGraph workflow that skips the LLM entirely for questions unrelated to your documents, checks short questions for ambiguity and evaluates confidence after every retrieval. Low-confidence results trigger automatic query rewriting and re-retrieval before resorting to contradiction detection or graceful fallback.

### Hybrid Retrieval
Combines vector similarity search (Qdrant, 384-dimensional embeddings) with PostgreSQL full-text search (BM25) using Reciprocal Rank Fusion (RRF). Retrieved results are re-ranked by a dedicated cross-encoder model for maximum precision.

### 3-Tier Confidence Scoring
A composite confidence score (0–100) combining vector similarity (30%), reranker confidence (50%), and result coverage (20%). Scores map to HIGH (≥65), MEDIUM (≥40), or LOW tiers that drive the self-correction workflow.

### Contradiction Detection
Identifies numerical conflicts (same figure cited in different contexts) and policy conflicts (positive vs. negative statements about the same policy) across retrieved chunks, preventing inconsistent answers.

### Clarification Engine
Detects ambiguous queries using regex patterns and optional LLM-based analysis. When ambiguity is detected, the system asks clarifying questions instead of guessing.

### Evaluation Framework
Built-in benchmark suite with 18 questions across 7 categories (the Evaluation page runs a quick 9-question set by default, in about a minute, with a live workflow view; "Run all 18" runs everything) (easy, medium, hard, contradictory, missing context, ambiguous, OCR). Measures faithfulness, hallucination rate, answer relevancy, context precision, context recall, and correctness.

### Explainability
Every answer includes a confidence score, latency breakdown across all pipeline stages, reasoning path visualization, and source citations with chunk-level references.

### Enterprise Ready
Docker Compose orchestration (PostgreSQL, Qdrant, FastAPI, Next.js, NGINX). Structured JSON logging, comprehensive health/readiness/metrics endpoints, rate limiting, security headers, and graceful degradation under failure.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           NGINX Reverse Proxy                             │
│                     (Rate Limiting / Security / SSL)                       │
└──────┬───────────────────────────────────────────────────────┬────────────┘
       │                                                       │
┌──────▼────────────────┐                          ┌──────────▼────────────┐
│    Next.js Frontend    │                          │   FastAPI Backend     │
│    (React 19, Dark)    │                          │   (Python 3.12)       │
│                        │                          │                       │
│   Dashboard            │◄──── HTTP/JSON ──────────►   LangGraph Pipeline  │
│   Chat UI              │                          │   9 self-correcting   │
│   Document Manager     │                          │   nodes               │
│   Evaluation View      │                          │                       │
│   Explainability Panel │                          │   Hybrid Retrieval    │
│                        │                          │   (Vector + BM25 +    │
│                        │                          │    Cross-Encoder)     │
│                        │                          │                       │
│                        │                          │   Evaluation Engine   │
│                        │                          │   18-question suite   │
└────────────────────────┘                          └──────────┬────────────┘
                                                               │
           ┌──────────────────────────────────┬────────────────┼──────────────────┐
           │                                  │                │                  │
   ┌───────▼────────┐                 ┌───────▼─────────┐  ┌──▼───────────┐  ┌──▼───────────┐
   │   PostgreSQL    │                 │     Qdrant       │  │    Redis     │  │  Tesseract   │
   │   16            │                 │   v1.16.2        │  │    v7        │  │  OCR         │
   │                 │                 │                  │  │              │  │              │
   │  Document meta  │                 │  384d embeddings │  │  (reserved   │  │  PDF/Image   │
   │  BM25 full-text │                 │  Vector search   │  │   for cache) │  │  text extr.  │
   │  Chunks storage │                 │  Collection: doc │  │              │  │              │
   └─────────────────┘                 └──────────────────┘  └──────────────┘  └──────────────┘
```

### Self-Correction Workflow (LangGraph)

```
User Query
    │
    ▼
┌─────────────────┐
│    Retrieve      │  Hybrid search (Vector + BM25 + RRF + Cross-Encoder)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     HIGH      ┌──────────────────┐
│   Confidence    │──────────────►│   Generate        │────► Answer with citations
│   Evaluation    │               │   Answer          │
│   (3-tier)      │               └──────────────────┘
└────────┬────────┘
         │ LOW / MEDIUM
         ▼
┌─────────────────┐
│   Query Rewrite │  LLM rewrites query for better retrieval
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Retry Retrieve │  Re-retrieve with improved query
└────────┬────────┘
         │
    ┌────┴────────────┐
    │                 │
    ▼                 ▼
┌──────────┐   ┌─────────────────┐
│ HIGH     │   │  Contradiction   │
│ (Pass)   │   │  Detection       │
└──────────┘   └────────┬────────┘
                        │
                  ┌─────┴──────────┐
                  │                │
                  ▼                ▼
            ┌────────────┐  ┌────────────┐
            │ Clarify     │  │ Fallback   │
            │ Ambiguity   │  │ Response   │
            └────────────┘  └────────────┘
```

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | Next.js, React, TypeScript, Tailwind CSS | 15, 19, 5.7, 3.4 |
| **Animation** | Framer Motion, Recharts | latest |
| **Backend** | Python, FastAPI, LangGraph | 3.12, 0.115, 0.4 |
| **ORM** | SQLAlchemy (async) | 2.0 |
| **Vector DB** | Qdrant | 1.16 |
| **Database** | PostgreSQL (asyncpg) | 16 |
| **Cache** | — | (future: Redis) |
| **Embeddings** | BAAI/bge-small-en-v1.5 (Sentence Transformers) | 384d |
| **Reranking** | ms-marco-MiniLM-L-6-v2 (Cross-Encoder) | — |
| **LLM** | Google Gemini (default; DeepSeek as an alternative), via langchain-openai | — |
| **OCR** | Tesseract (PyMuPDF + pytesseract) | — |
| **Infrastructure** | Docker, Docker Compose, NGINX | latest |
| **CI** | GitHub Actions (ruff + pytest + build) | — |
| **Testing** | pytest, pytest-asyncio, pytest-cov, pytest-benchmark | — |
| **Load Testing** | Locust | 2.33 |
| **Monitoring** | In-memory metrics, structured JSON logging, health/readiness endpoints | — |
| **Tokenization** | tiktoken (cl100k_base) with fallback estimator | 0.9 |
| **Migrations** | Alembic (async SQLAlchemy) | 1.14 |
| **Tracing** | Decision trace service (save/export CSV, Markdown, JSON) | — |

---

## Folder Structure

```
SentinalRAG/
├── backend/                  # FastAPI service (Python)
│   ├── app/
│   │   ├── api/v1/           # HTTP routes: auth, chat (SSE), documents, search, evaluation, health...
│   │   ├── core/             # settings, database, auth, middleware, rate limits
│   │   ├── graph/            # LangGraph pipeline and its nodes
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # retrieval, embeddings, reranker, LLM client, indexing, email...
│   ├── evaluation/           # benchmark dataset, runner, metrics and reports
│   ├── migrations/           # Alembic migrations (applied at startup)
│   ├── tests/                # pytest suite
│   └── performance/, load_tests/, observability/   # profiling and load-test tooling
├── frontend/                 # Next.js app (exported to static files and served by the backend)
│   ├── app/                  # pages: landing, login, dashboard (chat, documents, evaluation...)
│   ├── components/           # UI components
│   ├── e2e/                  # Playwright browser tests with an accessibility scan
│   └── services/, hooks/, lib/, types/
├── docs/                     # architecture, API, deployment, operations, benchmark, security reports
├── deploy/nginx/             # reverse-proxy config used by docker-compose
├── scripts/                  # benchmark, load test, smoke tests, setup and sample data
├── .github/workflows/        # CI (lint, tests, build, e2e), daily database backup
├── Dockerfile                # single-container build: API + web UI (what Railway deploys)
├── docker-compose.yml        # local multi-service setup
├── railway.json, Makefile
└── README.md, CONTRIBUTING.md, SECURITY.md, LICENSE
```

See [docs/](./docs/README.md) for the detailed documents.

---

## Installation

### Prerequisites

- Python 3.12+
- Node.js 22+
- Docker & Docker Compose (recommended)
- Tesseract OCR engine (`apt install tesseract-ocr tesseract-ocr-eng`)
- 4 GB+ RAM (for embedding/reranker models + LLM)
- LLM API key (Gemini, DeepSeek, or another OpenAI-compatible provider)

### Quick Start with Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/chethangowda-web/SentinalRAG.git
cd SentinalRAG

# 2. Configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY and your LLM API key (GEMINI_API_KEY, or DEEPSEEK_API_KEY)

# 3. Build and start all services
docker compose up --build

# 4. Access the application
# Frontend:   http://localhost
# Backend:    http://localhost/api/v1/health
# API Docs:   http://localhost/docs (Swagger UI)
```

The first startup will download embedding models (~100MB) and build containers, which takes 2–5 minutes depending on your network.

### Local Development (Without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Ensure PostgreSQL and Qdrant are running
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes* | — | Google Gemini API key (preferred provider when set) |
| `GEMINI_MODEL` | No | `gemini-3.5-flash` | Gemini model name. With reasoning off (see `GEMINI_MODEL_REASONING`) it answers in about 1.5 s; the `-lite` models were slower or often overloaded in testing |
| `GEMINI_FALLBACK_MODELS` | No | `gemini-3.1-flash-lite,gemini-3.5-flash-lite` | Tried in order, immediately, when a model is out of quota, rate limited or overloaded (503) |
| `GEMINI_MODEL_REASONING` | No | `gemini-3.5-flash=none` | Per-model `reasoning_effort` (`model=effort,...`). Hidden reasoning is the main source of slow answers |
| `SKIP_REWRITE_RERANK_THRESHOLD` | No | `-3.0` | A MEDIUM-confidence retrieval whose best passage scores at least this is answered directly, without the rewrite-and-retry detour |
| `OFF_TOPIC_RERANK_THRESHOLD` | No | `-10.0` | Questions whose best passage scores below this cross-encoder score are answered "nothing in your documents covers it" without an LLM call |
| `SENTRY_DSN` | No | _(empty)_ | Turns on Sentry error tracking (the SDK is already installed) |
| `FALLBACK_LLM_API_KEY` / `FALLBACK_LLM_MODEL` / `FALLBACK_LLM_BASE_URL` | No | _(empty)_ / _(empty)_ / Groq's URL | A second AI provider (any OpenAI-compatible API) tried after every Gemini model is busy or out of quota |
| `RESEND_API_KEY` / `SMTP_HOST` | No | _(empty)_ | Turns on "Forgot password": set `RESEND_API_KEY` (resend.com) or an SMTP server (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, e.g. Brevo). Off when neither is set |
| `MAIL_FROM` | No | `SentinelRAG <onboarding@resend.dev>` | From address of reset emails (must be a verified sender at your provider) |
| `PUBLIC_URL` | No | _(request host)_ | Public address of the app, used in the reset links |
| `RETRIEVAL_CONCURRENCY` | No | `2` | Searches (the CPU-heavy step of each question) running at once; others queue up to `RETRIEVAL_QUEUE_TIMEOUT_SECONDS`, then get a "busy" reply |
| `RATE_LIMIT_MAX_REQUESTS` | No | `240` | API requests per signed-in user per minute (`RATE_LIMIT_ANONYMOUS_MAX_REQUESTS`, default 120, per IP for signed-out callers) |
| `LLM_MAX_CONCURRENCY` / `ANSWER_CACHE_SIZE` | No | `4` / `256` | Simultaneous LLM calls; cached answers for identical question + passages |
| `LLM_REASONING_EFFORT` | No | — | Passed to the LLM as `reasoning_effort` (e.g. `none` to stop Gemini spending tokens on hidden thinking) |
| `GEMINI_BASE_URL` | No | `https://generativelanguage.googleapis.com/v1beta/openai/` | Gemini OpenAI-compatible endpoint |
| `DEEPSEEK_API_KEY` | Yes* | — | DeepSeek LLM API key (fallback) |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com/v1` | DeepSeek API base URL |
| `LLM_MODEL` | No | `deepseek-chat` | LLM model name |
| `LLM_TEMPERATURE` | No | `0.1` | LLM temperature |
| `DATABASE_URL` | No | `postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinelrag` | PostgreSQL connection |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `QDRANT_URL` | No | `http://localhost:6333` | Qdrant connection |
| `SECRET_KEY` | Yes | — | Signs login tokens. Must be a random 32+ char value; the server refuses to start with the old default or a short key (set `DEBUG=true` to bypass this for local development only) |
| `JWT_SECRET` | No | `SECRET_KEY` | Separate signing key for JWTs |
| `ADMIN_EMAILS` | No | — | Comma-separated emails allowed to view global metrics and change settings |
| `PRELOAD_MODELS` | No | `false` | Load embedding + reranker models at startup (~1 GB RAM) instead of on first use |
| `LLM_MAX_TOKENS` | No | `1024` | Max tokens per generated answer |
| `AUTO_INDEX_ON_UPLOAD` | No | `true` | Chunk + embed a document in the background right after upload (one at a time) |
| `AUTO_EVALUATE_ON_UPLOAD` | No | `false` | Also run the per-document quality evaluation after indexing (~8 LLM calls per upload) |
| `REGISTRATION_CODE` | No | — | If set, sign-up requires this invite code |
| `MAX_DOCUMENTS_PER_USER` / `MAX_STORAGE_MB_PER_USER` | No | `25` / `200` | Per-user upload limits |
| `MAX_CHATS_PER_USER_PER_DAY` | No | `100` | Questions per user per 24 h (protects the LLM quota) |
| `REGISTER_LIMIT_PER_HOUR` / `LOGIN_FAILURES_PER_10_MIN` | No | `5` / `8` | Sign-ups per IP per hour; failed logins per IP and per email |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `MAX_FILE_SIZE` | No | `104857600` | Max upload size (100MB) |
| `RATE_LIMIT_MAX_REQUESTS` | No | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Rate limit window |

*One of `GEMINI_API_KEY` or `DEEPSEEK_API_KEY` is required for LLM features. Priority: Gemini, then DeepSeek.

---

## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Basic health status, version, uptime |
| `GET` | `/api/v1/ready` | Full readiness check (DB, Qdrant, OCR, Embeddings, LLM) |
| `GET` | `/api/v1/metrics` | Detailed system metrics |
| `POST` | `/api/v1/chat` | Self-correcting Q&A with citations |
| `POST` | `/api/v1/chat/stream` | Same, streamed as Server-Sent Events (live pipeline steps, then the answer) |
| `POST` | `/api/v1/search` | Hybrid search with confidence scoring |
| `POST` | `/api/v1/ingest` | Upload document (PDF/PNG/JPG, max 100MB) |
| `POST` | `/api/v1/embed/{document_id}` | Generate embeddings for document |
| `GET` | `/api/v1/document/{document_id}/chunks` | List chunks for a document |
| `POST` | `/api/v1/evaluate` | Run full benchmark evaluation |
| `GET` | `/api/v1/evaluation/report` | Latest evaluation report |
| `GET` | `/api/v1/evaluation/history` | Evaluation run history |
| `GET` | `/api/v1/evaluation/dataset` | Benchmark dataset summary |
| `GET` | `/api/v1/traces` | List decision traces with optional session_id filter |
| `GET` | `/api/v1/traces/{trace_id}` | Get single decision trace |
| `GET` | `/api/v1/traces/export/csv` | Export traces as CSV file |
| `GET` | `/api/v1/traces/export/markdown` | Export traces as Markdown report |
| `GET` | `/metrics/performance` | Performance latency metrics (p50, p95, p99) |
| `GET` | `/metrics/system` | CPU, memory, disk usage |
| `GET` | `/metrics/errors` | Error counts by type |

Full interactive API documentation is available at `/docs` (Swagger UI) when the backend is running.

---

## Evaluation Results

SentinelRAG ships a benchmark that runs a baseline RAG (one hybrid retrieval + one answer) and the full self-correcting pipeline over the same 18 questions (`backend/evaluation/datasets/benchmark.json`) against a six-document corpus (`backend/evaluation/corpus/`: easy, medium, multi-step, contradictory, missing-context and ambiguous questions).

Latest run on the live deployment with `gemini-3.1-flash-lite` (full report and per-question answers: [BENCHMARK.md](./docs/BENCHMARK.md)):

| What the question should produce | Baseline | SentinelRAG |
|---|---|---|
| Specific questions answered | 9/11 | 9/11 |
| Unanswerable questions refused ("I don't have enough information") | 2/3 | **3/3** |
| Conflicting sources surfaced | 2/2 | 2/2 |
| Vague questions get a clarifying question | 0/2 | **2/2** |
| Mean latency | **6.9 s** | 9.8 s |

The two "specific" misses on each side are answers where the free Gemini tier rate-limited an LLM call and the system fell back to raw retrieved text. Where self-correction clearly helps is *knowing when not to answer*: refusing out-of-scope questions and asking about vague ones. The keyword-overlap quality metrics (faithfulness, correctness, relevancy, in BENCHMARK.md) are too noisy on 18 questions to separate the two pipelines: the gaps changed sign between runs, so don't read them as a win or a loss.

**What the benchmark caught along the way** (all fixed, with regression tests):
1. SentinelRAG returned *no answer* for 7 of 18 questions: every retried question was falsely flagged "contradictory" by a keyword heuristic and routed to a clarification step with nothing to ask. Clarification now continues to answering, and a flagged contradiction must be confirmed by the LLM.
2. That left vague questions never being clarified, so an early `ambiguity_check` node now judges short questions (6 words or fewer) from the question text alone.

Reproduce it against any deployment: `python scripts/run_benchmark.py --base-url https://your-app.up.railway.app`.

## Performance Results

| Metric | Value |
|---|---|
| Average Chat Latency (HIGH confidence, no retry) | 2.85s |
| Average Chat Latency (with retry path) | 4.80s |
| Max Throughput | 14.5 req/s |
| Error Rate (all load levels) | 0% |
| Memory Usage (idle) | ~800 MB RSS |
| Memory Usage (under 50 concurrent users) | ~1.2 GB RSS |
| CPU Usage (under load) | ~12.4% |
| Component Benchmarks (all CPU ops) | <15ms P99 |
| Failure Mode Tests Passed | 18/18 (100%) |

See [PERFORMANCE.md](./docs/PERFORMANCE.md) for detailed benchmarks, load test results, and observability reports.

---

## Roadmap

- [x] Core RAG pipeline with hybrid retrieval
- [x] Self-correcting LangGraph workflow
- [x] Confidence scoring and automatic retry
- [x] Contradiction detection
- [x] Query clarification
- [x] Document ingestion (PDF, images, OCR)
- [x] Comprehensive test suite (unit, integration, stress, failure, performance)
- [x] Evaluation framework with baseline comparison
- [x] Performance benchmarks and load testing
- [x] Docker Compose deployment
- [x] CI pipeline (lint, test, build)
- [x] API documentation (OpenAPI/Swagger)
- [x] Explainability & decision traceability (confidence breakdown, per-node execution traces)
- [x] AI Observability (LLM token usage tracking, model metadata)
- [x] Production hardening (SECRET_KEY validation, Alembic migrations, startup health checks)
- [x] Standardized error responses (request_id, trace_id, error_code)
- [x] Token counting (tiktoken integration)
- [ ] Multi-modal RAG (images, tables, charts)
- [x] Streaming pipeline progress (Server-Sent Events)
- [x] User authentication and per-user data isolation (JWT)
- [ ] Agentic tool use (calculator, DB queries, API calls)
- [ ] Fine-tuned embeddings for domain-specific retrieval
- [ ] A/B testing framework for configuration optimization
- [ ] Prometheus + Grafana production monitoring
- [ ] Kubernetes deployment (Helm charts)

---

## Deployment

### Live Deployment

| | URL |
|---|---|
| App (web UI + API) | [https://sentinalrag-production-37c9.up.railway.app](https://sentinalrag-production-37c9.up.railway.app) |
| API health | [/api/v1/health](https://sentinalrag-production-37c9.up.railway.app/api/v1/health), readiness: [/api/v1/ready](https://sentinalrag-production-37c9.up.railway.app/api/v1/ready) |
| Swagger docs | [/docs](https://sentinalrag-production-37c9.up.railway.app/docs) |

### Railway (single service)

The repo-root `Dockerfile` builds the Next.js app as a static export and bakes it into the API image, so **one service runs the whole app** (the API serves the UI at `/`). A project needs three services: the app, PostgreSQL, and Qdrant. That also fits Railway's free-plan limit.

1. Create a Railway project and add a **PostgreSQL** service.
2. Add a **Qdrant** service from the image `qdrant/qdrant:v1.16.2` and attach a volume at `/qdrant/storage`.
3. Add the app service from this GitHub repo. Leave its **Root Directory** at the repo root (`/`); `railway.json` selects the Dockerfile build.
4. Set these variables on the app service:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | random 32+ chars: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `GEMINI_API_KEY` | your Google Gemini key |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `QDRANT_URL` | `http://${{qdrant.RAILWAY_PRIVATE_DOMAIN}}:6333` |
   | `ADMIN_EMAILS` | optional: your email, after you have registered it |

5. Generate a public domain for the app service. Deploys run migrations automatically at startup.

The browser and API share one origin, so no CORS or `NEXT_PUBLIC_API_URL` setup is needed.

### Docker Compose (Self-Hosted)

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY and GEMINI_API_KEY
docker compose up --build
```

Access: http://localhost (frontend) / http://localhost/api/v1/health (API)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/) by LangChain
- Vector search powered by [Qdrant](https://qdrant.tech)
- Embeddings by [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)
- Reranking by [cross-encoder/ms-marco-MiniLM-L-6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2)
- UI components from [shadcn/ui](https://ui.shadcn.com)
- Evaluation inspired by [RAGAS](https://docs.ragas.io) and [DeepEval](https://docs.confident-ai.com)
- OCR via [Tesseract](https://github.com/tesseract-ocr/tesseract)
- Submitted to the [OneInbox AI Engineer Hackathon](https://oneinbox.ai)

---

<p align="center">
  Built with ❤️ for the OneInbox AI Engineer Hackathon
</p>

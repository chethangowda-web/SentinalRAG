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
A 9-node LangGraph workflow that checks short questions for ambiguity and evaluates confidence after every retrieval. Low-confidence results trigger automatic query rewriting and re-retrieval before resorting to contradiction detection or graceful fallback.

### Hybrid Retrieval
Combines vector similarity search (Qdrant, 384-dimensional embeddings) with PostgreSQL full-text search (BM25) using Reciprocal Rank Fusion (RRF). Retrieved results are re-ranked by a dedicated cross-encoder model for maximum precision.

### 3-Tier Confidence Scoring
A composite confidence score (0–100) combining vector similarity (30%), reranker confidence (50%), and result coverage (20%). Scores map to HIGH (≥65), MEDIUM (≥40), or LOW tiers that drive the self-correction workflow.

### Contradiction Detection
Identifies numerical conflicts (same figure cited in different contexts) and policy conflicts (positive vs. negative statements about the same policy) across retrieved chunks, preventing inconsistent answers.

### Clarification Engine
Detects ambiguous queries using regex patterns and optional LLM-based analysis. When ambiguity is detected, the system asks clarifying questions instead of guessing.

### Evaluation Framework
Built-in benchmark suite with 18 questions across 7 categories (easy, medium, hard, contradictory, missing context, ambiguous, OCR). Measures faithfulness, hallucination rate, answer relevancy, context precision, context recall, and correctness.

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
| **LLM** | Google Gemini (default; DeepSeek or Featherless as fallbacks), via langchain-openai | — |
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
sentinelrag/
│
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/                   # API routes
│   │   │   ├── router.py             # Route aggregation
│   │   │   ├── health.py             # /health, /ready, /metrics
│   │   │   ├── chat.py               # POST /chat (self-correcting Q&A)
│   │   │   ├── search.py             # POST /search (hybrid search)
│   │   │   ├── ingest.py             # POST /ingest (document upload)
│   │   │   ├── embed.py              # POST /embed, GET /chunks
│   │   │   ├── metrics.py            # GET /metrics/performance|system|errors
│   │   │   ├── evaluation.py         # POST /evaluate, GET /report|history|dataset
│   │   │   └── traces.py             # GET /traces, GET /export, POST /traces
│   │   ├── core/                     # Core framework
│   │   │   ├── config.py             # Pydantic Settings (all configuration)
│   │   │   ├── database.py           # Async SQLAlchemy engine & sessions
│   │   │   ├── logging.py            # Structured JSON logging
│   │   │   ├── middleware.py         # RequestID, Security headers, Rate limiting
│   │   │   ├── exceptions.py         # Custom exception hierarchy (8 types)
│   │   │   ├── cors.py               # CORS configuration
│   │   │   ├── metrics.py            # In-memory metrics collector (p50/p95/p99)
│   │   │   ├── resource_tracker.py   # CPU/memory/disk sampling (psutil)
│   │   │   └── qdrant.py             # Qdrant client singleton
│   │   ├── graph/                    # LangGraph self-correction pipeline
│   │   │   ├── state.py              # GraphState TypedDict
│   │   │   ├── graph_builder.py      # 9-node graph construction
│   │   │   └── nodes/                # Individual graph nodes
│   │   │       ├── retrieve_node.py
│   │   │       ├── ambiguity_node.py
│   │   │       ├── confidence_node.py
│   │   │       ├── rewrite_node.py
│   │   │       ├── retry_node.py
│   │   │       ├── contradiction_node.py
│   │   │       ├── clarification_node.py
│   │   │       ├── generation_node.py
│   │   │       └── fallback_node.py
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── document.py
│   │   │   └── chunk.py
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── health.py
│   │   │   ├── chat.py
│   │   │   ├── search.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   └── metrics.py
│   │   ├── services/                 # Business logic (20+ modules)
│   │   │   ├── file_service.py       # File validation & save
│   │   │   ├── document_service.py   # Ingest pipeline
│   │   │   ├── ocr_service.py        # Tesseract OCR
│   │   │   ├── text_cleaning.py      # Unicode normalization, cleanup
│   │   │   ├── chunking_service.py   # Semantic chunking (~500 words)
│   │   │   ├── embedding_service.py  # SentenceTransformer embeddings
│   │   │   ├── indexing_service.py   # Qdrant upsert orchestration
│   │   │   ├── qdrant_service.py     # Collection management
│   │   │   ├── query_preprocessor.py # Query normalization
│   │   │   ├── retrieval_service.py  # Full retrieval pipeline
│   │   │   ├── vector_search_service.py
│   │   │   ├── bm25_service.py       # PostgreSQL full-text search
│   │   │   ├── hybrid_search_service.py # RRF fusion
│   │   │   ├── reranker_service.py   # Cross-encoder reranking
│   │   │   ├── confidence_service.py # Composite confidence scoring
│   │   │   ├── query_rewriter.py     # LLM query rewriting
│   │   │   ├── contradiction_service.py # Conflict detection
│   │   │   ├── clarification_service.py # Ambiguity detection
│   │   │   ├── answer_generator.py   # LLM answer generation
│   │   │   ├── trace_service.py      # Decision trace CRUD + export
│   │   │   ├── token_counter.py      # tiktoken-based token counting
│   │   │   └── health_check.py       # Startup dependency waiter
│   │   ├── models/
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   └── trace.py              # Trace ORM model
│   │   └── utils/
│   │       └── file_utils.py         # UUID generation, path helpers
│   ├── migrations/                   # Alembic database migrations
│   │   ├── env.py                    # Async Alembic environment
│   │   ├── script.py.mako            # Migration template
│   │   └── versions/                 # Revision scripts
│   │       ├── 001_initial.py        # documents, chunks, traces
│   │       ├── 002_add_document_features.py
│   │       ├── 003_add_users_and_ownership.py
│   │       ├── 902bc76d113c_add_document_evaluations_table.py
│   │       └── 004_sync_schema_with_models.py
│   ├── evaluation/                   # Benchmark evaluation framework
│   │   ├── dataset.py                # Dataset loader
│   │   ├── datasets/benchmark.json   # 18-question benchmark
│   │   ├── services/
│   │   │   ├── baseline_rag.py       # Simple 2-step RAG baseline
│   │   │   ├── sentinel_rag.py       # Full LangGraph pipeline
│   │   │   └── runner.py             # Evaluation orchestrator
│   │   ├── metrics/
│   │   │   ├── base.py               # Base metric class
│   │   │   ├── ragas_metrics.py      # Faithfulness, relevancy, precision, recall
│   │   │   ├── deepeval_metrics.py   # Hallucination, bias, toxicity, correctness
│   │   │   ├── custom_metrics.py     # Confidence calibration, citation accuracy, etc.
│   │   │   └── collector.py          # Metrics aggregation
│   │   └── reports/
│   │       ├── report_generator.py   # JSON / CSV / Markdown reports
│   │       └── visualizer.py         # matplotlib charts & radar plots
│   ├── tests/                        # Comprehensive test suite
│   │   ├── test_health.py            # Integration health check
│   │   ├── test_search.py            # 409 lines: hybrid search tests
│   │   ├── test_ingest.py            # Upload validation tests
│   │   ├── test_indexing.py          # Embed/chunk endpoint tests
│   │   ├── test_graph.py             # 440 lines: full graph pipeline tests
│   │   ├── test_evaluation.py        # 841 lines: evaluation framework tests
│   │   ├── test_chunking.py          # Semantic chunking tests
│   │   ├── test_embedding.py         # Embedding normalization tests
│   │   ├── test_text_cleaning.py     # Text cleaning tests
│   │   ├── test_file_utils.py        # UUID/path tests
│   │   ├── stresstest/test_stress.py # Stress tests (time-bounded)
│   │   ├── failuretest/test_failure.py # Failure mode tests (18 scenarios)
│   │   └── performance/test_performance.py # Benchmarked performance tests
│   ├── load_tests/locustfile.py      # Locust load testing script
│   └── performance/                  # Performance benchmarks
│       ├── benchmark_runner.py       # Standalone benchmark runner
│       └── performance_report.md     # Comprehensive results
│
├── frontend/                         # Next.js 15 TypeScript frontend
│   ├── app/                          # App Router pages
│   │   ├── page.tsx                  # Landing (Hero, Features, Architecture)
│   │   ├── layout.tsx                # Root layout (dark mode)
│   │   └── dashboard/
│   │       ├── page.tsx              # Dashboard (stats, components, activity)
│   │       ├── chat/page.tsx         # Chat interface + explainability
│   │       ├── upload/page.tsx       # Upload with processing pipeline viz
│   │       ├── documents/page.tsx    # Document list + detail dialog
│   │       ├── evaluation/page.tsx   # Evaluation dash (charts, history)
│   │       └── settings/page.tsx     # Read-only system config display
│   ├── components/
│   │   ├── layout/                   # AppLayout, Sidebar, TopNavbar, Providers
│   │   ├── shared/                   # MetricCard, StatusBadge, UploadDropzone, etc.
│   │   ├── ui/                       # shadcn/ui primitives (10 components)
│   │   └── ExplainabilityPanel.tsx   # Sliding confidence/reasoning panel
│   ├── hooks/                        # React Query hooks (7 hooks)
│   ├── services/                     # Axios API client (8 modules)
│   ├── types/                        # TypeScript interfaces (167 lines)
│   └── lib/                          # cn() utility
│
├── nginx/nginx.conf                  # NGINX reverse proxy configuration
├── .github/workflows/ci.yml          # GitHub Actions CI pipeline
├── docker-compose.yml                # Multi-service orchestration (6 services)
├── Makefile                          # Common development commands
├── .env.example                      # Template environment file
└── .gitignore                        # Comprehensive ignores
```

---

## Installation

### Prerequisites

- Python 3.12+
- Node.js 22+
- Docker & Docker Compose (recommended)
- Tesseract OCR engine (`apt install tesseract-ocr tesseract-ocr-eng`)
- 4 GB+ RAM (for embedding/reranker models + LLM)
- LLM API key (DeepSeek, OpenAI-compatible, or Featherless)

### Quick Start with Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/chethangowda-web/SentinalRAG.git
cd SentinalRAG

# 2. Configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY and your LLM API key (GEMINI_API_KEY, or DEEPSEEK_API_KEY / FEATHERLESS_API_KEY)

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
| `GEMINI_MODEL` | No | `gemini-3.1-flash-lite` | Gemini model name. The free tier of `gemini-2.5-flash` allows only 5 requests/min, which one question can exceed (rewrite + clarify + answer) |
| `GEMINI_FALLBACK_MODELS` | No | `gemini-3.5-flash-lite,gemini-3.5-flash` | Tried in order when the primary model has used up its daily quota (each model has its own allowance) |
| `LLM_MAX_CONCURRENCY` / `ANSWER_CACHE_SIZE` | No | `4` / `256` | Simultaneous LLM calls; cached answers for identical question + passages |
| `LLM_REASONING_EFFORT` | No | — | Passed to the LLM as `reasoning_effort` (e.g. `none` to stop Gemini spending tokens on hidden thinking) |
| `GEMINI_BASE_URL` | No | `https://generativelanguage.googleapis.com/v1beta/openai/` | Gemini OpenAI-compatible endpoint |
| `DEEPSEEK_API_KEY` | Yes* | — | DeepSeek LLM API key (fallback) |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com/v1` | DeepSeek API base URL |
| `LLM_MODEL` | No | `deepseek-chat` | LLM model name |
| `LLM_TEMPERATURE` | No | `0.1` | LLM temperature |
| `FEATHERLESS_API_KEY` | Yes* | — | Featherless AI API key (alternative) |
| `FEATHERLESS_BASE_URL` | No | — | Featherless API base URL |
| `FEATHERLESS_MODEL` | No | — | Featherless model name |
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

*One of `GEMINI_API_KEY`, `DEEPSEEK_API_KEY` or `FEATHERLESS_API_KEY` is required for LLM features. Priority: Gemini, then Featherless, then DeepSeek.

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

Latest run on the live deployment with `gemini-3.1-flash-lite` (full report and per-question answers: [BENCHMARK.md](./BENCHMARK.md)):

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

See [PERFORMANCE.md](./PERFORMANCE.md) for detailed benchmarks, load test results, and observability reports.

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

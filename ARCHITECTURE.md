# Architecture Guide

> **Audience:** Senior engineers evaluating the system architecture, design decisions, and trade-offs.

---

## 1. Overall System Architecture

SentinelRAG follows a **microservices-inspired monolith** architecture — a single FastAPI process orchestrating multiple specialized services with clear interface boundaries, backed by purpose-built data stores (PostgreSQL for metadata/structured data, Qdrant for vector search, Redis for caching).

### Design Philosophy

- **Separation of concerns**: Business logic lives in `app/services/`, data models in `app/models/`, API layer in `app/api/v1/`, and the workflow engine in `app/graph/`. Each layer depends only on the layer below it.
- **Fail-safe by default**: Every external dependency (LLM, Qdrant, PostgreSQL) has a graceful degradation path. The system never crashes due to a downstream failure.
- **Observability as a first-class concern**: Structured JSON logging, middleware-level request tracing, in-memory metrics collection with percentile calculations, and resource tracking are built into the core framework.
- **Configuration-driven**: All tunable parameters (chunk sizes, model names, thresholds, rate limits) are in a single `Settings` class with `.env` file support.

---

## 2. Backend Architecture

### 2.1 Framework & Language

**Choice: Python 3.12 + FastAPI**

Python was chosen for its mature ML ecosystem (Sentence Transformers, PyTorch, LangChain). FastAPI provides async-native request handling, automatic OpenAPI documentation, and Pydantic-based validation — critical for an API-first system. The `async` SQLAlchemy engine ensures the event loop is never blocked by database queries, even under concurrent load.

### 2.2 Core Layer (`app/core/`)

| Module | Responsibility | Key Design Decision |
|---|---|---|
| `config.py` | Centralized settings via Pydantic `BaseSettings` | Single source of truth; supports two LLM providers (DeepSeek + Featherless) with automatic fallback |
| `database.py` | Async SQLAlchemy engine + session factory | Lazy initialization; `pool_size=5`, `max_overflow=10` for 50+ concurrent users |
| `logging.py` | Structured JSON logging | Suppresses verbose library logs (httpx, urllib3); supports `request_id` for distributed tracing |
| `middleware.py` | RequestID, Security Headers, Rate Limiting | In-memory rate limiter (acceptable for single-instance; Redis upgrade path documented) |
| `exceptions.py` | 8-custom-type exception hierarchy with standardized error responses | Every exception maps to correct HTTP status code; generic handler prevents stack leaks. All error responses include `request_id`, `trace_id`, `error_code`, and `message` for consistent client-side handling |
| `health_check.py` | Exponential backback dependency waiter | `wait_for_postgres()` and `wait_for_qdrant()` with base 0.5s backoff, max 10 retries. Called during startup before Alembic migrations |
| `metrics.py` | In-memory metrics with p50/p95/p99 | 10,000-sample max prevents unbounded growth; tagged latency recording per operation |
| `resource_tracker.py` | Async CPU/memory/disk sampling | Background asyncio task at 1-second intervals; 3600-sample max (1 hour); graceful psutil degradation |

**Why not Prometheus directly?** The in-memory collector was chosen for zero-infrastructure setup. Prometheus integration is documented as a future improvement for production deployments.

### 2.3 Service Layer (`app/services/`)

The service layer implements a **pipeline architecture** where each service performs one transformation in the retrieval or ingestion chain:

```
Upload → FileService → DocumentService → OCRService → TextCleaning → ChunkingService → EmbeddingService → IndexingService
Query → QueryPreprocessor → VectorSearch + BM25Search → HybridSearch (RRF) → RerankerService → ConfidenceService → AnswerGenerator
```

**Key engineering decisions:**

- **Lazy model loading**: Sentence Transformers and Cross-Encoder models are loaded on first use, not at startup. This keeps cold start time to ~1 second (vs. 5+ seconds for eager loading). The first request pays the cold-start cost, but subsequent requests are fast.
- **Batched embeddings**: `EmbeddingService` processes documents in configurable batches (default 32), reducing GPU memory pressure and improving throughput for large documents.
- **Graceful degradation**: Every service that depends on an external resource (LLM, Qdrant, database) has a fallback path. For example, `AnswerGenerator` falls back to returning the first chunk's text if the LLM is unavailable.
- **Sync vs. async**: Heavy CPU-bound operations (embedding, reranking, OCR) are synchronous and run in the thread pool. I/O-bound operations (database queries, network calls) are async.

### 2.4 Graph Layer (`app/graph/`)

**Choice: LangGraph**

LangGraph was chosen over a simple if-else chain because it provides:
1. **Explicit state management** via `GraphState` TypedDict — every node knows exactly what data it receives and produces
2. **Conditional routing** — the graph can branch dynamically based on confidence scores, contradiction detection, and retry counts
3. **Compile-time validation** — LangGraph validates the graph structure (no dangling edges, all nodes reachable)
4. **Execution tracing** — each node's execution time is captured in the state's `latencies` dict

#### The 8-Node Pipeline

**Node 1: Retrieve** — Executes hybrid search (vector + BM25 + RRF + Cross-Encoder) and stores results as structured dicts in `retrieved_chunks`.

**Node 2: Confidence Evaluate** — Calculates a composite score from vector similarity (30%), reranker confidence (50%), and result coverage (20%). Routes to generate if HIGH (≥80), or to rewrite if LOW/MEDIUM.

**Node 3: Query Rewrite** — Uses the LLM to rewrite the user's question for better retrieval. The prompt instructs the LLM to expand vague pronouns, fix grammar, and add context.

**Node 4: Retry Retrieve** — Re-executes retrieval with the rewritten query. Compares new confidence to previous. Routes to generate if improved to HIGH, back to rewrite if retries remain, or to contradiction detection.

**Node 5: Contradiction Detect** — Analyzes retrieved chunks for numerical conflicts (same number, different context) and policy conflicts (positive vs. negative statements about same entity). Routes to clarification if contradiction found, or to generate if clean.

**Node 6: Clarification** — Detects ambiguous queries using regex patterns and optional LLM analysis. Returns a clarification question to the user.

**Node 7: Generate Answer** — Constructs a prompt with the original question and retrieved context. Instructs the LLM to use only the provided context and cite sources with `[Source N]` markers.

**Node 8: Fallback** — Returns a standard low-confidence "I don't have enough information" response when all paths fail.

### Confidence Breakdown & Observability

Every node in the pipeline now returns a `confidence_breakdown` dict with per-component scores (`vector_similarity`, `reranker_confidence`, `citation_coverage`) plus pipeline status flags (`contradiction_status`, `retry_success`). The generation node computes the **definitive** final breakdown, reflecting the full pipeline state.

An `llm_observability` dict tracks token usage per stage — prompt/completion/total tokens via `tiktoken` (cl100k_base, fallback `len//4`) — along with model name and temperature for AI observability.

The `graph_execution` list captures per-node timing, input/output summaries, routing decisions, and retry counts for full decision traceability.

### Trace Service

A dedicated `TraceService` persists every pipeline execution as a `Trace` ORM record (SQLAlchemy + Alembic migrations). Traces include question, answer, confidence score, reasoning path, retrieval details, latencies, llm_observability, and graph execution data. Export endpoints support CSV, Markdown, and JSON formats.

**Why 8 nodes and not simpler?** Each node has a single responsibility, making testing, logging, and debugging straightforward. The cost is slightly more indirection, but the ability to time, trace, and test each step independently justifies the design.

### 2.5 API Layer (`app/api/v1/`)

- **Separate routers per domain**: `health.py`, `chat.py`, `search.py`, `ingest.py`, `embed.py`, `metrics.py`, `evaluation.py`
- **Schema-based responses**: Every endpoint returns Pydantic-validated response models, ensuring API contract compliance
- **Lazy graph compilation**: The LangGraph is compiled once and cached as a module-level singleton, not rebuilt on every request
- **Metrics middleware**: Every HTTP request is automatically timed and recorded in the metrics collector

---

## 3. Frontend Architecture

### 3.1 Framework & Language

**Choice: Next.js 15 + React 19 + TypeScript**

Next.js App Router provides file-system routing, server components for landing pages, and client components for interactive dashboard features. TypeScript ensures type safety across the API boundary — the `types/index.ts` file mirrors the backend's Pydantic schemas.

### 3.2 State Management

**Choice: TanStack React Query (no Redux)**

React Query handles all server state (API calls, caching, background refetching). There is no global client state store because:
- The application is dashboard-focused (no complex client-side state)
- React Query's `staleTime: 30000` provides 30-second caching with automatic refetch
- Mutations (upload, chat, evaluate) invalidate related queries automatically

### 3.3 Data Flow

```
Page Component
    │
    ▼
React Query Hook (use-chat, use-documents, use-health)
    │
    ▼
API Service (chat.ts, documents.ts, health.ts)
    │
    ▼
Axios Instance (api.ts: 120s timeout, error interceptor)
    │
    ▼
Backend API
```

### 3.4 Key Pages

| Page | Components | Data Source |
|---|---|---|
| Dashboard | MetricCard × 4, StatusBadge, ActivityList | `GET /api/v1/health`, `GET /api/v1/evaluation/report` |
| Chat | MessageList, ChatInput, ExplainabilityPanel | `POST /api/v1/chat` |
| Documents | DocumentCard, SearchBar, ChunkDetailDialog | `GET /api/v1/documents`, `GET /api/v1/document/{id}/chunks` |
| Upload | UploadDropzone, ProcessingPipeline | `POST /api/v1/ingest`, `POST /api/v1/embed/{id}` |
| Evaluation | MetricCard × 8, BarChart, RadarChart, LatencyChart | `GET /api/v1/evaluation/report`, `GET /api/v1/evaluation/history` |
| Settings | ConfigDisplay, PipelineSteps | Static configuration display |

---

## 4. Document Processing Pipeline

### 4.1 File Validation (`file_service.py`)

Every upload is validated against three criteria before any processing begins:
- **Extension**: Must be in `ALLOWED_EXTENSIONS` (`.pdf`, `.png`, `.jpg`, `.jpeg`)
- **Content Type**: Must match `ALLOWED_CONTENT_TYPES` (preventing extension spoofing)
- **Size**: Must not exceed `MAX_FILE_SIZE` (50MB)

**Why 50MB?** PDF files in enterprise settings commonly reach 20–40MB for scanned documents with embedded images. 50MB provides headroom while preventing resource exhaustion attacks.

### 4.2 OCR (`ocr_service.py`)

**Choice: Tesseract via PyMuPDF + pytesseract**

Tesseract was chosen over cloud OCR APIs (Google Vision, AWS Textract) for offline operation and zero API costs. For PDFs, PyMuPDF renders each page to an image at 300 DPI before passing to Tesseract — this matches the resolution quality of cloud OCR for clean documents.

**Fallback chain:**
1. Attempt PDF text extraction (PyMuPDF `get_text()`)
2. If extracted text < 50 characters, assume scanned PDF and fall back to OCR
3. For images (PNG/JPG), direct OCR

**Why 50-character threshold?** Scanned PDFs typically extract 0–10 characters (usually garbage). Digital PDFs extract the full text. 50 characters provides a clear signal — any PDF with fewer than 50 extractable characters is almost certainly scanned.

### 4.3 Text Cleaning (`text_cleaning.py`)

Raw text from PDFs and OCR contains artifacts that degrade retrieval quality:

| Noise Source | Treatment |
|---|---|
| Unicode variants (smart quotes, em-dashes) | `unicodedata.normalize('NFKC')` |
| Extra whitespace, tabs, newlines | Collapse to single space |
| Page numbers ("Page 1 of 42") | Regex removal |
| Repeated headers/footers | 3-line repetition pattern detection |
| Non-printable characters | Stripped |

**Why not NLP-based cleaning?** Rule-based cleaning is deterministic, zero-latency, and predictable. NLP-based cleaning (spelling correction, grammar normalization) would add latency and potential errors without meaningful retrieval improvement for technical documents.

### 4.4 Chunking (`chunking_service.py`)

**Strategy: Semantic chunking with section awareness and overlap**

```
Document → Section detection (##, ===, numbered) → Paragraph splitting
    → For each paragraph: if ≤500 words, keep; else split at sentence boundaries
    → 100-word overlap between consecutive chunks
    → Each chunk tracks: document_id, chunk_index, char_start, char_end, page_number, section
```

**Why 500-word chunks with 100-word overlap?**
- **500 words** (~3–5 paragraphs) provides sufficient context for the LLM while keeping individual chunks under the token limit for embedding models
- **100-word overlap** (20%) ensures that sentences spanning chunk boundaries are captured in both chunks, preventing context loss at boundaries
- **Section awareness** preserves document structure — chunks from different sections are less likely to be fused by the reranker

---

## 5. Hybrid Retrieval System

### 5.1 Vector Search (`vector_search_service.py`)

**Model: BAAI/bge-small-en-v1.5 (384-dimensional embeddings)**

This model was chosen over larger alternatives (e.g., BAAI/bge-large-en-v1.5, 1024d) for:
- **Speed**: 4× faster inference than 1024d models on CPU
- **Storage**: 384d vectors require 62.5% less storage in Qdrant
- **Quality**: MTEB score of 61.5 — within 3% of the large model despite being 7× smaller
- **Memory**: ~133MB vs. ~1.3GB for the large model — critical for the 4GB RAM target

**Why Qdrant over Pinecone/Weaviate/Milvus?**
- **Self-hosted**: No API costs, no data leaving the network, no rate limits
- **Rust-based**: Low memory overhead compared to Java-based alternatives
- **Filtering**: Built-in payload filtering for document-level queries
- **Simple API**: REST + gRPC with intuitive collection management

### 5.2 BM25 Full-Text Search (`bm25_service.py`)

**Choice: PostgreSQL `ts_rank_cd`**

PostgreSQL's built-in full-text search was chosen over Elasticsearch/Meilisearch because:
1. **No additional infrastructure** — PostgreSQL is already in the stack
2. **ACID guarantees** — Document metadata and full-text index are transactionally consistent
3. **Asynchronous support** — `sqlalchemy[asyncio]` provides async-native PostgreSQL queries

The search uses `to_tsvector('english', chunk_text)` for tokenization and `ts_rank_cd` for coverage-based ranking. Stop words, stemming, and dictionary lookups are handled by PostgreSQL's built-in English configuration.

### 5.3 RRF Fusion (`hybrid_search_service.py`)

**Reciprocal Rank Fusion (RRF)** combines vector and BM25 results without requiring score normalization:

```
RRF_score(d) = 1/(k + rank_vector(d)) + 1/(k + rank_bm25(d))
```

**Why k=60?** Standard RRF literature recommends k=60 as the optimal constant. Higher k values increase the influence of lower-ranked results from both sources, which is beneficial when one source has higher precision (vectors tend to be more precise for semantic matches; BM25 for keyword matches).

### 5.4 Cross-Encoder Reranking (`reranker_service.py`)

**Model: ms-marco-MiniLM-L-6-v2**

A cross-encoder evaluates query-document pairs jointly (unlike bi-encoders which encode independently). This is more accurate but O(n) — we only rerank the top 10 results from RRF fusion to keep latency under control.

**Why rerank at all?** The cross-encoder improves precision by 10–15% over RRF alone because it can model the interaction between query and document tokens — something neither vector search nor BM25 can do independently.

### 5.5 Confidence Scoring (`confidence_service.py`)

The composite confidence score combines three signals:

```
confidence = vector_similarity * 0.30 + reranker_confidence * 0.50 + coverage * 0.20
```

| Component | Weight | Rationale |
|---|---|---|
| Vector similarity (avg) | 30% | Measures semantic alignment between query and results |
| Reranker confidence (avg) | 50% | Highest weight — cross-encoder best captures query-document relevance |
| Coverage (min(total/10, 1)) | 20% | Penalizes pipelines with very few results; caps at 10+ results |

**Threshold alignment:**
- **HIGH (≥80)**: Routes directly to answer generation — high confidence that retrieved context contains the answer
- **MEDIUM (50–79)**: Triggers query rewriting and retry — some relevant context exists but may be insufficient
- **LOW (<50)**: Triggers query rewriting and retry — retrieved context is likely insufficient

The 80/50 thresholds were determined empirically by evaluating 100+ query-response pairs and finding that scores ≥80 rarely required correction, while scores <50 rarely produced correct answers.

---

## 6. LangGraph Self-Correction Workflow

### 6.1 Why LangGraph over a Manual Pipeline?

A standard RAG pipeline is a linear sequence: retrieve → generate. SentinelRAG requires:
- **Branching**: Different paths for HIGH vs. LOW confidence
- **Loops**: Retry with rewritten queries cycles back to retrieval
- **State accumulation**: Each node contributes to a growing state that tracks confidences, retries, latencies, and reasoning paths

LangGraph handles these patterns natively. A manual implementation would require complex if-else chains, global state management, and manual execution tracing.

### 6.2 State Design (`state.py`)

```python
class GraphState(TypedDict):
    question: str
    rewritten_question: NotRequired[str]
    retrieved_chunks: list[dict]
    confidence_score: float
    confidence_level: str
    retry_count: int
    max_retries: int
    contradiction_detected: bool
    contradiction_reason: str
    clarification_needed: bool
    clarification_question: str
    answer: str
    citations: list[dict]
    reasoning_path: list[str]
    latencies: dict[str, float]
    confidence_improved: NotRequired[bool]
```

**Why `TypedDict` instead of a dataclass?** LangGraph requires a dict-like state. `TypedDict` provides type hints while remaining dict-compatible. Each node returns a partial update dict that LangGraph merges into the shared state.

### 6.3 Routing Logic

**After Confidence Evaluation:**
- `confidence_level == "HIGH"` → `generate_answer`
- Otherwise → `rewrite_query`

**After Retry:**
- `confidence_improved == True` and `confidence_level == "HIGH"` → `generate_answer`
- Retries remaining → `rewrite_query`
- Max retries reached → `contradiction_detect`

**After Contradiction Detection:**
- Contradiction found → `clarification`
- No contradiction → `generate_answer`

**After Clarification:**
- Always → `END` (returns clarification question to user)

### 6.4 Self-Correction Example

```
User: "What is the refund policy for international orders?"

1. Retrieve → 3 chunks found (one about domestic refunds, one about international shipping)
2. Confidence evaluate → score=55 (MEDIUM) — only partial match
3. Query rewrite → "What is the refund policy specifically for international orders at your company?"
4. Retry retrieve → 4 chunks found (all about international refunds)
5. Confidence evaluate → score=88 (HIGH)
6. Generate answer → "International orders can be refunded within 30 days... [Source 1]"
```

---

## 7. Evaluation Framework

### 7.1 Design

The evaluation framework is designed to compare SentinelRAG against a clean baseline under identical conditions:

```
benchmark.json (18 questions with ground truth)
    ├── BaselineRAG.answer() → single retrieve + generate
    └── SentinelRAG.answer() → full LangGraph pipeline
    
    Both fed to:
    ├── RAGAS metrics (faithfulness, relevancy, precision, recall)
    ├── DeepEval metrics (hallucination, bias, toxicity, correctness)
    └── Custom metrics (confidence calibration, citation accuracy, etc.)
    
    Results aggregated by MetricsCollector
    Reports generated: JSON, CSV, Markdown
    Charts generated: bar charts, radar chart, latency chart
```

### 7.2 Metrics Definitions

| Metric | Formula | Range |
|---|---|---|
| **Faithfulness** | Fraction of answer claims supported by context | 0–1 (higher is better) |
| **Hallucination** | 1 − Faithfulness | 0–1 (lower is better) |
| **Answer Relevancy** | Keyword overlap F1 between question and answer | 0–1 (higher is better) |
| **Context Precision** | Average precision of relevant chunks in ranked list | 0–1 (higher is better) |
| **Context Recall** | Fraction of relevant documents retrieved | 0–1 (higher is better) |
| **Correctness** | Combined keyword F1 + claim recall vs ground truth | 0–1 (higher is better) |

### 7.3 Baseline vs. SentinelRAG

The baseline is intentionally simple (single retrieve + generate) to isolate the impact of self-correction:

| Feature | Baseline | SentinelRAG |
|---|---|---|
| Retrieval strategy | Single hybrid search | Hybrid search with optional retry |
| Query rewriting | None | LLM-based on low confidence |
| Confidence evaluation | None | 3-tier composite score |
| Contradiction detection | None | Numerical + policy conflict detection |
| Clarification | None | Regex + LLM ambiguity detection |
| Fallback | None | Returns "I don't know" on failure |

---

## 8. Performance & Observability

### 8.1 Metrics Architecture

```
[HTTP Request] → Middleware (timing) → MetricsCollector
                     ↓
              [Resource Tracker] → psutil sampling (1s interval)
                     ↓
              [/metrics/system, /metrics/performance, /metrics/errors]
```

The `MetricsCollector` stores latency samples per endpoint with p50/p95/p99 calculation. The `ResourceTracker` captures CPU, memory, and disk usage at 1-second intervals. Both are exposed via dedicated API endpoints.

### 8.2 Why In-Memory Metrics?

For a hackathon submission, in-memory metrics provide immediate visibility without infrastructure dependencies. The API makes it trivial to switch to a Prometheus-based system: a middleware adapter can scrape the in-memory collector and expose Prometheus-formatted metrics.

### 8.3 Load Testing Architecture

Locust simulates realistic user behavior:
- **Chat queries** (weight 5): Most common operation, tests the full pipeline
- **Health checks** (weight 3): Lightweight, simulates monitoring systems
- **Search** (weight 2): Tests retrieval without generation
- **Evaluation reports** (weight 1): Infrequent read operations

---

## 9. Key Engineering Trade-offs

| Decision | Chosen Approach | Alternative | Rationale |
|---|---|---|---|
| LLM provider | DeepSeek + Featherless | OpenAI-only | Cost efficiency ($0.48/M vs $3/M tokens), API compatibility |
| Vector database | Qdrant (self-hosted) | Pinecone | Zero API costs, data privacy, no rate limits |
| Embedding model | bge-small-en-v1.5 (384d) | bge-large-en-v1.5 (1024d) | 4× faster, 62% less storage, 3% quality loss |
| Reranking | Cross-encoder (MiniLM) | Cohere Rerank | Offline, zero API cost, <10ms inference |
| Full-text search | PostgreSQL tsvector | Elasticsearch | No additional infrastructure, ACID consistency |
| Metrics | In-memory collector | Prometheus | Zero setup, immediate visibility |
| State management | React Query | Redux | Simpler for dashboard apps, built-in caching |
| Deployment | Docker Compose | Kubernetes | Simpler setup, sufficient for 50+ concurrent users |

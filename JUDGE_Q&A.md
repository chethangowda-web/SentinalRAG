# Judge Q&A Preparation

> **Audience:** Presenters preparing for hackathon judge Q&A sessions. Contains 50+ technical questions with concise model answers covering every aspect of SentinelRAG.

---

## Architecture

**Q1: Why did you choose LangGraph over a simple if-else chain?**
LangGraph provides explicit state management via `GraphState` TypedDict, compile-time graph validation, conditional routing with dynamic branching, and automatic execution tracing. A manual chain would require complex global state, fragile if-else nesting, and manual logging — LangGraph handles all of this natively.

**Q2: Why FastAPI instead of Django or Flask?**
FastAPI is async-native, auto-generates OpenAPI documentation from Pydantic schemas, and provides built-in validation. Flask lacks async support (requires extensions), Django is too heavy for a focused API service. FastAPI's performance is on par with Node.js and Go for JSON APIs.

**Q3: How do you handle request tracing across the pipeline?**
A `RequestIDMiddleware` generates or propagates `X-Request-ID` headers. This ID is passed through structured JSON logs, allowing us to trace a single request across all middleware, API handlers, graph nodes, and service calls.

**Q4: Why did you separate the graph layer from the services layer?**
The graph layer handles workflow orchestration (routing, state, branching). The service layer handles business logic (retrieval, embedding, scoring). This separation means we can test the graph without running services, and test services without the graph.

**Q5: How is the application structured for testability?**
Every service is a standalone function (no class dependencies). The graph injects dependencies via `RunnableConfig`. The API layer delegates to services. This allows unit testing each layer in isolation with mocked dependencies.

---

## Hybrid Search

**Q6: Why hybrid search instead of pure vector search?**
Vector search excels at semantic similarity but misses exact keyword matches (names, numbers, codes). BM25 catches exact matches but ignores semantics. Hybrid search (vector + BM25 + RRF fusion) gets the best of both — 18.3% higher context recall than vector-only.

**Q7: Why k=60 in RRF?**
Standard RRF literature (Cormack et al.) empirically determined k=60 as the optimal constant for combining ranked results. Higher k values increase the influence of lower-ranked results, which helps when one search method is significantly more precise than the other.

**Q8: Why PostgreSQL for BM25 instead of Elasticsearch?**
PostgreSQL was already in our stack for document metadata. Adding Elasticsearch would mean another service to deploy, configure, and monitor. PostgreSQL's `ts_rank_cd` provides competitive full-text search performance for our scale, with the advantage of ACID consistency with document metadata.

**Q9: How do you normalize scores between vector and BM25 results?**
We don't. RRF operates on ranks, not scores, so no normalization is needed. Rank 1 from vector search contributes equally to rank 1 from BM25, regardless of their raw similarity scores.

**Q10: What happens when Qdrant is unavailable?**
The system degrades gracefully to BM25-only search. Vector results will be empty, but BM25 will still retrieve keyword-matched results. The confidence score will be lower (no vector component), which may trigger query rewriting and retry.

---

## Qdrant

**Q11: Why Qdrant over Pinecone, Weaviate, or Milvus?**
Qdrant is Rust-based (low memory footprint), self-hostable (zero API costs, data privacy), has a simple REST API, and supports payload filtering. Pinecone has API costs and egress fees. Weaviate is Java-based (higher memory). Milvus is more complex to operate.

**Q12: How do you handle vector collection management?**
`ensure_collection()` is called in `qdrant_service.py` before every upsert. It checks if the collection exists with the correct configuration (384 dimensions, cosine distance) and creates it if not. The collection name is configurable via `QDRANT_COLLECTION`.

**Q13: What distance metric do you use for vector search?**
Cosine similarity. All embeddings are L2-normalized before storage, so cosine similarity is equivalent to dot product, which Qdrant can optimize for maximum performance.

**Q14: How do you handle vector duplicates?**
`indexing_service.py` checks if a chunk is already embedded by querying its `embedding_status` in PostgreSQL. Only chunks with `embedding_status != 'embedded'` are processed. Qdrant's `upsert` with the same point ID overwrites existing vectors.

**Q15: How large is your Qdrant collection?**
Each vector is 384 float32 values (1,536 bytes) plus UUID and payload. A collection of 10,000 chunks uses approximately 15MB for vectors plus ~5MB for payloads. Qdrant's memory mapping handles collections much larger than available RAM efficiently.

---

## Embeddings

**Q16: Why bge-small-en-v1.5 over larger models?**
It's a 3-way trade-off: quality, speed, and memory. bge-small (384d, 133MB) is 4× faster than bge-large (1024d, 1.3GB) with only ~3% MTEB score difference (61.5 vs. 63.8). For a 4GB RAM target, saving 1.1GB is critical.

**Q17: Why L2 normalization after embedding?**
Normalization ensures all vectors are on the unit sphere, making cosine similarity equivalent to dot product. This allows Qdrant to use its optimized dot product implementation instead of computing cosine explicitly.

**Q18: How do you handle batch embedding for large documents?**
Documents are processed in configurable batches (default 32). Each batch is encoded by SentenceTransformer and normalized. Batching reduces GPU memory pressure and improves throughput through model parallelism.

**Q19: What happens when the embedding model fails to load?**
The `_load_model()` function logs the error and raises an exception. The API endpoint returns a 500 error with `embedding_failure` type. Disk-based operations (upload, OCR, chunking) continue to work.

**Q20: Can I swap the embedding model without code changes?**
Yes. Set `EMBEDDING_MODEL` and `EMBEDDING_DIMENSION` in environment variables. The model is loaded lazily on first use, so a restart is required. The Qdrant collection must be recreated if the dimension changes.

---

## Confidence Scoring

**Q21: How is the composite confidence score calculated?**
`confidence = (avg_vector × 0.30) + (avg_reranker × 0.50) + (coverage × 0.20)`. Vector measures semantic alignment, reranker measures query-document relevance (highest weight), and coverage penalizes systems with too few results.

**Q22: Why 80 and 50 as thresholds for HIGH/MEDIUM/LOW?**
Empirically determined. We evaluated 100+ query-response pairs and found that scores ≥80 rarely required correction, scores 50–79 often benefited from retry, and scores <50 almost never produced correct answers without retry.

**Q23: What happens when confidence is LOW after retry?**
The graph routes to contradiction detection, then to fallback. The system returns "I don't have enough information to answer this question" rather than generating a low-confidence hallucination.

**Q24: How do you prevent false HIGH confidence on hallucinated content?**
Confidence is based on retrieval quality, not answer quality. The LLM is instructed to answer only from provided context. The cross-encoder evaluates each chunk's relevance to the query. If context is genuinely relevant, HIGH confidence is correct.

**Q25: Can confidence thresholds be tuned?**
Yes. They're hardcoded in `confidence_service.py` but should be moved to `Settings` for configurability. Different domains may need different thresholds — legal documents might require ≥90 for HIGH.

---

## LangGraph

**Q26: Why 8 nodes? Why not simpler?**
Each node has a single responsibility (retrieve, evaluate, rewrite, retry, detect, clarify, generate, fallback). This makes testing trivial — each node can be tested in isolation. The 8-node structure maps directly to the 8 distinct operations in the self-correction workflow.

**Q27: How does state flow through the graph?**
`GraphState` is a `TypedDict` with fields for question, chunks, confidence, retries, contradictions, clarifications, answer, citations, reasoning path, and latencies. Each node returns a partial dict that LangGraph merges into the shared state.

**Q28: What happens if a node throws an exception?**
The exception propagates up to the `chat.py` API handler, which catches it and returns a safe error response. The middleware logs the error with request_id for debugging. The exception hierarchy maps to appropriate HTTP status codes.

**Q29: Can the graph be visualized or debugged?**
LangGraph provides built-in visualization (Mermaid diagrams via `graph.get_graph().draw_mermaid()`). The `reasoning_path` in the state tracks every node visited. Per-node latencies in `latencies` dict help identify bottlenecks.

**Q30: How is the graph compiled and cached?**
The graph is compiled once and cached as a module-level `_graph` singleton in `chat.py`. Compilation happens on first request, not at startup. This avoids rebuild overhead on every request.

---

## Evaluation

**Q31: How many questions are in the benchmark?**
18 questions across 7 categories: easy (3), medium (3), hard (3), contradictory (3), missing context (3), ambiguous (2), OCR (1). Each has ground truth, expected documents, and metadata flags.

**Q32: How are faithfulness and hallucination measured?**
Faithfulness extracts claims from the generated answer and verifies each claim against the retrieved context using NLI (Natural Language Inference). Hallucination rate is simply 1 − faithfulness.

**Q33: Why compare against a baseline?**
To isolate the impact of self-correction. The baseline is a simple retrieve-then-generate pipeline without confidence evaluation, query rewriting, retry, contradiction detection, or clarification. Any difference is attributable to the self-correction features.

**Q34: What metrics matter most for enterprise deployment?**
Faithfulness (95%) and hallucination rate (5.3%) are the primary metrics — they directly measure trustworthiness. Context recall (92%) matters for finding all relevant information. Correctness (90%) is the overall quality score.

**Q35: How do you prevent evaluation data leakage?**
The benchmark dataset is completely separate from the training data of all models used (embedding, reranker, LLM). Questions are synthetic and domain-specific (financial/regulatory), unlikely to appear in any model's training set.

---

## Performance

**Q36: Why is chat latency dominated by LLM time (85-95%)?**
Vector search takes ~50ms, BM25 ~15ms, RRF <1ms, reranking ~50ms, confidence scoring <5ms. The LLM's answer generation takes 1.5-3 seconds depending on answer length and model. The LLM is 30-60× slower than all other components combined.

**Q37: What is the system's throughput limit?**
Approximately 14.5 requests per second, limited by the LLM API. At 50 concurrent users, latency increases to 8.2 seconds P50 due to request queueing at the LLM API. The backend handles more concurrent requests than the LLM can process.

**Q38: How much memory does each model consume?**
bge-small: ~133MB, Cross-Encoder MiniLM: ~80MB, PyTorch runtime: ~400MB. Total model memory: ~613MB. Application overhead brings total to ~800MB idle, ~1.2GB under load.

**Q39: Can the system handle concurrent users?**
Yes. Tested up to 100 concurrent users with 0% error rate. Async SQLAlchemy ensures database I/O doesn't block the event loop. The 5-pool-size connection pool handles 50 concurrent queries without contention.

**Q40: What's the cold start time?**
About 5 seconds on first request — models load lazily. Subsequent requests take normal latency. We could preload models in the lifespan handler for zero cold start, but deferred loading optimizes for containers that restart frequently.

---

## Scalability

**Q41: How do you scale to more users?**
Add uvicorn `--workers N` for multi-process deployment (N = CPU cores). Switch rate limiting from in-memory to Redis. Add a connection pooler (PgBouncer) for PostgreSQL. Use an LLM provider with higher rate limits.

**Q42: How do you handle very large documents (500+ pages)?**
Chunking is O(n) and handles 100,000 words in 2.3 seconds (stress test verified). Embedding is batched at 32 chunks per batch. The 50MB upload limit and 500-word chunk size prevent unbounded processing.

**Q43: Can you scale to millions of documents?**
Qdrant handles millions of vectors efficiently. PostgreSQL with proper indexing scales to millions of rows. The bottleneck would be LLM API cost at scale (~$0.48/M tokens), not infrastructure.

**Q44: How does the system perform on low-resource hardware?**
Tested on 4GB RAM: all models fit (bge-small: 133MB, MiniLM: 80MB). Swap is used at peak but performance remains acceptable. The system is designed for the 4-8GB range typical of small cloud instances.

---

## Deployment

**Q45: How do you handle environment-specific configuration?**
A single `Settings` class loads all configuration from environment variables with sensible defaults. `.env.example` documents every variable. The `validate()` method warns on misconfiguration (missing API key, default SECRET_KEY).

**Q46: What's in the Docker Compose setup?**
6 services: PostgreSQL 16 (metadata + BM25), Redis 7 (cache), Qdrant 1.13 (vectors), FastAPI backend, Next.js frontend, NGINX reverse proxy. All on a single bridge network with health checks and JSON-file logging.

**Q47: How do you handle database migrations?**
Currently using SQLAlchemy `create_all()` on startup — acceptable for development but should use Alembic for production. The `create_all()` approach creates missing tables without altering existing ones.

**Q48: Can this run on a single machine?**
Yes. All services run in Docker Compose on a single machine. The full stack uses ~4GB RAM with all services running. The memory-intensive components are Python/ML models, not the databases.

---

## Security

**Q49: How do you prevent prompt injection?**
Multiple layers: system-level instructions constraining the LLM, context isolation (separating retrieved text from user input), low temperature (0.05) for answer generation, query rewriting with guardrails, and clarification checks on ambiguous input.

**Q50: How do you validate file uploads?**
Three checks: file extension against allowed list (`.pdf`, `.png`, `.jpg`, `.jpeg`), content type MIME match, and size limit (50MB configurable). All validation happens before any file processing begins.

**Q51: How are API keys protected?**
API keys are read from environment variables only. `.env` is in `.gitignore`. The `.env` file uses a placeholder key by default. In production, use a secrets manager or Docker secrets.

**Q52: What security headers does NGINX set?**
X-Frame-Options (SAMEORIGIN), X-Content-Type-Options (nosniff), X-XSS-Protection, Strict-Transport-Security (31536000s), Referrer-Policy, Permissions-Policy. Plus Content-Security-Policy to restrict resource loading.

---

## Failure Handling

**Q53: What happens when the LLM API is unreachable?**
The system falls back to a chunk-based answer. The `_no_llm_fallback` function in `answer_generator.py` returns the first retrieved chunk's text with a disclaimer. The `/chat` endpoint still returns a response — never crashes.

**Q54: What happens when Qdrant is down?**
Vector search returns empty results. The retrieval pipeline falls back to BM25-only search. Confidence scores are lower, which may trigger retry or fallback. The system continues operating with reduced functionality.

**Q55: What happens when a document upload fails mid-processing?**
The exception is caught by the document service, logged, and the database record is updated with `status: "failed"`. No partial state is left in Qdrant or PostgreSQL. The user receives an error response with details.

**Q56: How does the system handle corrupted PDF files?**
PyMuPDF attempts to read the PDF. If it fails, the system falls back to OCR (Tesseract on rendered pages). If OCR also fails, an `OCRError` is raised and the user receives a 500 error with details.

**Q57: What happens during a database connection failure?**
The `_check_database()` health endpoint returns `unhealthy`. API endpoints that need the database will raise `DatabaseConnectionError` (503). Read-only operations (chat with cached context) may still work depending on the failure type.

**Q58: How do you ensure the system doesn't silently fail?**
Every failure is logged with structured JSON (request_id, component, error_type). The metrics collector tracks error counts by type. The API returns appropriate HTTP status codes. The `/metrics/errors` endpoint exposes all errors for monitoring.

**Q59: What's the backup plan if the primary LLM provider fails?**
SentinelRAG supports two LLM providers simultaneously: DeepSeek and Featherless. The effective API key, base URL, and model are selected automatically — Featherless takes priority if configured, otherwise falls back to DeepSeek.

**Q60: How do you test failure modes?**
18 dedicated failure mode tests in `tests/failuretest/` cover: Qdrant unavailable, database unavailable, OCR failure, LLM timeout, embedding failure, invalid uploads, network errors, and corrupted input. Each test verifies the correct degradation behavior.

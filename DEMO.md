# Demo Guide

> **Audience:** Presenters demonstrating SentinelRAG to judges and stakeholders.

---

## Elevator Pitch (30 Seconds)

"Standard AI chatbots hallucinate — they make up confident-sounding answers when they don't know. SentinelRAG fixes this. Every time we retrieve information, we score our confidence. If it's low, we automatically rewrite the query and search again. If there are contradictions, we flag them. If the question is vague, we ask for clarification. We only generate an answer when we're confident the context supports it. The result: 95% faithfulness — a 70% reduction in hallucination over standard RAG systems."

---

## Product Demo (2 Minutes)

### Setup

```
Browser: http://localhost (dashboard open)
Terminal: docker compose logs -f (visible)
API client: curl ready
```

### Script

**0:00–0:15 | Dashboard Overview**
"Welcome to SentinelRAG. This dashboard shows our system status — all components healthy, documents indexed, and our latest evaluation run."

**0:15–0:30 | Upload a Document**
"Let me upload a financial disclosure document. Drag and drop — it validates the file type, extracts text via OCR if needed, and chunks it for retrieval."

**0:30–0:50 | Ask a Question (HIGH Confidence)**
"What was the total revenue in Q3 2024?" — The system finds the answer, shows HIGH confidence (92.5), and cites the source. The reasoning path shows: retrieve → confidence evaluate → generate answer.

**0:50–1:10 | Ask a Vague Question (Clarification)**
"What about the terms?" — The system detects ambiguity and asks for clarification, listing the topics it found. This prevents the common failure of guessing at vague questions.

**1:10–1:30 | Show Explainability**
"Let me show you the explainability panel — confidence score, latency breakdown across each pipeline stage, the reasoning path as a timeline, and the source citations with relevance scores."

**1:30–1:45 | Evaluation Results**
"Our benchmark evaluation compares SentinelRAG against a standard RAG pipeline. Across 18 questions, we achieved 95% faithfulness with a 70% reduction in hallucination."

**1:45–2:00 | Wrap**
"SentinelRAG is open source, Docker-ready, and available now on GitHub. Thank you."

---

## Hackathon Presentation (5 Minutes)

### Structure

| Time | Section | Slides |
|---|---|---|
| 0:00–0:30 | Introduction & Problem | 1–2 |
| 0:30–1:00 | Why Existing RAG Fails | 3 |
| 1:00–2:00 | Architecture & Self-Correction | 4–5 |
| 2:00–2:30 | Hybrid Retrieval | 6 |
| 2:30–3:30 | Live Demo | 7 |
| 3:30–4:00 | Evaluation Results | 8 |
| 4:00–4:30 | Performance Results | 9 |
| 4:30–5:00 | Conclusion & Q&A | 10 |

### Key Talking Points

1. **The Problem:** Hallucination is the #1 barrier to enterprise AI adoption
2. **Why It Happens:** Standard RAG has no mechanism to detect when it's wrong
3. **Our Solution:** A self-correcting pipeline that evaluates confidence, retries on failure, detects contradictions, and asks for clarification
4. **Technical Depth:** LangGraph 8-node workflow, hybrid search (vector + BM25 + cross-encoder), composite confidence scoring
5. **Results:** 95% faithfulness, 70% hallucination reduction, 100% failure mode test pass rate
6. **Demo:** Live walkthrough showing upload → chat → clarification → explainability
7. **Enterprise Ready:** Docker Compose, NGINX, health checks, rate limiting, structured logging

---

## Technical Walkthrough (10 Minutes)

### Segment 1: Architecture Deep-Dive (3 min)

Walk through the system architecture diagram:
1. **NGINX reverse proxy** — security headers, rate limiting, path routing
2. **FastAPI backend** — async handlers, Pydantic validation, middleware
3. **LangGraph pipeline** — show the 8-node graph with branching logic
4. **Services layer** — 18 business-logic modules with clear interfaces
5. **Data stores** — PostgreSQL (metadata + BM25), Qdrant (vectors), Redis (cache)

Explain key decisions:
- Why LangGraph over manual branching? (State management, tracing, validation)
- Why bge-small over larger models? (4× faster, 62% less storage, 3% quality loss)
- Why PostgreSQL for BM25? (No additional infrastructure, ACID consistency)

### Segment 2: Self-Correction Example (3 min)

Walk through one query step by step:

```
Question: "What are the shipping costs for international orders?"

1. Retrieve → 5 chunks found (domestic costs, timelines, restrictions)
2. Confidence Evaluate → score=62 (MEDIUM): partial match, not all chunks relevant
3. Query Rewrite → "What are the specific shipping costs and fees for international orders outside the domestic region?"
4. Retry Retrieve → 4 chunks found (all specifically about international costs)
5. Confidence Evaluate → score=91 (HIGH): all results highly relevant
6. Contradiction Detect → No contradictions found
7. Generate Answer → "International shipping costs vary by region..." [Source 1-4]
```

Show how the reasoning_path captures each step and the explainability panel visualizes it.

### Segment 3: Failure Mode Walkthrough (2 min)

Show three key failure modes and how SentinelRAG handles them:

**Missing Context:**
- Question about a topic not in any document
- Retry fails (no relevant context found)
- Falls back gracefully: "I don't have enough information to answer this question"

**Contradiction:**
- Two chunks cite different numbers for the same metric
- Contradiction detection flags the conflict
- System asks for clarification or returns a qualified answer

**LLM Unavailable:**
- API key not configured or rate limited
- Answer generator falls back to chunk-based response with disclaimer
- System continues operating with reduced functionality

### Segment 4: Evaluation & Performance (2 min)

Show the evaluation results table and explain:
- Metrics definitions (faithfulness, hallucination, relevancy, etc.)
- Baseline comparison methodology
- Failure mode reduction percentages
- Latency trade-off and why it's acceptable

Show performance benchmarks:
- Component-level latencies (all <15ms P99)
- Load test results (14.5 req/s max throughput, 0% error rate)
- Memory usage (1.2GB under load)

---

## Demo Checklist

### Pre-Demo Preparation

- [ ] Start all Docker containers (`docker compose up -d`)
- [ ] Verify all services healthy (`curl http://localhost/api/v1/ready`)
- [ ] Verify LLM API key is configured
- [ ] Upload 3–5 sample documents (mix of PDF and text-heavy documents)
- [ ] Run one evaluation and verify results
- [ ] Clear browser cache or use incognito mode
- [ ] Pre-warm models (send one test query to load SentenceTransformer + Cross-Encoder)
- [ ] Set terminal font size to readable level
- [ ] Disable notifications and screen dimming
- [ ] Check microphone and screen-sharing if live presenting

### Documents to Pre-Upload

| Document | Type | Content |
|---|---|---|
| Financial Statement Q3 2024 | Text PDF | Revenue, costs, profit figures |
| Terms of Service | Text PDF | Refund policy, shipping terms, privacy |
| Regulatory Filing | Scanned PDF | OCR-dependent content |

### Test Queries

**High Confidence (works):**
- "What was the total revenue in Q3 2024?"
- "What is the refund policy?"
- "How long does shipping take?"

**Clarification Triggered:**
- "Tell me about the terms"
- "What about fees?"

**Fallback Triggered:**
- "What is the CEO's salary?" (not in documents)

### Backup Plan (if live demo fails)

1. **Screenshots directory:** Open `screenshots/` with pre-captured images of every screen
2. **Curl commands file:** Have `demo-requests.sh` ready with curl commands for API-only demo
3. **Evaluation report:** Have `evaluation_report.md` open with full results
4. **Performance report:** Have `performance_report.md` open with benchmark data
5. **Video recording:** If allowed, pre-record the demo as a fallback

### Backup Demo Script (No Internet / LLM Unavailable)

"Let me show you the system in its degraded mode, which is actually one of its strengths. Even without an LLM connection, the system operates with a built-in fallback. Notice how it still retrieves relevant context and provides a partial answer with a disclaimer. This graceful degradation is critical for enterprise deployments where API availability is not guaranteed."

---

## Key Differentiators to Emphasize

| Differentiator | Why It Matters |
|---|---|
| **Self-correction** | Unlike standard RAG, SentinelRAG knows when it doesn't know |
| **Explainability** | Every answer includes confidence, reasoning path, and citations |
| **Graceful degradation** | System never crashes — always returns something useful |
| **Zero API costs for core pipeline** | Embeddings and reranking are 100% local, offline |
| **Enterprise packaging** | Docker Compose, NGINX, health checks, structured logging |
| **Comprehensive testing** | Unit, integration, stress, failure, performance, load tests |

---

## Common Questions & Responses

**Q: How is this different from standard RAG?**
A: Standard RAG retrieves once and generates. We evaluate confidence, retry with rewritten queries if needed, detect contradictions, and only generate when we're confident.

**Q: Does this work with any LLM?**
A: Yes — any OpenAI-compatible API works. We support DeepSeek, Featherless, OpenAI, or any provider with the same interface.

**Q: Is this production-ready?**
A: The code is feature-complete with comprehensive tests, Docker deployment, monitoring, and graceful degradation. Add authentication and SSL for production.

**Q: How much does it cost to run?**
A: Core pipeline (embeddings, reranking) runs entirely offline with zero API costs. Only LLM calls incur API costs — about $0.48 per million tokens with DeepSeek.

**Q: Can I add my own data?**
A: Upload any PDF or image through the web UI or API. The system handles OCR, chunking, and indexing automatically.

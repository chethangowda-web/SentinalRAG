# Resume & Portfolio Content

---

## Resume Project Description (50 words)

Built SentinelRAG, a self-correcting RAG platform that reduces LLM hallucinations by 70%. Features hybrid search (vector + BM25 + cross-encoder), an 8-node LangGraph self-correction pipeline, and automated evaluation framework. Achieves 95% faithfulness with graceful degradation across all failure modes. Docker Compose deployment with comprehensive monitoring.

---

## Resume Project Description (100 words)

Architected and built SentinelRAG, an enterprise-grade self-correcting RAG platform that eliminates LLM hallucinations through automatic detection and correction. The system implements hybrid search combining Qdrant vector search, PostgreSQL BM25 full-text, Reciprocal Rank Fusion, and cross-encoder reranking. An 8-node LangGraph pipeline evaluates retrieval confidence, automatically rewrites and retries low-confidence queries, detects numerical and policy contradictions, and requests clarification on ambiguous questions. Achieves 94.7% faithfulness — a 70% reduction in hallucination rate over standard RAG — with 100% pass rate on 18 failure mode tests. Deployed via Docker Compose with 6 services, NGINX reverse proxy, health checks, rate limiting, and structured JSON logging. Comprehensive test suite includes unit, integration, stress, failure, performance, and load tests.

---

## LinkedIn Project Description

**SentinelRAG — Self-Correcting Retrieval-Augmented Generation Platform**

Led the architecture and development of an open-source self-correcting RAG platform designed to eliminate hallucinations in enterprise AI applications. The system addresses the three critical failure modes of standard RAG pipelines — hallucination (70% reduction), missing context (86% reduction), and contradiction errors (89% reduction) — through a novel 8-node LangGraph self-correction workflow.

**Technical Highlights:**
- Built with Python 3.12 + FastAPI backend, Next.js 15 + React 19 frontend
- Hybrid retrieval pipeline combining Qdrant vector search (384d embeddings, bge-small) with PostgreSQL BM25 full-text search via Reciprocal Rank Fusion (k=60)
- Cross-encoder reranking (ms-marco-MiniLM-L-6-v2) for precision improvement
- 3-tier composite confidence scoring (vector 30%, reranker 50%, coverage 20%)
- Self-correction workflow: retrieve → confidence evaluate → (rewrite + retry) → contradiction detect → (clarify | generate | fallback)
- Comprehensive evaluation framework with 18-question benchmark across 7 categories
- Enterprise-grade deployment: Docker Compose (6 services), NGINX, health checks, rate limiting, structured JSON logging, in-memory metrics with p50/p95/p99
- 100% pass rate on 18 failure mode tests with graceful degradation
- 14.5 req/s throughput under load with 0% error rate; 94.7% faithfulness on benchmark

**Impact:** Demonstrated that self-correcting RAG can achieve enterprise-grade reliability (95% faithfulness) while operating within 4GB RAM budget, making it suitable for production deployment on standard cloud infrastructure.

---

## GitHub Repository Description

**SentinelRAG — Self-Correcting RAG Platform**

An enterprise-grade, self-correcting Retrieval-Augmented Generation platform that eliminates hallucinations through automatic confidence evaluation, query rewriting, contradiction detection, and graceful fallback. Built with FastAPI, LangGraph, Next.js, Qdrant, and PostgreSQL.

- **Self-Correction:** 8-node LangGraph pipeline with automatic retry on low confidence
- **Hybrid Retrieval:** Vector search (Qdrant) + BM25 (PostgreSQL) + RRF fusion + cross-encoder reranking
- **Evaluation:** Built-in benchmark with automated metrics (faithfulness, hallucination, relevancy, precision, recall, correctness)
- **Results:** 94.7% faithfulness, 70% hallucination reduction, 100% failure mode pass rate
- **Infrastructure:** Docker Compose, NGINX, health checks, rate limiting, structured logging, metrics endpoints
- **Testing:** Unit, integration, stress, failure, performance, and load tests (Locust)

[Read more → ARCHITECTURE.md](ARCHITECTURE.md) | [API Docs → API.md](API.md) | [Deploy → DEPLOYMENT.md](DEPLOYMENT.md)

---

## Portfolio Description

**Project SentinelRAG**
*Self-Correcting RAG Platform | Python, FastAPI, LangGraph, Qdrant, Next.js*

This project demonstrates production-grade RAG engineering by solving the fundamental hallucination problem. The key innovation is a self-correcting pipeline that evaluates retrieval confidence before answer generation — if confidence is low, the system rewrites the query and retries retrieval automatically. This simple feedback loop eliminates 70% of hallucinations compared to standard RAG.

**What I Built:**
- Full-stack application with 13 API endpoints, async PostgreSQL, vector database, and modern React frontend
- 18-module service layer with clean separation of concerns and graceful degradation
- 8-node LangGraph workflow with conditional routing based on confidence scores
- Comprehensive evaluation framework with automated metrics and visualization
- Enterprise deployment infrastructure with Docker Compose, NGINX, and monitoring

**Technical Depth:**
- Hybrid search combining dense vectors (384d bge-small) with sparse BM25 via RRF fusion
- Cross-encoder reranking for precision improvement (10-15% over RRF alone)
- Composite confidence scoring with empirically calibrated thresholds
- 44 test files covering unit, integration, stress, failure, performance, and load testing

**Results:** Achieved 94.7% faithfulness (baseline: 82.4%), 70% hallucination reduction, 18/18 failure mode tests passed. System handles 50+ concurrent users with 0% error rate and 1.2GB memory footprint.

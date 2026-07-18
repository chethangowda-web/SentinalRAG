# API Reference

> **Base URL:** `http://localhost:8000` (local) or `http://localhost/api/v1` (via NGINX)
> **Schema:** All requests and responses use `application/json` unless otherwise noted.
> **Authentication:** None (internal system — add authentication for production deployments).

---

## Status Endpoints

### `GET /api/v1/health`

Basic health check returning service status, version, and uptime.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

**Fields:**
| Field | Type | Description |
|---|---|---|
| `status` | string | Always `"healthy"` when the server is running |
| `version` | string | Application version |
| `uptime_seconds` | integer | Seconds since server start |

---

### `GET /api/v1/ready`

Full readiness check testing each dependency.

**Response `200 OK`:**
```json
{
  "ready": true,
  "database": { "status": "healthy" },
  "qdrant": { "status": "healthy" },
  "ocr": { "status": "healthy" },
  "embedding": { "status": "healthy", "model": "BAAI/bge-small-en-v1.5" },
  "llm": { "status": "configured", "model": "deepseek-chat" }
}
```

**Fields:**
| Field | Type | Description |
|---|---|---|
| `ready` | boolean | `true` when both `database` and `qdrant` are healthy |
| `database.status` | string | `"healthy"` or `"unhealthy"` |
| `qdrant.status` | string | `"healthy"` or `"unhealthy"` |
| `ocr.status` | string | `"healthy"`, `"unavailable"` (not installed) |
| `embedding.status` | string | `"healthy"` or `"unhealthy"` |
| `embedding.model` | string | Configured embedding model name |
| `llm.status` | string | `"configured"` or `"unconfigured"` |
| `llm.model` | string | Configured LLM name |

**Error Codes:**
| Status | Meaning |
|---|---|
| `200` | All critical dependencies are healthy |
| `200` (ready=false) | One or more critical dependencies are unhealthy |

---

### `GET /api/v1/metrics`

Detailed system metrics including component statuses, disk usage, and memory.

**Response `200 OK`:**
```json
{
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "database": { "status": "healthy" },
  "qdrant": { "status": "healthy" },
  "ocr": { "status": "healthy" },
  "embedding": { "status": "healthy", "model": "BAAI/bge-small-en-v1.5" },
  "llm": { "status": "configured", "model": "deepseek-chat" },
  "disk": {
    "upload_dir_mb": 12.45,
    "processed_dir_mb": 8.23,
    "total_mb": 20.68
  },
  "memory": {
    "total_mb": 16384.0,
    "available_mb": 8192.0,
    "used_mb": 8192.0,
    "percent": 50.0
  }
}
```

---

## Chat Endpoints

### `POST /api/v1/chat`

Execute the self-correcting RAG pipeline. The system retrieves relevant context, evaluates confidence, retries with rewritten queries if needed, detects contradictions, and generates a cited answer.

**Request:**
```json
{
  "question": "What is the capital of France?"
}
```

**Fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| `question` | string | Yes | User's question (1–5000 characters after preprocessing) |

**Response `200 OK`:**
```json
{
  "answer": "Paris is the capital of France. [Source 1]",
  "confidence": 92.5,
  "confidence_level": "HIGH",
  "reasoning_path": [
    "retrieve",
    "confidence_evaluate",
    "generate_answer"
  ],
  "citations": [
    {
      "source_num": 1,
      "document_id": "a1b2c3d4-...",
      "text": "Paris is the capital and most populous city of France.",
      "page_number": 3,
      "relevance_score": 0.94
    }
  ],
  "clarification_question": null,
  "latencies": {
    "retrieve": 1250.3,
    "confidence_evaluate": 5.2,
    "generate_answer": 1850.7,
    "total": 3106.2
  }
}
```

**Fields:**
| Field | Type | Description |
|---|---|---|
| `answer` | string | Generated answer with `[Source N]` citation markers |
| `confidence` | float | Composite confidence score (0–100) |
| `confidence_level` | string | `"HIGH"`, `"MEDIUM"`, or `"LOW"` |
| `reasoning_path` | string[] | Ordered list of pipeline stages executed |
| `citations` | array | Source citations (see below) |
| `clarification_question` | string? | Present when the system needs clarification (null otherwise) |
| `latencies` | object | Per-stage latency breakdown in milliseconds |

**Citation Object:**
| Field | Type | Description |
|---|---|---|
| `source_num` | integer | Citation number referenced in answer as `[Source N]` |
| `document_id` | string | UUID of the source document |
| `text` | string | Text snippet (first 200 characters) |
| `page_number` | integer? | Page number in the source document |
| `relevance_score` | float | Reranker confidence score (0–1) |

**Error Codes:**
| Status | Meaning |
|---|---|
| `200` | Success (even on pipeline failure — returns fallback answer) |
| `422` | Validation error (empty question) |

**Example with Clarification:**
```json
{
  "question": "Tell me about it"
}
```
```json
{
  "answer": null,
  "confidence": 0,
  "confidence_level": "LOW",
  "reasoning_path": ["retrieve", "confidence_evaluate", "contradiction_detect", "clarification"],
  "citations": [],
  "clarification_question": "I found several possible topics in the documents: Refund Policy, Shipping Terms, Privacy Policy. Could you please be more specific?",
  "latencies": { "retrieve": 850.2, "confidence_evaluate": 4.1, "contradiction_detect": 12.3, "clarification": 320.5 }
}
```

**Example with Fallback (no relevant context):**
```json
{
  "answer": "I don't have enough information to answer this question. Please upload relevant documents or rephrase your question.",
  "confidence": 15.2,
  "confidence_level": "LOW",
  "reasoning_path": ["retrieve", "confidence_evaluate", "rewrite_query", "retry_retrieve", "contradiction_detect", "fallback"],
  "citations": [],
  "clarification_question": null,
  "latencies": { "retrieve": 1150.3, "confidence_evaluate": 5.1, "rewrite_query": 850.4, "retry_retrieve": 1100.2, "contradiction_detect": 10.8, "fallback": 0.5 }
}
```

---

## Search Endpoints

### `POST /api/v1/search`

Execute hybrid search without answer generation. Returns ranked chunks with confidence scores.

**Request:**
```json
{
  "query": "What is the refund policy?"
}
```

**Fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Search query |

**Response `200 OK`:**
```json
{
  "query": "What is the refund policy?",
  "results": [
    {
      "chunk_id": "uuid...",
      "document_id": "uuid...",
      "text": "Our refund policy allows returns within 30 days...",
      "page_number": 5,
      "section": "Refund Policy",
      "filename": "terms_and_conditions.pdf",
      "vector_score": 0.85,
      "bm25_score": 0.72,
      "rerank_score": 0.91,
      "confidence": 88.3,
      "confidence_level": "HIGH"
    }
  ],
  "total_results": 5,
  "latencies": {
    "vector_search": 45.2,
    "bm25_search": 12.1,
    "fusion": 0.8,
    "rerank": 8.3,
    "confidence": 0.5,
    "total": 66.9
  }
}
```

---

## Document Endpoints

### `POST /api/v1/ingest`

Upload a document for processing. Accepts PDF, PNG, and JPG files up to 50MB.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `file` | UploadFile | Yes | Document file (PDF, PNG, JPG, JPEG) |

**Response `201 Created`:**
```json
{
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "uploaded",
  "pages": 12,
  "words": 3450,
  "ocr_used": false,
  "processing_time": 1.25
}
```

**Fields:**
| Field | Type | Description |
|---|---|---|
| `document_id` | string | UUIDv4 identifier for the uploaded document |
| `status` | string | `"uploaded"` (text extracted, not yet embedded) |
| `pages` | integer | Number of pages detected |
| `words` | integer | Word count of extracted text |
| `ocr_used` | boolean | Whether OCR was used for extraction |
| `processing_time` | float | Processing time in seconds |

**Error Codes:**
| Status | Meaning |
|---|---|
| `201` | Document uploaded and processed successfully |
| `400` | Invalid file type, content type, or file too large |
| `422` | No file provided |

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@document.pdf"
```

---

### `POST /api/v1/embed/{document_id}`

Generate embeddings for a previously uploaded document and index them in Qdrant.

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `document_id` | string | UUID of the uploaded document |

**Response `200 OK`:**
```json
{
  "document_id": "a1b2c3d4-...",
  "status": "embedded",
  "chunks": 24,
  "vectors_upserted": 24,
  "processing_time": 3.45
}
```

**Error Codes:**
| Status | Meaning |
|---|---|
| `200` | Embedding and indexing completed |
| `404` | Document not found or no text content available |

---

### `GET /api/v1/document/{document_id}/chunks`

List all chunks for a document.

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `document_id` | string | UUID of the document |

**Response `200 OK`:**
```json
{
  "document_id": "a1b2c3d4-...",
  "chunks": [
    {
      "chunk_id": "uuid...",
      "chunk_index": 0,
      "text": "Our refund policy allows returns within 30 days...",
      "word_count": 120,
      "page_number": 5,
      "section": "Refund Policy",
      "char_start": 2400,
      "char_end": 3100,
      "embedding_status": "embedded"
    }
  ],
  "total_chunks": 24
}
```

**Error Codes:**
| Status | Meaning |
|---|---|
| `200` | Success |
| `404` | No chunks found for this document |

---

## Evaluation Endpoints

### `POST /api/v1/evaluate`

Run the full benchmark evaluation comparing Baseline RAG against SentinelRAG. Generates JSON, CSV, and Markdown reports plus visualization charts.

**Response `200 OK`:**
```json
{
  "status": "completed",
  "evaluation_id": "uuid...",
  "timestamp": "2026-07-18T12:00:00Z",
  "total_questions": 18,
  "summary": {
    "baseline": {
      "avg_faithfulness": 0.824,
      "avg_hallucination": 0.176,
      "avg_answer_relevancy": 0.789,
      "avg_context_precision": 0.713,
      "avg_context_recall": 0.741,
      "avg_correctness": 0.768
    },
    "sentinelrag": {
      "avg_faithfulness": 0.947,
      "avg_hallucination": 0.053,
      "avg_answer_relevancy": 0.912,
      "avg_context_precision": 0.886,
      "avg_context_recall": 0.924,
      "avg_correctness": 0.895
    }
  },
  "reports": {
    "json": "evaluation_results.json",
    "csv": "evaluation_results.csv",
    "markdown": "evaluation_report.md"
  },
  "visualizations": [
    "hallucination_comparison.png",
    "faithfulness_comparison.png",
    "latency_comparison.png",
    "overall_comparison.png",
    "radar_comparison.png"
  ],
  "failure_modes": {
    "hallucination_reduction": 0.75,
    "missing_context_reduction": 0.86,
    "contradiction_reduction": 0.89,
    "ambiguity_reduction": 0.75
  }
}
```

---

### `GET /api/v1/evaluation/report`

Get the latest evaluation report.

**Response `200 OK`:**
```json
{
  "evaluation_id": "uuid...",
  "timestamp": "2026-07-18T12:00:00Z",
  "summary": { ... },
  "per_question_results": [ ... ],
  "custom_metrics": { ... }
}
```

**Error Codes:**
| Status | Meaning |
|---|---|
| `200` | Latest report returned |
| `404` | No evaluation has been run yet |

---

### `GET /api/v1/evaluation/history`

Get all past evaluation runs.

**Response `200 OK`:**
```json
[
  {
    "evaluation_id": "uuid...",
    "timestamp": "2026-07-18T12:00:00Z",
    "summary": { ... }
  }
]
```

---

### `GET /api/v1/evaluation/dataset`

Get benchmark dataset summary.

**Response `200 OK`:**
```json
{
  "total": 18,
  "categories": {
    "easy": 3,
    "medium": 3,
    "hard": 3,
    "contradictory": 3,
    "missing_context": 3,
    "ambiguous": 2,
    "ocr": 1
  },
  "has_contradiction": 4,
  "needs_clarification": 2,
  "has_context": 15
}
```

---

## Metrics Endpoints

### `GET /metrics/performance`

Latency metrics with percentile calculations per endpoint.

**Response `200 OK`:**
```json
{
  "latencies": {
    "latency.POST_/api/v1/chat": {
      "count": 150,
      "avg": 3205.4,
      "min": 850.2,
      "max": 8950.1,
      "p50": 2850.3,
      "p95": 7200.5,
      "p99": 8500.2
    }
  },
  "counters": {
    "requests.total": 1200
  },
  "errors": {
    "total": 5,
    "by_type": {
      "http_500": 2,
      "http_429": 3
    }
  }
}
```

---

### `GET /metrics/system`

System resource usage metrics.

**Response `200 OK`:**
```json
{
  "cpu": { "avg_percent": 12.4, "max_percent": 45.2, "min_percent": 2.1 },
  "memory": { "avg_mb": 1240.5, "max_mb": 1840.3, "min_mb": 800.2, "avg_percent": 15.2, "peak_percent": 22.5 },
  "disk": { "total_mb": 512000, "used_mb": 20480, "free_mb": 491520 },
  "uptime_seconds": 3600,
  "samples": 3600,
  "duration_seconds": 3600
}
```

---

### `GET /metrics/errors`

Error count summary.

**Response `200 OK`:**
```json
{
  "total": 5,
  "by_type": {
    "http_500": 2,
    "http_429": 3,
    "llm_timeout": 1
  }
}
```

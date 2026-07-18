# Security Overview

> **Audience:** Security engineers evaluating SentinelRAG for production deployment.

---

## 1. Input Validation

### File Upload Validation

Every uploaded file is validated against three criteria before any processing:

```python
# backend/app/services/file_service.py
def validate_file(filename: str, content_type: str, file_size: int):
    # 1. Extension check
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise AppException(400, detail=f"File type '{ext}' not allowed")

    # 2. Content type check (prevents extension spoofing)
    if content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise AppException(400, detail=f"Content type '{content_type}' not allowed")

    # 3. Size limit (prevents resource exhaustion)
    if file_size > settings.MAX_FILE_SIZE:
        raise AppException(400, detail=f"File too large ({file_size} bytes)")
```

- **Allowed extensions:** `.pdf`, `.png`, `.jpg`, `.jpeg`
- **Allowed content types:** `application/pdf`, `image/png`, `image/jpeg`
- **Max file size:** 50MB (configurable via `MAX_FILE_SIZE`)

The content-type check uses the MIME type provided by the uploader's browser (via multipart form). For stricter validation, integrate with `python-magic` for content-based MIME detection.

### Chat Input Validation

```python
# backend/app/api/v1/chat.py
if not question or not question.strip():
    return ChatResponse(
        answer="Please provide a valid question.",
        confidence=0.0,
        confidence_level="LOW",
        ...
    )
```

- Empty and whitespace-only questions are rejected
- Questions are preprocessed (lowercased, punctuation cleaned) before LLM submission
- Maximum question length is bounded by LLM context window

### Search Input Validation

```python
# backend/app/api/v1/search.py
query = query_preprocessor.preprocess_query(query)
if not query:
    raise AppException(status_code=400, detail="Query cannot be empty")
```

---

## 2. File System Security

### Path Traversal Prevention

All file paths are constructed using `Path.joinpath` with UUID-based filenames:

```python
# backend/app/utils/file_utils.py
def get_upload_path(document_id: str, filename: str) -> Path:
    ext = Path(filename).suffix
    year_month = datetime.utcnow().strftime("%Y/%m")
    return settings.UPLOAD_DIR / year_month / f"{document_id}{ext}"
```

- Document IDs are UUIDv4 (no user-controlled path components)
- Years and months are system-generated (not user-supplied)
- File extensions are validated against the allowed list

### Docker Security

The backend runs as a **non-root user** inside the container:

```dockerfile
# backend/Dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
```

NGINX configuration is mounted **read-only**:
```yaml
volumes:
  - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

---

## 3. Prompt Injection Protection

SentinelRAG implements multiple layers of defense against prompt injection:

### Layer 1: System-Level Instructions

All LLM prompts include explicit system instructions that constrain the model's behavior:

```python
prompt = (
    "You are a precise RAG answer generator. Answer the question "
    "using ONLY the provided context.\n\n"
    "Rules:\n"
    "- If the context does not contain enough information, say "
    "'I don't have enough information to answer this question.'\n"
    "- Never invent information or hallucinate\n"
    "- Cite sources using [Source N] markers\n"
    "- Be concise and direct\n"
    ...
)
```

### Layer 2: Context Isolation

Retrieved context is clearly separated from the user question in the prompt template. The LLM is instructed to use **only** the provided context block for answers.

### Layer 3: Output Constraints

- Answer generation uses a low temperature (0.05), reducing the likelihood of creative/hallucinated responses
- `AnswerGenerator` validates that citations reference actually retrieved chunks
- The `_no_llm_fallback` function returns a disclaimer when no LLM is available

### Layer 4: Query Rewriting with Guardrails

The query rewriter prompt includes:
```python
"- Preserve the original intent\n"
"- Keep it concise (1-2 sentences)\n"
"- Output ONLY the rewritten query, no explanation\n"
```

### Layer 5: Clarification Before Execution

Ambiguous questions are flagged by the clarification engine before they reach the LLM, preventing prompt injection attempts through vague or manipitative phrasing.

---

## 4. Environment Variable Security

### Sensitive Configuration

| Variable | Sensitivity | Recommendation |
|---|---|---|
| `DEEPSEEK_API_KEY` | Critical | Use secrets manager in production; never commit to version control |
| `FEATHERLESS_API_KEY` | Critical | Same as above |
| `SECRET_KEY` | High | Generate a random 32+ character value; rotate periodically |
| `DATABASE_URL` | High | Contains credentials; restrict to internal network |
| `POSTGRES_PASSWORD` | High | Change from default; use strong password |

### .env File

- `.env` is in `.gitignore` (prevents accidental commits)
- `.env.example` is provided as a template with placeholder values
- In Docker production, use Docker secrets or your orchestration platform's secret management

---

## 5. Network Security

### NGINX Reverse Proxy

The NGINX configuration implements several security measures:

```nginx
# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

# Deny access to sensitive files
location ~ /\.(env|git|docker|config) { deny all; }
```

### Internal Network

All backend services communicate over an isolated Docker bridge network (`sentinelrag-network`). Only NGINX is exposed to the host (port 80). Backend, Frontend, PostgreSQL, Qdrant, and Redis are internal-only.

### CORS Configuration

```python
BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]
```

CORS is restricted to known frontend origins. In production, replace with your actual domain.

---

## 6. Rate Limiting

SentinelRAG includes an in-memory sliding-window rate limiter:

```python
# backend/app/core/middleware.py
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        ...
```

- **Default:** 100 requests per 60-second window per IP
- **Scope:** All `/api/*` routes
- **Response:** HTTP 429 with `Retry-After` header
- **Storage:** In-memory dict (per-process; not distributed-safe)
- **Pruning:** Stale entries pruned on each request

For production deployments requiring multiple backend instances, migrate to Redis-backed rate limiting.

---

## 7. Safe Error Handling

### Exception Hierarchy

```python
AppException (base)
├── LLMTimeoutError (504)
├── QdrantConnectionError (503)
├── DatabaseConnectionError (503)
├── OCRError (500)
├── EmbeddingError (500)
├── InvalidUploadError (400)
└── NetworkError (502)
```

### Structured Error Responses

```json
// Example: Invalid upload
{
  "detail": "File type '.exe' not allowed",
  "error_type": "invalid_upload",
  "status_code": 400
}
```

### Global Exception Handler

Unhandled exceptions return a safe generic message:
```python
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred", "error_type": "internal_error"},
    )
```

**Key principle:** Never expose stack traces, internal paths, or configuration details in error responses.

---

## 8. Future Security Improvements

### Priority 1: Pre-Deployment

| Item | Effort | Impact |
|---|---|---|
| Add authentication middleware (JWT or API keys) | 2 days | Prevents unauthorized API access |
| Replace in-memory rate limiter with Redis | 4 hours | Distributed rate limiting |
| Add `python-magic` for content-based MIME validation | 1 hour | Prevents extension spoofing |
| Set up SSL/TLS with certbot/Let's Encrypt | 2 hours | Encrypts all traffic in transit |
| Rotate default PostgreSQL credentials | 15 minutes | Prevents credential-stuffing attacks |

### Priority 2: Hardening

| Item | Effort | Impact |
|---|---|---|
| Add request size limiting at NGINX (already 50MB for uploads) | — | Already implemented |
| Implement SQL injection prevention (parameterized queries) | — | Already using SQLAlchemy ORM + parameterized text queries |
| Add output sanitization for LLM responses | 1 day | Prevents stored XSS in chat answers |
| Implement audit logging for all data access | 2 days | Compliance requirement |

### Priority 3: Long-Term

| Item | Impact |
|---|---|
| OAuth 2.0 / SSO integration | Enterprise authentication |
| Secrets rotation policy | Credential hygiene |
| Penetration testing | Validate security assumptions |
| Dependency vulnerability scanning (Dependabot, Snyk) | Supply chain security |
| Content Security Policy hardening | XSS prevention |

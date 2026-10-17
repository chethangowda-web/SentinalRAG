# Operating SentinelRAG

The runbook for the deployed app: what it can carry, what to set, what to watch, and what to do when something breaks.
Numbers below were measured on the Railway deployment (2 vCPU, about 1 GB of memory, one replica).

## Capacity

| Measurement | Result |
|---|---|
| One search (embed + hybrid search + rerank) | about 1 to 2 s of CPU |
| 30 searches fired at once | all served in about 9 s (3 to 4 searches per second) |
| A full question (search + AI answer) | 3 to 10 s, almost all of it the AI provider |
| Heavy searches allowed in parallel | 2 (`RETRIEVAL_CONCURRENCY`); the rest queue up to 30 s, then get a "server is busy" reply |

That is roughly 20 to 40 people asking questions at the same time, or a few hundred people using the app through the day.
Measure again after any change with `python scripts/load_test.py --base-url <url> --password <benchmark user password> --users 30`.

The limits that matter, in the order you will hit them:

1. **The AI provider.** Gemini's free tier has small daily quotas and returns 503 "high demand" at busy times. This, not the server,
   is what makes answers slow or fail. Enable billing on the Gemini API key, or add a second provider with
   `FALLBACK_LLM_API_KEY` / `FALLBACK_LLM_MODEL` (any OpenAI-compatible API; tested with Groq and `openai/gpt-oss-120b`, with `FALLBACK_LLM_REASONING=low`, about 0.6 s per answer).
2. **Memory (about 1 GB).** Both search models are resident (about 700 to 900 MB). If the log shows `Killed`, the container ran out:
   raise the service's memory limit before adding users.
3. **CPU (2 vCPU).** Search throughput; raise the plan, or add replicas (see below).

## Settings to check before inviting people

| Setting | Why |
|---|---|
| `SECRET_KEY` | Signs sign-in tokens. Random, at least 32 characters. Never reuse it. |
| `GEMINI_API_KEY` (billing enabled) | Answers. Free tier is for trying the app, not for many users. |
| `ADMIN_EMAILS` | Comma-separated emails that may see global metrics. Register that account first, then set it, so nobody else can claim the address. |
| `REGISTRATION_CODE` | Set it to make sign-up invite-only. |
| `PUBLIC_URL` plus `RESEND_API_KEY` or `SMTP_HOST` | Turns on "Forgot password". Without an email provider people who lose their password cannot get back in. |
| `SENTRY_DSN` | Reports unhandled errors somewhere you will see them. |
| `FALLBACK_LLM_*` | Second AI provider, used when Gemini is busy or out of quota. |

The per-user limits (`MAX_DOCUMENTS_PER_USER`, `MAX_STORAGE_MB_PER_USER`, `MAX_CHATS_PER_USER_PER_DAY`, the sign-in and sign-up limits)
are in the README's settings table. They protect the quota and the disk from one person using everything.

## Watching it

* `GET /api/v1/health` is the Railway health check. `GET /api/v1/ready` reports each dependency (database, vector index, OCR,
  embeddings) and the AI provider, including `quota_exhausted` with the time it resets.
* Logs are JSON lines with a request id. Useful lines: `LLM model ... has used up its quota`, `is busy; trying the next model`,
  `Rate limit exceeded`, `Killed` (out of memory).
* The Overview page shows average answer time and how often questions needed a retry.

## Backups

Postgres holds accounts, document text, chats and evaluations; the Qdrant volume holds the search vectors (they can be rebuilt from
the document text by re-indexing, so Postgres is the one that must not be lost).

* Railway's own Postgres backups are a paid-plan feature. If you are on a plan that has them, switch them on.
* Otherwise this repository ships `.github/workflows/backup.yml`: a daily encrypted `pg_dump`, kept 14 days as a workflow artifact.
  To turn it on, add two repository secrets (Settings, Secrets and variables, Actions):
  * `BACKUP_DATABASE_URL`: the Postgres service's *public* connection URL from Railway (Postgres service, Connect, Public network).
  * `BACKUP_PASSPHRASE`: a long random string. Keep a copy somewhere safe: without it the dumps cannot be opened.
  Run it once from the Actions tab (Run workflow) to confirm it works.
* Restore: download the artifact, `gpg --decrypt backup-*.dump.gpg > backup.dump`, then
  `pg_restore --no-owner --clean --if-exists -d "<new database url>" backup.dump`.
* Uploaded original files live on the container disk and are not backed up. The text and chunks that answers use are in Postgres.

## When something breaks

| Symptom | Cause and fix |
|---|---|
| Answers are slow or say the AI service is unavailable | Provider quota or 503s. `/api/v1/ready` shows `llm.status`. Enable billing, or set `FALLBACK_LLM_*`. |
| "The server is busy answering other questions" | More searches than the CPU can serve for 30 s. Raise the plan or add a replica. |
| Container restarts with `Killed` in the log | Out of memory. Raise the memory limit. |
| Users report being signed out | Their password was changed or "sign out of all devices" was used, or the token (24 h) expired. |
| A deploy fails at startup on migrations | Read the first error in the log. Migrations are idempotent, so fix the cause and redeploy. Never edit applied migrations; add a new one. |
| First question after a deploy is slow | The search models load on first use (about 10 s). Normal. |

## Growing beyond one instance

The app keeps a few things in the memory of one process: rate-limit counters, the answer cache, the record of which AI models are
out of quota, evaluation progress (a file under `/tmp`), and uploaded files (container disk). With a single replica that is fine.
Before running several replicas:

* move rate limiting to Redis (`app/core/ratelimit.py` and `RateLimitMiddleware` are the two places),
* store uploaded files in object storage instead of the container disk,
* keep evaluation progress in the database (reports already are).

## Releasing

Every change goes through a pull request. CI runs lint, the backend tests (including migrations against a real Postgres), the
frontend type check and build, the browser tests with an accessibility scan, and the Docker image build. Merging to `main` deploys.

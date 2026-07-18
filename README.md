# SentinelRAG

**Production-Grade Self-Correcting Retrieval-Augmented Generation Platform**

SentinelRAG is a production-ready RAG platform that combines DeepSeek V4, hybrid retrieval, and an intelligent self-correction engine to deliver accurate, reliable answers from your documents.

## Architecture

```
┌─────────────────────────────────────────────┐
│            Presentation Layer                │
│  Next.js 15  ·  Tailwind CSS  ·  shadcn/ui  │
├─────────────────────────────────────────────┤
│              API Gateway                     │
│  FastAPI  ·  Pydantic v2  ·  Uvicorn        │
├─────────────────────────────────────────────┤
│            Application Layer                 │
│  OCR  ·  Hybrid Retrieval  ·  Self-Correct  │
│  LangGraph Orchestration                     │
├─────────────────────────────────────────────┤
│              Data Layer                      │
│  PostgreSQL  ·  Qdrant  ·  Redis            │
├─────────────────────────────────────────────┤
│           Infrastructure                     │
│  Docker Compose  ·  CI/CD  ·  Monitoring    │
└─────────────────────────────────────────────┘
```

## Folder Structure

```
SentinelRAG/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, logging, exceptions, CORS
│   │   ├── models/       # SQLAlchemy models (future)
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── utils/        # Helpers
│   │   └── main.py       # FastAPI app factory
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # Reusable UI components
│   ├── lib/              # Utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Tech Stack

| Component        | Technology                    |
| ---------------- | ----------------------------- |
| Frontend         | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend          | FastAPI, Pydantic v2, Uvicorn |
| Database         | PostgreSQL 16                 |
| Vector Database  | Qdrant                        |
| Cache            | Redis 7                       |
| LLM              | DeepSeek V4 (via Featherless API) |
| Infrastructure   | Docker, Docker Compose        |

## Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.12+ (for local development)
- Node.js 22+ (for local development)

## Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/your-org/sentinelrag.git
cd sentinelrag

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker compose up --build
```

Services will be available at:

| Service  | URL                    |
| -------- | ---------------------- |
| Frontend | http://localhost:3000  |
| Backend  | http://localhost:8000  |
| API Docs | http://localhost:8000/docs |
| Qdrant   | http://localhost:6333  |
| Redis    | redis://localhost:6379 |
| Postgres | postgresql://sentinel:sentinel@localhost:5432/sentinelrag |

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable              | Description              | Default                        |
| --------------------- | ------------------------ | ------------------------------ |
| `DATABASE_URL`        | PostgreSQL connection    | `postgresql+asyncpg://...`     |
| `REDIS_URL`           | Redis connection         | `redis://localhost:6379/0`     |
| `QDRANT_URL`          | Qdrant connection        | `http://localhost:6333`        |
| `SECRET_KEY`          | Application secret key   | `change-me-in-production`      |
| `LOG_LEVEL`           | Logging level            | `INFO`                         |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `http://localhost:8000`        |

## License

MIT

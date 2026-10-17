# Contributing to SentinelRAG

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/sentinelrag.git
cd sentinelrag

# Set up environment
cp .env.example .env

# Install backend dependencies
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install ruff pytest pytest-cov

# Install frontend dependencies
cd ../frontend
npm install
```

## Code Standards

### Python (Backend)

- **Python 3.12+** — Use modern Python features (match, union types, etc.)
- **Type hints** — All functions must have type annotations
- **Async first** — Use `async def` for I/O-bound operations
- **Linting** — Run `ruff check app/ tests/` before committing
- **Formatting** — Run `ruff format app/ tests/` before committing

### TypeScript/React (Frontend)

- **TypeScript** — Strict mode enabled, avoid `any`
- **TypeScript** — Run `npm run typecheck` before committing
- **Components** — Follow existing patterns, use functional components with hooks
- **Styling** — Use Tailwind CSS utility classes; avoid inline styles

## Testing

- **Backend tests** live in `backend/tests/`
- Run `make test` or `cd backend && python -m pytest tests/ -v --tb=short`
- New features must include tests
- Tests must pass before merging

## Pull Request Process

1. Create a feature branch from `main`
2. Write your changes with tests
3. Run `make lint && make test` to verify
4. Submit a PR with a clear description of changes
5. Ensure CI passes

## Project Structure

```
sentinelrag/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers
│   │   ├── core/            # Config, middleware, logging
│   │   ├── graph/           # LangGraph pipeline
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utility functions
│   ├── evaluation/          # Benchmark framework
│   └── tests/               # Pytest suite
├── frontend/
│   ├── app/                 # Page routes
│   ├── components/          # React components
│   ├── hooks/               # React Query hooks
│   └── services/            # API client
└── docs/                    # Documentation
```

## Commit Messages

Follow conventional commits:

```
feat: add contradiction detection for numerical comparisons
fix: handle empty document list in frontend
docs: update API reference with new endpoints
chore: bump LangGraph to 0.4.2
test: add tests for query rewrite node
```

## Adding a New API Endpoint

1. Create the route handler in `backend/app/api/v1/`
2. Add the Pydantic schema in `backend/app/schemas/`
3. Implement business logic in `backend/app/services/`
4. Add the route to `backend/app/api/v1/router.py`
5. Add tests in `backend/tests/`
6. Add the frontend hook in `frontend/hooks/`
7. Add the service function in `frontend/services/`
8. Add the UI component or page as needed
9. Update `docs/API.md` with the new endpoint

## Adding a LangGraph Node

1. Create the node function in `backend/app/graph/nodes/`
2. Update the `GraphState` in `backend/app/graph/state.py` if needed
3. Add the node to `backend/app/graph/graph_builder.py`
4. Define edges to/from the new node
5. Add tests in `backend/tests/test_graph.py`

## Questions?

Open an issue on GitHub or reach out to the maintainers.

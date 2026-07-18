.PHONY: dev build up down test lint format clean

# ─── Development ───────────────────────────────────────

dev:
	@echo "Starting development environment..."
	docker compose -f docker-compose.yml up --build

dev-backend:
	@echo "Starting backend..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "Starting frontend..."
	cd frontend && npm run dev

# ─── Docker ────────────────────────────────────────────

build:
	@echo "Building all services..."
	docker compose build

up:
	@echo "Starting all services..."
	docker compose up -d

down:
	@echo "Stopping all services..."
	docker compose down

restart:
	@echo "Restarting all services..."
	docker compose restart

logs:
	@echo "Tailing logs..."
	docker compose logs -f

logs-backend:
	@echo "Tailing backend logs..."
	docker compose logs -f backend

ps:
	@echo "Service status..."
	docker compose ps

# ─── Testing ───────────────────────────────────────────

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v --tb=short

test-cov:
	@echo "Running backend tests with coverage..."
	cd backend && python -m pytest tests/ -v --tb=short --cov=app --cov-report=term --cov-report=html

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm run build

# ─── Linting ───────────────────────────────────────────

lint:
	@echo "Running linting..."
	cd backend && ruff check app/ tests/
	cd frontend && npm run lint

format:
	@echo "Formatting code..."
	cd backend && ruff format app/ tests/

# ─── Cleanup ───────────────────────────────────────────

clean:
	@echo "Cleaning up..."
	rm -rf backend/.pytest_cache
	rm -rf backend/__pycache__
	rm -rf backend/app/__pycache__
	rm -rf .pytest_cache
	rm -rf frontend/.next
	rm -rf backend/htmlcov

clean-all: clean
	@echo "Removing all Docker data..."
	docker compose down -v

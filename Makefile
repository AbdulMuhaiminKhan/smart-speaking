.PHONY: up down logs dev-deps api worker web test e2e lint

# Full stack in Docker: http://localhost:8080
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker

# Native development: Postgres and Redis in Docker, everything else on the host.
dev-deps:
	docker compose up -d postgres redis

api: dev-deps
	cd backend && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8000

worker: dev-deps
	cd backend && uv run python -m app.worker.run

web:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm run build

e2e:
	cd backend && uv run pytest -m e2e

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd frontend && npm run lint

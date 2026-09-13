.PHONY: install db-up db-down run-finance run-agent run-mcp run-telegram run-frontend docker-up docker-down format lint test test-mcp

install:
	uv sync --all-packages
	cd frontend && npm install

setup:
	git config core.hooksPath .githooks

db-up:
	docker-compose --env-file .env -f infra/docker-compose.yml up -d db

db-down:
	docker-compose -f infra/docker-compose.yml down

run-finance:
	uv run uvicorn finance_api.main:app --port 8000 --reload

run-agent:
	uv run uvicorn agent_api.main:app --port 8001 --reload

run-graph:
	uv run uvicorn graph_api.main:app --port 8002 --reload

run-mcp: run-graph

run-telegram:
	uv run python -m telegram_api.main

run-frontend:
	cd frontend && npm run dev

docker-up:
	docker-compose --env-file .env -f infra/docker-compose.yml up -d --build

docker-down:
	docker-compose -f infra/docker-compose.yml down

format:
	uv run black .
	uv run ruff check --fix .

lint:
	uv run black --check .
	uv run ruff check .

test:
	uv run pytest

test-graph:
	uv run pytest graph_api/tests

test-mcp:
	uv run pytest tests/finance_api/test_mcp_tools.py

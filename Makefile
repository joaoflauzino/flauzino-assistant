.PHONY: install db-up db-down run-finance run-agent run-telegram run-frontend docker-up docker-down format lint test

install:
	uv sync
	cd frontend && npm install

db-up:
	docker-compose --env-file .env -f infra/docker-compose.yml up -d db

db-down:
	docker-compose -f infra/docker-compose.yml down

run-finance:
	uv run uvicorn finance_api.main:app --port 8000 --reload

run-agent:
	uv run uvicorn agent_api.main:app --port 8001 --reload

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

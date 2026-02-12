# Stage 1: Builder
FROM python:3.13-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-install-project --no-dev --python /usr/local/bin/python

# Stage 2: Runtime
FROM python:3.13-slim-bookworm

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY telegram_api ./telegram_api

# Place the virtualenv in the path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["python", "-m", "telegram_api.main"]

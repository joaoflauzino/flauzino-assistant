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
# Using the system python to ensure shebangs match the runtime image
RUN uv sync --frozen --no-install-project --no-dev --python /usr/local/bin/python

# Stage 2: Runtime
FROM python:3.13-slim-bookworm

# Install system dependencies for OCR and OpenCV (Runtime only)
# --no-install-recommends reduces size
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY agent_api ./agent_api

# Place the virtualenv in the path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["uvicorn", "agent_api.main:app", "--host", "0.0.0.0", "--port", "8001"]


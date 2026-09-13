FROM ghcr.io/astral-sh/uv:0.9.26 AS uv

FROM python:3.13.14-slim-bookworm

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libexpat1 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Copia uv
COPY --from=uv /uv /bin/uv

WORKDIR /app

# Instala apenas as dependências do graph_api (workspace)
COPY pyproject.toml uv.lock ./
COPY graph_api/pyproject.toml graph_api/pyproject.toml
RUN uv sync --frozen --no-dev --package graph_api --python /usr/local/bin/python

# Copia código
COPY graph_api ./graph_api

# Expõe porta 8002
EXPOSE 8002

CMD ["/app/.venv/bin/uvicorn", "graph_api.main:app", "--host", "0.0.0.0", "--port", "8002"]

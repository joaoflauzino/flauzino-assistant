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

# Instala dependências
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --python /usr/local/bin/python

# Copia código
COPY . ./mcp_server

# Expõe porta 8002
EXPOSE 8002

CMD ["/app/.venv/bin/uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8002"]

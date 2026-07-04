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
COPY pyproject.toml .
RUN uv venv
RUN uv pip install -e .

# Copia código
COPY . .

# Expõe porta 8002
EXPOSE 8002

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]

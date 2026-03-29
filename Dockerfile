FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into the system Python (no venv needed in container)
RUN uv sync --frozen --no-dev --no-editable

# Copy application source
COPY app/ ./app/
COPY data/ ./data/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.13-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# dependency files first (cache layer)
COPY pyproject.toml uv.lock ./

# FORCE venv location (critical fix)
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

RUN uv sync --frozen --no-dev

# ensure correct runtime path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# copy full backend code
COPY . .

# entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/admin/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

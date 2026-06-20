# syntax=docker/dockerfile:1.7
# Multi-stage build for the FastAPI backend. Targets free-tier Render / Fly.io /
# similar. Non-root user, slim image, deps cached in a separate layer.

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install build deps (asyncpg / passlib / argon2 need a C toolchain at install time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --user -r requirements.txt

# ---- runtime ----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/app/.local/bin:$PATH

# Non-root user
RUN useradd --create-home --uid 10001 app
WORKDIR /home/app

COPY --from=builder /root/.local /home/app/.local
COPY --chown=app:app . .

USER app

EXPOSE 8000

# Render / Fly inject $PORT; default to 8000 locally
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

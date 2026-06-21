# syntax=docker/dockerfile:1.7
# Multi-stage build for the FastAPI backend. Targets free-tier Render / Fly.io /
# similar — slim image, non-root user, deps cached in a separate layer, and a
# HEALTHCHECK so the platform's orchestrator can drain a failing pod without
# guessing.

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Build deps (asyncpg / passlib / argon2 / cryptography need a C toolchain
# only at install time — they're not in the runtime image).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --user -r requirements.txt

# ---- runtime ----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/app/.local/bin:$PATH \
    LOG_FORMAT=json

# Non-root user — runtime container can't escalate even if a CVE in a dep
# lets an attacker exec.
RUN useradd --create-home --uid 10001 app
WORKDIR /home/app

COPY --from=builder /root/.local /home/app/.local
COPY --chown=app:app . .

USER app

EXPOSE 8000

# /healthz is the cheap liveness probe (no I/O); the orchestrator uses it to
# decide whether to restart the container. Use /readyz from the platform's
# health-check setting if you want DB-aware draining.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+__import__('os').environ.get('PORT','8000')+'/api/v1/healthz', timeout=3).status==200 else 1)" \
    || exit 1

# Render / Fly inject $PORT; default to 8000 locally. We `alembic upgrade head`
# every boot — idempotent, cheap, and avoids forgetting the migration step on
# a code-only deploy.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]

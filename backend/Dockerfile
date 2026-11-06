# One image for both the API and the worker.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SS_MEDIA_DIR=/data/media \
    SS_MODELS_DIR=/data/models

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg espeak-ng curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH"

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home --uid 1000 app && mkdir -p /data/media /data/models && chown -R app /data
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

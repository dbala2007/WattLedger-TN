# Multi-stage build: the "builder" stage has uv and compiles/installs
# dependencies into a virtual environment; the final stage copies only that
# venv plus the app code, so the shipped image doesn't carry build tools.
FROM python:3.13-slim AS builder

# uv is the same dependency manager used for local development (CLAUDE.md
# section 16) - installing it here keeps `uv sync` identical in both places.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy only the dependency files first so Docker can cache this layer -
# rebuilding after an app code change won't re-download dependencies.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app

FROM python:3.13-slim

# CLAUDE.md section 14: containers should not run as root where practical.
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/app ./app

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8000

# No --reload (that's a dev-only convenience); Postgres connection details
# and SECRET_KEY come from the container's environment (docker-compose.yml),
# never baked into the image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

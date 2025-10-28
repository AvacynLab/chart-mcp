# syntax=docker/dockerfile:1.5

FROM python:3.11-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG PIP_VERSION="24.2"

WORKDIR /app

# Install the default compiler toolchain for building wheels.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
# Pin pip and disable its cache so hadolint and build reproducibility requirements are met.
RUN python -m pip install --no-cache-dir --upgrade "pip==${PIP_VERSION}" \
    && pip install --no-cache-dir --prefix=/install --requirement requirements.txt

FROM python:3.11-slim AS runtime

# Ensure the runtime Python process can import both third-party dependencies copied
# from the builder layer (installed under ``/install``) and the project sources living
# in ``/app/src`` without requiring an additional editable installation step.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages:/app/src"

WORKDIR /app

COPY --from=builder /install /install
COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY docker/healthcheck.py ./docker/healthcheck.py
COPY README.md LICENSE ./

RUN groupadd -r chartmcp && useradd -r -g chartmcp chartmcp
USER chartmcp

EXPOSE 8000

# Delegate the health probe to the dedicated script that also ships with unit tests so
# Docker and CI reuse the exact same logic.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python", "docker/healthcheck.py"]

CMD ["uvicorn", "chart_mcp.app:app", "--host", "0.0.0.0", "--port", "8000"]

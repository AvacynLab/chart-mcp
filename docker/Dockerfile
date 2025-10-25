# syntax=docker/dockerfile:1.5

FROM python:3.11-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Debian trixie currently ships build-essential 12.10; pin to the latest tested release.
ARG BUILD_ESSENTIAL_VERSION="12.10"
ARG PIP_VERSION="24.2"

WORKDIR /app

# Pin the compiler toolchain to guarantee reproducible wheels for numpy/scipy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential="${BUILD_ESSENTIAL_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
# Pin pip and disable its cache so hadolint and build reproducibility requirements are met.
RUN python -m pip install --no-cache-dir --upgrade "pip==${PIP_VERSION}" \
    && pip install --no-cache-dir --prefix=/install --requirement requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH"

WORKDIR /app

COPY --from=builder /install /install
COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY README.md LICENSE ./
COPY docker/healthcheck.py /usr/local/bin/healthcheck.py

RUN groupadd -r chartmcp && useradd -r -g chartmcp chartmcp
USER chartmcp

EXPOSE 8000

# Use a standalone Python health probe script to avoid heredoc parsing issues across builders.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python", "/usr/local/bin/healthcheck.py"]

CMD ["uvicorn", "chart_mcp.app:app", "--host", "0.0.0.0", "--port", "8000"]

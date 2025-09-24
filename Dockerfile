# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system packages required for Postgres client SSL and build tooling
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for better layer caching
COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt

# Install only runtime dependencies (production image stays slim)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app app
COPY migrations migrations
COPY gunicorn.conf.py gunicorn.conf.py
COPY wsgi.py wsgi.py
COPY README.md README.md
COPY Procfile Procfile

# Create non-root user for running the service
RUN groupadd --system valezap \ 
    && useradd --system --gid valezap --home /app valezap

USER valezap

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]

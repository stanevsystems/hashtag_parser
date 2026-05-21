FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py exporter.py git_sync.py main.py proxy_config.py scanner.py state.py sync_service.py ./

RUN mkdir -p /app/data /app/secrets \
    && chmod 700 /app/secrets

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# .env, data/, secrets/ монтируются с хоста (см. docker-compose.yml)
CMD ["python", "main.py"]

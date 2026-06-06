FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Litestream — continuous S3-compatible replication of the SQLite DB.
ARG LITESTREAM_VERSION=0.3.13
RUN curl -fsSL -o /tmp/litestream.tar.gz \
      "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-amd64.tar.gz" \
    && tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz \
    && rm /tmp/litestream.tar.gz

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . --break-system-packages
RUN python -m playwright install --with-deps chromium

COPY . .

RUN mkdir -p /data
VOLUME /data

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV BRAND3_DB_PATH=/data/brand3.sqlite3
ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["/entrypoint.sh"]

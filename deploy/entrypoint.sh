#!/bin/bash
# Brand3 web app entrypoint.
#
# 1. If the SQLite DB is missing and a Litestream replica is configured,
#    restore it from S3/R2.
# 2. Start Litestream replication and uvicorn as a single foreground process
#    (Litestream owns the PID, so it can flush WAL on SIGTERM).

set -euo pipefail

if [ "${BRAND3_DISABLE_LITESTREAM:-false}" = "true" ]; then
  if [ "${BRAND3_ENVIRONMENT:-development}" = "production" ]; then
    echo "[entrypoint] refusing BRAND3_DISABLE_LITESTREAM=true in production." >&2
    exit 1
  fi
  echo "[entrypoint] BRAND3_DISABLE_LITESTREAM=true — starting uvicorn without replication."
  exec uvicorn web.app:app --host 0.0.0.0 --port 8080
fi

if [ ! -f "${BRAND3_DB_PATH}" ]; then
  echo "[entrypoint] DB not found at ${BRAND3_DB_PATH}; attempting Litestream restore..."
  litestream restore -if-replica-exists -config /app/litestream.yml "${BRAND3_DB_PATH}" \
    || echo "[entrypoint] no replica found — starting fresh."
fi

exec litestream replicate \
  -exec "uvicorn web.app:app --host 0.0.0.0 --port 8080" \
  -config /app/litestream.yml

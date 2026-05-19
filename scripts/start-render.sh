#!/usr/bin/env bash
# Render.com start: ensure data dirs exist, run Gunicorn.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -n "${DATABASE_PATH:-}" ]; then
  mkdir -p "$(dirname "$DATABASE_PATH")"
fi
if [ -n "${MEDIA_ROOT:-}" ]; then
  mkdir -p "$MEDIA_ROOT"
fi

cd "$ROOT/backend"
exec gunicorn tradex.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"

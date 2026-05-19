#!/usr/bin/env bash
# Render.com start: ensure data dirs exist, run Gunicorn.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

_ensure_dir() {
  local dir="$1"
  [ -z "$dir" ] && return 0
  mkdir -p "$dir" 2>/dev/null || {
    echo "WARNING: Cannot create '${dir}'. Unset DATABASE_PATH/MEDIA_ROOT on Free tier."
    return 0
  }
}

if [ -n "${DATABASE_PATH:-}" ]; then
  _ensure_dir "$(dirname "$DATABASE_PATH")"
fi
if [ -n "${MEDIA_ROOT:-}" ]; then
  _ensure_dir "$MEDIA_ROOT"
fi

# manage.py adds backend/tradex to sys.path; gunicorn needs the same
export PYTHONPATH="${ROOT}/backend/tradex${PYTHONPATH:+:${PYTHONPATH}}"
cd "$ROOT/backend"
exec gunicorn tradex.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"

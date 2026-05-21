#!/usr/bin/env bash
# Render.com start: persistent disk is mounted here — migrate DB, then Gunicorn.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

_ensure_dir() {
  local dir="$1"
  [ -z "$dir" ] && return 0
  mkdir -p "$dir" 2>/dev/null || {
    echo "WARNING: Cannot create '${dir}'. Attach a Render disk at /var/data or unset DATABASE_PATH."
    return 0
  }
}

if [ -n "${DATABASE_PATH:-}" ]; then
  _ensure_dir "$(dirname "$DATABASE_PATH")"
fi
if [ -n "${MEDIA_ROOT:-}" ]; then
  _ensure_dir "$MEDIA_ROOT"
fi

export PYTHONPATH="${ROOT}/backend/tradex${PYTHONPATH:+:${PYTHONPATH}}"
cd "$ROOT/backend"

echo "==> Applying migrations on persistent database..."
python manage.py shell -c "
import os
from django.conf import settings
db = settings.DATABASES['default']['NAME']
print('==> DATABASE file:', db)
print('==> DATABASE_PATH env:', os.environ.get('DATABASE_PATH') or '(not set)')
print('==> DB exists on disk:', os.path.exists(db) if db else False)
"

python manage.py migrate --noinput

bash "$ROOT/scripts/ensure-render-admin.sh"

echo "==> Starting Gunicorn..."
exec gunicorn tradex.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"

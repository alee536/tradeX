#!/usr/bin/env bash
# Render.com build: Python deps, frontend build, sync static files, migrate SQLite.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

echo "==> Building frontend..."
cd frontend
if command -v npm >/dev/null 2>&1; then
  npm ci --legacy-peer-deps
  NODE_ENV=production npm run build
else
  echo "ERROR: npm not found. Set NODE_VERSION in Render environment."
  exit 1
fi

echo "==> Syncing frontend build into Django..."
rm -rf "$ROOT/backend/static/frontend"
mkdir -p "$ROOT/backend/static/frontend"
cp -r dist/* "$ROOT/backend/static/frontend/"
cp dist/index.html "$ROOT/backend/templates/index.html"

_ensure_dir() {
  local dir="$1"
  local label="$2"
  if [ -z "$dir" ]; then
    return 0
  fi
  if mkdir -p "$dir" 2>/dev/null; then
    return 0
  fi
  echo "WARNING: Cannot create ${label} at '${dir}' (read-only or no disk)."
  echo "         On Render Free, remove DATABASE_PATH and MEDIA_ROOT from env vars."
  return 0
}

echo "==> Django collectstatic (no DB migrate at build — disk not mounted during build)..."
cd "$ROOT/backend"

python manage.py collectstatic --noinput

echo "==> Build complete. Migrations run at start on /var/data (see start-render.sh)."

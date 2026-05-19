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
  npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps
  NODE_ENV=production npm run build
else
  echo "ERROR: npm not found. Set NODE_VERSION in Render environment."
  exit 1
fi

echo "==> Syncing frontend build into Django..."
mkdir -p "$ROOT/backend/static/frontend"
rm -rf "$ROOT/backend/static/frontend/"*
cp -r dist/* "$ROOT/backend/static/frontend/"
cp dist/index.html "$ROOT/backend/templates/index.html"

echo "==> Django collectstatic & migrations..."
cd "$ROOT/backend"
if [ -n "${DATABASE_PATH:-}" ]; then
  mkdir -p "$(dirname "$DATABASE_PATH")"
fi
if [ -n "${MEDIA_ROOT:-}" ]; then
  mkdir -p "$MEDIA_ROOT"
fi

python manage.py collectstatic --noinput
python manage.py migrate --noinput

echo "==> Build complete."

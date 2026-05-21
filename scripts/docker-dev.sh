#!/usr/bin/env bash
# Start full dev stack (backend + frontend) via Docker Compose
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

docker compose up --build "$@"

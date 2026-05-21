# Local development with Docker

Docker Compose runs the **backend** (Django) and **frontend** (Vite) together. Production deploys use Render, not these files.

## Quick start

```bash
# From repo root
docker compose up --build

# Or
bash scripts/docker-dev.sh
```

| Service  | URL |
|----------|-----|
| Frontend | **http://localhost:5173** (use this URL only) |
| User dashboard | http://localhost:5173/user/dashboard |
| Backend API | http://localhost:8000/api |
| Django admin | http://localhost:8000/admin/ |

**Do not use the Docker container IP** (e.g. `http://172.19.0.3:5173`) for daily testing. It is a different browser origin than `localhost`, so login/token and fixes do not carry over.

## Optional env overrides

```bash
cp .env.docker.example .env.docker
# Edit .env.docker — file is gitignored
docker compose --env-file .env.docker up --build
```

## Without Docker

```bash
# Backend
cd backend && python manage.py migrate && python manage.py runserver

# Frontend (separate terminal)
cd frontend && pnpm install && pnpm run dev
```

## Branches

- **`main`** / **`feature/profit-percentage-part-02`**: profit + Render fixes; Docker files tracked here for local dev.
- **`feature/docker-dev-setup`**: older branch; Docker was merged into the profit branch via tracked files (no need to switch branches for Compose).

## Notes

- SQLite DB: `backend/tradex/db.sqlite3` (persisted via volume mount).
- Frontend proxy uses `VITE_API_PROXY_TARGET=http://backend:8000` inside Compose.
- Profit claim migrations (`0005`, `0006`) run automatically on backend start.

## Troubleshooting

### `localhost` broken but `172.19.x.x:5173` works

Browsers treat these as **different sites**:

| URL | Login token (`localStorage`) |
|-----|------------------------------|
| `http://localhost:5173` | Stored only here |
| `http://172.19.0.3:5173` | Stored only here (not shared) |

- Home `/` works without login on both.
- `/user/dashboard` needs login — if you logged in on `172.19.0.3`, `localhost` has **no token** and looks broken.
- **Fix:** Always open **http://localhost:5173**, log in again, then go to `/user/dashboard`.

Also stop any **local** `pnpm run dev` on the host if Docker is running (both use port 5173; the wrong app may answer on `localhost`).

```bash
# See what uses port 5173
ss -tlnp | grep 5173
docker compose ps
```

### `useClaimProfitReward` is not exported

Vite cached an old API client build. Clear cache and restart:

```bash
rm -rf frontend/node_modules/.vite
docker compose down
docker compose up --build
```

Or without Docker: `rm -rf frontend/node_modules/.vite && cd frontend && pnpm run dev`

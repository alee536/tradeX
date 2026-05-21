# Deploy 24TradeX to Render (SQLite)

## Prerequisites

- GitHub repo connected to Render
- Render account

## 1. Persistent disk (required for SQLite)

Without a disk, SQLite and uploaded screenshots are **lost on every redeploy** and you will see **all migrations run again** plus **superuser/data gone**.

**Blueprint (`render.yaml`)** includes a 1 GB disk at `/var/data`. If you deployed manually:

1. Render Dashboard → your Web Service → **Disks**
2. Add disk: **1 GB**, mount path: `/var/data`
3. Set environment variables (see `backend/.env.render.example`):
   - `DATABASE_PATH=/var/data/db.sqlite3`
   - `MEDIA_ROOT=/var/data/media`

**Important:** Migrations run at **start** (not build), because the disk is only mounted when the service runs. Build logs may show no migrate; runtime logs show `Applying migrations...` only for **new** migrations after the first deploy.

## 2. Environment variables

Open `backend/.env.render.example` and copy variables into:

**Render → Web Service → Environment**

Update:

- `ALLOWED_HOSTS` — your `*.onrender.com` hostname + custom domain
- `SITE_URL` — `https://your-app.onrender.com`
- `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` — same HTTPS origins
- `SECRET_KEY` / `JWT_SECRET` — generate strong random values

Render can auto-generate `SECRET_KEY` if you use `render.yaml` with `generateValue: true`.

## 3. Deploy with Blueprint (recommended)

1. Push this repo to GitHub
2. Render → **New** → **Blueprint**
3. Connect repo — Render reads `render.yaml`
4. Replace `your-app.onrender.com` in `render.yaml` env vars with your real hostname
5. Apply blueprint

## 4. Manual deploy (alternative)

| Setting | Value |
|---------|--------|
| **Root Directory** | *(repo root)* |
| **Build Command** | `bash scripts/build-render.sh` |
| **Start Command** | `bash scripts/start-render.sh` |
| **Health Check** | `/api/healthz` |

Add env vars from `backend/.env.render.example`.

## 5. Admin user (after first deploy)

**Option A — automatic (recommended):** In Render → Environment, add (do not commit passwords to git):

| Variable | Example |
|----------|---------|
| `RENDER_ADMIN_EMAIL` | `admin@gmail.com` |
| `RENDER_ADMIN_PASSWORD` | strong password |
| `RENDER_ADMIN_FULL_NAME` | `Admin` (optional) |

Redeploy once. `start-render.sh` creates/updates this user on every start without wiping existing data.

**Option B — manual shell:**

```bash
# Render Shell (Dashboard → Shell)
cd backend
python manage.py createsuperuser
```

## 6. Verify

- `https://your-app.onrender.com/api/healthz` → `{"status":"ok"}`
- `https://your-app.onrender.com/` → React app
- `https://your-app.onrender.com/admin/` → Django admin
- Register / login / purchase flow

## 7. Custom domain

1. Render → Settings → Custom Domains
2. Add `s24tx.com` / `www.s24tx.com`
3. Update DNS per Render instructions
4. Update `ALLOWED_HOSTS`, `SITE_URL`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`

## Local production build test

```bash
# Linux / macOS / Git Bash
export DATABASE_PATH=./data/db.sqlite3
export MEDIA_ROOT=./data/media
bash scripts/build-render.sh
bash scripts/start-render.sh
```

Windows: use Git Bash or WSL for the shell scripts.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 404 on `/api/api/...` | Do not call `setBaseUrl('/api')` — paths already include `/api` |
| Static files 404 | Re-run build; check `collectstatic` in build logs |
| Data lost after deploy | Attach persistent disk at `/var/data`; set `DATABASE_PATH` and `MEDIA_ROOT` |
| All migrations run every deploy | Fixed: migrate moved from build to start; attach disk so DB persists |
| Superuser gone after deploy | Same as data loss — use persistent disk + `RENDER_ADMIN_*` env vars |
| Build fails on frontend | Ensure `frontend/lib/api-client-react` is committed to git |
| `check --deploy` warnings | Set `DEBUG=False` and strong `SECRET_KEY` on Render |

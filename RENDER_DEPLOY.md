# Deploy 24TradeX to Render (SQLite)

## Prerequisites

- GitHub repo connected to Render
- Render account

## 1. Persistent disk (required for SQLite)

Without a disk, SQLite and uploaded screenshots are **lost on every redeploy**.

1. Render Dashboard → your Web Service → **Disks**
2. Add disk: **1 GB**, mount path: `/var/data`
3. Set environment variables (see `backend/.env.render.example`):
   - `DATABASE_PATH=/var/data/db.sqlite3`
   - `MEDIA_ROOT=/var/data/media`

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

## 5. After first deploy

```bash
# Render Shell (Dashboard → Shell)
cd backend
python manage.py createsuperuser
```

Or create admin via shell:

```python
from apps.accounts.models import User
u, _ = User.objects.get_or_create(email='admin@gmail.com', defaults={'username':'admin','full_name':'Admin','is_staff':True,'is_superuser':True})
u.set_password('your-secure-password')
u.save()
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
| Data lost after deploy | Attach persistent disk; set `DATABASE_PATH` |
| Build fails on frontend | Ensure `frontend/lib/api-client-react` is committed to git |
| `check --deploy` warnings | Set `DEBUG=False` and strong `SECRET_KEY` on Render |

# 24TradeX

A premium crypto token trading platform inspired by Binance/Bybit — dark, futuristic, and feature-complete.

## Stack

- **Frontend:** React 18+ with Vite, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** Django 5.2+ with Django REST Framework, SQLite (dev)
- **Type Safety:** TypeScript throughout, Zod schemas, Orval code generation
- **Package Manager:** pnpm monorepo (Node.js), pipenv (Python)
- **Auth:** JWT tokens (PyJWT) stored in localStorage

## Prerequisites

Before setting up, ensure you have installed:
- **Node.js** 24+ (or latest LTS)
- **pnpm** (install via `npm install -g pnpm`)
- **Python** 3.11+
- **pipenv** (install via `pip install pipenv`)

## Local Setup

### Quick Start (Automated)

**Windows (PowerShell):**
```powershell
.\scripts\setup-local.ps1
```

**macOS/Linux (Bash):**
```bash
bash scripts/setup-local.sh
```

The script will:
1. Install all Node.js dependencies
2. Set up the Python environment with pipenv
3. Run Django migrations
4. Provide instructions for starting dev servers

### Manual Setup

#### 1. Install Node.js Dependencies
```bash
pnpm install
```

#### 2. Set Up Python Environment
```bash
# Create and activate pipenv environment
pipenv install --python 3.11 -r backend/requirements.txt

# Or if you prefer virtualenv instead:
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
pip install -r backend/requirements.txt
```

#### 3. Run Django Migrations
```bash
cd backend/tradex
pipenv run python manage.py migrate
# Or if using virtualenv:
python manage.py migrate
```

## Running the Application

### Start the Django Backend
```bash
cd backend/tradex
pipenv run python manage.py runserver
# Or if using virtualenv:
python manage.py runserver
```

The API will be available at `http://localhost:8000/api`

### Start the React Frontend (in a new terminal)
```bash
cd frontend
pnpm run dev
```

The frontend will typically run on `http://localhost:5173`

## Development

### Project Structure
```
.
├── frontend/              # Main React frontend (Vite)
├── backend/tradex/         # Django application
│   ├── apps/               # Django apps (accounts, purchases, etc.)
│   ├── manage.py           # Django CLI
│   └── db.sqlite3          # Development database
├── lib/
│   ├── api-spec/           # OpenAPI specification
│   ├── api-client-react/   # Generated React hooks
│   ├── api-zod/            # Generated Zod schemas
│   └── db/                 # Drizzle ORM schemas
├── scripts/                # Utility scripts
└── pnpm-workspace.yaml     # Monorepo configuration
```

### Common Commands

#### Frontend (from `frontend/`)
```bash
pnpm run dev          # Start dev server
pnpm run build        # Build for production
pnpm run serve        # Serve production build
pnpm run typecheck    # Type check TypeScript
```

#### Backend (from `backend/tradex/`)
```bash
python manage.py makemigrations   # Create migrations
python manage.py migrate          # Run migrations
python manage.py createsuperuser  # Create admin user
python manage.py runserver        # Start dev server
```

#### API Code Generation (from workspace root)
```bash
pnpm --filter api-spec run codegen
```

This regenerates React hooks in `lib/api-client-react/src/generated/` and Zod schemas in `lib/api-zod/src/generated/` from the OpenAPI spec.

### Django Admin
- **URL:** http://localhost:8000/admin
- **Default credentials:** username `admin`, password `*******`

## Architecture

- **Django Backend:** Serves at `/api` path with Django REST Framework
- **JWT Authentication:** Tokens stored in localStorage and attached via custom-fetch middleware
- **Sponsor Codes:** Auto-generated as `24TX-XXXXXX` format on user creation
- **Token Unlock:** 3-stage time-based logic (72h → 50%, 24h → 25%, 24h → 25%)
- **Admin Panel:** Approve/reject purchases and withdrawals, manage users and settings

## Features

24TradeX allows users to:
- Register with a sponsor code or sponsor link
- Submit token purchase requests (USDT BEP20) with TXID proof
- View time-locked token unlock progress
- Submit withdrawal requests once tokens unlock
- Earn sponsor commissions when referred users make purchases
- Admins can approve/reject transactions and manage the platform

## Important Notes

- **Django uses SQLite** for development (stored at `backend/tradex/db.sqlite3`)
- **Never use "Investment"** in the UI — use "Purchase", "Sale", "Trading", or "Token Purchase"
- **Dark theme only** — the app uses a dark, futuristic UI inspired by Binance/Bybit
- Always run `python manage.py makemigrations && python manage.py migrate` after model changes
- Frontend API base URL is `/api` (relative, configured in `lib/api-client-react/src/custom-fetch.ts`)

## Troubleshooting

**pnpm not found:**
```bash
npm install -g pnpm
```

**pipenv not found:**
```bash
pip install pipenv
```

**Django migrations fail:**
```bash
# Check if Python is in PATH
python --version

# Reset database (dev only)
rm backend/tradex/db.sqlite3
python backend/tradex/manage.py migrate
```

**Port already in use:**
- Django (default 8000): `python manage.py runserver 8001`
- Vite (default 5173): `pnpm --filter artifacts/24tradex dev -- --port 5174`

## Support

For issues, refer to:
- Replit-related files archived in `/archive/`
- Django docs: https://docs.djangoproject.com/
- React/Vite docs: https://vitejs.dev/
- pnpm docs: https://pnpm.io/

# 24TradeX
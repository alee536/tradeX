# 24TradeX - Local development setup (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== 24TradeX local setup ===" -ForegroundColor Cyan

# Backend
Write-Host "`n[1/4] Python backend..." -ForegroundColor Yellow
$Backend = Join-Path $Root "backend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    python -m venv (Join-Path $Backend ".venv")
}
& (Join-Path $Backend ".venv\Scripts\pip.exe") install -r (Join-Path $Backend "requirements.txt")

if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Copy-Item (Join-Path $Backend ".env.example") (Join-Path $Backend ".env")
    Write-Host "Created backend/.env from .env.example" -ForegroundColor Green
}

$ManagePy = Join-Path $Backend "manage.py"
& $VenvPython $ManagePy migrate --noinput
Write-Host "Migrations applied." -ForegroundColor Green

# Frontend api-client (restore from git if missing)
$ApiClient = Join-Path $Root "frontend\lib\api-client-react\package.json"
if (-not (Test-Path $ApiClient)) {
    Write-Host "Restoring api-client-react from git..." -ForegroundColor Yellow
    Push-Location $Root
    git checkout 9a3a817 -- lib/api-client-react
    New-Item -ItemType Directory -Force -Path "frontend\lib" | Out-Null
    Move-Item -Force "lib\api-client-react" "frontend\lib\api-client-react"
    Remove-Item -Recurse -Force "lib" -ErrorAction SilentlyContinue
    Pop-Location
}

# Frontend
Write-Host "`n[2/4] Frontend dependencies..." -ForegroundColor Yellow
$Frontend = Join-Path $Root "frontend"
Push-Location $Frontend
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm install
} else {
    Write-Host "pnpm not found; using npm..." -ForegroundColor DarkYellow
    npm install
}
Pop-Location

Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host @"

Start the app in TWO terminals:

  Terminal 1 (backend):
    cd backend
    .venv\Scripts\python.exe manage.py runserver

  Or from repo root:
    backend\.venv\Scripts\python.exe backend\manage.py runserver

  Terminal 2 (frontend):
    cd frontend
    npm run dev
    (or: pnpm run dev)

  Backend API:  http://127.0.0.1:8000/api/healthz
  Frontend UI:  http://127.0.0.1:5173
  Django admin: http://127.0.0.1:8000/admin/

  Create admin user:
    backend\.venv\Scripts\python.exe backend\manage.py createsuperuser

"@

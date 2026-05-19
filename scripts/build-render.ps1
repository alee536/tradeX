# Windows local test of Render build steps
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> Python dependencies..." -ForegroundColor Cyan
python -m pip install -r (Join-Path $Root "backend\requirements.txt")

Write-Host "==> Frontend build..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
npm install --legacy-peer-deps
$env:NODE_ENV = "production"
npm run build
Pop-Location

Write-Host "==> Sync to Django static..." -ForegroundColor Cyan
$staticDir = Join-Path $Root "backend\static\frontend"
New-Item -ItemType Directory -Force -Path $staticDir | Out-Null
Copy-Item -Path (Join-Path $Root "frontend\dist\*") -Destination $staticDir -Recurse -Force
Copy-Item -Path (Join-Path $Root "frontend\dist\index.html") -Destination (Join-Path $Root "backend\templates\index.html") -Force

Write-Host "==> collectstatic & migrate..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "backend")
python manage.py collectstatic --noinput
python manage.py migrate --noinput
Pop-Location

Write-Host "==> Done. Start with: cd backend; python -m gunicorn tradex.wsgi:application --bind 127.0.0.1:8000" -ForegroundColor Green

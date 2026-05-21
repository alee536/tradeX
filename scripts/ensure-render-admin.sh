#!/usr/bin/env bash
# Idempotent admin bootstrap for Render (only when env vars are set).
set -euo pipefail

EMAIL="${RENDER_ADMIN_EMAIL:-}"
PASSWORD="${RENDER_ADMIN_PASSWORD:-}"
USERNAME="${RENDER_ADMIN_USERNAME:-}"
FULL_NAME="${RENDER_ADMIN_FULL_NAME:-Admin}"

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "==> Skipping admin bootstrap (set RENDER_ADMIN_EMAIL and RENDER_ADMIN_PASSWORD to enable)."
  exit 0
fi

echo "==> Ensuring Render admin user exists (${EMAIL})..."
python manage.py shell <<PY
from apps.accounts.models import User

email = """${EMAIL}"""
password = """${PASSWORD}"""
full_name = """${FULL_NAME}"""

login_username = """${USERNAME}""" or email
user, created = User.objects.update_or_create(
    email=email,
    defaults={
        "username": login_username,
        "full_name": full_name,
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
    },
)
if login_username != user.username:
    user.username = login_username
user.set_password(password)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()
print("Admin", "created" if created else "updated", ":", user.email)
PY

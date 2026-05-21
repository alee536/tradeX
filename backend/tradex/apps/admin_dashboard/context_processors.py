import os

from django.conf import settings


def _resolve_frontend_url() -> str:
    """Trader SPA base URL for admin Home link (works even if FRONTEND_URL not in settings yet)."""
    env_url = os.environ.get('FRONTEND_URL', '').strip().rstrip('/')
    if env_url:
        return env_url

    configured = getattr(settings, 'FRONTEND_URL', None)
    if configured:
        return str(configured).rstrip('/')

    site_url = getattr(settings, 'SITE_URL', 'https://www.s24tx.com')
    site_url = str(site_url).rstrip('/')
    if getattr(settings, 'DEBUG', False):
        return 'http://127.0.0.1:5173'
    return site_url


def frontend_url(request):
    return {'FRONTEND_URL': _resolve_frontend_url()}

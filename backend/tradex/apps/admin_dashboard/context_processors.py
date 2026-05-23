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


ADMIN_NOTIFICATION_TYPE_PREFIX = 'admin_'
ADMIN_NOTIFICATION_RECENT_LIMIT = 5


def _admin_notification_link(notification_type: str) -> str:
    """Deep-link an admin notification to the relevant pending list page."""
    if notification_type == 'admin_purchase_submitted':
        return '/admin/purchases/?status=pending'
    if notification_type == 'admin_sponsor_submitted':
        return '/admin/sponsor-access/?status=pending'
    return '/admin/'


def admin_notifications(request):
    """
    Inject admin bell data for staff users only.
    Cheap — runs only for authenticated staff/superusers and uses indexed lookups.
    Always returns a dict (never raises) so the admin layout cannot break.
    """
    empty = {
        'admin_unread_count': 0,
        'admin_recent_notifications': [],
    }
    try:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return empty
        if not (user.is_staff or user.is_superuser):
            return empty

        from apps.notifications.models import Notification

        base_qs = Notification.objects.filter(
            user=user,
            type__startswith=ADMIN_NOTIFICATION_TYPE_PREFIX,
        )
        unread_count = base_qs.filter(is_read=False).count()
        recent = list(
            base_qs.only('id', 'message', 'type', 'is_read', 'created_at')
            .order_by('-created_at')[:ADMIN_NOTIFICATION_RECENT_LIMIT]
        )
        return {
            'admin_unread_count': unread_count,
            'admin_recent_notifications': [
                {
                    'id': n.id,
                    'message': n.message,
                    'type': n.type,
                    'is_read': n.is_read,
                    'created_at': n.created_at,
                    'link': _admin_notification_link(n.type),
                }
                for n in recent
            ],
        }
    except Exception:
        return empty

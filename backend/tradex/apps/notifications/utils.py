def create_notification(user, notification_type, message):
    from .models import Notification
    return Notification.objects.create(
        user=user,
        type=notification_type,
        message=message,
    )


def notify_admins(notification_type, message):
    """
    Bulk-create an in-app notification for every staff/superuser account.
    Uses bulk_create so one INSERT covers all admins — safe if no admins exist.
    """
    from django.contrib.auth import get_user_model
    from .models import Notification

    User = get_user_model()
    admin_ids = list(User.objects.filter(is_staff=True).values_list('id', flat=True))
    if not admin_ids:
        return
    Notification.objects.bulk_create([
        Notification(user_id=uid, type=notification_type, message=message)
        for uid in admin_ids
    ])

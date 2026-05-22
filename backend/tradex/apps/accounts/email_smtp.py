"""
SMTP connectivity helpers for OTP email delivery.
"""

import logging
import smtplib

from django.conf import settings

logger = logging.getLogger(__name__)


def normalize_app_password(value):
    """Gmail app passwords: 16 characters, often shown in 4 groups with spaces."""
    return (value or '').replace(' ', '').strip()


def smtp_configured():
    user = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    password = normalize_app_password(getattr(settings, 'EMAIL_HOST_PASSWORD', ''))
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    return (
        'smtp' in backend.lower()
        and bool(user)
        and bool(password)
    )


def verify_smtp_login():
    """
    Test Gmail SMTP credentials. Returns (ok: bool, message: str).
    Does not send mail.
    """
    if not smtp_configured():
        return False, 'SMTP is not configured (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD).'

    host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
    port = int(getattr(settings, 'EMAIL_PORT', 587))
    use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
    use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
    user = settings.EMAIL_HOST_USER.strip()
    password = normalize_app_password(settings.EMAIL_HOST_PASSWORD)

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if use_tls:
                server.starttls()
        server.login(user, password)
        server.quit()
        return True, 'SMTP login successful.'
    except smtplib.SMTPAuthenticationError:
        logger.warning('SMTP authentication failed for user=%s', user)
        return False, (
            'Gmail rejected the app password. Use a 16-character App Password '
            '(Google Account → Security → 2-Step Verification → App passwords), '
            'not your normal Gmail password.'
        )
    except Exception as exc:
        logger.warning('SMTP connection failed: %s', exc)
        return False, f'SMTP connection failed: {exc}'

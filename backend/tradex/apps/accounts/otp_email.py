"""
Shared helpers for sending OTP verification emails (signup, password reset).
"""

import logging
import smtplib

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def log_email_backend_status(flow_label):
    """Log SMTP configuration at debug level (development only)."""
    if not settings.DEBUG:
        return
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    logger.debug(
        '%s email backend=%s host=%s user=%r password_configured=%s',
        flow_label,
        backend,
        getattr(settings, 'EMAIL_HOST', ''),
        getattr(settings, 'EMAIL_HOST_USER', ''),
        bool(getattr(settings, 'EMAIL_HOST_PASSWORD', '')),
    )
    if 'console' in backend:
        logger.debug(
            '%s using console backend — OTP appears in process logs only',
            flow_label,
        )


def send_otp_email(recipient, otp_code, subject, body, flow_label='OTP'):
    """
    Send a plain-text OTP email.

    Logs OTP value only when DEBUG is True (never in production logs).
    """
    log_email_backend_status(flow_label)
    if settings.DEBUG:
        logger.debug('%s code for %s: %s', flow_label, recipient, otp_code)

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except smtplib.SMTPAuthenticationError:
        password = (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '')
        if password in ('', 'YOUR_GMAIL_APP_PASSWORD_HERE', 'your-gmail-app-password-here'):
            logger.error(
                '%s: EMAIL_HOST_PASSWORD is missing or still a placeholder in backend/.env. '
                'Set a 16-character Gmail App Password and run: docker compose up -d --force-recreate backend',
                flow_label,
            )
        logger.exception('%s email delivery failed for %s', flow_label, recipient)
        raise
    except Exception:
        logger.exception('%s email delivery failed for %s', flow_label, recipient)
        raise

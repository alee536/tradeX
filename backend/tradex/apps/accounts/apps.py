import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        from django.conf import settings

        from apps.accounts.otp_email import log_email_backend_status

        log_email_backend_status('Accounts')

        if settings.DEBUG and 'smtp' in getattr(settings, 'EMAIL_BACKEND', '').lower():
            from apps.accounts.email_smtp import verify_smtp_login

            ok, msg = verify_smtp_login()
            if ok:
                logger.info('SMTP ready for OTP emails (%s)', settings.EMAIL_HOST_USER)
            else:
                logger.warning('SMTP not ready — signup OTP emails will fail: %s', msg)

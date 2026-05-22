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

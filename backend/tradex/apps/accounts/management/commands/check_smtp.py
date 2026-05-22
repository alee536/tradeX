from django.core.management.base import BaseCommand

from apps.accounts.email_smtp import smtp_configured, verify_smtp_login


class Command(BaseCommand):
    help = 'Verify Gmail SMTP credentials used for signup/password-reset OTP emails.'

    def handle(self, *args, **options):
        if not smtp_configured():
            self.stderr.write(self.style.ERROR(
                'SMTP not configured. Set EMAIL_BACKEND=smtp, EMAIL_HOST_USER, '
                'and EMAIL_HOST_PASSWORD (16-char Gmail App Password).',
            ))
            return

        ok, msg = verify_smtp_login()
        if ok:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stderr.write(self.style.ERROR(msg))

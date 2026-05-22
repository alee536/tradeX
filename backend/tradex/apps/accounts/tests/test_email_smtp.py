from django.test import TestCase, override_settings

from apps.accounts.email_smtp import normalize_app_password, smtp_configured


class EmailSmtpHelpersTests(TestCase):
    def test_normalize_app_password_strips_spaces(self):
        self.assertEqual(
            normalize_app_password('yqvc qvey svuo hjng'),
            'yqvcqveysvuohjng',
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST_USER='test@gmail.com',
        EMAIL_HOST_PASSWORD='abcd1234efgh5678',
    )
    def test_smtp_configured_when_user_and_password_set(self):
        self.assertTrue(smtp_configured())

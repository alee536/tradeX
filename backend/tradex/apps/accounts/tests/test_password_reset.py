"""
Tests for forgot-password OTP flow.
"""

from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import PasswordResetOtp, User
from apps.accounts.password_reset import (
    PasswordResetError,
    confirm_password_reset,
    request_password_reset,
    resend_password_reset_otp,
    _hash_reset_otp,
)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PASSWORD_RESET_OTP_EXPIRY_MINUTES=15,
    PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS=60,
    PASSWORD_RESET_OTP_MAX_ATTEMPTS=5,
)
class PasswordResetServiceTests(TestCase):
    """Unit tests for password_reset service."""

    def setUp(self):
        mail.outbox.clear()
        self.user = User.objects.create_user(
            username='reset_user',
            email='reset_test@example.com',
            password='OldPassword123!',
            full_name='Reset Test',
        )
        self.unknown_email = 'nobody@example.com'

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='112233')
    def test_request_sends_email_for_existing_user(self, _mock):
        result = request_password_reset(self.user.email)
        self.assertIn('verification code', result['message'].lower())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('112233', mail.outbox[0].body)
        record = PasswordResetOtp.objects.get(email='reset_test@example.com')
        self.assertEqual(record.otp_hash, _hash_reset_otp('reset_test@example.com', '112233'))

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='112233')
    def test_request_unknown_email_same_message_no_mail(self, _mock):
        result = request_password_reset(self.unknown_email)
        self.assertIn('verification code', result['message'].lower())
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(PasswordResetOtp.objects.filter(email=self.unknown_email).exists())

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='445566')
    def test_old_token_invalidated_on_new_request(self, _mock):
        request_password_reset(self.user.email)
        first_id = PasswordResetOtp.objects.filter(email='reset_test@example.com').first().pk
        request_password_reset(self.user.email)
        first = PasswordResetOtp.objects.get(pk=first_id)
        self.assertIsNotNone(first.used_at)
        active = PasswordResetOtp.objects.filter(
            email='reset_test@example.com',
            used_at__isnull=True,
        )
        self.assertEqual(active.count(), 1)

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='778899')
    def test_confirm_updates_password_and_marks_used(self, _mock):
        request_password_reset(self.user.email)
        confirm_password_reset('reset_test@example.com', '778899', 'NewSecurePass99!')
        self.user.refresh_from_db()
        self.assertTrue(check_password('NewSecurePass99!', self.user.password))
        self.assertFalse(check_password('OldPassword123!', self.user.password))
        record = PasswordResetOtp.objects.filter(
            email='reset_test@example.com',
        ).order_by('-created_at').first()
        self.assertIsNotNone(record.used_at)

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='778899')
    def test_confirm_fails_after_otp_used(self, _mock):
        request_password_reset(self.user.email)
        confirm_password_reset('reset_test@example.com', '778899', 'NewSecurePass99!')
        with self.assertRaises(PasswordResetError) as ctx:
            confirm_password_reset('reset_test@example.com', '778899', 'AnotherPass99!')
        self.assertEqual(ctx.exception.code, 'no_pending_reset')

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='101010')
    def test_invalid_otp_increments_attempts(self, _mock):
        request_password_reset(self.user.email)
        with self.assertRaises(PasswordResetError) as ctx:
            confirm_password_reset('reset_test@example.com', '000000', 'NewSecurePass99!')
        self.assertEqual(ctx.exception.code, 'invalid_otp')
        record = PasswordResetOtp.objects.filter(
            email='reset_test@example.com',
            used_at__isnull=True,
        ).first()
        self.assertEqual(record.attempts, 1)

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='202020')
    def test_expired_otp_rejected(self, _mock):
        request_password_reset(self.user.email)
        record = PasswordResetOtp.objects.filter(email='reset_test@example.com').first()
        record.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        record.save(update_fields=['expires_at'])
        with self.assertRaises(PasswordResetError) as ctx:
            confirm_password_reset('reset_test@example.com', '202020', 'NewSecurePass99!')
        self.assertEqual(ctx.exception.code, 'otp_expired')

    @patch('apps.accounts.password_reset._generate_otp_code')
    def test_resend_after_cooldown(self, mock_gen):
        mock_gen.side_effect = ['303030', '404040']
        request_password_reset(self.user.email)
        record = PasswordResetOtp.objects.filter(email='reset_test@example.com').first()
        record.last_sent_at = timezone.now() - timezone.timedelta(seconds=120)
        record.save(update_fields=['last_sent_at'])
        mail.outbox.clear()
        resend_password_reset_otp(self.user.email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('404040', mail.outbox[0].body)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS=0,
)
class PasswordResetApiTests(TestCase):
    """HTTP tests for forgot-password endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='api_reset_user',
            email='api_reset@example.com',
            password='OldPassword123!',
            full_name='API Reset',
        )

    @patch('apps.accounts.password_reset._generate_otp_code', return_value='535353')
    def test_full_reset_flow_via_api(self, _mock):
        mail.outbox.clear()
        r1 = self.client.post(
            '/api/auth/forgot-password/request',
            {'email': 'api_reset@example.com'},
            format='json',
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        r2 = self.client.post(
            '/api/auth/forgot-password/confirm',
            {
                'email': 'api_reset@example.com',
                'otp': '535353',
                'password': 'BrandNewPass88!',
            },
            format='json',
        )
        self.assertEqual(r2.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(check_password('BrandNewPass88!', self.user.password))

        login = self.client.post(
            '/api/auth/login',
            {'username': 'api_reset@example.com', 'password': 'BrandNewPass88!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)

    def test_unknown_email_returns_200_generic(self):
        r = self.client.post(
            '/api/auth/forgot-password/request',
            {'email': 'missing@example.com'},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('message', r.data)

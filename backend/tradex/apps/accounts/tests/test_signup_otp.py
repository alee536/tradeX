"""
Tests for email OTP signup flow.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import SignupOtpVerification, User
from apps.accounts.signup_otp import (
    SignupOtpError,
    request_signup_otp,
    resend_signup_otp,
    verify_signup_otp,
    _hash_otp,
    _generate_otp_code,
)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SIGNUP_OTP_EXPIRY_MINUTES=10,
    SIGNUP_OTP_RESEND_COOLDOWN_SECONDS=60,
    SIGNUP_OTP_MAX_ATTEMPTS=5,
)
class SignupOtpServiceTests(TestCase):
    """Unit tests for signup_otp service helpers."""

    def setUp(self):
        mail.outbox.clear()
        self.payload = {
            'username': 'otp_user',
            'full_name': 'OTP Test User',
            'email': 'otp_test@example.com',
            'password': 'securepass123',
            'sponsor_code': '',
        }

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='123456')
    def test_request_otp_sends_email_and_stores_hash(self, _mock_gen):
        result = request_signup_otp(self.payload)
        self.assertIn('sent', result['message'].lower())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('123456', mail.outbox[0].body)

        record = SignupOtpVerification.objects.get(email='otp_test@example.com')
        self.assertEqual(record.otp_hash, _hash_otp('otp_test@example.com', '123456'))
        self.assertFalse(User.objects.filter(email='otp_test@example.com').exists())

    def test_request_otp_rejects_existing_email(self):
        User.objects.create_user(
            username='existing',
            email='otp_test@example.com',
            password='securepass123',
            full_name='Existing',
        )
        with self.assertRaises(SignupOtpError) as ctx:
            request_signup_otp(self.payload)
        self.assertEqual(ctx.exception.code, 'email_already_registered')

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='654321')
    def test_verify_creates_user_and_marks_verified(self, _mock_gen):
        request_signup_otp(self.payload)
        user = verify_signup_otp('otp_test@example.com', '654321')
        self.assertEqual(user.email, 'otp_test@example.com')
        record = SignupOtpVerification.objects.get(email='otp_test@example.com')
        self.assertIsNotNone(record.verified_at)

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='111111')
    def test_invalid_otp_increments_attempts(self, _mock_gen):
        request_signup_otp(self.payload)
        with self.assertRaises(SignupOtpError) as ctx:
            verify_signup_otp('otp_test@example.com', '999999')
        self.assertEqual(ctx.exception.code, 'invalid_otp')
        record = SignupOtpVerification.objects.get(email='otp_test@example.com')
        self.assertEqual(record.attempts, 1)

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='222222')
    def test_expired_otp_rejected(self, _mock_gen):
        request_signup_otp(self.payload)
        record = SignupOtpVerification.objects.get(email='otp_test@example.com')
        record.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        record.save(update_fields=['expires_at'])
        with self.assertRaises(SignupOtpError) as ctx:
            verify_signup_otp('otp_test@example.com', '222222')
        self.assertEqual(ctx.exception.code, 'otp_expired')

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='333333')
    def test_resend_respects_cooldown(self, _mock_gen):
        request_signup_otp(self.payload)
        with self.assertRaises(SignupOtpError) as ctx:
            resend_signup_otp('otp_test@example.com')
        self.assertEqual(ctx.exception.code, 'resend_cooldown')

    @patch('apps.accounts.signup_otp._generate_otp_code')
    def test_resend_after_cooldown_sends_new_code(self, mock_gen):
        mock_gen.side_effect = ['444444', '555555']
        request_signup_otp(self.payload)
        record = SignupOtpVerification.objects.get(email='otp_test@example.com')
        record.last_sent_at = timezone.now() - timezone.timedelta(seconds=120)
        record.save(update_fields=['last_sent_at'])
        mail.outbox.clear()
        resend_signup_otp('otp_test@example.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('555555', mail.outbox[0].body)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SIGNUP_OTP_RESEND_COOLDOWN_SECONDS=0,
)
class SignupOtpApiTests(TestCase):
    """HTTP tests for register OTP endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.signup_body = {
            'username': 'api_otp_user',
            'full_name': 'API OTP User',
            'email': 'api_otp@example.com',
            'password': 'securepass123',
        }

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='424242')
    def test_full_signup_flow_via_api(self, _mock_gen):
        mail.outbox.clear()
        r1 = self.client.post('/api/auth/register/request-otp', self.signup_body, format='json')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        r2 = self.client.post(
            '/api/auth/register/verify',
            {'email': 'api_otp@example.com', 'otp': '424242'},
            format='json',
        )
        self.assertEqual(r2.status_code, 201)
        self.assertIn('token', r2.data)
        self.assertTrue(User.objects.filter(email='api_otp@example.com').exists())

    def test_legacy_register_returns_otp_required(self):
        response = self.client.post('/api/auth/register', self.signup_body, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'otp_required')

    @patch('apps.accounts.signup_otp._generate_otp_code', return_value='101010')
    def test_verify_invalid_otp_returns_error_code(self, _mock_gen):
        self.client.post('/api/auth/register/request-otp', self.signup_body, format='json')
        response = self.client.post(
            '/api/auth/register/verify',
            {'email': 'api_otp@example.com', 'otp': '000000'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'invalid_otp')

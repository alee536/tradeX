"""
Email OTP verification before account creation.

Signup is two-step: request OTP (stores pending payload) → verify OTP (creates user).
"""

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import SignupOtpVerification, User
from apps.accounts.otp_email import send_otp_email
from apps.sponsor.access import resolve_active_sponsor_by_ref

logger = logging.getLogger(__name__)

OTP_LENGTH = 6


class SignupOtpError(Exception):
    """Raised when signup OTP flow fails; maps to API error responses."""

    def __init__(self, message, code='otp_error', http_status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


def _otp_settings():
    return {
        'expiry_minutes': int(getattr(settings, 'SIGNUP_OTP_EXPIRY_MINUTES', 10)),
        'resend_cooldown_seconds': int(
            getattr(settings, 'SIGNUP_OTP_RESEND_COOLDOWN_SECONDS', 60)
        ),
        'max_attempts': int(getattr(settings, 'SIGNUP_OTP_MAX_ATTEMPTS', 5)),
    }


def _normalize_email(email):
    return (email or '').strip().lower()


def _hash_otp(email, otp_code):
    """HMAC hash so OTP is never stored in plain text."""
    key = settings.SECRET_KEY.encode('utf-8')
    msg = f'{_normalize_email(email)}:{otp_code}'.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _generate_otp_code():
    return ''.join(str(secrets.randbelow(10)) for _ in range(OTP_LENGTH))


def _build_signup_payload(validated_data):
    sponsor_code = validated_data.get('sponsor_code')
    payload = {
        'username': validated_data['username'],
        'full_name': validated_data['full_name'],
        'email': _normalize_email(validated_data['email']),
        'password': validated_data['password'],
    }
    if sponsor_code:
        payload['sponsor_code'] = (sponsor_code or '').strip()
    return payload


def _resolve_sponsored_by(sponsor_code):
    if not sponsor_code:
        return None
    code = sponsor_code.strip()
    sponsored_by = resolve_active_sponsor_by_ref(code)
    if sponsored_by is not None:
        return sponsored_by
    return User.objects.filter(
        sponsor_code=code,
        sponsor_access_status=User.SPONSOR_ACCESS_ACTIVE,
    ).first()


def _create_user_from_payload(payload):
    sponsored_by = _resolve_sponsored_by(payload.get('sponsor_code'))
    return User.objects.create_user(
        username=payload['username'],
        email=payload['email'],
        password=payload['password'],
        full_name=payload['full_name'],
        sponsored_by=sponsored_by,
    )


def _send_signup_otp_email(email, otp_code):
    expiry = _otp_settings()['expiry_minutes']
    body = (
        f'Your verification code is: {otp_code}\n\n'
        f'This code expires in {expiry} minutes.\n'
        'If you did not request this, you can ignore this email.\n\n'
        '— 24TRADEX'
    )
    try:
        send_otp_email(
            email,
            otp_code,
            'Your 24TRADEX verification code',
            body,
            flow_label='Signup OTP',
        )
    except Exception as exc:
        from django.conf import settings as django_settings

        detail = 'Unable to send verification email. Please try again later.'
        if django_settings.DEBUG:
            detail = (
                f'{detail} (dev: check EMAIL_HOST_PASSWORD is a 16-char Gmail App Password '
                f'for {django_settings.EMAIL_HOST_USER})'
            )
        raise SignupOtpError(
            detail,
            code='email_send_failed',
            http_status=503,
        ) from exc


def _enforce_signup_otp_request_throttle(email):
    """
    Minimum interval between signup OTP emails for one address.

    Aligns with resend cooldown so initial request cannot bypass resend limits.
    """
    cfg = _otp_settings()
    last = (
        SignupOtpVerification.objects.filter(email=email)
        .order_by('-last_sent_at')
        .only('last_sent_at')
        .first()
    )
    if not last or not last.last_sent_at:
        return

    elapsed = (timezone.now() - last.last_sent_at).total_seconds()
    if elapsed < cfg['resend_cooldown_seconds']:
        wait = int(cfg['resend_cooldown_seconds'] - elapsed)
        raise SignupOtpError(
            f'Please wait {wait} seconds before requesting another code.',
            code='request_throttled',
            http_status=429,
        )


def _get_active_pending(email):
    """Latest non-verified, non-expired OTP row for this email."""
    now = timezone.now()
    return (
        SignupOtpVerification.objects.filter(
            email=email,
            verified_at__isnull=True,
            expires_at__gt=now,
        )
        .order_by('-created_at')
        .first()
    )


@transaction.atomic
def request_signup_otp(validated_data):
    """
    Validate signup fields, store pending payload, email OTP.

    Replaces any previous pending OTP for the same email.
    """
    email = _normalize_email(validated_data['email'])
    cfg = _otp_settings()

    _enforce_signup_otp_request_throttle(email)

    if User.objects.filter(email=email).exists():
        raise SignupOtpError(
            'Email already registered',
            code='email_already_registered',
            http_status=400,
        )

    SignupOtpVerification.objects.filter(
        email=email,
        verified_at__isnull=True,
    ).delete()

    otp_code = _generate_otp_code()
    now = timezone.now()
    record = SignupOtpVerification.objects.create(
        email=email,
        otp_hash=_hash_otp(email, otp_code),
        signup_payload=_build_signup_payload(validated_data),
        expires_at=now + timedelta(minutes=cfg['expiry_minutes']),
        last_sent_at=now,
    )

    _send_signup_otp_email(email, otp_code)

    return {
        'message': 'Verification code sent to your email.',
        'email': email,
        'expires_in_minutes': cfg['expiry_minutes'],
        'resend_cooldown_seconds': cfg['resend_cooldown_seconds'],
        'verification_id': record.id,
    }


@transaction.atomic
def resend_signup_otp(email):
    """Resend OTP for an existing pending signup (cooldown enforced)."""
    email = _normalize_email(email)
    cfg = _otp_settings()
    now = timezone.now()

    record = _get_active_pending(email)
    if record is None:
        raise SignupOtpError(
            'No active verification found. Please start signup again.',
            code='no_pending_signup',
            http_status=400,
        )

    if record.last_sent_at:
        elapsed = (now - record.last_sent_at).total_seconds()
        if elapsed < cfg['resend_cooldown_seconds']:
            wait = int(cfg['resend_cooldown_seconds'] - elapsed)
            raise SignupOtpError(
                f'Please wait {wait} seconds before requesting a new code.',
                code='resend_cooldown',
                http_status=429,
            )

    otp_code = _generate_otp_code()
    record.otp_hash = _hash_otp(email, otp_code)
    record.attempts = 0
    record.expires_at = now + timedelta(minutes=cfg['expiry_minutes'])
    record.last_sent_at = now
    record.save(
        update_fields=['otp_hash', 'attempts', 'expires_at', 'last_sent_at']
    )

    _send_signup_otp_email(email, otp_code)

    return {
        'message': 'A new verification code has been sent.',
        'email': email,
        'expires_in_minutes': cfg['expiry_minutes'],
        'resend_cooldown_seconds': cfg['resend_cooldown_seconds'],
    }


def verify_signup_otp(email, otp_code):
    """
    Verify OTP and create the user account.

    Returns the created User instance.
    """
    email = _normalize_email(email)
    otp_code = (otp_code or '').strip()
    cfg = _otp_settings()

    if not otp_code or len(otp_code) != OTP_LENGTH or not otp_code.isdigit():
        raise SignupOtpError(
            'Invalid verification code.',
            code='invalid_otp',
            http_status=400,
        )

    if User.objects.filter(email=email).exists():
        raise SignupOtpError(
            'Email already registered',
            code='email_already_registered',
            http_status=400,
        )

    record = (
        SignupOtpVerification.objects.filter(
            email=email,
            verified_at__isnull=True,
        )
        .order_by('-created_at')
        .first()
    )

    if record is None:
        raise SignupOtpError(
            'No active verification found. Please start signup again.',
            code='no_pending_signup',
            http_status=400,
        )

    now = timezone.now()
    if record.expires_at <= now:
        raise SignupOtpError(
            'Verification code has expired. Please request a new code.',
            code='otp_expired',
            http_status=400,
        )

    if record.attempts >= cfg['max_attempts']:
        raise SignupOtpError(
            'Too many failed attempts. Please request a new code.',
            code='too_many_attempts',
            http_status=400,
        )

    expected_hash = _hash_otp(email, otp_code)
    if not hmac.compare_digest(record.otp_hash, expected_hash):
        SignupOtpVerification.objects.filter(pk=record.pk).update(
            attempts=F('attempts') + 1,
        )
        record.refresh_from_db(fields=['attempts'])
        remaining = max(0, cfg['max_attempts'] - record.attempts)
        raise SignupOtpError(
            f'Invalid verification code. {remaining} attempt(s) remaining.',
            code='invalid_otp',
            http_status=400,
        )

    with transaction.atomic():
        locked = (
            SignupOtpVerification.objects.select_for_update()
            .filter(pk=record.pk, verified_at__isnull=True)
            .first()
        )
        if locked is None:
            raise SignupOtpError(
                'No active verification found. Please start signup again.',
                code='no_pending_signup',
                http_status=400,
            )
        if locked.expires_at <= timezone.now():
            raise SignupOtpError(
                'Verification code has expired. Please request a new code.',
                code='otp_expired',
                http_status=400,
            )

        user = _create_user_from_payload(locked.signup_payload)
        locked.verified_at = timezone.now()
        locked.save(update_fields=['verified_at'])

        SignupOtpVerification.objects.filter(
            email=email,
            verified_at__isnull=True,
        ).exclude(pk=locked.pk).delete()

    return user

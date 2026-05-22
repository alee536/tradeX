"""
Password reset via email OTP.

Flow: request OTP → verify OTP + set new password (Django hashed).
Security: generic responses (no email enumeration), HMAC OTP storage,
expiry, attempt limits, resend cooldown, invalidates prior pending resets.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import PasswordResetOtp, User
from apps.accounts.otp_email import send_otp_email

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
GENERIC_REQUEST_MESSAGE = (
    'If an account exists for this email, a verification code has been sent.'
)


class PasswordResetError(Exception):
    """Maps to API error payload for password reset endpoints."""

    def __init__(self, message, code='reset_error', http_status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


def _reset_settings():
    return {
        'expiry_minutes': int(
            getattr(settings, 'PASSWORD_RESET_OTP_EXPIRY_MINUTES', 15)
        ),
        'resend_cooldown_seconds': int(
            getattr(settings, 'PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS', 60)
        ),
        'max_attempts': int(
            getattr(settings, 'PASSWORD_RESET_OTP_MAX_ATTEMPTS', 5)
        ),
    }


def _normalize_email(email):
    return (email or '').strip().lower()


def _hash_reset_otp(email, otp_code):
    """HMAC hash; namespace separate from signup OTP."""
    key = settings.SECRET_KEY.encode('utf-8')
    msg = f'password_reset:{_normalize_email(email)}:{otp_code}'.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _generate_otp_code():
    return ''.join(str(secrets.randbelow(10)) for _ in range(OTP_LENGTH))


def _validate_new_password(password, user):
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise PasswordResetError(
            ' '.join(exc.messages),
            code='weak_password',
            http_status=400,
        ) from exc


def _send_reset_otp_email(email, otp_code):
    cfg = _reset_settings()
    body = (
        f'Your password reset code is: {otp_code}\n\n'
        f'This code expires in {cfg["expiry_minutes"]} minutes.\n'
        'If you did not request a password reset, ignore this email.\n\n'
        '— 24TRADEX'
    )
    try:
        send_otp_email(
            email,
            otp_code,
            '24TRADEX password reset code',
            body,
            flow_label='Password reset',
        )
    except Exception as exc:
        raise PasswordResetError(
            'Unable to send reset email. Please try again later.',
            code='email_send_failed',
            http_status=503,
        ) from exc


def _is_password_reset_request_throttled(email):
    """Per-email cooldown on initial reset requests (reduces email abuse)."""
    cfg = _reset_settings()
    last = (
        PasswordResetOtp.objects.filter(email=email)
        .order_by('-last_sent_at')
        .only('last_sent_at')
        .first()
    )
    if not last or not last.last_sent_at:
        return False
    elapsed = (timezone.now() - last.last_sent_at).total_seconds()
    return elapsed < cfg['resend_cooldown_seconds']


def _get_user_for_reset(email):
    """Active, non-banned users only."""
    return User.objects.filter(
        email=email,
        is_active=True,
        is_banned=False,
    ).first()


def _get_active_reset_record(email):
    now = timezone.now()
    return (
        PasswordResetOtp.objects.filter(
            email=email,
            used_at__isnull=True,
            expires_at__gt=now,
        )
        .select_related('user')
        .order_by('-created_at')
        .first()
    )


def _invalidate_pending_resets(email):
    """Mark all unused resets for this email as used (old token invalidation)."""
    now = timezone.now()
    PasswordResetOtp.objects.filter(
        email=email,
        used_at__isnull=True,
    ).update(used_at=now)


@transaction.atomic
def request_password_reset(email):
    """
    Send reset OTP if account exists.

    Always returns the same message (no email enumeration).
    """
    email = _normalize_email(email)
    user = _get_user_for_reset(email)

    if user is None:
        logger.info('Password reset requested for unknown/inactive email=%s', email)
        return {
            'message': GENERIC_REQUEST_MESSAGE,
            'email': email,
        }

    if _is_password_reset_request_throttled(email):
        logger.info('Password reset request throttled for email=%s', email)
        return {
            'message': GENERIC_REQUEST_MESSAGE,
            'email': email,
        }

    _invalidate_pending_resets(email)

    otp_code = _generate_otp_code()
    now = timezone.now()
    cfg = _reset_settings()

    PasswordResetOtp.objects.create(
        user=user,
        email=email,
        otp_hash=_hash_reset_otp(email, otp_code),
        expires_at=now + timedelta(minutes=cfg['expiry_minutes']),
        last_sent_at=now,
    )

    _send_reset_otp_email(email, otp_code)

    return {
        'message': GENERIC_REQUEST_MESSAGE,
        'email': email,
        'expires_in_minutes': cfg['expiry_minutes'],
        'resend_cooldown_seconds': cfg['resend_cooldown_seconds'],
    }


@transaction.atomic
def resend_password_reset_otp(email):
    """Resend OTP for active pending reset; enforces cooldown."""
    email = _normalize_email(email)
    cfg = _reset_settings()
    now = timezone.now()

    record = _get_active_reset_record(email)
    if record is None:
        # Same generic message — do not reveal whether email exists
        return {
            'message': GENERIC_REQUEST_MESSAGE,
            'email': email,
        }

    if record.last_sent_at:
        elapsed = (now - record.last_sent_at).total_seconds()
        if elapsed < cfg['resend_cooldown_seconds']:
            wait = int(cfg['resend_cooldown_seconds'] - elapsed)
            raise PasswordResetError(
                f'Please wait {wait} seconds before requesting a new code.',
                code='resend_cooldown',
                http_status=429,
            )

    otp_code = _generate_otp_code()
    record.otp_hash = _hash_reset_otp(email, otp_code)
    record.attempts = 0
    record.expires_at = now + timedelta(minutes=cfg['expiry_minutes'])
    record.last_sent_at = now
    record.save(
        update_fields=['otp_hash', 'attempts', 'expires_at', 'last_sent_at']
    )

    _send_reset_otp_email(email, otp_code)

    return {
        'message': GENERIC_REQUEST_MESSAGE,
        'email': email,
        'expires_in_minutes': cfg['expiry_minutes'],
        'resend_cooldown_seconds': cfg['resend_cooldown_seconds'],
    }


def confirm_password_reset(email, otp_code, new_password):
    """
    Verify OTP and set new password (Django password hashers).
    Invalidates all pending reset tokens for this email.
    """
    email = _normalize_email(email)
    otp_code = (otp_code or '').strip()
    cfg = _reset_settings()

    if not otp_code or len(otp_code) != OTP_LENGTH or not otp_code.isdigit():
        raise PasswordResetError(
            'Invalid verification code.',
            code='invalid_otp',
            http_status=400,
        )

    record = (
        PasswordResetOtp.objects.filter(
            email=email,
            used_at__isnull=True,
        )
        .select_related('user')
        .order_by('-created_at')
        .first()
    )

    if record is None:
        raise PasswordResetError(
            'No active reset request. Please start again.',
            code='no_pending_reset',
            http_status=400,
        )

    now = timezone.now()
    if record.expires_at <= now:
        raise PasswordResetError(
            'Reset code has expired. Please request a new code.',
            code='otp_expired',
            http_status=400,
        )

    if record.attempts >= cfg['max_attempts']:
        raise PasswordResetError(
            'Too many failed attempts. Please request a new code.',
            code='too_many_attempts',
            http_status=400,
        )

    expected = _hash_reset_otp(email, otp_code)
    if not hmac.compare_digest(record.otp_hash, expected):
        PasswordResetOtp.objects.filter(pk=record.pk).update(
            attempts=F('attempts') + 1,
        )
        record.refresh_from_db(fields=['attempts'])
        remaining = max(0, cfg['max_attempts'] - record.attempts)
        raise PasswordResetError(
            f'Invalid verification code. {remaining} attempt(s) remaining.',
            code='invalid_otp',
            http_status=400,
        )

    user = record.user
    if not user.is_active or user.is_banned:
        raise PasswordResetError(
            'This account cannot reset its password.',
            code='account_disabled',
            http_status=403,
        )

    _validate_new_password(new_password, user)

    with transaction.atomic():
        locked = (
            PasswordResetOtp.objects.select_for_update()
            .filter(pk=record.pk, used_at__isnull=True)
            .first()
        )
        if locked is None:
            raise PasswordResetError(
                'Reset code already used. Please request a new code.',
                code='otp_already_used',
                http_status=400,
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        used_time = timezone.now()
        locked.used_at = used_time
        locked.save(update_fields=['used_at'])

        # Invalidate any other pending resets for this account
        PasswordResetOtp.objects.filter(
            email=email,
            used_at__isnull=True,
        ).exclude(pk=locked.pk).update(used_at=used_time)

    logger.info('Password reset completed for user_id=%s', user.id)
    return {
        'message': 'Password updated successfully. You can sign in now.',
        'email': email,
    }

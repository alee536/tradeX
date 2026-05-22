"""
============== Sponsor link access service ==============

Business rules:
    1. One-time fee (default 5 USDT, configurable in SystemSettings).
    2. User submits request from Sponsor tab with payment proof + desired ref slug.
    3. Admin approves or rejects.
    4. On approval, sponsor link is active for lifetime (user.sponsor_access_status=active).
    5. Users with active access or pending request cannot submit again.
"""

import re
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.utils import create_notification
from apps.settings_app.models import SystemSettings

from .models import SponsorAccessRequest


class SponsorAccessError(Exception):
    """Raised when sponsor access actions are invalid."""


REF_SLUG_RE = re.compile(r'^[A-Za-z0-9]{4,20}$')


def normalize_ref_slug(value):
    return (value or '').strip().upper()


def get_sponsor_payment_wallet():
    """Platform wallet for sponsor access fee (separate from coin purchase wallet)."""
    return getattr(
        settings,
        'SPONSOR_PAYMENT_WALLET_ADDRESS',
        '',
    ).strip()


def get_sponsor_access_fee():
    settings_obj = SystemSettings.get_settings()
    fee = getattr(settings_obj, 'sponsor_access_fee_usdt', None)
    if fee is None:
        return Decimal('5')
    return Decimal(str(fee))


def user_can_request_sponsor_access(user):
    """Return (allowed: bool, reason: str)."""
    if user.sponsor_access_status == User.SPONSOR_ACCESS_ACTIVE:
        return False, 'You already have an active sponsor link.'
    if user.sponsor_access_status == User.SPONSOR_ACCESS_PENDING:
        return False, 'You already have a pending sponsor access request.'
    if SponsorAccessRequest.objects.filter(
        user=user,
        status=SponsorAccessRequest.STATUS_PENDING,
    ).exists():
        return False, 'You already have a pending sponsor access request.'
    return True, ''


def validate_ref_slug(ref_slug, exclude_user_id=None):
    slug = normalize_ref_slug(ref_slug)
    if not REF_SLUG_RE.match(slug):
        raise SponsorAccessError(
            'Referral code must be 4–20 letters or numbers (e.g. ALEE24).'
        )
    qs = User.objects.filter(sponsor_ref_slug__iexact=slug)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    if qs.exists():
        raise SponsorAccessError('This referral code is already taken.')
    pending = SponsorAccessRequest.objects.filter(
        ref_slug__iexact=slug,
        status=SponsorAccessRequest.STATUS_PENDING,
    )
    if exclude_user_id:
        pending = pending.exclude(user_id=exclude_user_id)
    if pending.exists():
        raise SponsorAccessError('This referral code is pending approval.')
    return slug


def build_public_sponsor_link(user):
    path = user.sponsor_public_path
    if not path:
        return None
    base = getattr(settings, 'SPONSOR_REF_BASE_URL', settings.SITE_URL).rstrip('/')
    return f"{base}{path}"


def serialize_access_status(user):
    """Payload for sponsor tab / profile."""
    fee = get_sponsor_access_fee()
    pending_request = (
        SponsorAccessRequest.objects.filter(
            user=user,
            status=SponsorAccessRequest.STATUS_PENDING,
        )
        .order_by('-created_at')
        .first()
    )
    return {
        'sponsor_access_status': user.sponsor_access_status,
        'sponsor_payment_status': user.sponsor_payment_status,
        'sponsor_activated_at': (
            user.sponsor_activated_at.isoformat() if user.sponsor_activated_at else None
        ),
        'sponsor_ref_slug': user.sponsor_ref_slug,
        'sponsor_code': user.sponsor_code,
        'sponsor_link': build_public_sponsor_link(user),
        'sponsor_public_path': user.sponsor_public_path,
        'access_fee_usdt': float(fee),
        'sponsor_payment_wallet': get_sponsor_payment_wallet(),
        'can_request': user_can_request_sponsor_access(user)[0],
        'pending_request': _serialize_request(pending_request) if pending_request else None,
    }


def _serialize_request(req):
    if req is None:
        return None
    return {
        'id': req.id,
        'status': req.status,
        'payment_status': req.payment_status,
        'fee_usdt': float(req.fee_usdt),
        'ref_slug': req.ref_slug,
        'payment_txid': req.payment_txid,
        'payment_wallet': req.payment_wallet,
        'rejection_reason': req.rejection_reason,
        'created_at': req.created_at.isoformat() if req.created_at else None,
        'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
        'activated_at': req.activated_at.isoformat() if req.activated_at else None,
    }


@transaction.atomic
def create_sponsor_access_request(user, ref_slug, payment_txid, payment_wallet):
    allowed, reason = user_can_request_sponsor_access(user)
    if not allowed:
        raise SponsorAccessError(reason)

    slug = validate_ref_slug(ref_slug)
    txid = (payment_txid or '').strip()
    wallet = (payment_wallet or '').strip()
    if not txid:
        raise SponsorAccessError('Payment transaction ID is required.')
    if not wallet:
        raise SponsorAccessError('Payment wallet address is required.')

    fee = get_sponsor_access_fee()
    req = SponsorAccessRequest.objects.create(
        user=user,
        status=SponsorAccessRequest.STATUS_PENDING,
        payment_status=SponsorAccessRequest.PAYMENT_PENDING,
        fee_usdt=fee,
        ref_slug=slug,
        payment_txid=txid,
        payment_wallet=wallet,
    )

    user.sponsor_access_status = User.SPONSOR_ACCESS_PENDING
    user.sponsor_payment_status = User.SPONSOR_PAYMENT_PENDING
    user.save(update_fields=['sponsor_access_status', 'sponsor_payment_status'])

    create_notification(
        user,
        'sponsor_request_submitted',
        (
            f'Your sponsor link request ({slug}) was submitted. '
            f'Fee: {fee} USDT. Waiting for admin approval.'
        ),
    )
    return req


@transaction.atomic
def approve_sponsor_access_request(request_obj, reviewer=None):
    if request_obj.status != SponsorAccessRequest.STATUS_PENDING:
        raise SponsorAccessError('Only pending requests can be approved.')

    user = request_obj.user
    slug = validate_ref_slug(request_obj.ref_slug, exclude_user_id=user.id)
    now = timezone.now()

    request_obj.status = SponsorAccessRequest.STATUS_APPROVED
    request_obj.payment_status = SponsorAccessRequest.PAYMENT_PAID
    request_obj.reviewed_at = now
    request_obj.activated_at = now
    request_obj.rejection_reason = None
    request_obj.save(update_fields=[
        'status', 'payment_status', 'reviewed_at', 'activated_at', 'rejection_reason',
    ])

    user.sponsor_access_status = User.SPONSOR_ACCESS_ACTIVE
    user.sponsor_payment_status = User.SPONSOR_PAYMENT_PAID
    user.sponsor_ref_slug = slug
    user.sponsor_activated_at = now
    user.save(update_fields=[
        'sponsor_access_status',
        'sponsor_payment_status',
        'sponsor_ref_slug',
        'sponsor_activated_at',
    ])

    link = build_public_sponsor_link(user)
    create_notification(
        user,
        'sponsor_request_approved',
        f'Your sponsor link is now active for lifetime: {link or slug}',
    )
    return request_obj


@transaction.atomic
def reject_sponsor_access_request(request_obj, reason):
    if request_obj.status != SponsorAccessRequest.STATUS_PENDING:
        raise SponsorAccessError('Only pending requests can be rejected.')

    reason = (reason or '').strip() or 'Rejected by admin.'
    now = timezone.now()
    user = request_obj.user

    request_obj.status = SponsorAccessRequest.STATUS_REJECTED
    request_obj.reviewed_at = now
    request_obj.rejection_reason = reason
    request_obj.save(update_fields=['status', 'reviewed_at', 'rejection_reason'])

    user.sponsor_access_status = User.SPONSOR_ACCESS_REJECTED
    user.sponsor_payment_status = User.SPONSOR_PAYMENT_NONE
    user.save(update_fields=['sponsor_access_status', 'sponsor_payment_status'])

    create_notification(
        user,
        'sponsor_request_rejected',
        f'Your sponsor link request was rejected. Reason: {reason}',
    )
    return request_obj


def resolve_active_sponsor_by_ref(ref_slug):
    """Public lookup for registration via /ref/SLUG."""
    slug = normalize_ref_slug(ref_slug)
    if not slug:
        return None
    return User.objects.filter(
        sponsor_ref_slug__iexact=slug,
        sponsor_access_status=User.SPONSOR_ACCESS_ACTIVE,
    ).first()

"""
============== Purchase Claim Service ==============

Encapsulates the per-purchase staged claim/withdrawal logic.

Business rules:
    1. Timer for Stage 1 starts at purchase approval (coins assignment).
    2. Stage 1 unlocks after `stage1_hours` (default 72h).
    3. Stage N (N>1) unlocks after `stageN_hours` measured from the time
       Stage N-1 was approved by an admin.
    4. Stage percentages come from `SystemSettings` (normalized to 100).
    5. A new claim can only be created if no pending/approved claim already
       exists for that stage.

All timestamps are stored in the database; the frontend only renders the
schedule returned by the API.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.notifications.utils import create_notification


class ClaimError(Exception):
    """Raised when a claim action cannot be processed."""


# ============== Helpers ==============

def _stage_hours(settings_obj, stage):
    if stage == 1:
        return int(settings_obj.stage1_hours or 0)
    if stage == 2:
        return int(settings_obj.stage2_hours or 0)
    if stage == 3:
        return int(settings_obj.stage3_hours or 0)
    return 0


def _normalized_percentages(settings_obj):
    """Stage percentages from settings, normalized to 100."""
    s1 = Decimal(str(settings_obj.stage1_percent or 0))
    s2 = Decimal(str(settings_obj.stage2_percent or 0))
    s3 = Decimal(str(settings_obj.stage3_percent or 0))
    total = s1 + s2 + s3
    if total <= 0:
        return Decimal('50'), Decimal('25'), Decimal('25')
    if total != Decimal('100'):
        scale = Decimal('100') / total
        s1 = (s1 * scale).quantize(Decimal('0.01'))
        s2 = (s2 * scale).quantize(Decimal('0.01'))
        s3 = Decimal('100') - s1 - s2
    return s1, s2, s3


def _purchase_total_coins(purchase):
    if purchase.approved_coin_amount is not None:
        return Decimal(str(purchase.approved_coin_amount))
    return Decimal(str(purchase.calculated_coins or 0))


def _purchase_total_usdt(purchase):
    return Decimal(str(purchase.amount or 0))


def _stage_amounts(total_coins, total_usdt, percentages):
    s1, s2, s3 = percentages
    coins1 = (total_coins * s1 / Decimal('100')).quantize(Decimal('0.00000001'))
    coins2 = (total_coins * s2 / Decimal('100')).quantize(Decimal('0.00000001'))
    coins3 = (total_coins - coins1 - coins2).quantize(Decimal('0.00000001'))
    usdt1 = (total_usdt * s1 / Decimal('100')).quantize(Decimal('0.00000001'))
    usdt2 = (total_usdt * s2 / Decimal('100')).quantize(Decimal('0.00000001'))
    usdt3 = (total_usdt - usdt1 - usdt2).quantize(Decimal('0.00000001'))
    return (
        (coins1, usdt1),
        (coins2, usdt2),
        (coins3, usdt3),
    )


def _purchase_reference_time(purchase):
    return purchase.coins_assigned_at or purchase.approved_at


# ============== Schedule computation ==============

def _build_stage_state(stage, percent, coins, usdt, unlock_at, claim, now):
    """Return one stage payload for the frontend."""
    seconds_until_unlock = None
    state = 'locked'
    can_request = False

    if claim is None:
        if unlock_at is None:
            seconds_until_unlock = None
        elif now >= unlock_at:
            state = 'available'
            can_request = True
            seconds_until_unlock = 0
        else:
            seconds_until_unlock = int((unlock_at - now).total_seconds())
    else:
        state = claim.status
        if state == 'rejected':
            # User can resubmit after rejection.
            can_request = True

    return {
        'stage': stage,
        'percent': float(percent),
        'amount_coins': float(coins),
        'amount_usdt': float(usdt),
        'state': state,
        'can_request': can_request,
        'unlock_at': unlock_at.isoformat() if unlock_at else None,
        'seconds_until_unlock': seconds_until_unlock,
        'claim': _serialize_claim(claim) if claim else None,
    }


def _serialize_claim(claim):
    return {
        'id': claim.id,
        'status': claim.status,
        'amount_coins': float(claim.amount_coins or 0),
        'amount_usdt_snapshot': float(claim.amount_usdt_snapshot or 0),
        'wallet_address': claim.wallet_address,
        'manual_tx_hash': claim.manual_tx_hash,
        'rejection_reason': claim.rejection_reason,
        'created_at': claim.created_at.isoformat() if claim.created_at else None,
        'approved_at': claim.approved_at.isoformat() if claim.approved_at else None,
        'rejected_at': claim.rejected_at.isoformat() if claim.rejected_at else None,
    }


def get_purchase_schedule(purchase, settings_obj=None):
    """Return the 3-stage claim schedule for a single purchase."""
    from apps.settings_app.models import SystemSettings
    from .models import PurchaseClaim

    settings_obj = settings_obj or SystemSettings.get_settings()
    now = timezone.now()
    ref = _purchase_reference_time(purchase)
    percentages = _normalized_percentages(settings_obj)
    total_coins = _purchase_total_coins(purchase)
    total_usdt = _purchase_total_usdt(purchase)
    stage_amounts = _stage_amounts(total_coins, total_usdt, percentages)

    claims_qs = PurchaseClaim.objects.filter(purchase=purchase)
    # Use the latest claim per stage (so resubmits after rejection are reflected).
    latest_by_stage = {}
    for claim in claims_qs.order_by('-created_at'):
        latest_by_stage.setdefault(claim.stage, claim)

    stages_payload = []
    previous_unlocked_at = None
    for index, stage_no in enumerate((1, 2, 3), start=0):
        coins, usdt = stage_amounts[index]
        percent = percentages[index]
        claim = latest_by_stage.get(stage_no)
        stage_hours = _stage_hours(settings_obj, stage_no)

        if stage_no == 1:
            unlock_at = ref + timedelta(hours=stage_hours) if ref else None
        else:
            prev_claim = latest_by_stage.get(stage_no - 1)
            if prev_claim and prev_claim.status == 'approved' and prev_claim.approved_at:
                unlock_at = prev_claim.approved_at + timedelta(hours=stage_hours)
            else:
                unlock_at = None

        previous_unlocked_at = unlock_at
        stages_payload.append(
            _build_stage_state(stage_no, percent, coins, usdt, unlock_at, claim, now)
        )

    return {
        'purchase_id': purchase.id,
        'transaction_id': purchase.transaction_id,
        'reference_time': ref.isoformat() if ref else None,
        'total_coins': float(total_coins),
        'total_usdt': float(total_usdt),
        'stages': stages_payload,
    }


def get_user_claim_schedule(user):
    """Return claim schedule for all eligible purchases of a user."""
    from apps.purchases.models import Purchase
    from apps.settings_app.models import SystemSettings

    settings_obj = SystemSettings.get_settings()
    purchases = (
        Purchase.objects.filter(user=user, status='approved', is_coins_assigned=True)
        .only('id', 'transaction_id', 'amount', 'approved_at', 'coins_assigned_at',
              'approved_coin_amount', 'coin_rate_at_approval')
        .order_by('-approved_at')
    )
    return [get_purchase_schedule(p, settings_obj) for p in purchases]


# ============== Claim mutations ==============

def _stage_amount_for(purchase, stage, settings_obj):
    percentages = _normalized_percentages(settings_obj)
    total_coins = _purchase_total_coins(purchase)
    total_usdt = _purchase_total_usdt(purchase)
    stage_amounts = _stage_amounts(total_coins, total_usdt, percentages)
    coins, usdt = stage_amounts[stage - 1]
    return coins, usdt


def _validate_stage_ready(purchase, stage, settings_obj):
    from .models import PurchaseClaim

    if stage not in (1, 2, 3):
        raise ClaimError('Invalid stage. Must be 1, 2, or 3.')

    if purchase.status != 'approved' or not purchase.is_coins_assigned:
        raise ClaimError('Purchase is not approved or coins are not assigned yet.')

    active_claim = PurchaseClaim.objects.filter(
        purchase=purchase,
        stage=stage,
        status__in=('pending', 'approved'),
    ).first()
    if active_claim:
        raise ClaimError(
            f'Stage {stage} already has a {active_claim.status} claim.'
        )

    now = timezone.now()
    if stage == 1:
        ref = _purchase_reference_time(purchase)
        if not ref:
            raise ClaimError('Purchase reference time is missing.')
        unlock_at = ref + timedelta(hours=_stage_hours(settings_obj, 1))
        if now < unlock_at:
            raise ClaimError(
                f'Stage 1 unlocks at {unlock_at.isoformat()}.'
            )
        return

    previous = (
        PurchaseClaim.objects.filter(purchase=purchase, stage=stage - 1)
        .order_by('-created_at')
        .first()
    )
    if not previous or previous.status != 'approved':
        raise ClaimError(f'Stage {stage - 1} must be approved by admin first.')

    if not previous.approved_at:
        raise ClaimError(f'Stage {stage - 1} is missing an approval timestamp.')

    unlock_at = previous.approved_at + timedelta(hours=_stage_hours(settings_obj, stage))
    if now < unlock_at:
        raise ClaimError(
            f'Stage {stage} unlocks at {unlock_at.isoformat()}.'
        )


@transaction.atomic
def create_claim(user, purchase, stage, wallet_address):
    """User-side action: submit a claim request for one stage."""
    from apps.settings_app.models import SystemSettings
    from .models import PurchaseClaim

    if purchase.user_id != user.id:
        raise ClaimError('Purchase does not belong to the user.')

    wallet_address = (wallet_address or '').strip()
    if not wallet_address:
        raise ClaimError('Wallet address is required.')

    settings_obj = SystemSettings.get_settings()
    _validate_stage_ready(purchase, stage, settings_obj)

    coins, usdt = _stage_amount_for(purchase, stage, settings_obj)
    if coins <= 0:
        raise ClaimError('Stage amount must be greater than zero.')

    claim = PurchaseClaim.objects.create(
        purchase=purchase,
        user=user,
        stage=stage,
        status='pending',
        amount_coins=coins,
        amount_usdt_snapshot=usdt,
        coin_rate_snapshot=Decimal(str(settings_obj.coin_rate or 0)),
        wallet_address=wallet_address,
    )

    create_notification(
        user,
        'claim_submitted',
        (
            f'Claim Stage {stage} ({coins} coins) for purchase '
            f'{purchase.transaction_id} has been submitted for admin review.'
        ),
    )
    return claim


@transaction.atomic
def approve_claim(claim, manual_tx_hash):
    """Admin-side action: approve a pending claim."""
    if claim.status != 'pending':
        raise ClaimError('Only pending claims can be approved.')

    tx = (manual_tx_hash or '').strip()
    if not tx:
        raise ClaimError('Manual transaction hash is required.')

    claim.status = 'approved'
    claim.manual_tx_hash = tx
    claim.approved_at = timezone.now()
    claim.rejected_at = None
    claim.rejection_reason = None
    claim.save(update_fields=[
        'status', 'manual_tx_hash', 'approved_at',
        'rejected_at', 'rejection_reason',
    ])

    create_notification(
        claim.user,
        'claim_approved',
        (
            f'Stage {claim.stage} claim of {claim.amount_coins} coins for purchase '
            f'{claim.purchase.transaction_id} has been approved. '
            f'Next stage timer has started.'
        ),
    )
    return claim


@transaction.atomic
def reject_claim(claim, reason):
    """Admin-side action: reject a pending claim."""
    if claim.status != 'pending':
        raise ClaimError('Only pending claims can be rejected.')

    reason = (reason or '').strip() or 'Rejected by admin.'
    claim.status = 'rejected'
    claim.rejection_reason = reason
    claim.rejected_at = timezone.now()
    claim.save(update_fields=['status', 'rejection_reason', 'rejected_at'])

    create_notification(
        claim.user,
        'claim_rejected',
        (
            f'Stage {claim.stage} claim for purchase '
            f'{claim.purchase.transaction_id} has been rejected. Reason: {reason}'
        ),
    )
    return claim


def total_claimed_coins(user):
    """Sum of pending + approved claim amounts (counted against balance)."""
    from .models import PurchaseClaim
    from django.db.models import Sum

    total = PurchaseClaim.objects.filter(
        user=user,
        status__in=('pending', 'approved'),
    ).aggregate(total=Sum('amount_coins'))['total']
    return float(total or 0)

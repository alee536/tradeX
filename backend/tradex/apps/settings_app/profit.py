from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.notifications.utils import create_notification


class ProfitClaimError(Exception):
    """Raised when a profit claim cannot be processed."""


def _purchase_reference_time(purchase):
    return purchase.coins_assigned_at or purchase.approved_at


def _assigned_purchases_qs(user):
    from apps.purchases.models import Purchase

    return Purchase.objects.filter(
        user=user,
        status='approved',
        is_coins_assigned=True,
    ).only('amount', 'approved_at', 'coins_assigned_at')


def _sum_base_usdt(purchases):
    base_usdt = Decimal('0')
    for purchase in purchases:
        base_usdt += Decimal(str(purchase.amount or 0))
    return base_usdt


def _first_claim_due_at(purchases, cycle):
    """Earliest time the user becomes eligible for the first profit claim."""
    first_due = None
    for purchase in purchases:
        ref = _purchase_reference_time(purchase)
        if not ref:
            continue
        candidate = ref + cycle
        if first_due is None or candidate < first_due:
            first_due = candidate
    return first_due


def _can_claim_now(user, purchases, cycle_hours, now):
    cycle = timedelta(hours=cycle_hours)
    if not purchases:
        return False
    last_claim = _last_profit_claim_at(user)
    if last_claim:
        return now >= last_claim + cycle
    first_due = _first_claim_due_at(purchases, cycle)
    return bool(first_due and now >= first_due)


def _next_claim_deadline(user, purchases, cycle_hours):
    """Next claim window (countdown target)."""
    cycle = timedelta(hours=cycle_hours)
    last_claim = _last_profit_claim_at(user)
    if last_claim:
        return last_claim + cycle
    return _first_claim_due_at(purchases, cycle)


def _last_profit_claim_at(user):
    from .models import ProfitClaim

    return (
        ProfitClaim.objects.filter(user=user)
        .order_by('-claimed_at')
        .values_list('claimed_at', flat=True)
        .first()
    )


def get_profit_bonus_coins(user):
    """Total bonus coins credited from profit claims (withdrawable)."""
    from .models import ProfitClaim

    total = ProfitClaim.objects.filter(user=user).aggregate(
        total=Sum('amount_coins'),
    )['total']
    return float(total or 0)


def _profit_claim_totals(user):
    from .models import ProfitClaim

    agg = ProfitClaim.objects.filter(user=user).aggregate(
        usdt=Sum('amount_usdt'),
        coins=Sum('amount_coins'),
    )
    return {
        'total_claimed_usdt': float(agg['usdt'] or 0),
        'total_claimed_coins': float(agg['coins'] or 0),
    }


def compute_user_profit_summary(user, settings_obj):
    """
    Profit on assigned approved purchase USDT totals, one reward per cycle.
    Includes claim readiness and lifetime claimed totals.
    """
    try:
        if not settings_obj.profit_enabled:
            return {'enabled': False}
    except Exception:
        return {'enabled': False}

    pct = Decimal(str(settings_obj.profit_percentage or 0))
    cycle_hours = int(settings_obj.profit_cycle_hours or 72)
    totals = _profit_claim_totals(user)

    if pct <= 0 or cycle_hours <= 0:
        return {
            'enabled': True,
            'profit_percentage': float(pct),
            'profit_cycle_hours': cycle_hours,
            'base_usdt': 0.0,
            'estimated_profit_usdt': 0.0,
            'total_after_profit_usdt': 0.0,
            'claimable_usdt': 0.0,
            'claimable_coins': 0.0,
            'can_claim': False,
            'next_claim_at': None,
            'seconds_until_claim': None,
            **totals,
        }

    purchases = list(_assigned_purchases_qs(user))
    base_usdt = _sum_base_usdt(purchases)
    now = timezone.now()
    next_claim_at = _next_claim_deadline(user, purchases, cycle_hours)

    estimated_profit = (base_usdt * pct / Decimal('100')).quantize(Decimal('0.00000001'))
    total_after = (base_usdt + estimated_profit).quantize(Decimal('0.00000001'))

    can_claim = bool(base_usdt > 0 and _can_claim_now(user, purchases, cycle_hours, now))
    seconds_until = None
    next_claim_iso = None
    if next_claim_at:
        next_claim_iso = next_claim_at.isoformat()
        if not can_claim:
            seconds_until = max(0, int((next_claim_at - now).total_seconds()))

    claimable_usdt = float(estimated_profit) if can_claim else 0.0
    claimable_coins = 0.0
    if can_claim:
        rate = Decimal(str(settings_obj.coin_rate or 0))
        if rate > 0:
            claimable_coins = float(
                (estimated_profit / rate).quantize(Decimal('0.00000001'))
            )

    return {
        'enabled': True,
        'profit_percentage': float(pct),
        'profit_cycle_hours': cycle_hours,
        'base_usdt': float(base_usdt),
        'estimated_profit_usdt': float(estimated_profit),
        'total_after_profit_usdt': float(total_after),
        'claimable_usdt': claimable_usdt,
        'claimable_coins': claimable_coins,
        'can_claim': can_claim,
        'next_claim_at': next_claim_iso,
        'seconds_until_claim': seconds_until,
        **totals,
    }


@transaction.atomic
def execute_profit_claim(user):
    """
    Credit one profit cycle to the user ledger and return updated summary.
    """
    from apps.accounts.models import User
    from .models import ProfitClaim, SystemSettings

    User.objects.select_for_update().get(pk=user.pk)
    settings_obj = SystemSettings.get_settings()
    summary = compute_user_profit_summary(user, settings_obj)

    if not summary.get('enabled'):
        raise ProfitClaimError('Profit system is disabled.')

    if not summary.get('can_claim'):
        raise ProfitClaimError('Reward is not ready to claim yet.')

    claim_usdt = Decimal(str(summary['claimable_usdt']))
    if claim_usdt <= 0:
        raise ProfitClaimError('No claimable profit amount.')

    rate = Decimal(str(settings_obj.coin_rate or 0))
    if rate <= 0:
        raise ProfitClaimError('Coin rate is not configured.')

    claim_coins = (claim_usdt / rate).quantize(Decimal('0.00000001'))
    pct = Decimal(str(settings_obj.profit_percentage))
    cycle_hours = int(settings_obj.profit_cycle_hours)

    purchases = list(_assigned_purchases_qs(user))
    base_usdt = _sum_base_usdt(purchases)

    ProfitClaim.objects.create(
        user=user,
        amount_usdt=claim_usdt,
        amount_coins=claim_coins,
        profit_percentage=pct,
        profit_cycle_hours=cycle_hours,
        base_usdt_snapshot=base_usdt,
    )

    create_notification(
        user,
        'profit_claimed',
        (
            f'Profit reward claimed: +{claim_usdt} USDT '
            f'({claim_coins} coins) at {pct}% on your assigned purchases.'
        ),
    )

    return compute_user_profit_summary(user, settings_obj)

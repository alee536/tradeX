from datetime import timedelta
from decimal import Decimal

from django.utils import timezone


def _purchase_reference_time(purchase):
    return purchase.coins_assigned_at or purchase.approved_at


def compute_user_profit_summary(user, settings_obj):
    """
    Profit on assigned approved purchase USDT totals, paid each profit_cycle_hours.
    """
    from apps.purchases.models import Purchase

    try:
        if not settings_obj.profit_enabled:
            return {'enabled': False}
    except Exception:
        return {'enabled': False}

    pct = Decimal(str(settings_obj.profit_percentage or 0))
    cycle_hours = int(settings_obj.profit_cycle_hours or 72)
    if pct <= 0 or cycle_hours <= 0:
        return {
            'enabled': True,
            'profit_percentage': float(pct),
            'profit_cycle_hours': cycle_hours,
            'base_usdt': 0.0,
            'estimated_profit_usdt': 0.0,
            'total_after_profit_usdt': 0.0,
            'next_claim_at': None,
            'seconds_until_claim': None,
        }

    purchases = Purchase.objects.filter(
        user=user,
        status='approved',
        is_coins_assigned=True,
    ).only('amount', 'approved_at', 'coins_assigned_at')

    base_usdt = Decimal('0')
    next_claim_at = None
    now = timezone.now()
    cycle = timedelta(hours=cycle_hours)

    for purchase in purchases:
        base_usdt += Decimal(str(purchase.amount or 0))
        ref = _purchase_reference_time(purchase)
        if not ref:
            continue
        elapsed = now - ref
        if elapsed < cycle:
            candidate = ref + cycle
        else:
            cycles = int(elapsed.total_seconds() // cycle.total_seconds())
            candidate = ref + cycle * (cycles + 1)
        if next_claim_at is None or candidate < next_claim_at:
            next_claim_at = candidate

    estimated_profit = (base_usdt * pct / Decimal('100')).quantize(Decimal('0.00000001'))
    total_after = (base_usdt + estimated_profit).quantize(Decimal('0.00000001'))

    seconds_until = None
    next_claim_iso = None
    if next_claim_at:
        next_claim_iso = next_claim_at.isoformat()
        seconds_until = max(0, int((next_claim_at - now).total_seconds()))

    return {
        'enabled': True,
        'profit_percentage': float(pct),
        'profit_cycle_hours': cycle_hours,
        'base_usdt': float(base_usdt),
        'estimated_profit_usdt': float(estimated_profit),
        'total_after_profit_usdt': float(total_after),
        'next_claim_at': next_claim_iso,
        'seconds_until_claim': seconds_until,
    }

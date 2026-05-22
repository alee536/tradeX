from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .purchase_totals import purchase_base_usdt, purchase_totals_with_profit, profit_percentage_value


class ProfitClaimError(Exception):
    """Raised when a profit claim cannot be processed."""


def _assigned_purchases_qs(user):
    from apps.purchases.models import Purchase

    return Purchase.objects.filter(
        user=user,
        status='approved',
        is_coins_assigned=True,
    ).only(
        'amount', 'approved_at', 'coins_assigned_at',
        'approved_coin_amount', 'coin_rate_at_approval',
    )


def _sum_base_usdt(purchases):
    base_usdt = Decimal('0')
    for purchase in purchases:
        base_usdt += purchase_base_usdt(purchase)
    return base_usdt


def get_profit_bonus_coins(user):
    """Legacy profit-claim ledger; staged claims are the primary payout path."""
    from .models import ProfitClaim

    total = ProfitClaim.objects.filter(user=user).aggregate(
        total=Sum('amount_coins'),
    )['total']
    return float(total or 0)


def _staged_claim_totals(user):
    from apps.withdrawals.models import PurchaseClaim

    agg = PurchaseClaim.objects.filter(user=user, status='approved').aggregate(
        usdt=Sum('amount_usdt_snapshot'),
        coins=Sum('amount_coins'),
    )
    return {
        'total_claimed_usdt': float(agg['usdt'] or 0),
        'total_claimed_coins': float(agg['coins'] or 0),
    }


def compute_user_profit_summary(user, settings_obj):
    """
    Display: deposit + admin profit% = total claimable via 50/25/25 staged claims.
    Payouts happen on Withdraw (auto-approved claims), not a separate profit button.
    """
    try:
        if not settings_obj.profit_enabled:
            return {'enabled': False}
    except Exception:
        return {'enabled': False}

    pct = profit_percentage_value(settings_obj)
    purchases = list(_assigned_purchases_qs(user))
    purchase_count = len(purchases)
    base_usdt = _sum_base_usdt(purchases)

    estimated_profit = Decimal('0')
    total_after = Decimal('0')
    for purchase in purchases:
        totals = purchase_totals_with_profit(purchase, settings_obj)
        estimated_profit += totals['profit_usdt']
        total_after += totals['total_usdt']

    estimated_profit = estimated_profit.quantize(Decimal('0.00000001'))
    total_after = total_after.quantize(Decimal('0.00000001'))
    staged = _staged_claim_totals(user)

    return {
        'enabled': True,
        'profit_percentage': float(pct),
        'profit_cycle_hours': int(settings_obj.stage1_hours or 72),
        'purchase_count': purchase_count,
        'base_usdt': float(base_usdt),
        'estimated_profit_usdt': float(estimated_profit),
        'total_after_profit_usdt': float(total_after),
        'claimable_usdt': 0.0,
        'claimable_coins': 0.0,
        'can_claim': False,
        'claim_via_stages': True,
        'next_claim_at': None,
        'seconds_until_claim': None,
        'stage1_hours': int(settings_obj.stage1_hours or 72),
        'stage2_hours': int(settings_obj.stage2_hours or 24),
        'stage3_hours': int(settings_obj.stage3_hours or 24),
        **staged,
    }


@transaction.atomic
def execute_profit_claim(user):
    """Profit is paid through per-purchase staged claims (Withdraw page), not here."""
    raise ProfitClaimError(
        'Profit is included in your purchase total and paid via staged claims on the '
        'Withdraw page (50% after 72h, then 25% + 25%). No separate profit claim is needed.',
    )

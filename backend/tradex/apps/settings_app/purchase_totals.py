"""Purchase amounts including admin profit % (deposit + profit = claimable total)."""

from decimal import Decimal


def profit_multiplier(settings_obj):
    """1.10 for 10% profit when enabled; else 1."""
    try:
        if not settings_obj.profit_enabled:
            return Decimal('1')
    except Exception:
        return Decimal('1')
    pct = Decimal(str(settings_obj.profit_percentage or 0))
    if pct <= 0:
        return Decimal('1')
    return (Decimal('1') + pct / Decimal('100')).quantize(Decimal('0.0000000001'))


def profit_percentage_value(settings_obj):
    mult = profit_multiplier(settings_obj)
    if mult <= Decimal('1'):
        return Decimal('0')
    return ((mult - Decimal('1')) * Decimal('100')).quantize(Decimal('0.01'))


def purchase_base_usdt(purchase):
    return Decimal(str(purchase.amount or 0))


def purchase_base_coins(purchase, settings_obj=None):
    """Base coins for profit math; works as soon as purchase is approved (before assign)."""
    if purchase.approved_coin_amount is not None:
        return Decimal(str(purchase.approved_coin_amount))
    rate = purchase.coin_rate_at_approval
    if rate and Decimal(str(rate)) > 0:
        return (Decimal(str(purchase.amount or 0)) / Decimal(str(rate))).quantize(
            Decimal('0.00000001'),
        )
    if settings_obj is not None:
        fallback_rate = Decimal(str(settings_obj.coin_rate or 0))
        if fallback_rate > 0:
            return (Decimal(str(purchase.amount or 0)) / fallback_rate).quantize(
                Decimal('0.00000001'),
            )
    return Decimal('0')


def purchase_totals_with_profit(purchase, settings_obj):
    """
    base + profit% = total used for 50/25/25 staged claims.
    Example: 100 USDT deposit, 10% -> 110 total.
    """
    base_usdt = purchase_base_usdt(purchase)
    base_coins = purchase_base_coins(purchase, settings_obj)
    mult = profit_multiplier(settings_obj)
    total_usdt = (base_usdt * mult).quantize(Decimal('0.00000001'))
    total_coins = (base_coins * mult).quantize(Decimal('0.00000001'))
    profit_usdt = (total_usdt - base_usdt).quantize(Decimal('0.00000001'))
    profit_coins = (total_coins - base_coins).quantize(Decimal('0.00000001'))
    pct = profit_percentage_value(settings_obj)
    return {
        'base_usdt': base_usdt,
        'base_coins': base_coins,
        'profit_usdt': profit_usdt,
        'profit_coins': profit_coins,
        'profit_percentage': float(pct),
        'total_usdt': total_usdt,
        'total_coins': total_coins,
        'profit_enabled': bool(
            getattr(settings_obj, 'profit_enabled', False) and pct > 0,
        ),
    }

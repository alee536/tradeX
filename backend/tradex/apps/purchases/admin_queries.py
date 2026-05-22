"""
Admin purchase list helpers — filtering, search, and display values.

Used by the Django admin dashboard (and optionally admin API) so TXID search
and expected-coin calculation stay consistent in one place.
"""

from decimal import Decimal, InvalidOperation

from django.db.models import Q

from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings


def filter_admin_purchases(status_filter='', search=''):
    """
    Return purchases for admin list with optimized select_related.

    Search matches username, email, internal transaction_id, or payment TXID.
    """
    queryset = Purchase.objects.select_related('user').all()

    status_filter = (status_filter or '').strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    search_term = (search or '').strip()
    if search_term:
        queryset = queryset.filter(
            Q(user__username__icontains=search_term)
            | Q(user__email__icontains=search_term)
            | Q(transaction_id__icontains=search_term)
            | Q(txid__icontains=search_term)
        )

    return queryset.order_by('-created_at')


def get_active_coin_rate(purchase, settings_obj=None):
    """Resolve coin rate for expected-coins calculation."""
    if purchase.coin_rate_at_approval is not None:
        try:
            rate = Decimal(str(purchase.coin_rate_at_approval))
            if rate > 0:
                return rate
        except (InvalidOperation, TypeError):
            pass

    settings_obj = settings_obj or SystemSettings.get_settings()
    try:
        rate = Decimal(str(settings_obj.coin_rate or 0))
        return rate if rate > 0 else None
    except (InvalidOperation, TypeError):
        return None


def expected_coins_for_purchase(purchase, settings_obj=None):
    """
    Coins admin should expect for this purchase.

    Uses approved_coin_amount when set; otherwise amount / current coin rate.
    """
    if purchase.approved_coin_amount is not None:
        return purchase.approved_coin_amount

    rate = get_active_coin_rate(purchase, settings_obj)
    if rate is None:
        return Decimal('0')

    try:
        amount = Decimal(str(purchase.amount or 0))
    except (InvalidOperation, TypeError):
        return Decimal('0')

    if amount <= 0:
        return Decimal('0')

    return (amount / rate).quantize(Decimal('0.00000001'))


def build_admin_purchase_rows(purchases, settings_obj=None):
    """
    Attach display-friendly values for the admin purchases table.

    Returns list of dicts: purchase, expected_coins, has_screenshot, txid_for_copy.
    """
    settings_obj = settings_obj or SystemSettings.get_settings()
    rows = []
    for purchase in purchases:
        txid = (purchase.txid or '').strip()
        rows.append({
            'purchase': purchase,
            'expected_coins': expected_coins_for_purchase(purchase, settings_obj),
            'has_screenshot': bool(purchase.screenshot),
            'txid_for_copy': txid,
            'txid_display': txid if txid else '—',
            'wallet_display': (purchase.wallet_address or '').strip() or '—',
        })
    return rows

from decimal import Decimal

from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.settings_app.profit import compute_user_profit_summary, get_profit_bonus_coins
from apps.withdrawals.models import Withdrawal
from apps.withdrawals.money import to_decimal


def _as_api_number(value):
    """JSON-safe float for API responses."""
    return float(to_decimal(value))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    user = request.user
    from apps.withdrawals.views import get_available_balance, sync_user_withdrawals

    sync_user_withdrawals(user)

    settings_obj = SystemSettings.get_settings()
    coin_rate = to_decimal(settings_obj.coin_rate)

    approved_assigned_purchases = Purchase.objects.filter(
        user=user,
        status='approved',
        is_coins_assigned=True,
    ).only('approved_coin_amount', 'amount', 'coin_rate_at_approval')

    total_purchased = Decimal('0')
    for purchase in approved_assigned_purchases:
        coin_amount = (
            purchase.approved_coin_amount
            if purchase.approved_coin_amount is not None
            else purchase.calculated_coins
        )
        total_purchased += to_decimal(coin_amount)

    available_withdrawal, wallet_from_claims, _total_assigned = get_available_balance(user)
    available_withdrawal = to_decimal(available_withdrawal)
    wallet_from_claims = to_decimal(wallet_from_claims)

    total_withdrawn = Withdrawal.objects.filter(
        user=user,
        status__in=['pending', 'approved', 'completed'],
    ).aggregate(total=Sum('amount'))['total']
    total_withdrawn = to_decimal(total_withdrawn)

    locked_coins = total_purchased - wallet_from_claims
    if locked_coins < Decimal('0'):
        locked_coins = Decimal('0')

    profit_bonus = to_decimal(get_profit_bonus_coins(user))
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

    try:
        profit = compute_user_profit_summary(user, settings_obj)
    except Exception:
        profit = {'enabled': False}

    return Response({
        'total_purchased': _as_api_number(total_purchased),
        'total_sold': 0,
        'available_withdrawal': _as_api_number(available_withdrawal),
        'available_withdrawal_usdt': _as_api_number(available_withdrawal * coin_rate),
        'current_coin_rate': _as_api_number(coin_rate),
        'pending_withdrawal': _as_api_number(locked_coins),
        'sponsor_earnings': _as_api_number(user.sponsor_earnings),
        'unread_notifications': unread_notifications,
        'profit_bonus_coins': _as_api_number(profit_bonus),
        'profit': profit,
    })

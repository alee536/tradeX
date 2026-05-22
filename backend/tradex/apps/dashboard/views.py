from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.purchases.models import Purchase
from apps.withdrawals.models import Withdrawal
from apps.notifications.models import Notification
from apps.settings_app.models import SystemSettings
from apps.settings_app.profit import (
    compute_user_profit_summary,
    get_profit_bonus_coins,
    sum_profit_inclusive_totals,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    user = request.user
    from apps.withdrawals.views import sync_user_withdrawals

    sync_user_withdrawals(user)

    from apps.withdrawals.views import get_available_balance

    settings_obj = SystemSettings.get_settings()
    approved_purchases = Purchase.objects.filter(user=user, status='approved')

    # Wallet balance: only coins already credited via staged claims (withdraw later)
    profit_bonus = get_profit_bonus_coins(user)
    available_withdrawal, wallet_from_claims, total_assigned_base = get_available_balance(user)

    # Dashboard totals: show deposit + profit% as soon as purchase is approved
    profit_aggregates = sum_profit_inclusive_totals(user, settings_obj)
    total_entitled_coins = float(profit_aggregates['total_entitled_coins'])
    total_purchased_base = sum(
        float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)
        for p in approved_purchases.filter(is_coins_assigned=True)
    )
    # Value visible on dashboard minus what is already in the claim wallet
    locked_coins = max(0.0, total_entitled_coins - float(wallet_from_claims))

    total_withdrawn = sum(
        w.amount for w in Withdrawal.objects.filter(user=user, status__in=['pending', 'approved', 'completed'])
    )

    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

    try:
        profit = compute_user_profit_summary(user, settings_obj)
    except Exception:
        profit = {'enabled': False}

    return Response({
        # Profit-inclusive coin total (e.g. 100 USDT + 10% => 110 coins at rate 1)
        'total_purchased': total_entitled_coins,
        'total_purchased_base': total_purchased_base,
        'total_sold': 0,
        'available_withdrawal': available_withdrawal,
        'available_withdrawal_usdt': float(available_withdrawal * float(settings_obj.coin_rate)),
        'current_coin_rate': float(settings_obj.coin_rate),
        'pending_withdrawal': float(locked_coins),
        'sponsor_earnings': float(user.sponsor_earnings),
        'unread_notifications': unread_notifications,
        'profit_bonus_coins': profit_bonus,
        'profit': profit,
    })

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.purchases.models import Purchase
from apps.withdrawals.models import Withdrawal
from apps.notifications.models import Notification
from apps.settings_app.models import SystemSettings
from apps.settings_app.profit import compute_user_profit_summary, get_profit_bonus_coins


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    user = request.user
    from apps.withdrawals.views import sync_user_withdrawals

    sync_user_withdrawals(user)

    # Only consider purchases for which coins have actually been assigned
    approved_assigned_purchases = Purchase.objects.filter(user=user, status='approved', is_coins_assigned=True)
    total_purchased = sum(float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins) for p in approved_assigned_purchases)

    # Only unlocked amounts from assigned purchases are available for withdrawal
    total_unlocked = sum(p.unlocked_amount for p in approved_assigned_purchases)
    total_withdrawn = sum(w.amount for w in Withdrawal.objects.filter(user=user, status__in=['pending', 'approved', 'completed']))
    # Coins that are assigned but not yet unlocked (shown on dashboard as pending/locked coins)
    locked_coins = max(0, float(total_purchased) - float(total_unlocked))

    profit_bonus = get_profit_bonus_coins(user)
    available_withdrawal = max(0, float(total_unlocked) + profit_bonus - float(total_withdrawn))
    settings_obj = SystemSettings.get_settings()

    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

    try:
        profit = compute_user_profit_summary(user, settings_obj)
    except Exception:
        profit = {'enabled': False}

    return Response({
        'total_purchased': float(total_purchased),
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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from .models import Withdrawal
from .serializers import WithdrawalSerializer, WithdrawalInputSerializer
from apps.notifications.utils import create_notification


ACTIVE_WITHDRAWAL_STATUSES = ['pending', 'approved', 'completed']


def get_withdrawal_stage_amounts(withdrawal):
    return withdrawal.stage_amounts


def sync_withdrawal_payout_state(withdrawal):
    from apps.settings_app.models import SystemSettings

    if withdrawal.status not in ['approved', 'completed'] or not withdrawal.approved_at:
        return False

    settings_obj = SystemSettings.get_settings()
    now = timezone.now()
    stage1_due = withdrawal.approved_at + timedelta(hours=settings_obj.stage1_hours)
    stage2_due = stage1_due + timedelta(hours=settings_obj.stage2_hours)
    stage3_due = stage2_due + timedelta(hours=settings_obj.stage3_hours)

    stage1_amount, stage2_amount, stage3_amount = get_withdrawal_stage_amounts(withdrawal)
    stage1_percent, stage2_percent, stage3_percent = withdrawal.stage_percentages
    updates = []
    updated = False

    if not withdrawal.stage1_paid_at and now >= stage1_due:
        withdrawal.stage1_paid_at = now
        withdrawal.payment_stage = max(withdrawal.payment_stage, 1)
        create_notification(
            withdrawal.user,
            'withdrawal_stage_paid',
            f'Withdrawal {withdrawal.id}: Stage 1 payment ({stage1_percent}%) of {stage1_amount:.8f} coins has been released.'
        )
        updates.extend(['stage1_paid_at', 'payment_stage'])
        updated = True

    if withdrawal.stage1_paid_at and not withdrawal.stage2_paid_at and now >= stage2_due:
        withdrawal.stage2_paid_at = now
        withdrawal.payment_stage = max(withdrawal.payment_stage, 2)
        create_notification(
            withdrawal.user,
            'withdrawal_stage_paid',
            f'Withdrawal {withdrawal.id}: Stage 2 payment ({stage2_percent}%) of {stage2_amount:.8f} coins has been released.'
        )
        updates.extend(['stage2_paid_at', 'payment_stage'])
        updated = True

    if withdrawal.stage2_paid_at and not withdrawal.stage3_paid_at and now >= stage3_due:
        withdrawal.stage3_paid_at = now
        withdrawal.payment_stage = 3
        withdrawal.status = 'completed'
        withdrawal.completed_at = now
        create_notification(
            withdrawal.user,
            'withdrawal_completed',
            f'Withdrawal {withdrawal.id}: Final payment ({stage3_percent}%) of {stage3_amount:.8f} coins has been released and the withdrawal is completed.'
        )
        updates.extend(['stage3_paid_at', 'payment_stage', 'status', 'completed_at'])
        updated = True

    if updated:
        withdrawal.save(update_fields=updates)
    return updated


def sync_user_withdrawals(user):
    withdrawals = Withdrawal.objects.filter(user=user, status__in=['approved', 'completed']).order_by('created_at')
    for withdrawal in withdrawals:
        sync_withdrawal_payout_state(withdrawal)


def get_available_balance(user):
    from apps.purchases.models import Purchase
    from apps.settings_app.profit import get_profit_bonus_coins

    approved_purchases = Purchase.objects.filter(user=user, status='approved', is_coins_assigned=True)
    total_unlocked = sum(float(p.unlocked_amount) for p in approved_purchases)
    total_assigned = sum(
        float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)
        for p in approved_purchases
    )
    profit_bonus = get_profit_bonus_coins(user)

    total_withdrawn = sum(
        w.amount for w in Withdrawal.objects.filter(user=user, status__in=ACTIVE_WITHDRAWAL_STATUSES)
    )
    available = max(0.0, float(total_unlocked) + profit_bonus - float(total_withdrawn))
    return available, float(total_unlocked), float(total_assigned)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def withdrawals_list(request):
    sync_user_withdrawals(request.user)

    if request.method == 'GET':
        qs = Withdrawal.objects.filter(user=request.user).order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = WithdrawalSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = WithdrawalInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    amount = serializer.validated_data['amount']
    available, total_unlocked, total_assigned = get_available_balance(request.user)

    if float(amount) > available:
        if total_assigned > 0 and total_unlocked <= 0:
            from apps.settings_app.models import SystemSettings
            settings_obj = SystemSettings.get_settings()
            return Response(
                {
                    'error': (
                        f'Your coins are still locked. Total assigned: {total_assigned:.8f}. '
                        f'First unlock starts after {settings_obj.stage1_hours} hours from approval.'
                    )
                },
                status=400,
            )

        return Response({'error': f'Insufficient balance. Available: {available:.8f}'}, status=400)

    withdrawal = Withdrawal.objects.create(
        user=request.user,
        amount=amount,
        wallet_address=serializer.validated_data['wallet_address'],
    )
    create_notification(request.user, 'withdrawal_submitted', f'Your withdrawal request of {amount} tokens has been submitted.')
    return Response(WithdrawalSerializer(withdrawal).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unlocked_amount(request):
    from apps.purchases.models import Purchase
    from apps.settings_app.models import SystemSettings

    sync_user_withdrawals(request.user)

    from apps.settings_app.profit import get_profit_bonus_coins

    approved_purchases = Purchase.objects.filter(user=request.user, status='approved', is_coins_assigned=True)
    total_unlocked = sum(p.unlocked_amount for p in approved_purchases)
    profit_bonus = get_profit_bonus_coins(request.user)
    total_withdrawn = sum(
        w.amount for w in Withdrawal.objects.filter(user=request.user, status__in=ACTIVE_WITHDRAWAL_STATUSES)
    )
    available = float(total_unlocked) + profit_bonus - float(total_withdrawn)

    breakdown = []
    settings_obj = SystemSettings.get_settings()

    for p in approved_purchases:
        if not p.approved_at:
            continue
        now = timezone.now()
        elapsed = now - p.approved_at
        elapsed_hours = elapsed.total_seconds() / 3600

        stage1_h = settings_obj.stage1_hours
        stage2_h = stage1_h + settings_obj.stage2_hours
        stage3_h = stage2_h + settings_obj.stage3_hours

        current_stage = 0
        next_unlock_at = None
        if elapsed_hours < stage1_h:
            current_stage = 0
            hours_left = stage1_h - elapsed_hours
            next_unlock_at = (now + timedelta(hours=hours_left)).isoformat()
        elif elapsed_hours < stage2_h:
            current_stage = 1
            hours_left = stage2_h - elapsed_hours
            next_unlock_at = (now + timedelta(hours=hours_left)).isoformat()
        elif elapsed_hours < stage3_h:
            current_stage = 2
            hours_left = stage3_h - elapsed_hours
            next_unlock_at = (now + timedelta(hours=hours_left)).isoformat()
        else:
            current_stage = 3

        purchase_coin_amount = float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)

        breakdown.append({
            'purchase_id': p.id,
            'transaction_id': p.transaction_id,
            'amount': purchase_coin_amount,
            'unlocked': p.unlocked_amount,
            'unlocked_usdt': float(p.unlocked_amount) * float(settings_obj.coin_rate),
            'stage': current_stage,
            'next_unlock_at': next_unlock_at,
        })

    return Response({
        'total_unlocked': float(total_unlocked),
        'total_withdrawn': float(total_withdrawn),
        'available': max(0, available),
        'available_usdt_equivalent': float(max(0, available) * float(settings_obj.coin_rate)),
        'coin_rate': float(settings_obj.coin_rate),
        'breakdown': breakdown,
    })

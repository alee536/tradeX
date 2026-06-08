from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.utils import create_notification

from .claims import (
    ClaimError,
    create_claim,
    get_purchase_schedule,
    get_user_claim_schedule,
    total_claimed_coins,
)
from .models import PurchaseClaim, Withdrawal
from .money import exceeds_balance, to_decimal
from .serializers import WithdrawalInputSerializer, WithdrawalSerializer


ACTIVE_WITHDRAWAL_STATUSES = ['pending', 'approved', 'completed']


def get_withdrawal_stage_amounts(withdrawal):
    return withdrawal.stage_amounts


def sync_withdrawal_payout_state(withdrawal):
    """
    Approved withdrawals pay 100% of the requested amount immediately (no staged cuts).
    """
    if withdrawal.status not in ['approved', 'completed'] or not withdrawal.approved_at:
        return False

    if withdrawal.status == 'completed':
        return False

    now = timezone.now()
    withdrawal.stage1_paid_at = now
    withdrawal.stage2_paid_at = now
    withdrawal.stage3_paid_at = now
    withdrawal.payment_stage = 3
    withdrawal.status = 'completed'
    withdrawal.completed_at = now
    withdrawal.save(
        update_fields=[
            'stage1_paid_at',
            'stage2_paid_at',
            'stage3_paid_at',
            'payment_stage',
            'status',
            'completed_at',
        ]
    )
    create_notification(
        withdrawal.user,
        'withdrawal_completed',
        f'Withdrawal {withdrawal.id}: {withdrawal.amount} coins has been released in full.',
    )
    return True


def sync_user_withdrawals(user):
    withdrawals = Withdrawal.objects.filter(user=user, status__in=['approved', 'completed']).order_by('created_at')
    for withdrawal in withdrawals:
        sync_withdrawal_payout_state(withdrawal)


def get_available_balance(user):
    """
    Wallet balance available for withdrawal requests.
    Staged claims credit coins instantly; withdrawals still need admin approval.
    """
    from apps.purchases.models import Purchase
    from apps.settings_app.profit import get_profit_bonus_coins

    approved_purchases = Purchase.objects.filter(
        user=user,
        status='approved',
        is_coins_assigned=True,
    ).only('approved_coin_amount', 'amount', 'coin_rate_at_approval')
    total_assigned = Decimal('0')
    for purchase in approved_purchases:
        coin_amount = (
            purchase.approved_coin_amount
            if purchase.approved_coin_amount is not None
            else purchase.calculated_coins
        )
        total_assigned += to_decimal(coin_amount)

    wallet_from_claims = total_claimed_coins(user)
    wallet_from_sponsor = to_decimal(user.wallet_balance)
    profit_bonus = to_decimal(get_profit_bonus_coins(user))

    total_withdrawn = Withdrawal.objects.filter(
        user=user,
        status__in=ACTIVE_WITHDRAWAL_STATUSES,
    ).aggregate(total=Sum('amount'))['total']
    total_withdrawn = to_decimal(total_withdrawn)

    wallet_total = wallet_from_claims + wallet_from_sponsor
    available = wallet_from_claims + wallet_from_sponsor + profit_bonus - total_withdrawn
    if available < Decimal('0'):
        available = Decimal('0')

    return available, wallet_total, total_assigned


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
    available, wallet_from_claims, total_assigned = get_available_balance(request.user)

    if exceeds_balance(amount, available):
        if total_assigned > 0 and wallet_from_claims <= 0:
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

    approved_purchases = Purchase.objects.filter(
        user=request.user, status='approved', is_coins_assigned=True,
    ).only(
        'id', 'transaction_id', 'approved_at', 'approved_coin_amount',
        'amount', 'coin_rate_at_approval',
    )
    available, wallet_from_claims, total_assigned = get_available_balance(request.user)
    profit_bonus = to_decimal(get_profit_bonus_coins(request.user))
    total_withdrawn = Withdrawal.objects.filter(
        user=request.user,
        status__in=ACTIVE_WITHDRAWAL_STATUSES,
    ).aggregate(total=Sum('amount'))['total']
    total_withdrawn = to_decimal(total_withdrawn)

    breakdown = []
    settings_obj = SystemSettings.get_settings()
    coin_rate = to_decimal(settings_obj.coin_rate)

    approved_claims = PurchaseClaim.objects.filter(
        user=request.user,
        status='approved',
        purchase_id__in=approved_purchases.values_list('id', flat=True),
    ).values('purchase_id').annotate(
        claimed_total=Sum('amount_coins'),
        stage_count=models.Count('id'),
    )
    claim_stats_by_purchase = {
        row['purchase_id']: row for row in approved_claims
    }

    for purchase in approved_purchases:
        if not purchase.approved_at:
            continue
        purchase_coin_amount = to_decimal(
            purchase.approved_coin_amount
            if purchase.approved_coin_amount is not None
            else purchase.calculated_coins
        )
        claim_stats = claim_stats_by_purchase.get(purchase.id, {})
        claimed_for_purchase = to_decimal(claim_stats.get('claimed_total'))
        breakdown.append({
            'purchase_id': purchase.id,
            'transaction_id': purchase.transaction_id,
            'amount': purchase_coin_amount,
            'unlocked': claimed_for_purchase,
            'unlocked_usdt': claimed_for_purchase * coin_rate,
            'stage': claim_stats.get('stage_count', 0),
            'next_unlock_at': None,
        })

    available = max(Decimal('0'), available)
    return Response({
        'total_unlocked': wallet_from_claims,
        'total_withdrawn': total_withdrawn,
        'available': available,
        'available_usdt_equivalent': available * coin_rate,
        'coin_rate': coin_rate,
        'profit_bonus_coins': profit_bonus,
        'breakdown': breakdown,
    })


# ============== Purchase Claim Endpoints (APIView) ==============


def _get_purchase_or_404(user, purchase_id):
    from apps.purchases.models import Purchase

    try:
        return Purchase.objects.get(pk=purchase_id, user=user)
    except Purchase.DoesNotExist:
        return None


class ClaimScheduleView(APIView):
    """============== List user's per-purchase claim schedule =============="""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        purchase_id = request.query_params.get('purchase_id')
        if purchase_id:
            purchase = _get_purchase_or_404(request.user, purchase_id)
            if purchase is None:
                return Response({'error': 'Purchase not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'purchases': [get_purchase_schedule(purchase)]})

        return Response({'purchases': get_user_claim_schedule(request.user)})


class ClaimCreateView(APIView):
    """============== Submit a claim request for one stage =============="""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        purchase_id = request.data.get('purchase_id')
        stage = request.data.get('stage')
        wallet_address = request.data.get('wallet_address')

        if purchase_id is None or stage is None:
            return Response(
                {'error': 'purchase_id and stage are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            stage = int(stage)
        except (TypeError, ValueError):
            return Response({'error': 'stage must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        purchase = _get_purchase_or_404(request.user, purchase_id)
        if purchase is None:
            return Response({'error': 'Purchase not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            claim = create_claim(request.user, purchase, stage, wallet_address)
        except ClaimError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'message': (
                    f'Stage {stage} claimed successfully. '
                    f'{claim.amount_coins} coins added to your wallet.'
                ),
                'schedule': get_purchase_schedule(purchase),
            },
            status=status.HTTP_201_CREATED,
        )

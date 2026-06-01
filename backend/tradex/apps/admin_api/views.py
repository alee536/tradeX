from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone

from apps.accounts.models import User
from apps.purchases.models import Purchase, PurchaseRejectionDocument
from apps.withdrawals.claims import ClaimError, approve_claim, reject_claim
from apps.withdrawals.models import PurchaseClaim, Withdrawal
from apps.sponsor.access import (
    SponsorAccessError,
    approve_sponsor_access_request,
    reject_sponsor_access_request,
)
from apps.sponsor.models import SponsorAccessRequest
from apps.sponsor.report import get_sponsor_report_rows
from apps.notifications.utils import create_notification
from apps.settings_app.models import SystemSettings
from apps.settings_app.serializers import SystemSettingsSerializer
from .permissions import IsAdminUser


class AdminPaginator(PageNumberPagination):
    page_size = 20


# ---- Users ----

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_list_users(request):
    qs = User.objects.all().order_by('-date_joined')
    search = request.query_params.get('search')
    if search:
        qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)

    results = []
    for u in qs:
        # Sum purchases in coins (approved_coin_amount if present, else calculated_coins)
        total_purchased = 0
        for p in Purchase.objects.filter(user=u, status='approved'):
            total_purchased += float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)

        # Withdrawals are stored in coins
        total_withdrawn = sum(w.amount for w in Withdrawal.objects.filter(user=u, status__in=['pending', 'approved', 'completed']))

        results.append({
            'id': u.id,
            'unique_id': u.unique_id,
            'username': u.username,
            'full_name': u.full_name,
            'email': u.email,
            'is_active': u.is_active,
            'is_banned': u.is_banned,
            'sponsor_code': u.sponsor_code,
            'total_purchased': float(total_purchased),
            'total_withdrawn': float(total_withdrawn),
            'date_joined': u.date_joined.isoformat(),
        })

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(results, request)
    return paginator.get_paginated_response(page)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_update_user(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    is_self_admin_update = request.user.is_staff and request.user.id == user.id

    # Security: only admin can update own credentials; never update other users' credentials.
    if 'username' in request.data and not is_self_admin_update:
        return Response({'error': 'Admin cannot modify username for other users.'}, status=403)
    if 'password' in request.data and not is_self_admin_update:
        return Response({'error': 'Admin cannot modify password for other users.'}, status=403)

    if is_self_admin_update and 'username' in request.data:
        user.username = request.data['username']
    if is_self_admin_update and 'password' in request.data:
        user.set_password(request.data['password'])

    # Allow activation/deactivation and ban status
    if 'is_active' in request.data:
        user.is_active = request.data['is_active']
    if 'is_banned' in request.data:
        user.is_banned = request.data['is_banned']
    if 'full_name' in request.data:
        user.full_name = request.data['full_name']
    if 'wallet_address' in request.data:
        user.wallet_address = request.data['wallet_address']
    
    user.save()
    return Response({'message': 'User updated successfully', 'user': {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'is_active': user.is_active,
        'is_banned': user.is_banned,
    }})


# ---- Purchases ----

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_list_purchases(request):
    qs = Purchase.objects.all().select_related('user').order_by('-created_at')
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    from apps.purchases.serializers import PurchaseSerializer

    results = []
    for p in qs:
        data = PurchaseSerializer(p).data
        data['username'] = p.user.username
        results.append(data)

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(results, request)
    return paginator.get_paginated_response(page)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_approve_purchase(request, pk):
    try:
        purchase = Purchase.objects.get(pk=pk)
    except Purchase.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if purchase.status != 'pending':
        return Response({'error': 'Purchase is not pending'}, status=400)

    settings_obj = SystemSettings.get_settings()
    calculated_coins = purchase.approved_coin_amount
    if calculated_coins is None:
        from decimal import Decimal
        coin_rate = purchase.coin_rate_at_approval or settings_obj.coin_rate
        if coin_rate <= 0:
            return Response({'error': 'Coin rate must be greater than 0'}, status=400)
        calculated_coins = Decimal(purchase.amount) / Decimal(coin_rate)
        purchase.coin_rate_at_approval = coin_rate
        purchase.approved_coin_amount = calculated_coins

    # Update global sold_coins in settings (only when transitioning from pending to approved)
    settings_obj = SystemSettings.get_settings()
    try:
        # Add to sold_coins if this purchase was just approved (status change)
        settings_obj.sold_coins = (float(settings_obj.sold_coins) + float(calculated_coins))
        settings_obj.save()
    except Exception:
        pass

    purchase.status = 'approved'
    purchase.approved_at = timezone.now()
    purchase.is_coins_assigned = False
    purchase.coins_assigned_at = None
    purchase.save()

    if purchase.user.sponsored_by:
        from apps.sponsor.purchase_rewards import credit_sponsor_for_approved_purchase

        sponsor = purchase.user.sponsored_by
        earning_coins = credit_sponsor_for_approved_purchase(sponsor, calculated_coins)
        if earning_coins > 0:
            create_notification(
                sponsor,
                'sponsor_earning',
                f'You earned {float(earning_coins):.8f} sponsor reward coins from '
                f'{purchase.user.username}\'s purchase.',
            )

    create_notification(
        purchase.user,
        'purchase_approved',
        f'Your token purchase of {purchase.amount} USDT (ID: {purchase.transaction_id}) has been approved. Calculated coins: {float(calculated_coins):.8f}.'
    )
    return Response({
        'message': 'Purchase approved. Coins are ready to assign.',
        'purchase_id': purchase.id,
        'coin_rate': str(purchase.coin_rate_at_approval or settings_obj.coin_rate),
        'calculated_coins': str(calculated_coins),
        'is_coins_assigned': purchase.is_coins_assigned,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_delete_user(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    # Prevent deleting superuser accidentally via API
    if user.is_superuser:
        return Response({'error': 'Cannot delete superuser via admin API.'}, status=403)

    # Adjust global sold_coins by subtracting this user's approved purchases (if any)
    settings_obj = SystemSettings.get_settings()
    try:
        approved_purchases = Purchase.objects.filter(user=user, status='approved')
        total_coins = 0.0
        for p in approved_purchases:
            total_coins += float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)
        settings_obj.sold_coins = max(0, float(settings_obj.sold_coins) - total_coins)
        settings_obj.save()
    except Exception:
        pass

    user.delete()
    return Response({'message': 'User deleted successfully.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_reject_purchase(request, pk):
    try:
        purchase = Purchase.objects.get(pk=pk)
    except Purchase.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    reason_type = str(request.data.get('reason_type', '')).strip()
    custom_notes = str(request.data.get('custom_notes', '')).strip()

    if not reason_type or reason_type not in dict(Purchase.REJECTION_REASON_CHOICES):
        return Response({'error': 'Valid rejection reason is required.'}, status=400)

    if purchase.status != 'pending':
        return Response({'error': 'Only pending purchases can be rejected.'}, status=400)

    # Build the full rejection message
    reason_display = dict(Purchase.REJECTION_REASON_CHOICES).get(reason_type, reason_type)
    full_message = f"Reason: {reason_display}"
    if custom_notes:
        full_message += f"\n\nAdmin Notes: {custom_notes}"

    purchase.status = 'rejected'
    purchase.rejection_reason_type = reason_type
    purchase.rejection_reason = reason_display
    purchase.rejection_notes = custom_notes
    purchase.rejection_date = timezone.now()
    purchase.save()

    create_notification(
        purchase.user, 
        'purchase_rejected', 
        f'Your token purchase of {purchase.amount} USDT (ID: {purchase.transaction_id}) has been rejected.\n\n{full_message}\n\nYou can upload supporting documents to appeal this decision.'
    )
    
    return Response({
        'message': 'Purchase rejected successfully',
        'purchase_id': purchase.id,
        'reason_type': reason_type,
        'rejection_reason': reason_display,
        'rejection_notes': custom_notes,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assign_purchase_coins(request, pk):
    try:
        purchase = Purchase.objects.get(pk=pk)
    except Purchase.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if purchase.status != 'approved':
        return Response({'error': 'Only approved purchases can be assigned.'}, status=400)

    if purchase.is_coins_assigned:
        return Response({'error': 'Coins are already assigned for this purchase.'}, status=400)

    if purchase.approved_coin_amount is None:
        settings_obj = SystemSettings.get_settings()
        if settings_obj.coin_rate <= 0:
            return Response({'error': 'Coin rate must be greater than 0'}, status=400)
        purchase.coin_rate_at_approval = settings_obj.coin_rate
        from decimal import Decimal
        purchase.approved_coin_amount = Decimal(purchase.amount) / Decimal(settings_obj.coin_rate)

    purchase.is_coins_assigned = True
    purchase.coins_assigned_at = timezone.now()
    purchase.save(update_fields=['coin_rate_at_approval', 'approved_coin_amount', 'is_coins_assigned', 'coins_assigned_at'])

    create_notification(
        purchase.user,
        'purchase_coins_assigned',
        f'Coins assigned for purchase {purchase.transaction_id}: {purchase.approved_coin_amount:.8f}.'
    )

    return Response({
        'message': 'Coins assigned successfully.',
        'purchase_id': purchase.id,
        'approved_coin_amount': str(purchase.approved_coin_amount),
        'coin_rate_at_approval': str(purchase.coin_rate_at_approval),
        'is_coins_assigned': purchase.is_coins_assigned,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_delete_purchase(request, pk):
    try:
        purchase = Purchase.objects.get(pk=pk)
    except Purchase.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    # If purchase was approved, decrement sold_coins accordingly
    settings_obj = SystemSettings.get_settings()
    try:
        if purchase.status == 'approved':
            coin_amount = float(purchase.approved_coin_amount if purchase.approved_coin_amount is not None else purchase.calculated_coins)
            settings_obj.sold_coins = max(0, float(settings_obj.sold_coins) - coin_amount)
            settings_obj.save()
    except Exception:
        pass

    purchase.delete()
    return Response({'message': 'Purchase deleted successfully.'})


# ---- Withdrawals ----

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_list_withdrawals(request):
    qs = Withdrawal.objects.all().select_related('user').order_by('-created_at')
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    from apps.withdrawals.views import sync_withdrawal_payout_state
    for withdrawal in qs:
        sync_withdrawal_payout_state(withdrawal)

    from apps.withdrawals.serializers import WithdrawalSerializer
    results = []
    for w in qs:
        data = WithdrawalSerializer(w).data
        data['username'] = w.user.username
        results.append(data)

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(results, request)
    return paginator.get_paginated_response(page)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_approve_withdrawal(request, pk):
    try:
        withdrawal = Withdrawal.objects.get(pk=pk)
    except Withdrawal.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if withdrawal.status != 'pending':
        return Response({'error': 'Withdrawal is not pending'}, status=400)

    manual_tx_hash = request.data.get('manual_tx_hash', '')
    if not manual_tx_hash:
        return Response({'error': 'manual_tx_hash is required'}, status=400)

    withdrawal.status = 'approved'
    withdrawal.manual_tx_hash = manual_tx_hash
    withdrawal.approved_at = timezone.now()
    withdrawal.save()

    from apps.withdrawals.views import sync_withdrawal_payout_state

    sync_withdrawal_payout_state(withdrawal)

    create_notification(
        withdrawal.user,
        'withdrawal_approved',
        f'Your withdrawal of {withdrawal.amount} coins has been approved and released in full.',
    )
    return Response({
        'message': 'Withdrawal approved',
        'withdrawal': {
            'id': withdrawal.id,
            'payment_stage': withdrawal.payment_stage,
            'approved_at': withdrawal.approved_at,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_reject_withdrawal(request, pk):
    try:
        withdrawal = Withdrawal.objects.get(pk=pk)
    except Withdrawal.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    reason = request.data.get('reason', '')
    withdrawal.status = 'rejected'
    withdrawal.rejection_reason = reason
    withdrawal.save()

    create_notification(withdrawal.user, 'withdrawal_rejected', f'Your withdrawal of {withdrawal.amount} tokens has been rejected. Reason: {reason}')
    return Response({'message': 'Withdrawal rejected'})


# ============== Purchase Claims (staged withdrawal) ==============


def _serialize_admin_claim(claim):
    user = claim.user
    purchase = claim.purchase
    return {
        'id': claim.id,
        'stage': claim.stage,
        'status': claim.status,
        'amount_coins': float(claim.amount_coins or 0),
        'amount_usdt_snapshot': float(claim.amount_usdt_snapshot or 0),
        'coin_rate_snapshot': float(claim.coin_rate_snapshot or 0),
        'wallet_address': claim.wallet_address,
        'manual_tx_hash': claim.manual_tx_hash,
        'rejection_reason': claim.rejection_reason,
        'created_at': claim.created_at.isoformat() if claim.created_at else None,
        'approved_at': claim.approved_at.isoformat() if claim.approved_at else None,
        'rejected_at': claim.rejected_at.isoformat() if claim.rejected_at else None,
        'purchase': {
            'id': getattr(purchase, 'id', None),
            'transaction_id': getattr(purchase, 'transaction_id', None),
            'amount_usdt': float(getattr(purchase, 'amount', 0) or 0),
        },
        'user': {
            'id': getattr(user, 'id', None),
            'username': getattr(user, 'username', None),
            'email': getattr(user, 'email', None),
            'full_name': getattr(user, 'full_name', None),
        },
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_list_claims(request):
    """List all staged purchase claims for admin review."""
    qs = (
        PurchaseClaim.objects.all()
        .select_related('user', 'purchase')
        .order_by('-created_at')
    )

    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    stage_filter = request.query_params.get('stage')
    if stage_filter:
        try:
            qs = qs.filter(stage=int(stage_filter))
        except ValueError:
            return Response({'error': 'stage must be an integer.'}, status=400)

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(
        [_serialize_admin_claim(c) for c in page]
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_approve_claim(request, pk):
    try:
        claim = PurchaseClaim.objects.select_related('user', 'purchase').get(pk=pk)
    except PurchaseClaim.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    manual_tx_hash = request.data.get('manual_tx_hash', '')
    try:
        approve_claim(claim, manual_tx_hash)
    except ClaimError as exc:
        return Response({'error': str(exc)}, status=400)

    return Response({
        'message': 'Claim approved.',
        'claim': _serialize_admin_claim(claim),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_reject_claim(request, pk):
    try:
        claim = PurchaseClaim.objects.select_related('user', 'purchase').get(pk=pk)
    except PurchaseClaim.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    reason = request.data.get('reason', '')
    try:
        reject_claim(claim, reason)
    except ClaimError as exc:
        return Response({'error': str(exc)}, status=400)

    return Response({
        'message': 'Claim rejected.',
        'claim': _serialize_admin_claim(claim),
    })


# ============== Sponsor access requests ==============


def _serialize_admin_sponsor_request(req):
    user = req.user
    return {
        'id': req.id,
        'status': req.status,
        'payment_status': req.payment_status,
        'fee_usdt': float(req.fee_usdt),
        'ref_slug': req.ref_slug,
        'payment_txid': req.payment_txid,
        'payment_wallet': req.payment_wallet,
        'rejection_reason': req.rejection_reason,
        'created_at': req.created_at.isoformat() if req.created_at else None,
        'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
        'activated_at': req.activated_at.isoformat() if req.activated_at else None,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
        },
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_list_sponsor_access_requests(request):
    qs = (
        SponsorAccessRequest.objects.all()
        .select_related('user')
        .order_by('-created_at')
    )
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(
        [_serialize_admin_sponsor_request(r) for r in page]
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_approve_sponsor_access(request, pk):
    try:
        req = SponsorAccessRequest.objects.select_related('user').get(pk=pk)
    except SponsorAccessRequest.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    try:
        approve_sponsor_access_request(req)
    except SponsorAccessError as exc:
        return Response({'error': str(exc)}, status=400)
    return Response({
        'message': 'Sponsor access approved.',
        'request': _serialize_admin_sponsor_request(req),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_reject_sponsor_access(request, pk):
    try:
        req = SponsorAccessRequest.objects.select_related('user').get(pk=pk)
    except SponsorAccessRequest.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    reason = request.data.get('reason', '')
    try:
        reject_sponsor_access_request(req, reason)
    except SponsorAccessError as exc:
        return Response({'error': str(exc)}, status=400)
    return Response({
        'message': 'Sponsor access rejected.',
        'request': _serialize_admin_sponsor_request(req),
    })


# ---- Settings ----

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_settings(request):
    settings_obj = SystemSettings.get_settings()
    if request.method == 'GET':
        return Response(SystemSettingsSerializer(settings_obj).data)
    serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


# ---- Sponsor ----

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_sponsor_report(request):
    """
    Flat sponsor-wise summary: full downline counts, investment, and earnings.
    No tree structure — each qualifying sponsor appears as one table row.
    """
    search = request.query_params.get('search')
    order_by = request.query_params.get('order_by', '-direct_referrals_investment_usdt')
    allowed_order = {
        'my_investment_usdt',
        '-my_investment_usdt',
        'direct_referrals_investment_usdt',
        '-direct_referrals_investment_usdt',
        'sponsored_users_count',
        '-sponsored_users_count',
        'total_earning',
        '-total_earning',
        'total_earning_usd',
        '-total_earning_usd',
        'sponsor_name',
        '-sponsor_name',
    }
    if order_by not in allowed_order:
        order_by = '-direct_referrals_investment_usdt'

    rows = get_sponsor_report_rows(search=search, order_by=order_by)

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(rows, request)
    return paginator.get_paginated_response(page)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_sponsor_list(request):
    """
    Get list of sponsors who have actually sponsored users.
    Only show users with sponsored_users_count > 0
    """
    # Get all users who have sponsored at least one user
    qs = User.objects.filter(sponsored_users__isnull=False).distinct().select_related('sponsored_by')
    
    search = request.query_params.get('search')
    if search:
        qs = qs.filter(username__icontains=search) | qs.filter(full_name__icontains=search)

    results = []
    for sponsor in qs:
        # Get all users sponsored by this sponsor
        sponsored_users = sponsor.sponsored_users.all()

        # Calculate totals in coins
        total_purchases = 0.0
        total_withdrawals = 0.0

        for su in sponsored_users:
            purchases = Purchase.objects.filter(user=su, status='approved')
            withdrawals = Withdrawal.objects.filter(user=su, status__in=['pending', 'approved', 'completed'])
            for p in purchases:
                total_purchases += float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)
            total_withdrawals += sum(float(w.amount) for w in withdrawals)

        # Calculate sponsor earnings in coins (based on coin purchases)
        settings_obj = SystemSettings.get_settings()
        total_sponsor_earnings = float(total_purchases) * float(settings_obj.sponsor_percentage) / 100

        results.append({
            'sponsor_id': sponsor.id,
            'sponsor_unique_id': sponsor.unique_id,
            'sponsor_username': sponsor.username,
            'sponsor_full_name': sponsor.full_name,
            'sponsor_email': sponsor.email,
            'sponsored_users_count': sponsor.sponsored_users_count,
            'total_purchase_amount': float(total_purchases),
            'total_withdrawal_amount': float(total_withdrawals),
            'total_sponsor_earnings': total_sponsor_earnings,
            'sponsor_earnings_field': float(sponsor.sponsor_earnings),
            'date_joined': sponsor.date_joined.isoformat(),
        })

    paginator = AdminPaginator()
    page = paginator.paginate_queryset(results, request)
    return paginator.get_paginated_response(page)


# ---- Sponsor Tree (Recursive) ----

def build_sponsor_tree(user, depth=0, max_depth=10):
    """
    Recursively build sponsor tree structure.
    Returns nested tree data for expandable/collapsible display.
    """
    if depth >= max_depth:
        return []
    
    # Get child users (sponsored by this user)
    children = []
    child_users = User.objects.filter(sponsored_by=user)
    
    for child in child_users:
        child_purchases = Purchase.objects.filter(user=child, status='approved')
        child_withdrawals = Withdrawal.objects.filter(user=child, status__in=['pending', 'approved', 'completed'])

        # Sum purchases in coins
        total_purchases_coins = 0.0
        for p in child_purchases:
            total_purchases_coins += float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)

        child_data = {
            'id': child.id,
            'unique_id': child.unique_id,
            'username': child.username,
            'full_name': child.full_name,
            'email': child.email,
            'total_purchases': float(total_purchases_coins),
            'total_withdrawals': float(sum(w.amount for w in child_withdrawals)),
            'sponsored_users_count': child.sponsored_users_count,
            'sponsor_earnings': float(child.sponsor_earnings),
            'total_sponsored_count': child.total_sponsored_count,
            'is_active': child.is_active,
            'date_joined': child.date_joined.isoformat(),
            'children': build_sponsor_tree(child, depth + 1, max_depth),
        }
        children.append(child_data)
    
    return children


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_sponsor_tree(request, pk):
    """
    Get recursive sponsor tree for a specific user.
    Shows complete parent-child hierarchy starting from the given user.
    Query params:
    - max_depth: Maximum depth to traverse (default: 10)
    """
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    max_depth = int(request.query_params.get('max_depth', 10))
    
    # Get user's parent sponsor if exists
    parent_sponsor = None
    if user.sponsored_by:
        parent_sponsor = {
            'id': user.sponsored_by.id,
            'unique_id': user.sponsored_by.unique_id,
            'username': user.sponsored_by.username,
            'full_name': user.sponsored_by.full_name,
        }
    
    # Build tree starting from this user's children
    tree_children = build_sponsor_tree(user, depth=0, max_depth=max_depth)
    
    return Response({
        'user': {
            'id': user.id,
            'unique_id': user.unique_id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
                'sponsor_earnings': float(user.sponsor_earnings),
        },
        'parent_sponsor': parent_sponsor,
        'direct_sponsored_count': user.sponsored_users_count,
        'total_sponsored_count': user.total_sponsored_count,
        'tree': {
            'children': tree_children,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_sponsor_tree_root(request):
    """
    Get all root sponsors (users with no parent sponsor) and their trees.
    Shows all sponsor trees in the system.
    """
    # Get all root users (no sponsor parent)
    root_users = User.objects.filter(sponsored_by__isnull=True, sponsored_users__isnull=False).distinct()
    
    results = []
    for root in root_users:
        tree_children = build_sponsor_tree(root, depth=0, max_depth=10)
        
        results.append({
            'user': {
                'id': root.id,
                'unique_id': root.unique_id,
                'username': root.username,
                'full_name': root.full_name,
                'email': root.email,
                'is_active': root.is_active,
                'date_joined': root.date_joined.isoformat(),
                    'sponsor_earnings': float(root.sponsor_earnings),
            },
            'direct_sponsored_count': root.sponsored_users_count,
            'total_sponsored_count': root.total_sponsored_count,
            'tree': {
                'children': tree_children,
            }
        })
    
    return Response({
        'total_root_sponsors': len(results),
        'sponsor_trees': results,
    })


# ---- Stats ----

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_stats(request):
    total_users = User.objects.filter(is_staff=False).count()
    approved_purchases = Purchase.objects.filter(status='approved')
    # total_purchases should represent coins sold
    total_purchases = 0.0
    for p in approved_purchases:
        total_purchases += float(p.approved_coin_amount if p.approved_coin_amount is not None else p.calculated_coins)
    approved_withdrawals = Withdrawal.objects.filter(status__in=['pending', 'approved', 'completed'])
    total_withdrawals = float(sum(w.amount for w in approved_withdrawals))
    pending_purchases = Purchase.objects.filter(status='pending').count()
    pending_withdrawals_count = Withdrawal.objects.filter(status='pending').count()

    settings_obj = SystemSettings.get_settings()
    return Response({
        'total_users': total_users,
        'total_purchases': float(total_purchases),
        'total_withdrawals': total_withdrawals,
        'total_volume': float(total_purchases),
        'pending_purchases': pending_purchases,
        'pending_withdrawals': pending_withdrawals_count,
        'total_coin_supply': float(settings_obj.total_coin_supply),
        'sold_coins': float(settings_obj.sold_coins),
        'remaining_coins': float(settings_obj.remaining_coins),
    })


# ---- User Details with Sponsor Hierarchy ----

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_user_detail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    # Get child users (sponsored by this user)
    child_users = User.objects.filter(sponsored_by=user)
    children_data = []
    for child in child_users:
        child_purchases = Purchase.objects.filter(user=child, status='approved')
        child_withdrawals = Withdrawal.objects.filter(user=child, status__in=['pending', 'approved', 'completed'])
        children_data.append({
            'id': child.id,
            'unique_id': child.unique_id,
            'username': child.username,
            'full_name': child.full_name,
            'email': child.email,
            'total_purchased': float(sum(p.amount for p in child_purchases)),
            'total_withdrawn': float(sum(w.amount for w in child_withdrawals)),
            'is_active': child.is_active,
            'date_joined': child.date_joined.isoformat(),
            'sponsored_users_count': child.sponsored_users_count,
        })

    # Get user's purchases
    purchases = []
    for p in Purchase.objects.filter(user=user).order_by('-created_at'):
        purchases.append({
            'id': p.id,
            'transaction_id': p.transaction_id,
            'amount': float(p.amount),
            'coin_rate_at_approval': float(p.coin_rate_at_approval) if p.coin_rate_at_approval is not None else None,
            'approved_coin_amount': float(p.approved_coin_amount) if p.approved_coin_amount is not None else None,
            'calculated_coins': float(p.calculated_coins) if p.calculated_coins is not None else None,
            'status': p.status,
            'created_at': p.created_at.isoformat(),
            'approved_at': p.approved_at.isoformat() if p.approved_at else None,
            'unlocked_amount': float(p.unlocked_amount),
        })

    # Get user's withdrawals
    withdrawals = []
    for w in Withdrawal.objects.filter(user=user).order_by('-created_at'):
        withdrawals.append({
            'id': w.id,
            'amount': float(w.amount),
            'status': w.status,
            'wallet_address': w.wallet_address,
            'created_at': w.created_at.isoformat(),
            'approved_at': w.approved_at.isoformat() if w.approved_at else None,
        })

    # Get sponsor earnings
    from apps.sponsor.models import SponsorEarning
    sponsor_earnings = []
    for e in SponsorEarning.objects.filter(sponsor=user).order_by('-created_at'):
        sponsor_earnings.append({
            'id': e.id,
            'sponsored_user': e.sponsored_user.username,
            'amount': float(e.amount),
            'created_at': e.created_at.isoformat(),
        })

    return Response({
        'user': {
            'id': user.id,
            'unique_id': user.unique_id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'wallet_address': user.wallet_address,
            'is_active': user.is_active,
            'is_banned': user.is_banned,
            'sponsor_code': user.sponsor_code,
            'sponsored_by': {
                'id': user.sponsored_by.id,
                'unique_id': user.sponsored_by.unique_id,
                'username': user.sponsored_by.username,
                'full_name': user.sponsored_by.full_name,
            } if user.sponsored_by else None,
            'sponsor_earnings': float(user.sponsor_earnings),
            'date_joined': user.date_joined.isoformat(),
            'direct_sponsored_count': user.sponsored_users_count,
            'total_sponsored_count': user.total_sponsored_count,
        },
        'statistics': {
            'total_purchased': float(sum(p['amount'] for p in purchases if p['status'] == 'approved')),
            'total_withdrawn': float(sum(w['amount'] for w in withdrawals if w['status'] == 'approved')),
            'total_sponsor_earnings': float(sum(e['amount'] for e in sponsor_earnings)),
            'child_users_count': len(children_data),
            'pending_purchases': len([p for p in purchases if p['status'] == 'pending']),
            'pending_withdrawals': len([w for w in withdrawals if w['status'] == 'pending']),
        },
        'child_users': children_data,
        'purchases': purchases,
        'withdrawals': withdrawals,
        'sponsor_earnings': sponsor_earnings,
    })


# ---- Purchase Rejection Documents ----

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_rejection_document(request, purchase_id):
    """User uploads supporting document for a rejected purchase"""
    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user)
    except Purchase.DoesNotExist:
        return Response({'error': 'Purchase not found or does not belong to you'}, status=404)

    if purchase.status != 'rejected':
        return Response({'error': 'Can only upload documents for rejected purchases'}, status=400)

    if 'document' not in request.FILES:
        return Response({'error': 'Document file is required'}, status=400)

    document_file = request.FILES['document']
    
    # Validate file size (max 10MB)
    if document_file.size > 10 * 1024 * 1024:
        return Response({'error': 'File size must not exceed 10MB'}, status=400)

    # Validate file type (allow common document and image formats)
    allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx', 'xls', 'xlsx']
    file_ext = document_file.name.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        return Response({'error': f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'}, status=400)

    # Create document record
    doc = PurchaseRejectionDocument.objects.create(
        purchase=purchase,
        document=document_file
    )

    create_notification(
        User.objects.filter(is_staff=True).first(),
        'document_uploaded',
        f'User {request.user.username} uploaded a supporting document for rejected purchase {purchase.transaction_id}. Please review and reconsider the rejection.'
    )

    return Response({
        'message': 'Document uploaded successfully',
        'document_id': doc.id,
        'uploaded_at': doc.uploaded_at.isoformat(),
        'document_url': doc.document.url if doc.document else None,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_rejection_documents(request, purchase_id):
    """Admin views documents uploaded for rejected purchase"""
    try:
        purchase = Purchase.objects.get(id=purchase_id)
    except Purchase.DoesNotExist:
        return Response({'error': 'Purchase not found'}, status=404)

    documents = PurchaseRejectionDocument.objects.filter(purchase=purchase)
    
    docs_data = []
    for doc in documents:
        docs_data.append({
            'id': doc.id,
            'document_url': doc.document.url if doc.document else None,
            'filename': doc.document.name.split('/')[-1] if doc.document else None,
            'uploaded_at': doc.uploaded_at.isoformat(),
        })

    return Response({
        'purchase_id': purchase.id,
        'transaction_id': purchase.transaction_id,
        'user': purchase.user.username,
        'rejection_reason_type': purchase.rejection_reason_type,
        'rejection_reason': purchase.rejection_reason,
        'rejection_notes': purchase.rejection_notes,
        'rejection_date': purchase.rejection_date.isoformat() if purchase.rejection_date else None,
        'documents': docs_data,
        'document_count': len(docs_data),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_revert_rejection(request, pk):
    """Admin reverts rejection (e.g., after reviewing documents) and puts purchase back to pending"""
    try:
        purchase = Purchase.objects.get(pk=pk)
    except Purchase.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if purchase.status != 'rejected':
        return Response({'error': 'Only rejected purchases can be reverted'}, status=400)

    purchase.status = 'pending'
    purchase.rejection_reason_type = None
    purchase.rejection_reason = None
    purchase.rejection_notes = None
    purchase.rejection_date = None
    purchase.save()

    create_notification(
        purchase.user,
        'purchase_reverted',
        f'Your rejected token purchase (ID: {purchase.transaction_id}) has been reverted to pending. It will be reviewed again.'
    )

    return Response({
        'message': 'Rejection reverted successfully. Purchase is now pending again.',
        'purchase_id': purchase.id,
        'status': 'pending',
    })

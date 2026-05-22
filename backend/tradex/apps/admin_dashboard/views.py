from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Sum
from django.db.models import DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import json

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.withdrawals.claims import ClaimError, approve_claim, reject_claim
from apps.withdrawals.models import PurchaseClaim, Withdrawal
from apps.sponsor.access import (
    SponsorAccessError,
    approve_sponsor_access_request,
    reject_sponsor_access_request,
)
from apps.sponsor.models import SponsorAccessRequest
from apps.notifications.utils import create_notification
from .permissions import admin_required


# ==================== AUTH VIEWS ====================
def admin_login(request):
    """Admin login page."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard:dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        
        if user and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect('admin_dashboard:dashboard')
        else:
            return render(request, 'admin/login.html', {'error': 'Invalid credentials or not an admin'})
    
    return render(request, 'admin/login.html')


@admin_required
def admin_logout(request):
    """Admin logout."""
    logout(request)
    return redirect('admin_dashboard:login')


# ==================== DASHBOARD VIEW ====================
@admin_required
def dashboard(request):
    """Admin dashboard overview."""
    settings = SystemSettings.get_settings()
    
    # Calculate stats
    total_users = User.objects.filter(is_active=True).count()
    active_users = User.objects.filter(is_active=True, purchases__status='approved').distinct().count()
    pending_purchases = Purchase.objects.filter(status='pending').count()
    approved_purchases = Purchase.objects.filter(status='approved').count()
    pending_withdrawals = Withdrawal.objects.filter(status='pending').count()
    
    context = {
        'total_coin_supply': settings.total_coin_supply,
        'sold_coins': settings.sold_coins,
        'remaining_coins': settings.remaining_coins,
        'coin_rate': settings.coin_rate,
        'total_users': total_users,
        'active_users': active_users,
        'pending_purchases': pending_purchases,
        'approved_purchases': approved_purchases,
        'pending_withdrawals': pending_withdrawals,
    }
    
    return render(request, 'admin/dashboard.html', context)


# ==================== PURCHASES VIEWS ====================
@admin_required
def purchases_list(request):
    """Admin purchases list."""
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    purchases = Purchase.objects.select_related('user').all()
    
    if status_filter:
        purchases = purchases.filter(status=status_filter)
    
    if search:
        purchases = purchases.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(transaction_id__icontains=search)
        )
    
    purchases = purchases.order_by('-created_at')
    
    context = {
        'purchases': purchases,
        'status_filter': status_filter,
        'search': search,
        'statuses': Purchase.STATUS_CHOICES,
    }
    
    return render(request, 'admin/purchases.html', context)


@admin_required
def purchase_detail(request, purchase_id):
    """Admin purchase detail view."""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    settings = SystemSettings.get_settings()
    
    context = {
        'purchase': purchase,
        'coin_rate': purchase.coin_rate_at_approval or settings.coin_rate,
        'calculated_coins': purchase.calculated_coins,
    }
    
    return render(request, 'admin/purchase_detail.html', context)


@admin_required
@require_http_methods(["POST"])
def approve_purchase(request, purchase_id):
    """Approve a purchase."""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    
    if purchase.status != 'pending':
        messages.info(request, 'Purchase is already processed. Only pending purchases can be approved.')
        return redirect('admin_dashboard:purchases')
    
    settings = SystemSettings.get_settings()
    if not settings.coin_rate or Decimal(str(settings.coin_rate)) <= 0:
        messages.error(request, 'Coin rate is invalid. Please update coin settings first.')
        return redirect('admin_dashboard:purchases')

    coins_to_assign = Decimal(str(purchase.amount)) / Decimal(str(settings.coin_rate))
    purchase.status = 'approved'
    purchase.approved_at = timezone.now()
    purchase.coin_rate_at_approval = settings.coin_rate
    purchase.approved_coin_amount = coins_to_assign
    purchase.save()
    
    settings.sold_coins = Decimal(str(settings.sold_coins or 0)) + coins_to_assign
    settings.save()
    
    messages.success(request, f'Purchase approved. Expected coins: {coins_to_assign:.8f}')
    return redirect('admin_dashboard:purchases')


@admin_required
@require_http_methods(["POST"])
def assign_coins(request, purchase_id):
    """Assign coins to user after approval."""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    
    if purchase.status != 'approved':
        messages.error(request, 'Only approved purchases can be assigned.')
        return redirect('admin_dashboard:purchases')
    
    if purchase.is_coins_assigned:
        messages.info(request, 'Coins are already assigned for this purchase.')
        return redirect('admin_dashboard:purchases')
    
    purchase.is_coins_assigned = True
    purchase.coins_assigned_at = timezone.now()
    purchase.save()

    messages.success(request, f'{purchase.calculated_coins:.8f} coins assigned successfully.')
    return redirect('admin_dashboard:purchases')


@admin_required
@require_http_methods(["POST"])
def reject_purchase(request, purchase_id):
    """Reject a purchase."""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    
    if purchase.status != 'pending':
        messages.info(request, 'Purchase is already processed. Only pending purchases can be rejected.')
        return redirect('admin_dashboard:purchases')
    
    reason = request.POST.get('reason', '')
    
    if not reason or not reason.strip():
        messages.error(request, 'Rejection reason is required.')
        return redirect('admin_dashboard:purchases')
    
    purchase.status = 'rejected'
    purchase.rejection_reason = reason
    purchase.save()
    
    messages.success(request, 'Purchase rejected successfully.')
    return redirect('admin_dashboard:purchases')


# ==================== USERS VIEWS ====================
@admin_required
def users_list(request):
    """Admin users list."""
    search = request.GET.get('search', '')
    is_active = request.GET.get('is_active', '')
    
    users = User.objects.prefetch_related('purchases', 'withdrawals').all()
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(full_name__icontains=search) |
            Q(unique_id__icontains=search)
        )
    
    if is_active:
        users = users.filter(is_active=is_active == 'true')
    
    users = users.order_by('-date_joined')
    
    context = {
        'users': users,
        'search': search,
        'is_active': is_active,
    }
    
    return render(request, 'admin/users.html', context)


@admin_required
def user_detail(request, user_id):
    """Admin user detail view."""
    user = get_object_or_404(User, id=user_id)
    purchases = user.purchases.all().order_by('-created_at')
    withdrawals = user.withdrawals.all().order_by('-created_at') if hasattr(user, 'withdrawals') else []
    sponsored_users = user.sponsored_users.select_related('sponsored_by').all().order_by('-date_joined')
    
    # Calculate coin stats
    total_purchased = sum(float(p.calculated_coins) if p.status == 'approved' else 0 for p in purchases)
    withdrawn = sum(float(w.amount) for w in withdrawals if w.status == 'completed')
    available = total_purchased - withdrawn
    
    context = {
        'user': user,
        'purchases': purchases,
        'withdrawals': withdrawals,
        'sponsored_users': sponsored_users,
        'total_purchased': round(total_purchased, 8),
        'available': round(available, 8),
        'withdrawn': round(withdrawn, 8),
    }
    
    return render(request, 'admin/user_detail.html', context)


@admin_required
@require_http_methods(["POST"])
def delete_user(request, user_id):
    """Delete a user (soft delete - set is_active to False)."""
    user = get_object_or_404(User, id=user_id)
    
    if request.user.id == user.id:
        return JsonResponse({'error': 'Cannot delete yourself'}, status=400)
    
    # Instead of hard delete, deactivate the user
    user.is_active = False
    user.save()
    
    # Adjust sold_coins if user had approved purchases
    approved_coins = sum(
        float(p.calculated_coins) for p in user.purchases.filter(status='approved')
    )
    if approved_coins > 0:
        settings = SystemSettings.get_settings()
        settings.sold_coins = max(0, (settings.sold_coins or 0) - int(approved_coins))
        settings.save()
    
    return JsonResponse({'success': True, 'message': 'User deleted'})


# ==================== SPONSOR VIEWS ====================
@admin_required
def sponsor_users_list(request):
    """List only users who have sponsored others."""
    search = request.GET.get('search', '').strip()
    min_sponsored_count = request.GET.get('min_sponsored_count', '').strip()

    sponsors = User.objects.annotate(
        sponsored_count=Count('sponsored_users', distinct=True)
    ).filter(sponsored_count__gt=0)

    if search:
        sponsors = sponsors.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(full_name__icontains=search) |
            Q(unique_id__icontains=search)
        )

    # Only apply min_count filter if explicitly provided by user
    min_count_value = None
    if min_sponsored_count:
        try:
            min_count_value = int(min_sponsored_count)
            if min_count_value > 0:
                sponsors = sponsors.filter(sponsored_count__gte=min_count_value)
        except (TypeError, ValueError):
            pass

    sponsors = sponsors.order_by('-sponsored_count', 'username')
    
    context = {
        'sponsors': sponsors,
        'search': search,
        'min_sponsored_count': min_count_value or '',
    }
    
    return render(request, 'admin/sponsor_users.html', context)


def _user_tree_payload(user):
    """Serialize one user node for hierarchy UI."""
    user.total_coins = user.total_coins or Decimal('0')
    return {
        'id': user.id,
        'username': user.username,
        'unique_id': user.unique_id,
        'email': user.email,
        'join_date': user.date_joined.strftime('%Y-%m-%d'),
        'total_purchases': user.total_purchases,
        'total_coins': str(user.total_coins),
        'child_count': user.child_count,
        'has_children': user.child_count > 0,
    }


def _children_queryset(parent_id):
    """Fetch only direct children for a sponsor node."""
    return (
        User.objects
        .filter(sponsored_by_id=parent_id)
        .annotate(
            child_count=Count('sponsored_users', distinct=True),
            total_purchases=Count('purchases', filter=Q(purchases__status='approved'), distinct=True),
            total_coins=Coalesce(
                Sum('purchases__approved_coin_amount', filter=Q(purchases__status='approved')),
                Decimal('0'),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            ),
        )
        .order_by('date_joined', 'id')
    )


@admin_required
def sponsor_hierarchy_view(request, user_id):
    """Render dedicated sponsor hierarchy page for one selected root user."""
    sponsor_options = (
        User.objects
        .annotate(sponsored_count=Count('sponsored_users', distinct=True))
        .filter(sponsored_count__gt=0)
        .order_by('username')
        .values('id', 'username', 'unique_id')[:200]
    )

    root_user = get_object_or_404(
        User.objects.annotate(
            child_count=Count('sponsored_users', distinct=True),
            total_purchases=Count('purchases', filter=Q(purchases__status='approved'), distinct=True),
            total_coins=Coalesce(
                Sum('purchases__approved_coin_amount', filter=Q(purchases__status='approved')),
                Decimal('0'),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            ),
        ),
        id=user_id,
    )

    context = {
        'root_node_json': json.dumps(_user_tree_payload(root_user)),
        'root_user_id': root_user.id,
        'sponsor_options': sponsor_options,
    }
    return render(request, 'admin/sponsor_hierarchy.html', context)


@admin_required
def sponsor_hierarchy_children_api(request, user_id):
    """Lazy-load direct children for one hierarchy node only."""
    if not User.objects.filter(id=user_id).exists():
        return JsonResponse({'error': 'User not found'}, status=404)

    children = [_user_tree_payload(child) for child in _children_queryset(user_id)]
    return JsonResponse({
        'id': user_id,
        'children_count': len(children),
        'children': children,
    })


@admin_required
def sponsor_hierarchy_search_api(request):
    """Search sponsor users for quick hierarchy navigation."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    users = (
        User.objects
        .annotate(sponsored_count=Count('sponsored_users', distinct=True))
        .filter(
            sponsored_count__gt=0,
        )
        .filter(
            Q(username__icontains=query) |
            Q(unique_id__icontains=query) |
            Q(email__icontains=query) |
            Q(full_name__icontains=query)
        )
        .order_by('username')
        .values('id', 'username', 'unique_id')[:12]
    )

    return JsonResponse({'results': list(users)})


def build_sponsor_tree(user, depth=0, max_depth=10):
    """Recursively build sponsor tree."""
    if depth > max_depth:
        return None
    
    node = {
        'id': user.id,
        'username': user.username,
        'unique_id': user.unique_id,
        'email': user.email,
        'total_purchases': user.purchases.filter(status='approved').count(),
        'total_coins': sum(float(p.calculated_coins) for p in user.purchases.filter(status='approved')),
        'children': [],
    }
    
    for child in user.sponsored_users.all():
        child_node = build_sponsor_tree(child, depth + 1, max_depth)
        if child_node:
            node['children'].append(child_node)
    
    return node


@admin_required
def sponsor_tree(request):
    """Legacy sponsor tree route now redirects to the sponsor list page."""
    return redirect('admin_dashboard:sponsor_users')


# ==================== COIN SETTINGS VIEWS ====================
@admin_required
def coin_settings(request):
    """Admin coin settings page."""
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        new_rate = request.POST.get('coin_rate')
        total_supply = request.POST.get('total_coin_supply')
        stage1_hours = request.POST.get('stage1_hours')
        stage2_hours = request.POST.get('stage2_hours')
        stage3_hours = request.POST.get('stage3_hours')
        stage1_percent = request.POST.get('stage1_percent')
        stage2_percent = request.POST.get('stage2_percent')
        profit_enabled = request.POST.get('profit_enabled') == 'on'
        profit_percentage = request.POST.get('profit_percentage')
        profit_cycle_hours = request.POST.get('profit_cycle_hours')

        try:
            if new_rate:
                settings.coin_rate = Decimal(new_rate)
            if total_supply:
                settings.total_coin_supply = Decimal(total_supply)

            if stage1_hours:
                settings.stage1_hours = int(stage1_hours)
            if stage2_hours:
                settings.stage2_hours = int(stage2_hours)
            if stage3_hours:
                settings.stage3_hours = int(stage3_hours)

            if stage1_percent:
                settings.stage1_percent = Decimal(stage1_percent)
            if stage2_percent:
                settings.stage2_percent = Decimal(stage2_percent)

            remainder_percent = Decimal('100') - Decimal(str(settings.stage1_percent)) - Decimal(str(settings.stage2_percent))
            if remainder_percent < 0:
                messages.error(request, 'Stage 1 and Stage 2 percentages cannot exceed 100%.')
                return render(request, 'admin/coin_settings.html', {'settings': settings})
            settings.stage3_percent = remainder_percent

            settings.profit_enabled = profit_enabled
            if profit_percentage is not None and profit_percentage != '':
                pct = Decimal(profit_percentage)
                if pct < 0 or pct > 100:
                    messages.error(request, 'Profit percentage must be between 0 and 100.')
                    return render(request, 'admin/coin_settings.html', {'settings': settings})
                settings.profit_percentage = pct
            if profit_cycle_hours:
                cycle_h = int(profit_cycle_hours)
                if cycle_h < 1:
                    messages.error(request, 'Profit cycle hours must be at least 1.')
                    return render(request, 'admin/coin_settings.html', {'settings': settings})
                settings.profit_cycle_hours = cycle_h

            settings.save()
            
            messages.success(request, 'Settings updated successfully')
            return redirect('admin_dashboard:coin_settings')
        except (InvalidOperation, ValueError, TypeError) as e:
            return render(request, 'admin/coin_settings.html', {
                'settings': settings,
                'error': str(e)
            })
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'admin/coin_settings.html', context)


# ==================== WITHDRAWALS VIEWS ====================
@admin_required
def withdrawals_list(request):
    """Admin withdrawals list."""
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    settings = SystemSettings.get_settings()
    
    withdrawals = Withdrawal.objects.select_related('user').all()
    
    if status_filter:
        withdrawals = withdrawals.filter(status=status_filter)
    
    if search:
        withdrawals = withdrawals.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(wallet_address__icontains=search)
        )

    withdrawals = withdrawals.order_by('-created_at')

    for withdrawal in withdrawals:
        withdrawal.usdt_equivalent = (Decimal(str(withdrawal.amount)) * Decimal(str(settings.coin_rate))).quantize(Decimal('0.00000001'))
        withdrawal.usdt_equivalent_display = f"{withdrawal.usdt_equivalent:.2f}"
    
    context = {
        'withdrawals': withdrawals,
        'status_filter': status_filter,
        'search': search,
        'statuses': Withdrawal.STATUS_CHOICES if hasattr(Withdrawal, 'STATUS_CHOICES') else [],
        'coin_rate': settings.coin_rate,
    }
    
    return render(request, 'admin/withdrawals.html', context)


@admin_required
@require_http_methods(["POST"])
def approve_withdrawal(request, withdrawal_id):
    """Approve a withdrawal from the admin dashboard."""
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)

    if withdrawal.status != 'pending':
        messages.info(request, 'Withdrawal is already processed. Only pending withdrawals can be approved.')
        return redirect('admin_dashboard:withdrawals')

    manual_tx_hash = (request.POST.get('manual_tx_hash') or '').strip()
    if not manual_tx_hash:
        messages.error(request, 'Manual transaction hash is required to approve a withdrawal.')
        return redirect('admin_dashboard:withdrawals')

    settings = SystemSettings.get_settings()
    withdrawal.status = 'approved'
    withdrawal.manual_tx_hash = manual_tx_hash
    withdrawal.approved_at = timezone.now()
    withdrawal.payment_stage = 0
    withdrawal.stage1_paid_at = None
    withdrawal.stage2_paid_at = None
    withdrawal.stage3_paid_at = None
    withdrawal.completed_at = None
    withdrawal.save()

    create_notification(
        withdrawal.user,
        'withdrawal_approved',
        f'Your withdrawal of {withdrawal.amount} coins has been approved. Stage 1 (50%) will be released after {settings.stage1_hours} hours.'
    )
    messages.success(request, 'Withdrawal approved successfully.')
    return redirect('admin_dashboard:withdrawals')


@admin_required
@require_http_methods(["POST"])
def reject_withdrawal(request, withdrawal_id):
    """Reject a withdrawal from the admin dashboard."""
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)

    if withdrawal.status != 'pending':
        messages.info(request, 'Withdrawal is already processed. Only pending withdrawals can be rejected.')
        return redirect('admin_dashboard:withdrawals')

    reason = (request.POST.get('reason') or '').strip() or 'Rejected by admin'
    withdrawal.status = 'rejected'
    withdrawal.rejection_reason = reason
    withdrawal.save(update_fields=['status', 'rejection_reason'])

    create_notification(
        withdrawal.user,
        'withdrawal_rejected',
        f'Your withdrawal of {withdrawal.amount} tokens has been rejected. Reason: {reason}'
    )
    messages.success(request, 'Withdrawal rejected successfully.')
    return redirect('admin_dashboard:withdrawals')


# ==================== STAGED CLAIM VIEWS ====================


@admin_required
def claims_list(request):
    """List all staged purchase claims for admin review."""
    qs = (
        PurchaseClaim.objects
        .select_related('user', 'purchase')
        .order_by('-created_at')
    )

    status_filter = request.GET.get('status', '')
    stage_filter = request.GET.get('stage', '')
    search = (request.GET.get('search') or '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if stage_filter:
        try:
            qs = qs.filter(stage=int(stage_filter))
        except ValueError:
            pass
    if search:
        qs = qs.filter(
            Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
            | Q(purchase__transaction_id__icontains=search)
            | Q(wallet_address__icontains=search)
        )

    context = {
        'claims': qs[:200],
        'status_filter': status_filter,
        'stage_filter': stage_filter,
        'search': search,
        'statuses': PurchaseClaim.STATUS_CHOICES,
        'stages': PurchaseClaim.STAGE_CHOICES,
    }
    return render(request, 'admin/claims.html', context)


@admin_required
@require_http_methods(["POST"])
def approve_claim_view(request, claim_id):
    """Approve a staged claim from the admin dashboard."""
    claim = get_object_or_404(PurchaseClaim, id=claim_id)
    manual_tx_hash = (request.POST.get('manual_tx_hash') or '').strip()
    try:
        approve_claim(claim, manual_tx_hash)
    except ClaimError as exc:
        messages.error(request, str(exc))
        return redirect('admin_dashboard:claims')

    messages.success(
        request,
        f'Stage {claim.stage} claim approved for {claim.user.username}.'
    )
    return redirect('admin_dashboard:claims')


@admin_required
@require_http_methods(["POST"])
def reject_claim_view(request, claim_id):
    """Reject a staged claim from the admin dashboard."""
    claim = get_object_or_404(PurchaseClaim, id=claim_id)
    reason = (request.POST.get('reason') or '').strip()
    try:
        reject_claim(claim, reason)
    except ClaimError as exc:
        messages.error(request, str(exc))
        return redirect('admin_dashboard:claims')

    messages.success(
        request,
        f'Stage {claim.stage} claim rejected for {claim.user.username}.'
    )
    return redirect('admin_dashboard:claims')


# ==================== SPONSOR ACCESS REQUEST VIEWS ====================


@admin_required
def sponsor_access_list(request):
    """List sponsor link access requests (5 USDT one-time fee)."""
    base_qs = SponsorAccessRequest.objects.select_related('user')
    qs = base_qs.order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    context = {
        'requests': qs[:200],
        'status_filter': status_filter,
        'statuses': SponsorAccessRequest.STATUS_CHOICES,
        'stats_total': base_qs.count(),
        'stats_pending': base_qs.filter(
            status=SponsorAccessRequest.STATUS_PENDING,
        ).count(),
        'stats_approved': base_qs.filter(
            status=SponsorAccessRequest.STATUS_APPROVED,
        ).count(),
        'stats_rejected': base_qs.filter(
            status=SponsorAccessRequest.STATUS_REJECTED,
        ).count(),
    }
    return render(request, 'admin/sponsor_access.html', context)


@admin_required
@require_http_methods(['POST'])
def approve_sponsor_access(request, request_id):
    req = get_object_or_404(SponsorAccessRequest, id=request_id)
    try:
        approve_sponsor_access_request(req)
        messages.success(request, f'Sponsor link {req.ref_slug} approved.')
    except SponsorAccessError as exc:
        messages.error(request, str(exc))
    return redirect('admin_dashboard:sponsor_access')


@admin_required
@require_http_methods(['POST'])
def reject_sponsor_access(request, request_id):
    req = get_object_or_404(SponsorAccessRequest, id=request_id)
    reason = (request.POST.get('reason') or '').strip()
    try:
        reject_sponsor_access_request(req, reason)
        messages.success(request, 'Sponsor access request rejected.')
    except SponsorAccessError as exc:
        messages.error(request, str(exc))
    return redirect('admin_dashboard:sponsor_access')

"""
============== Sponsor API (APIView) ==============
"""

from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from django.db.models import Sum

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.withdrawals.models import Withdrawal

from .access import (
    SponsorAccessError,
    build_public_sponsor_link,
    create_sponsor_access_request,
    resolve_active_sponsor_by_ref,
    serialize_access_status,
)
from .models import SponsorAccessRequest
from .rewards import (
    SponsorRewardError,
    claim_sponsor_reward,
    compute_all_sponsors_summary,
    compute_sponsor_reward_summary,
)


class SponsorStatsView(APIView):
    """GET sponsor network stats + link access status."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        sponsored_users = User.objects.filter(sponsored_by=user)
        active_sponsored = sponsored_users.filter(is_active=True, is_banned=False)

        sponsored_purchases = Purchase.objects.filter(
            user__in=sponsored_users, status='approved',
        )
        sponsored_withdrawals = Withdrawal.objects.filter(
            user__in=sponsored_users,
            status__in=['pending', 'approved', 'completed'],
        )

        from apps.settings_app.models import SystemSettings

        settings_obj = SystemSettings.get_settings()
        total_purchases = sum(p.amount for p in sponsored_purchases)
        total_withdrawals = sum(w.amount for w in sponsored_withdrawals)
        my_investment = (
            Purchase.objects.filter(user=user, status='approved')
            .aggregate(total=Sum('amount'))['total']
        )
        reward_coins = float(user.sponsor_earnings or 0)
        coin_rate = float(settings_obj.coin_rate or 0)
        reward_usd = reward_coins * coin_rate if coin_rate > 0 else 0.0

        payload = serialize_access_status(user)
        payload.update({
            'sponsor_code': user.sponsor_code,
            'sponsor_link': build_public_sponsor_link(user) or user.sponsor_link,
            'total_sponsored': sponsored_users.count(),
            'active_sponsored': active_sponsored.count(),
            'sponsor_earnings': reward_coins,
            'sponsor_earnings_usd': reward_usd,
            'wallet_balance': float(user.wallet_balance or 0),
            'my_investment_usdt': float(my_investment or 0),
            'direct_referrals_investment_usdt': float(total_purchases),
            'min_claim_amount_usd': float(settings_obj.sponsor_min_claim_amount_usd or 100),
            'can_claim_reward': reward_usd >= float(settings_obj.sponsor_min_claim_amount_usd or 100)
            and reward_coins > 0,
            'sponsored_purchases': float(total_purchases),
            'sponsored_withdrawals': float(total_withdrawals),
        })
        return Response(payload)


class SponsoredUsersView(APIView):
    """GET paginated list of users sponsored by the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = User.objects.filter(sponsored_by=user)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(full_name__icontains=search)

        status_filter = request.query_params.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True, is_banned=False)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        results = []
        for su in qs:
            purchases = Purchase.objects.filter(user=su, status='approved')
            withdrawals = Withdrawal.objects.filter(
                user=su, status__in=['pending', 'approved', 'completed'],
            )
            purchase_amount = sum(p.amount for p in purchases)
            withdrawal_amount = sum(w.amount for w in withdrawals)
            status_str = 'banned' if su.is_banned else ('active' if su.is_active else 'inactive')
            results.append({
                'id': su.id,
                'username': su.username,
                'full_name': su.full_name,
                'purchase_amount': float(purchase_amount),
                'sale_amount': 0,
                'withdrawal_amount': float(withdrawal_amount),
                'status': status_str,
                'date_joined': su.date_joined.isoformat(),
            })

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(results, request)
        return paginator.get_paginated_response(page)


class SponsorAccessRequestView(APIView):
    """POST submit one-time sponsor link access request."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ref_slug = request.data.get('ref_slug', '')
        payment_txid = request.data.get('payment_txid', '')
        payment_wallet = request.data.get('payment_wallet', '')

        try:
            req = create_sponsor_access_request(
                request.user,
                ref_slug,
                payment_txid,
                payment_wallet,
            )
        except SponsorAccessError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': 'Sponsor access request submitted for admin review.',
                'request': {
                    'id': req.id,
                    'ref_slug': req.ref_slug,
                    'fee_usdt': float(req.fee_usdt),
                    'status': req.status,
                    'payment_status': req.payment_status,
                },
                'access': serialize_access_status(request.user),
            },
            status=status.HTTP_201_CREATED,
        )


class PublicSponsorRefView(APIView):
    """GET resolve /ref/SLUG for registration (no auth)."""

    permission_classes = [AllowAny]

    def get(self, request, slug):
        sponsor = resolve_active_sponsor_by_ref(slug)
        if sponsor is None:
            return Response({'error': 'Invalid or inactive referral link.'}, status=404)
        return Response({
            'ref_slug': sponsor.sponsor_ref_slug,
            'sponsor_code': sponsor.sponsor_code,
            'sponsor_username': sponsor.username,
            'register_path': f"/register?ref={sponsor.sponsor_ref_slug}",
        })


class SponsorRewardSummaryView(APIView):
    """
    GET direct-level sponsor reward summary.

    Admin / superuser  → array of ALL sponsors' direct reward data (full table).
    Normal user        → single object with own direct reward data only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser

        try:
            if is_admin:
                rows = compute_all_sponsors_summary()
                return Response({'is_admin': True, 'sponsors': rows})
            else:
                payload = compute_sponsor_reward_summary(user)
                payload['is_admin'] = False
                return Response(payload)
        except Exception as exc:
            return Response(
                {'error': 'Unable to compute reward summary.', 'detail': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SponsorRewardClaimView(APIView):
    """POST atomically claim outstanding direct-level reward."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        claim_user_id = request.data.get('sponsor_id')
        user = request.user

        if claim_user_id and (user.is_staff or user.is_superuser):
            try:
                user = User.objects.get(pk=int(claim_user_id))
            except (User.DoesNotExist, ValueError, TypeError):
                return Response(
                    {'error': 'Sponsor user not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            payload = claim_sponsor_reward(user)
        except SponsorRewardError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_201_CREATED)


class AdminSetRewardPercentageView(APIView):
    """POST set per-sponsor reward percentage (admin only)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not (user.is_staff or user.is_superuser):
            return Response(
                {'error': 'Admin access required.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        sponsor_id = request.data.get('sponsor_id')
        percentage = request.data.get('reward_percentage')

        if not sponsor_id:
            return Response(
                {'error': 'sponsor_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pct = Decimal(str(percentage))
            if pct < 0 or pct > 100:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            return Response(
                {'error': 'reward_percentage must be a number between 0 and 100.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sponsor = User.objects.get(pk=int(sponsor_id))
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': 'Sponsor user not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        sponsor.sponsor_reward_percentage = pct
        sponsor.save(update_fields=['sponsor_reward_percentage'])

        summary = compute_sponsor_reward_summary(sponsor)
        return Response({
            'message': f'Reward percentage set to {pct}% for {sponsor.username}.',
            'sponsor': summary,
        })

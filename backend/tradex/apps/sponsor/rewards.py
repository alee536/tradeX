"""
============== Direct-level sponsor reward computation + claim ==============

A sponsor earns a configurable percentage of the TOTAL purchase volume made by
their DIRECT sponsored users only (first-level referrals). Second-level and
deeper users are NOT counted.

The reward percentage can be set per-sponsor by admin via
``User.sponsor_reward_percentage``. When null, the global
``SystemSettings.sponsor_percentage`` is used as fallback.

Once total direct team sales cross ``SystemSettings.sponsor_reward_threshold_usdt``,
the sponsor can claim the outstanding reward. Claim credits coins to the
sponsor's wallet via ``User.sponsor_earnings`` and is idempotent (concurrent
clicks cannot double-credit thanks to ``select_for_update``).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings

from .models import SponsorRewardClaim

EIGHT = Decimal('0.00000001')
TWO = Decimal('0.01')


class SponsorRewardError(Exception):
    """Raised when a sponsor reward claim cannot be processed."""


def _direct_team_sales_usdt(user_id: int) -> Decimal:
    """Sum approved purchase amounts of DIRECT sponsored users only."""
    direct_user_ids = list(
        User.objects.filter(sponsored_by_id=user_id).values_list('id', flat=True)
    )
    if not direct_user_ids:
        return Decimal('0')
    total = (
        Purchase.objects
        .filter(user_id__in=direct_user_ids, status='approved')
        .aggregate(total=Sum('amount'))['total']
    )
    return Decimal(str(total or 0))


def _direct_sponsored_count(user_id: int) -> int:
    """Count DIRECT sponsored users only."""
    return User.objects.filter(sponsored_by_id=user_id).count()


def _claimed_so_far_usdt(user_id: int) -> Decimal:
    total = (
        SponsorRewardClaim.objects.filter(
            user_id=user_id,
            status=SponsorRewardClaim.STATUS_APPROVED,
        )
        .aggregate(total=Sum('amount_usdt'))['total']
    )
    return Decimal(str(total or 0))


def _get_reward_percentage(user: User, settings_obj: SystemSettings) -> Decimal:
    """Per-sponsor percentage if set, else global fallback."""
    if user.sponsor_reward_percentage is not None:
        return Decimal(str(user.sponsor_reward_percentage))
    return Decimal(str(settings_obj.sponsor_percentage or 0))


def compute_sponsor_reward_summary(
    user: User,
    settings_obj: SystemSettings | None = None,
) -> dict[str, Any]:
    """
    Return the reward summary row for one sponsor — used by both the
    summary endpoint (normal user view) and the claim endpoint.
    Only counts DIRECT sponsored users.
    """
    settings_obj = settings_obj or SystemSettings.get_settings()
    reward_percentage = _get_reward_percentage(user, settings_obj)
    threshold = Decimal(str(settings_obj.sponsor_reward_threshold_usdt or 0))

    direct_count = _direct_sponsored_count(user.id)
    direct_sales = _direct_team_sales_usdt(user.id).quantize(EIGHT)

    gross_reward = (direct_sales * reward_percentage / Decimal('100')).quantize(EIGHT)
    claimed_so_far = _claimed_so_far_usdt(user.id).quantize(EIGHT)
    outstanding = max(Decimal('0'), gross_reward - claimed_so_far).quantize(EIGHT)

    is_eligible = direct_sales >= threshold and reward_percentage > 0
    can_claim = is_eligible and outstanding > 0

    if claimed_so_far > 0 and not can_claim:
        status = 'claimed'
    elif is_eligible:
        status = 'eligible'
    else:
        status = 'not_eligible'

    display_name = (user.full_name or user.username or '').strip() or user.username

    return {
        'sponsor_id': user.id,
        'sponsor_name': display_name,
        'sponsor_username': user.username,
        'direct_sponsored_count': direct_count,
        'total_direct_sales_usdt': float(direct_sales),
        'reward_percentage': float(reward_percentage.quantize(TWO)),
        'calculated_reward_usdt': float(gross_reward),
        'claimed_so_far_usdt': float(claimed_so_far),
        'outstanding_reward_usdt': float(outstanding),
        'threshold_usdt': float(threshold.quantize(EIGHT)),
        'is_eligible': is_eligible,
        'can_claim': can_claim,
        'status': status,
    }


def compute_all_sponsors_summary(
    settings_obj: SystemSettings | None = None,
) -> list[dict[str, Any]]:
    """
    Return reward summary rows for ALL sponsors (users with at least one
    direct referral). Used by admin view only.
    Optimised: batch-fetches direct counts and sales in minimal queries.
    """
    settings_obj = settings_obj or SystemSettings.get_settings()
    global_pct = Decimal(str(settings_obj.sponsor_percentage or 0))
    threshold = Decimal(str(settings_obj.sponsor_reward_threshold_usdt or 0))

    sponsors = list(
        User.objects
        .filter(sponsored_users__isnull=False)
        .distinct()
        .only(
            'id', 'username', 'full_name',
            'sponsor_reward_percentage', 'sponsor_earnings',
        )
    )
    if not sponsors:
        return []

    sponsor_ids = [s.id for s in sponsors]

    # 1) Direct sponsored user counts per sponsor — single query
    direct_counts: dict[int, int] = dict(
        User.objects
        .filter(sponsored_by_id__in=sponsor_ids)
        .values('sponsored_by_id')
        .annotate(cnt=Count('id'))
        .values_list('sponsored_by_id', 'cnt')
    )

    # 2) Map child → sponsor for purchase aggregation
    child_sponsor_pairs = list(
        User.objects
        .filter(sponsored_by_id__in=sponsor_ids)
        .values_list('id', 'sponsored_by_id')
    )
    child_to_sponsor: dict[int, int] = {uid: sid for uid, sid in child_sponsor_pairs}
    all_child_ids = list(child_to_sponsor.keys())

    # 3) Direct team sales (approved purchases of direct children) — single query
    sales_by_sponsor: dict[int, Decimal] = {sid: Decimal('0') for sid in sponsor_ids}
    if all_child_ids:
        for row in (
            Purchase.objects
            .filter(user_id__in=all_child_ids, status='approved')
            .values('user_id')
            .annotate(total=Sum('amount'))
        ):
            sponsor_id = child_to_sponsor.get(row['user_id'])
            if sponsor_id is not None:
                sales_by_sponsor[sponsor_id] += Decimal(str(row['total'] or 0))

    # 4) Already-claimed amounts per sponsor — single query
    claimed_map: dict[int, Decimal] = {}
    for row in (
        SponsorRewardClaim.objects
        .filter(user_id__in=sponsor_ids, status=SponsorRewardClaim.STATUS_APPROVED)
        .values('user_id')
        .annotate(total=Sum('amount_usdt'))
    ):
        claimed_map[row['user_id']] = Decimal(str(row['total'] or 0))

    # 5) Assemble rows
    rows: list[dict[str, Any]] = []
    for sponsor in sponsors:
        pct = (
            Decimal(str(sponsor.sponsor_reward_percentage))
            if sponsor.sponsor_reward_percentage is not None
            else global_pct
        )
        d_count = direct_counts.get(sponsor.id, 0)
        d_sales = sales_by_sponsor.get(sponsor.id, Decimal('0')).quantize(EIGHT)
        gross = (d_sales * pct / Decimal('100')).quantize(EIGHT)
        claimed = claimed_map.get(sponsor.id, Decimal('0')).quantize(EIGHT)
        outstanding = max(Decimal('0'), gross - claimed).quantize(EIGHT)
        is_eligible = d_sales >= threshold and pct > 0
        can_claim = is_eligible and outstanding > 0

        if claimed > 0 and not can_claim:
            status = 'claimed'
        elif is_eligible:
            status = 'eligible'
        else:
            status = 'not_eligible'

        display_name = (sponsor.full_name or sponsor.username or '').strip() or sponsor.username
        rows.append({
            'sponsor_id': sponsor.id,
            'sponsor_name': display_name,
            'sponsor_username': sponsor.username,
            'direct_sponsored_count': d_count,
            'total_direct_sales_usdt': float(d_sales),
            'reward_percentage': float(pct.quantize(TWO)),
            'calculated_reward_usdt': float(gross),
            'claimed_so_far_usdt': float(claimed),
            'outstanding_reward_usdt': float(outstanding),
            'threshold_usdt': float(threshold.quantize(EIGHT)),
            'is_eligible': is_eligible,
            'can_claim': can_claim,
            'status': status,
        })

    rows.sort(key=lambda r: r['total_direct_sales_usdt'], reverse=True)
    return rows


@transaction.atomic
def claim_sponsor_reward(user: User) -> dict[str, Any]:
    """
    Atomically claim the outstanding direct-level reward for one user.

    - Locks the user row (SELECT FOR UPDATE) to prevent double-credit.
    - Recomputes outstanding INSIDE the lock.
    - Credits ``User.sponsor_earnings`` (coins) using the live coin rate.
    - Writes a ``SponsorRewardClaim`` ledger row for audit.
    """
    settings_obj = SystemSettings.get_settings()
    coin_rate = Decimal(str(settings_obj.coin_rate or 0))
    if coin_rate <= 0:
        raise SponsorRewardError('Coin rate is not configured.')

    locked_user = User.objects.select_for_update().get(pk=user.pk)

    summary = compute_sponsor_reward_summary(locked_user, settings_obj)
    if not summary['can_claim']:
        if not summary['is_eligible']:
            raise SponsorRewardError(
                'Reward is not eligible — direct team sales are below the threshold '
                'or no reward percentage is set.',
            )
        raise SponsorRewardError('No outstanding reward available to claim.')

    outstanding_usdt = Decimal(str(summary['outstanding_reward_usdt']))
    amount_coins = (outstanding_usdt / coin_rate).quantize(EIGHT)

    claim = SponsorRewardClaim.objects.create(
        user=locked_user,
        total_investment_usdt=Decimal(str(summary['total_direct_sales_usdt'])),
        reward_percentage=Decimal(str(summary['reward_percentage'])),
        gross_reward_usdt=Decimal(str(summary['calculated_reward_usdt'])),
        amount_usdt=outstanding_usdt,
        amount_coins=amount_coins,
        coin_rate_at_claim=coin_rate,
        status=SponsorRewardClaim.STATUS_APPROVED,
    )

    locked_user.sponsor_earnings = (
        Decimal(str(locked_user.sponsor_earnings or 0)) + amount_coins
    )
    locked_user.save(update_fields=['sponsor_earnings'])

    fresh_summary = compute_sponsor_reward_summary(locked_user, settings_obj)
    fresh_summary['claim'] = {
        'id': claim.id,
        'amount_usdt': float(claim.amount_usdt),
        'amount_coins': float(claim.amount_coins),
        'coin_rate_at_claim': float(claim.coin_rate_at_claim),
        'created_at': claim.created_at.isoformat() if claim.created_at else timezone.now().isoformat(),
    }
    return fresh_summary

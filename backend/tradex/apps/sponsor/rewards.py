"""
Direct-level sponsor rewards: accrue coins on purchase approval, claim to main wallet.

- Commission applies only to DIRECT referrals' approved purchases.
- Accrued balance lives in ``User.sponsor_earnings`` (coins).
- Claim compares USD equivalent (coins × coin_rate) to ``sponsor_min_claim_amount_usd``.
- Successful claim moves coins to ``User.wallet_balance`` (withdrawable main wallet).
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


def get_reward_percentage_for_user(user: User, settings_obj: SystemSettings | None = None) -> Decimal:
    settings_obj = settings_obj or SystemSettings.get_settings()
    if user.sponsor_reward_percentage is not None:
        return Decimal(str(user.sponsor_reward_percentage))
    return Decimal(str(settings_obj.sponsor_percentage or 0))


def _direct_team_sales_usdt(user_id: int) -> Decimal:
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
    return User.objects.filter(sponsored_by_id=user_id).count()


def _reward_coins_and_usd(user: User, settings_obj: SystemSettings) -> tuple[Decimal, Decimal]:
    coins = Decimal(str(user.sponsor_earnings or 0)).quantize(EIGHT)
    rate = Decimal(str(settings_obj.coin_rate or 0))
    usd = (coins * rate).quantize(TWO) if rate > 0 else Decimal('0')
    return coins, usd


def _min_claim_usd(settings_obj: SystemSettings) -> Decimal:
    return Decimal(str(settings_obj.sponsor_min_claim_amount_usd or 100)).quantize(TWO)


def compute_sponsor_reward_summary(
    user: User,
    settings_obj: SystemSettings | None = None,
) -> dict[str, Any]:
    settings_obj = settings_obj or SystemSettings.get_settings()
    reward_percentage = get_reward_percentage_for_user(user, settings_obj)
    min_claim_usd = _min_claim_usd(settings_obj)

    direct_count = _direct_sponsored_count(user.id)
    direct_sales = _direct_team_sales_usdt(user.id).quantize(EIGHT)
    reward_coins, reward_usd = _reward_coins_and_usd(user, settings_obj)

    theoretical_gross = (direct_sales * reward_percentage / Decimal('100')).quantize(EIGHT)
    can_claim = reward_coins > 0 and reward_usd >= min_claim_usd

    if reward_coins <= 0:
        status = 'empty'
    elif can_claim:
        status = 'claimable'
    else:
        status = 'accumulating'

    display_name = (user.full_name or user.username or '').strip() or user.username

    return {
        'sponsor_id': user.id,
        'sponsor_name': display_name,
        'sponsor_username': user.username,
        'direct_sponsored_count': direct_count,
        'total_direct_sales_usdt': float(direct_sales),
        'reward_percentage': float(reward_percentage.quantize(TWO)),
        'reward_coins': float(reward_coins),
        'reward_usd': float(reward_usd),
        'min_claim_amount_usd': float(min_claim_usd),
        'theoretical_reward_usdt': float(theoretical_gross),
        'calculated_reward_usdt': float(reward_usd),
        'outstanding_reward_usdt': float(reward_usd),
        'threshold_usdt': float(min_claim_usd),
        'is_eligible': can_claim,
        'can_claim': can_claim,
        'status': status,
        'wallet_balance': float(Decimal(str(user.wallet_balance or 0))),
    }


def compute_all_sponsors_summary(
    settings_obj: SystemSettings | None = None,
) -> list[dict[str, Any]]:
    settings_obj = settings_obj or SystemSettings.get_settings()
    sponsors = list(
        User.objects
        .filter(sponsored_users__isnull=False)
        .distinct()
        .only(
            'id', 'username', 'full_name',
            'sponsor_reward_percentage', 'sponsor_earnings', 'wallet_balance',
        )
    )
    return [compute_sponsor_reward_summary(s, settings_obj) for s in sponsors]


@transaction.atomic
def claim_sponsor_reward(user: User) -> dict[str, Any]:
    """
    Transfer accumulated sponsor_earnings to wallet_balance for the logged-in user.
    """
    settings_obj = SystemSettings.get_settings()
    coin_rate = Decimal(str(settings_obj.coin_rate or 0))
    if coin_rate <= 0:
        raise SponsorRewardError('Coin rate is not configured.')

    locked_user = User.objects.select_for_update().get(pk=user.pk)
    summary = compute_sponsor_reward_summary(locked_user, settings_obj)

    if not summary['can_claim']:
        reward_usd = Decimal(str(summary['reward_usd']))
        min_claim = _min_claim_usd(settings_obj)
        if reward_usd < min_claim:
            raise SponsorRewardError(
                f'Minimum claim amount is ${min_claim}. '
                f'Your reward balance is ${reward_usd}.',
            )
        raise SponsorRewardError('No sponsor reward balance available to claim.')

    amount_coins = Decimal(str(locked_user.sponsor_earnings or 0)).quantize(EIGHT)
    if amount_coins <= 0:
        raise SponsorRewardError('No sponsor reward balance available to claim.')

    amount_usdt = (amount_coins * coin_rate).quantize(EIGHT)
    direct_sales = _direct_team_sales_usdt(locked_user.id)
    reward_pct = get_reward_percentage_for_user(locked_user, settings_obj)
    gross_theoretical = (direct_sales * reward_pct / Decimal('100')).quantize(EIGHT)

    claim = SponsorRewardClaim.objects.create(
        user=locked_user,
        total_investment_usdt=direct_sales,
        reward_percentage=reward_pct,
        gross_reward_usdt=gross_theoretical,
        amount_usdt=amount_usdt,
        amount_coins=amount_coins,
        coin_rate_at_claim=coin_rate,
        status=SponsorRewardClaim.STATUS_APPROVED,
    )

    locked_user.wallet_balance = Decimal(str(locked_user.wallet_balance or 0)) + amount_coins
    locked_user.sponsor_earnings = Decimal('0')
    locked_user.save(update_fields=['wallet_balance', 'sponsor_earnings'])

    fresh_summary = compute_sponsor_reward_summary(locked_user, settings_obj)
    fresh_summary['claim'] = {
        'id': claim.id,
        'amount_usdt': float(claim.amount_usdt),
        'amount_coins': float(claim.amount_coins),
        'coin_rate_at_claim': float(claim.coin_rate_at_claim),
        'created_at': claim.created_at.isoformat() if claim.created_at else timezone.now().isoformat(),
    }
    return fresh_summary

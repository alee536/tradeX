"""
Credit sponsor commission when a direct referral's purchase is approved.
"""

from __future__ import annotations

from decimal import Decimal

from apps.accounts.models import User
from apps.settings_app.models import SystemSettings

from .rewards import get_reward_percentage_for_user

EIGHT = Decimal('0.00000001')


def credit_sponsor_for_approved_purchase(sponsor: User, coin_amount) -> Decimal:
    """
    Add commission coins to sponsor_earnings (direct referrals only).
    Caller must ensure *sponsor* is the purchaser's direct parent.
    """
    settings_obj = SystemSettings.get_settings()
    percentage = get_reward_percentage_for_user(sponsor, settings_obj)
    if percentage <= 0:
        return Decimal('0')

    coins = Decimal(str(coin_amount or 0))
    if coins <= 0:
        return Decimal('0')

    earning = (coins * percentage / Decimal('100')).quantize(EIGHT)
    if earning <= 0:
        return Decimal('0')

    sponsor.sponsor_earnings = Decimal(str(sponsor.sponsor_earnings or 0)) + earning
    sponsor.save(update_fields=['sponsor_earnings'])
    return earning

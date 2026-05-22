"""Staged claims use deposit + admin profit% as the claimable total."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.withdrawals.claims import create_claim, get_purchase_schedule


class ProfitUnifiedClaimTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.settings = SystemSettings.get_settings()
        cls.settings.profit_enabled = True
        cls.settings.profit_percentage = Decimal('10')
        cls.settings.stage1_hours = 0
        cls.settings.stage2_hours = 0
        cls.settings.stage3_hours = 0
        cls.settings.stage1_percent = Decimal('50')
        cls.settings.stage2_percent = Decimal('25')
        cls.settings.stage3_percent = Decimal('25')
        cls.settings.coin_rate = Decimal('1')
        cls.settings.save()

        cls.user = User.objects.create_user(
            username='profit_claim_user',
            email='profit_claim@example.com',
            password='testpass123',
        )
        now = timezone.now()
        cls.purchase = Purchase.objects.create(
            user=cls.user,
            transaction_id='TX24XPROFIT',
            amount=Decimal('100'),
            status='approved',
            approved_at=now - timedelta(hours=1),
            is_coins_assigned=True,
            coins_assigned_at=now - timedelta(hours=1),
            approved_coin_amount=Decimal('100'),
            coin_rate_at_approval=Decimal('1'),
        )

    def test_schedule_total_includes_ten_percent_profit(self):
        schedule = get_purchase_schedule(self.purchase, self.settings)
        self.assertEqual(schedule['base_usdt'], 100.0)
        self.assertEqual(schedule['profit_usdt'], 10.0)
        self.assertEqual(schedule['total_usdt'], 110.0)
        self.assertEqual(schedule['total_coins'], 110.0)
        self.assertEqual(schedule['stages'][0]['amount_usdt'], 55.0)
        self.assertEqual(schedule['stages'][0]['amount_coins'], 55.0)

    def test_stage_claim_amounts_use_total_with_profit(self):
        claim1 = create_claim(self.user, self.purchase, 1)
        self.assertEqual(float(claim1.amount_coins), 55.0)
        claim2 = create_claim(self.user, self.purchase, 2)
        self.assertEqual(float(claim2.amount_coins), 27.5)
        claim3 = create_claim(self.user, self.purchase, 3)
        self.assertEqual(float(claim3.amount_coins), 27.5)

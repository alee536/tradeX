from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.settings_app.profit import ProfitClaimError, compute_user_profit_summary, execute_profit_claim


class ProfitSummaryTests(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()
        self.settings.profit_enabled = True
        self.settings.profit_percentage = Decimal('10')
        self.settings.save()
        self.user = User.objects.create_user(
            username='profit_sum_user',
            email='profit_sum@example.com',
            password='testpass123',
        )
        Purchase.objects.create(
            user=self.user,
            transaction_id='TX24XSUM',
            amount=Decimal('100'),
            status='approved',
            is_coins_assigned=True,
            approved_coin_amount=Decimal('100'),
            coin_rate_at_approval=Decimal('1'),
        )

    def test_summary_shows_total_with_profit(self):
        summary = compute_user_profit_summary(self.user, self.settings)
        self.assertTrue(summary['enabled'])
        self.assertEqual(summary['base_usdt'], 100.0)
        self.assertEqual(summary['estimated_profit_usdt'], 10.0)
        self.assertEqual(summary['total_after_profit_usdt'], 110.0)
        self.assertFalse(summary['can_claim'])

    def test_separate_profit_claim_disabled(self):
        with self.assertRaises(ProfitClaimError):
            execute_profit_claim(self.user)

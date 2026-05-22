"""Dashboard shows deposit + profit% immediately on purchase approval."""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings


class DashboardProfitDisplayTests(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()
        self.settings.profit_enabled = True
        self.settings.profit_percentage = Decimal('10')
        self.settings.coin_rate = Decimal('1')
        self.settings.save()

        self.user = User.objects.create_user(
            username='dash_profit_user',
            email='dash_profit@example.com',
            password='testpass123',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_dashboard_shows_profit_before_coins_assigned(self):
        Purchase.objects.create(
            user=self.user,
            transaction_id='TX24XDASH',
            amount=Decimal('100'),
            status='approved',
            approved_at=timezone.now(),
            is_coins_assigned=False,
            approved_coin_amount=Decimal('100'),
            coin_rate_at_approval=Decimal('1'),
        )

        response = self.client.get('/api/dashboard/summary')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['total_purchased'], 110.0)
        self.assertEqual(data['profit']['base_usdt'], 100.0)
        self.assertEqual(data['profit']['estimated_profit_usdt'], 10.0)
        self.assertEqual(data['profit']['total_after_profit_usdt'], 110.0)
        self.assertEqual(data['available_withdrawal'], 0.0)
        self.assertEqual(data['pending_withdrawal'], 110.0)

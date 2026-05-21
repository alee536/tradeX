"""
QA test suite: Admin profit percentage feature
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.settings_app.profit import compute_user_profit_summary
from apps.settings_app.serializers import SystemSettingsSerializer


class ProfitCalculationTests(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()
        self.settings.profit_enabled = True
        self.settings.profit_percentage = Decimal('10')
        self.settings.profit_cycle_hours = 72
        self.settings.save()

        self.user = User.objects.create_user(
            username='profit_qa@test.com',
            email='profit_qa@test.com',
            password='testpass123',
            full_name='Profit QA User',
        )

    def test_disabled_returns_enabled_false(self):
        self.settings.profit_enabled = False
        self.settings.save()
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertEqual(result, {'enabled': False})

    def test_10_percent_on_100_usdt(self):
        now = timezone.now()
        Purchase.objects.create(
            user=self.user,
            amount=Decimal('100'),
            status='approved',
            is_coins_assigned=True,
            approved_at=now - timedelta(hours=1),
            coins_assigned_at=now - timedelta(hours=1),
        )
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['base_usdt'], 100.0)
        self.assertEqual(result['estimated_profit_usdt'], 10.0)
        self.assertEqual(result['total_after_profit_usdt'], 110.0)
        self.assertEqual(result['profit_percentage'], 10.0)

    def test_pending_purchase_excluded(self):
        Purchase.objects.create(
            user=self.user,
            amount=Decimal('500'),
            status='pending',
            is_coins_assigned=False,
        )
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertEqual(result['base_usdt'], 0.0)

    def test_approved_without_assign_excluded(self):
        Purchase.objects.create(
            user=self.user,
            amount=Decimal('200'),
            status='approved',
            is_coins_assigned=False,
            approved_at=timezone.now(),
        )
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertEqual(result['base_usdt'], 0.0)

    def test_multiple_purchases_summed(self):
        now = timezone.now()
        for amt in (100, 50):
            Purchase.objects.create(
                user=self.user,
                amount=Decimal(str(amt)),
                status='approved',
                is_coins_assigned=True,
                approved_at=now - timedelta(hours=2),
                coins_assigned_at=now - timedelta(hours=2),
            )
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertEqual(result['base_usdt'], 150.0)
        self.assertEqual(result['estimated_profit_usdt'], 15.0)
        self.assertEqual(result['total_after_profit_usdt'], 165.0)

    def test_next_claim_within_cycle(self):
        now = timezone.now()
        assigned = now - timedelta(hours=10)
        Purchase.objects.create(
            user=self.user,
            amount=Decimal('100'),
            status='approved',
            is_coins_assigned=True,
            approved_at=assigned,
            coins_assigned_at=assigned,
        )
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertIsNotNone(result['next_claim_at'])
        self.assertGreater(result['seconds_until_claim'], 0)
        expected_next = assigned + timedelta(hours=72)
        self.assertIn(expected_next.isoformat()[:16], result['next_claim_at'][:16])

    def test_zero_percentage_no_crash(self):
        self.settings.profit_percentage = Decimal('0')
        self.settings.save()
        result = compute_user_profit_summary(self.user, self.settings)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['estimated_profit_usdt'], 0.0)


class ProfitSerializerValidationTests(TestCase):
    def test_rejects_profit_over_100(self):
        settings = SystemSettings.get_settings()
        ser = SystemSettingsSerializer(settings, data={'profit_percentage': 150}, partial=True)
        self.assertFalse(ser.is_valid())
        self.assertIn('profit_percentage', ser.errors)

    def test_rejects_negative_profit(self):
        settings = SystemSettings.get_settings()
        ser = SystemSettingsSerializer(settings, data={'profit_percentage': -5}, partial=True)
        self.assertFalse(ser.is_valid())

    def test_rejects_zero_cycle_hours(self):
        settings = SystemSettings.get_settings()
        ser = SystemSettingsSerializer(settings, data={'profit_cycle_hours': 0}, partial=True)
        self.assertFalse(ser.is_valid())

    def test_accepts_valid_profit_fields(self):
        settings = SystemSettings.get_settings()
        ser = SystemSettingsSerializer(
            settings,
            data={'profit_enabled': True, 'profit_percentage': 15, 'profit_cycle_hours': 48},
            partial=True,
        )
        self.assertTrue(ser.is_valid(), ser.errors)


class DashboardProfitAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.settings = SystemSettings.get_settings()
        self.settings.profit_enabled = True
        self.settings.profit_percentage = Decimal('10')
        self.settings.profit_cycle_hours = 72
        self.settings.save()

        self.user = User.objects.create_user(
            username='api_qa@test.com',
            email='api_qa@test.com',
            password='testpass123',
            full_name='API QA',
        )
        self.client.force_authenticate(user=self.user)

    def test_dashboard_includes_profit_key(self):
        response = self.client.get('/api/dashboard/summary')
        self.assertEqual(response.status_code, 200)
        self.assertIn('profit', response.data)
        self.assertTrue(response.data['profit']['enabled'])

    def test_dashboard_profit_disabled(self):
        self.settings.profit_enabled = False
        self.settings.save()
        response = self.client.get('/api/dashboard/summary')
        self.assertEqual(response.data['profit'], {'enabled': False})

    def test_unauthenticated_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/dashboard/summary')
        self.assertIn(response.status_code, (401, 403))


class AdminSettingsProfitAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='staff_qa@test.com',
            email='staff_qa@test.com',
            password='testpass123',
            full_name='Staff QA',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_admin_patch_rejects_invalid_profit(self):
        response = self.client.patch(
            '/api/admin/settings',
            {'profit_percentage': 150},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_patch_saves_profit_fields(self):
        response = self.client.patch(
            '/api/admin/settings',
            {'profit_enabled': True, 'profit_percentage': 12.5, 'profit_cycle_hours': 24},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data['profit_percentage']), 12.5)
        settings = SystemSettings.get_settings()
        self.assertTrue(settings.profit_enabled)
        self.assertEqual(int(settings.profit_cycle_hours), 24)


class PublicSettingsProfitTests(TestCase):
    def test_public_settings_exposes_profit_when_enabled(self):
        settings = SystemSettings.get_settings()
        settings.profit_enabled = True
        settings.profit_percentage = Decimal('12')
        settings.profit_cycle_hours = 24
        settings.save()

        client = APIClient()
        response = client.get('/api/settings/public')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['profit_enabled'])
        self.assertEqual(float(response.data['profit_percentage']), 12.0)

    def test_public_settings_hides_percentage_when_disabled(self):
        settings = SystemSettings.get_settings()
        settings.profit_enabled = False
        settings.save()

        client = APIClient()
        response = client.get('/api/settings/public')
        self.assertFalse(response.data['profit_enabled'])
        self.assertNotIn('profit_percentage', response.data)

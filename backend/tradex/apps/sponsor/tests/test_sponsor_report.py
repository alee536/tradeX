"""
Tests for flat admin sponsor report (full downline aggregation).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.sponsor.report import get_sponsor_report_rows

User = get_user_model()


def _user(username, email, password='testpass123', **extra):
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        full_name=extra.pop('full_name', username.title()),
        **extra,
    )


class SponsorReportServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        settings = SystemSettings.get_settings()
        settings.coin_rate = Decimal('2')
        settings.sponsor_percentage = Decimal('5')
        settings.save()

        cls.ali = _user('ali', 'ali@test.com', full_name='Ali')
        cls.ahmed = _user('ahmed', 'ahmed@test.com', full_name='Ahmed', sponsored_by=cls.ali)
        cls.sara = _user('sara', 'sara@test.com', sponsored_by=cls.ali)
        cls.fatima = _user('fatima', 'fatima@test.com', sponsored_by=cls.ahmed)

        Purchase.objects.create(
            user=cls.ahmed,
            transaction_id='TX24XALI1',
            amount=Decimal('1000'),
            status='approved',
            approved_coin_amount=Decimal('500'),
        )
        Purchase.objects.create(
            user=cls.sara,
            transaction_id='TX24XALI2',
            amount=Decimal('1000'),
            status='approved',
            approved_coin_amount=Decimal('500'),
        )
        Purchase.objects.create(
            user=cls.fatima,
            transaction_id='TX24XAHMED1',
            amount=Decimal('500'),
            status='approved',
            approved_coin_amount=Decimal('250'),
        )

        cls.ali.sponsor_earnings = Decimal('50')
        cls.ali.save(update_fields=['sponsor_earnings'])
        cls.ahmed.sponsor_earnings = Decimal('12.5')
        cls.ahmed.save(update_fields=['sponsor_earnings'])

    def test_ali_downline_includes_nested_users(self):
        rows = {r['sponsor_username']: r for r in get_sponsor_report_rows()}
        self.assertIn('ali', rows)
        self.assertIn('ahmed', rows)
        self.assertEqual(rows['ali']['sponsored_users_count'], 3)
        self.assertEqual(rows['ali']['direct_sponsored_count'], 2)
        self.assertAlmostEqual(rows['ali']['total_investment_usdt'], 2500.0)
        self.assertAlmostEqual(rows['ali']['total_earning'], 50.0)

    def test_child_sponsor_has_own_row(self):
        rows = {r['sponsor_username']: r for r in get_sponsor_report_rows()}
        ahmed = rows['ahmed']
        self.assertEqual(ahmed['sponsored_users_count'], 1)
        self.assertEqual(ahmed['direct_sponsored_count'], 1)
        self.assertAlmostEqual(ahmed['total_investment_usdt'], 500.0)
        self.assertAlmostEqual(ahmed['total_earning'], 12.5)

    def test_search_filters_sponsors(self):
        rows = get_sponsor_report_rows(search='ahmed')
        usernames = {r['sponsor_username'] for r in rows}
        self.assertEqual(usernames, {'ahmed'})

    def test_order_by_investment_desc(self):
        rows = get_sponsor_report_rows(order_by='-total_investment_usdt')
        self.assertGreaterEqual(
            rows[0]['total_investment_usdt'],
            rows[-1]['total_investment_usdt'],
        )

    def test_user_without_referrals_not_listed(self):
        lone = _user('lone', 'lone@test.com')
        rows = get_sponsor_report_rows()
        self.assertNotIn(lone.username, {r['sponsor_username'] for r in rows})


class SponsorReportApiTests(TestCase):
    def setUp(self):
        self.admin = _user('admin_report', 'admin_report@test.com', is_staff=True, is_superuser=True)
        self.user = _user('buyer_report', 'buyer_report@test.com')
        self.sponsor = _user('sp_report', 'sp_report@test.com')
        child = _user('child_report', 'child_report@test.com', sponsored_by=self.sponsor)
        Purchase.objects.create(
            user=child,
            transaction_id='TX24XREPORTAPI',
            amount=Decimal('100'),
            status='approved',
            approved_coin_amount=Decimal('50'),
        )
        self.client = APIClient()

    def test_admin_can_access_report_api(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/admin/sponsor/report')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/admin/sponsor/report')
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_unauthorized(self):
        response = self.client.get('/api/admin/sponsor/report')
        self.assertIn(response.status_code, (401, 403))


class SponsorReportDashboardTests(TestCase):
    def setUp(self):
        self.admin = _user('admin_dash', 'admin_dash@test.com', is_staff=True)
        self.sponsor = _user('dash_sp', 'dash_sp@test.com')
        _user('dash_child', 'dash_child@test.com', sponsored_by=self.sponsor)
        self.client = Client()

    def test_dashboard_page_requires_login(self):
        url = reverse('admin_dashboard:sponsor_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_dashboard_page_renders_for_staff(self):
        self.client.login(username='admin_dash', password='testpass123')
        url = reverse('admin_dashboard:sponsor_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sponsor Report')
        self.assertContains(response, 'dash_sp')

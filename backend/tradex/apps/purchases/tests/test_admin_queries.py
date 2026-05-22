"""
Tests for admin purchase list helpers: TXID search, expected coins, display rows.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.purchases.admin_queries import (
    build_admin_purchase_rows,
    expected_coins_for_purchase,
    filter_admin_purchases,
)
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings


class AdminPurchaseQueriesTests(TestCase):
    """Unit tests for filter_admin_purchases and coin display helpers."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SystemSettings.get_settings()
        cls.settings.coin_rate = Decimal('2')
        cls.settings.save()

        cls.user = User.objects.create_user(
            username='purchase_admin_user',
            email='padmin@example.com',
            password='testpass123',
        )
        cls.other_user = User.objects.create_user(
            username='other_user',
            email='other@example.com',
            password='testpass123',
        )
        cls.admin = User.objects.create_user(
            username='purchase_admin',
            email='admin_purchase@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )

        cls.purchase_with_txid = Purchase.objects.create(
            user=cls.user,
            transaction_id='TX24XADMINTEST1',
            amount=Decimal('100'),
            txid='0xabc123def456paymenthash',
            wallet_address='TRXwallet123456789',
            status='pending',
        )
        cls.purchase_no_txid = Purchase.objects.create(
            user=cls.other_user,
            transaction_id='TX24XADMINTEST2',
            amount=Decimal('50'),
            txid='',
            status='pending',
        )
        cls.purchase_approved = Purchase.objects.create(
            user=cls.user,
            transaction_id='TX24XADMINTEST3',
            amount=Decimal('200'),
            txid='uniquehash999',
            status='approved',
            approved_coin_amount=Decimal('75'),
            coin_rate_at_approval=Decimal('2'),
        )

    def test_filter_by_partial_txid(self):
        results = list(filter_admin_purchases(search='abc123def'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.purchase_with_txid.id)

    def test_filter_by_txid_case_insensitive(self):
        results = list(filter_admin_purchases(search='UNIQUEHASH'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.purchase_approved.id)

    def test_filter_by_internal_transaction_id(self):
        results = list(filter_admin_purchases(search='TX24XADMINTEST2'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.purchase_no_txid.id)

    def test_filter_empty_search_returns_all_ordered(self):
        results = list(filter_admin_purchases())
        self.assertEqual(len(results), 3)
        self.assertGreaterEqual(
            results[0].created_at,
            results[1].created_at,
        )

    def test_filter_whitespace_search_ignored(self):
        results = list(filter_admin_purchases(search='   '))
        self.assertEqual(len(results), 3)

    def test_filter_status_pending(self):
        results = list(filter_admin_purchases(status_filter='pending'))
        self.assertEqual(len(results), 2)
        ids = {p.id for p in results}
        self.assertIn(self.purchase_with_txid.id, ids)
        self.assertIn(self.purchase_no_txid.id, ids)

    def test_filter_special_chars_safe(self):
        """ORM icontains must not break on SQL-like input."""
        results = list(filter_admin_purchases(search="'; DROP TABLE purchases;--"))
        self.assertEqual(len(results), 0)

    def test_expected_coins_uses_approved_amount_when_set(self):
        coins = expected_coins_for_purchase(self.purchase_approved, self.settings)
        self.assertEqual(coins, Decimal('75'))

    def test_expected_coins_from_amount_and_rate_when_pending(self):
        coins = expected_coins_for_purchase(self.purchase_with_txid, self.settings)
        self.assertEqual(coins, Decimal('50.00000000'))

    def test_expected_coins_zero_when_rate_invalid(self):
        bad_settings = SystemSettings.get_settings()
        bad_settings.coin_rate = Decimal('0')
        bad_settings.save()
        purchase = Purchase.objects.create(
            user=self.user,
            transaction_id='TX24XBADRATE',
            amount=Decimal('10'),
            status='pending',
        )
        coins = expected_coins_for_purchase(purchase, bad_settings)
        self.assertEqual(coins, Decimal('0'))

    def test_build_admin_purchase_rows_display(self):
        purchases = Purchase.objects.filter(id=self.purchase_with_txid.id)
        rows = build_admin_purchase_rows(purchases, self.settings)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['txid_display'], '0xabc123def456paymenthash')
        self.assertEqual(row['txid_for_copy'], '0xabc123def456paymenthash')
        self.assertEqual(row['wallet_display'], 'TRXwallet123456789')
        self.assertFalse(row['has_screenshot'])

    def test_build_row_empty_txid_and_wallet(self):
        purchases = Purchase.objects.filter(id=self.purchase_no_txid.id)
        rows = build_admin_purchase_rows(purchases, self.settings)
        row = rows[0]
        self.assertEqual(row['txid_display'], '—')
        self.assertEqual(row['txid_for_copy'], '')
        self.assertEqual(row['wallet_display'], '—')


class AdminPurchasesListViewTests(TestCase):
    """Integration: purchases_list renders TXID in HTML and search works."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SystemSettings.get_settings()
        cls.settings.coin_rate = Decimal('1')
        cls.settings.save()

        cls.admin = User.objects.create_user(
            username='view_admin',
            email='view_admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )
        cls.user = User.objects.create_user(
            username='view_user',
            email='view_user@example.com',
            password='testpass123',
        )
        cls.purchase = Purchase.objects.create(
            user=cls.user,
            transaction_id='TX24XVIEWTEST',
            amount=Decimal('25'),
            txid='blockchain-txid-view-test',
            wallet_address='wallet-for-view-test',
            status='pending',
        )

    def setUp(self):
        self.client = Client()

    def test_purchases_list_requires_admin(self):
        url = reverse('admin_dashboard:purchases')
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))

    def test_purchases_list_shows_txid_and_search(self):
        self.client.login(username='view_admin', password='testpass123')
        url = reverse('admin_dashboard:purchases')

        response = self.client.get(url, {'search': 'blockchain-txid-view'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('blockchain-txid-view-test', content)
        self.assertIn('wallet-for-view-test', content)
        self.assertIn('Copy TXID', content)
        self.assertIn('$25', content)

        empty = self.client.get(url, {'search': 'nonexistent-txid-xyz'})
        self.assertEqual(empty.status_code, 200)
        self.assertNotIn('blockchain-txid-view-test', empty.content.decode())

"""
Admin notification tests — verifies that staff users receive in-app
notifications whenever a purchase or sponsor access payment is submitted.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.utils import notify_admins
from apps.settings_app.models import SystemSettings


def _make_user(username, email, is_staff=False):
    u = User.objects.create_user(
        username=username,
        email=email,
        password='testpass123',
        is_staff=is_staff,
    )
    return u


class NotifyAdminsHelperTests(TestCase):
    """Unit tests for the notify_admins() utility."""

    def test_notifies_all_staff_users(self):
        admin1 = _make_user('admin1', 'admin1@test.com', is_staff=True)
        admin2 = _make_user('admin2', 'admin2@test.com', is_staff=True)
        _make_user('regular', 'user@test.com', is_staff=False)

        notify_admins('test_event', 'Hello admins')

        self.assertEqual(Notification.objects.filter(type='test_event').count(), 2)
        recipients = set(
            Notification.objects.filter(type='test_event').values_list('user_id', flat=True)
        )
        self.assertIn(admin1.id, recipients)
        self.assertIn(admin2.id, recipients)

    def test_non_staff_user_not_notified(self):
        _make_user('regular', 'user@test.com', is_staff=False)
        notify_admins('test_event', 'Hello admins')
        self.assertEqual(Notification.objects.filter(type='test_event').count(), 0)

    def test_no_admins_does_not_crash(self):
        """If there are no staff users, bulk_create([]) should be a no-op."""
        try:
            notify_admins('test_event', 'No admins yet')
        except Exception as exc:
            self.fail(f'notify_admins raised unexpectedly: {exc}')
        self.assertEqual(Notification.objects.filter(type='test_event').count(), 0)

    def test_notification_fields_are_correct(self):
        admin = _make_user('admin', 'admin@test.com', is_staff=True)
        notify_admins('admin_purchase_submitted', 'New $100 purchase')
        notif = Notification.objects.get(user=admin, type='admin_purchase_submitted')
        self.assertEqual(notif.message, 'New $100 purchase')
        self.assertFalse(notif.is_read)

    def test_superuser_also_notified(self):
        su = User.objects.create_superuser(
            username='superuser',
            email='su@test.com',
            password='testpass123',
        )
        notify_admins('test_event', 'Superuser check')
        self.assertEqual(
            Notification.objects.filter(user=su, type='test_event').count(), 1
        )


class PurchaseSubmitAdminNotificationTests(TestCase):
    """Integration tests — submitting a purchase via the API triggers admin notifications."""

    def setUp(self):
        SystemSettings.objects.get_or_create(pk=1)
        self.admin = _make_user('admin', 'admin@s24tx.com', is_staff=True)
        self.user = _make_user('buyer', 'buyer@test.com', is_staff=False)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_admin_notified_on_purchase_submit(self):
        payload = {
            'amount': '100.00',
            'txid': 'TXID_HASH_001',
            'wallet_address': '0xABCDEF1234567890',
        }
        response = self.client.post('/api/purchases', payload)
        self.assertEqual(response.status_code, 201)

        admin_notif = Notification.objects.filter(
            user=self.admin,
            type='admin_purchase_submitted',
        ).first()
        self.assertIsNotNone(admin_notif, 'Admin should receive a notification on purchase submit')
        self.assertIn('100', admin_notif.message)
        self.assertFalse(admin_notif.is_read)

    def test_user_still_gets_their_own_notification(self):
        payload = {
            'amount': '50.00',
            'txid': 'TXID_HASH_002',
            'wallet_address': '0xABCDEF1234567890',
        }
        self.client.post('/api/purchases', payload)
        user_notif = Notification.objects.filter(
            user=self.user,
            type='purchase_submitted',
        ).first()
        self.assertIsNotNone(user_notif, 'User should also still get their own notification')

    def test_multiple_admins_all_notified_on_purchase(self):
        admin2 = _make_user('admin2', 'admin2@s24tx.com', is_staff=True)
        payload = {
            'amount': '200.00',
            'txid': 'TXID_HASH_003',
            'wallet_address': '0xABCDEF1234567890',
        }
        self.client.post('/api/purchases', payload)
        self.assertEqual(
            Notification.objects.filter(type='admin_purchase_submitted').count(), 2
        )
        recipients = set(
            Notification.objects.filter(type='admin_purchase_submitted').values_list('user_id', flat=True)
        )
        self.assertIn(self.admin.id, recipients)
        self.assertIn(admin2.id, recipients)


class SponsorSubmitAdminNotificationTests(TestCase):
    """Integration tests — submitting a sponsor access request triggers admin notifications."""

    def setUp(self):
        SystemSettings.objects.get_or_create(pk=1)
        self.admin = _make_user('admin', 'admin@s24tx.com', is_staff=True)
        self.user = _make_user('sponsor_user', 'sponsor@test.com', is_staff=False)

    def test_admin_notified_on_sponsor_request(self):
        from apps.sponsor.access import create_sponsor_access_request

        create_sponsor_access_request(
            user=self.user,
            ref_slug='TESTSLUG',
            payment_txid='SPONSOR_TXID_001',
            payment_wallet='0xSPONSOR_WALLET',
        )

        admin_notif = Notification.objects.filter(
            user=self.admin,
            type='admin_sponsor_submitted',
        ).first()
        self.assertIsNotNone(admin_notif, 'Admin should receive notification on sponsor request')
        self.assertIn('TESTSLUG', admin_notif.message)
        self.assertFalse(admin_notif.is_read)

    def test_user_still_gets_their_sponsor_notification(self):
        from apps.sponsor.access import create_sponsor_access_request

        create_sponsor_access_request(
            user=self.user,
            ref_slug='MYSLUG2',
            payment_txid='SPONSOR_TXID_002',
            payment_wallet='0xSPONSOR_WALLET2',
        )

        user_notif = Notification.objects.filter(
            user=self.user,
            type='sponsor_request_submitted',
        ).first()
        self.assertIsNotNone(user_notif, 'User should still get their own sponsor notification')

    def test_multiple_admins_all_notified_on_sponsor_request(self):
        from apps.sponsor.access import create_sponsor_access_request

        admin2 = _make_user('admin2', 'admin2@s24tx.com', is_staff=True)
        create_sponsor_access_request(
            user=self.user,
            ref_slug='SLUG3XY',
            payment_txid='SPONSOR_TXID_003',
            payment_wallet='0xSPONSOR_WALLET3',
        )
        self.assertEqual(
            Notification.objects.filter(type='admin_sponsor_submitted').count(), 2
        )
        recipients = set(
            Notification.objects.filter(type='admin_sponsor_submitted').values_list('user_id', flat=True)
        )
        self.assertIn(self.admin.id, recipients)
        self.assertIn(admin2.id, recipients)

"""
Admin notification bell — context processor + mark-read endpoint tests.

Covers:
- Context processor returns correct unread count + list for staff users
- Context processor returns empty payload for anonymous users
- Context processor returns empty payload for non-staff users
- Only `admin_*` notifications are counted (user-facing types are ignored)
- Mark-single-read endpoint updates only the right notification and only for the
  current admin user (cross-user safety)
- Mark-all-read endpoint flips only this admin user's unread `admin_*` rows
- Non-staff users cannot access mark-read endpoints (redirected to login)
"""

from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.admin_dashboard.context_processors import admin_notifications
from apps.notifications.models import Notification


def _staff(username='admin', email='admin@s24tx.com'):
    return User.objects.create_user(
        username=username, email=email, password='testpass123', is_staff=True,
    )


def _user(username='buyer', email='buyer@test.com'):
    return User.objects.create_user(
        username=username, email=email, password='testpass123', is_staff=False,
    )


class AdminNotificationsContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = _staff()

    def _request(self, user):
        req = self.factory.get('/admin/')
        req.user = user
        return req

    def test_anonymous_returns_empty(self):
        from django.contrib.auth.models import AnonymousUser
        ctx = admin_notifications(self._request(AnonymousUser()))
        self.assertEqual(ctx['admin_unread_count'], 0)
        self.assertEqual(ctx['admin_recent_notifications'], [])

    def test_non_staff_returns_empty(self):
        regular = _user()
        Notification.objects.create(
            user=regular, type='admin_purchase_submitted', message='ignored',
        )
        ctx = admin_notifications(self._request(regular))
        self.assertEqual(ctx['admin_unread_count'], 0)
        self.assertEqual(ctx['admin_recent_notifications'], [])

    def test_staff_only_sees_admin_prefixed_notifications(self):
        Notification.objects.create(
            user=self.admin, type='admin_purchase_submitted', message='New purchase',
        )
        Notification.objects.create(
            user=self.admin, type='admin_sponsor_submitted', message='New sponsor',
        )
        Notification.objects.create(
            user=self.admin, type='purchase_approved', message='user-facing — should be ignored',
        )

        ctx = admin_notifications(self._request(self.admin))
        self.assertEqual(ctx['admin_unread_count'], 2)
        self.assertEqual(len(ctx['admin_recent_notifications']), 2)
        types = {n['type'] for n in ctx['admin_recent_notifications']}
        self.assertEqual(types, {'admin_purchase_submitted', 'admin_sponsor_submitted'})

    def test_recent_list_capped_at_five(self):
        for i in range(8):
            Notification.objects.create(
                user=self.admin, type='admin_purchase_submitted', message=f'msg {i}',
            )
        ctx = admin_notifications(self._request(self.admin))
        self.assertEqual(ctx['admin_unread_count'], 8)
        self.assertEqual(len(ctx['admin_recent_notifications']), 5)

    def test_deep_links_resolve_per_type(self):
        Notification.objects.create(
            user=self.admin, type='admin_purchase_submitted', message='p',
        )
        Notification.objects.create(
            user=self.admin, type='admin_sponsor_submitted', message='s',
        )
        ctx = admin_notifications(self._request(self.admin))
        links_by_type = {n['type']: n['link'] for n in ctx['admin_recent_notifications']}
        self.assertEqual(links_by_type['admin_purchase_submitted'], '/admin/purchases/?status=pending')
        self.assertEqual(links_by_type['admin_sponsor_submitted'], '/admin/sponsor-access/?status=pending')


class AdminMarkReadEndpointTests(TestCase):
    def setUp(self):
        self.admin = _staff()
        self.other_admin = _staff(username='admin2', email='admin2@s24tx.com')
        self.regular = _user()
        self.n1 = Notification.objects.create(
            user=self.admin, type='admin_purchase_submitted', message='n1',
        )
        self.n2 = Notification.objects.create(
            user=self.admin, type='admin_sponsor_submitted', message='n2',
        )
        self.other_n = Notification.objects.create(
            user=self.other_admin, type='admin_purchase_submitted', message='other admin n',
        )

    def test_mark_single_read_requires_staff(self):
        self.client.force_login(self.regular)
        url = reverse('admin_dashboard:admin_notification_mark_read', args=[self.n1.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.url)
        self.n1.refresh_from_db()
        self.assertFalse(self.n1.is_read)

    def test_mark_single_read_only_affects_current_admin(self):
        self.client.force_login(self.admin)
        url = reverse('admin_dashboard:admin_notification_mark_read', args=[self.other_n.id])
        response = self.client.post(url, {'next': '/admin/'})
        self.assertEqual(response.status_code, 302)
        self.other_n.refresh_from_db()
        self.assertFalse(self.other_n.is_read, 'Should not have been able to mark another admin notification')

    def test_mark_single_read_success(self):
        self.client.force_login(self.admin)
        url = reverse('admin_dashboard:admin_notification_mark_read', args=[self.n1.id])
        response = self.client.post(url, {'next': '/admin/purchases/?status=pending'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/purchases/?status=pending')
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.n2.refresh_from_db()
        self.assertFalse(self.n2.is_read)

    def test_mark_single_read_rejects_open_redirect(self):
        self.client.force_login(self.admin)
        url = reverse('admin_dashboard:admin_notification_mark_read', args=[self.n1.id])
        response = self.client.post(url, {'next': '//evil.example.com/path'})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.example.com', response.url)

    def test_mark_all_read_only_for_current_admin_and_admin_types(self):
        Notification.objects.create(
            user=self.admin, type='purchase_approved', message='user-facing should stay unread',
        )
        self.client.force_login(self.admin)
        url = reverse('admin_dashboard:admin_notification_mark_all_read')
        response = self.client.post(url, {'next': '/admin/'})
        self.assertEqual(response.status_code, 302)

        self.n1.refresh_from_db()
        self.n2.refresh_from_db()
        self.other_n.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.assertTrue(self.n2.is_read)
        self.assertFalse(self.other_n.is_read, 'Should not have touched other admin')
        user_facing = Notification.objects.filter(user=self.admin, type='purchase_approved').first()
        self.assertFalse(user_facing.is_read, 'Should not have touched user-facing notifications')

    def test_mark_all_read_requires_staff(self):
        self.client.force_login(self.regular)
        url = reverse('admin_dashboard:admin_notification_mark_all_read')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.url)
        self.n1.refresh_from_db()
        self.assertFalse(self.n1.is_read)

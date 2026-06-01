"""
Sponsor reward accrual, USD threshold claim, wallet transfer, report columns, withdrawals.
"""

from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient

from django.test import TestCase, TransactionTestCase
from threading import Thread

from django.db import close_old_connections

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.sponsor.models import SponsorRewardClaim
from apps.sponsor.purchase_rewards import credit_sponsor_for_approved_purchase
from apps.sponsor.rewards import (
    SponsorRewardError,
    claim_sponsor_reward,
    compute_sponsor_reward_summary,
)
from apps.sponsor.report import get_sponsor_report_rows
from apps.withdrawals.models import Withdrawal
from apps.withdrawals.views import get_available_balance, sync_withdrawal_payout_state


def _user(username, email, sponsored_by=None, **extra):
    return User.objects.create_user(
        username=username,
        email=email,
        password='testpass123',
        full_name=extra.pop('full_name', username.title()),
        sponsored_by=sponsored_by,
        **extra,
    )


def _purchase(user, amount, tx):
    return Purchase.objects.create(
        user=user,
        transaction_id=tx,
        amount=Decimal(amount),
        status='approved',
        approved_at=timezone.now(),
        approved_coin_amount=Decimal(amount),
        coin_rate_at_approval=Decimal('1'),
    )


class SponsorAccrualAndClaimTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = SystemSettings.get_settings()
        s.sponsor_percentage = Decimal('10')
        s.sponsor_min_claim_amount_usd = Decimal('100')
        s.coin_rate = Decimal('1')
        s.save()

        cls.sponsor = _user('sp_main', 'sp_main@test.com')
        cls.child = _user('sp_child', 'sp_child@test.com', sponsored_by=cls.sponsor)
        cls.grandchild = _user('sp_grand', 'sp_grand@test.com', sponsored_by=cls.child)

    def test_commission_only_on_direct_child_purchase(self):
        credit_sponsor_for_approved_purchase(self.sponsor, Decimal('1000'))
        _purchase(self.grandchild, '500', 'TXGRAND')
        self.child.sponsor_earnings = Decimal('0')
        self.child.save(update_fields=['sponsor_earnings'])
        credit_sponsor_for_approved_purchase(self.child, Decimal('500'))

        self.sponsor.refresh_from_db()
        self.child.refresh_from_db()
        self.assertEqual(self.sponsor.sponsor_earnings, Decimal('100'))
        self.assertEqual(self.child.sponsor_earnings, Decimal('50'))

    def test_claim_disabled_below_usd_threshold(self):
        self.sponsor.sponsor_earnings = Decimal('50')
        self.sponsor.save(update_fields=['sponsor_earnings'])
        summary = compute_sponsor_reward_summary(self.sponsor)
        self.assertFalse(summary['can_claim'])
        self.assertEqual(summary['status'], 'accumulating')

    def test_claim_transfers_to_wallet_balance(self):
        self.sponsor.sponsor_earnings = Decimal('150')
        self.sponsor.save(update_fields=['sponsor_earnings'])
        payload = claim_sponsor_reward(self.sponsor)
        self.sponsor.refresh_from_db()
        self.assertEqual(self.sponsor.sponsor_earnings, Decimal('0'))
        self.assertEqual(self.sponsor.wallet_balance, Decimal('150'))
        self.assertEqual(payload['claim']['amount_coins'], 150.0)

        available, _, _ = get_available_balance(self.sponsor)
        self.assertGreaterEqual(available, 150.0)


class SponsorReportColumnTests(TestCase):
    def test_my_vs_direct_investment_columns(self):
        s = SystemSettings.get_settings()
        s.coin_rate = Decimal('1')
        s.save()

        ali = _user('rep_ali', 'rep_ali@test.com')
        ahmed = _user('rep_ahmed', 'rep_ahmed@test.com', sponsored_by=ali)
        _purchase(ali, '200', 'TXALI')
        _purchase(ahmed, '800', 'TXAHMED')
        _purchase(_user('rep_deep', 'rep_deep@test.com', sponsored_by=ahmed), '500', 'TXDEEP')

        rows = {r['sponsor_username']: r for r in get_sponsor_report_rows()}
        self.assertAlmostEqual(rows['rep_ali']['my_investment_usdt'], 200.0)
        self.assertAlmostEqual(rows['rep_ali']['direct_referrals_investment_usdt'], 800.0)
        self.assertNotEqual(
            rows['rep_ali']['my_investment_usdt'],
            rows['rep_ali']['direct_referrals_investment_usdt'],
        )


class WithdrawalFullPayoutTests(TestCase):
    def test_approved_withdrawal_pays_full_amount_immediately(self):
        user = _user('wd_user', 'wd_user@test.com', wallet_balance=Decimal('500'))
        withdrawal = Withdrawal.objects.create(
            user=user,
            amount=Decimal('200'),
            wallet_address='TRXtestwalletaddress123456789',
            status='approved',
            approved_at=timezone.now(),
        )
        sync_withdrawal_payout_state(withdrawal)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'completed')
        self.assertEqual(withdrawal.paid_amount, Decimal('200'))
        self.assertEqual(withdrawal.remaining_amount, Decimal('0'))


class SponsorClaimApiTests(TestCase):
    def setUp(self):
        s = SystemSettings.get_settings()
        s.sponsor_min_claim_amount_usd = Decimal('100')
        s.coin_rate = Decimal('1')
        s.save()
        self.user = _user('api_sp', 'api_sp@test.com')
        self.user.sponsor_earnings = Decimal('120')
        self.user.save(update_fields=['sponsor_earnings'])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_claim_endpoint_moves_to_wallet(self):
        response = self.client.post('/api/sponsor/reward/claim')
        self.assertEqual(response.status_code, 201)
        self.user.refresh_from_db()
        self.assertEqual(self.user.sponsor_earnings, Decimal('0'))
        self.assertEqual(self.user.wallet_balance, Decimal('120'))


class SponsorClaimConcurrencyTests(TransactionTestCase):
    def test_concurrent_claims_do_not_double_credit_wallet(self):
        s = SystemSettings.get_settings()
        s.sponsor_min_claim_amount_usd = Decimal('50')
        s.coin_rate = Decimal('1')
        s.save()
        user = _user('race_sp', 'race_sp@test.com')
        user.sponsor_earnings = Decimal('200')
        user.save(update_fields=['sponsor_earnings'])

        results = []

        def worker():
            try:
                claim_sponsor_reward(user)
                results.append('ok')
            except SponsorRewardError as exc:
                results.append(str(exc))
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        user.refresh_from_db()
        self.assertLessEqual(SponsorRewardClaim.objects.filter(user=user).count(), 1)
        self.assertLessEqual(user.wallet_balance, Decimal('200'))

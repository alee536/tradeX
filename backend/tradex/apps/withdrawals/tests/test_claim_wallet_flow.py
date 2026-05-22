"""
Test cases: instant claim → wallet credit; withdrawal still needs admin approval.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.withdrawals.claims import ClaimError, create_claim, total_claimed_coins
from apps.withdrawals.models import PurchaseClaim, Withdrawal
from apps.withdrawals.views import get_available_balance


class ClaimWalletFlowTests(TestCase):
    """Covers manual QA checklist for staged claims + withdrawals."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SystemSettings.get_settings()
        cls.settings.profit_enabled = False
        cls.settings.stage1_hours = 0
        cls.settings.stage2_hours = 0
        cls.settings.stage3_hours = 0
        cls.settings.stage1_percent = Decimal('50')
        cls.settings.stage2_percent = Decimal('25')
        cls.settings.stage3_percent = Decimal('25')
        cls.settings.coin_rate = Decimal('1')
        cls.settings.save()

        cls.user = User.objects.create_user(
            username='claim_test_user',
            email='claim_test@example.com',
            password='testpass123',
            full_name='Claim Test User',
            wallet_address='0xclaimtestwallet',
        )
        cls.admin = User.objects.create_user(
            username='claim_test_admin',
            email='claim_admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )

        now = timezone.now()
        cls.purchase = Purchase.objects.create(
            user=cls.user,
            transaction_id='TX24XCLAIMTEST',
            amount=Decimal('100'),
            status='approved',
            approved_at=now - timedelta(hours=1),
            is_coins_assigned=True,
            coins_assigned_at=now - timedelta(hours=1),
            approved_coin_amount=Decimal('100'),
            coin_rate_at_approval=Decimal('1'),
        )

    def test_tc01_claim_auto_approved_no_admin(self):
        """TC-01: Claim is approved instantly (no pending admin step)."""
        claim = create_claim(self.user, self.purchase, 1)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'approved')
        self.assertIsNotNone(claim.approved_at)
        self.assertEqual(
            PurchaseClaim.objects.filter(
                purchase=self.purchase, stage=1, status='pending',
            ).count(),
            0,
        )

    def test_tc02_claim_increases_wallet_balance(self):
        """TC-02: Available balance increases right after claim."""
        before, _, _ = get_available_balance(self.user)
        claim = create_claim(self.user, self.purchase, 1)
        after, wallet_coins, _ = get_available_balance(self.user)
        self.assertEqual(wallet_coins, float(claim.amount_coins))
        self.assertGreater(after, before)
        self.assertEqual(total_claimed_coins(self.user), float(claim.amount_coins))

    def test_tc03_duplicate_claim_same_stage_blocked(self):
        """TC-03: Cannot claim the same stage twice."""
        create_claim(self.user, self.purchase, 1)
        with self.assertRaises(ClaimError):
            create_claim(self.user, self.purchase, 1)

    def test_tc04_withdrawal_stays_pending_until_admin(self):
        """TC-04: User withdrawal is pending; not completed without admin."""
        create_claim(self.user, self.purchase, 1)
        available, _, _ = get_available_balance(self.user)
        withdrawal = Withdrawal.objects.create(
            user=self.user,
            amount=Decimal(str(min(10, available))),
            wallet_address='0xwithdrawdest',
        )
        self.assertEqual(withdrawal.status, 'pending')
        self.assertIsNone(withdrawal.approved_at)

    def test_tc05_withdraw_exceeding_available_rejected(self):
        """TC-05: Withdraw API rejects amount greater than available wallet."""
        create_claim(self.user, self.purchase, 1)
        available, _, _ = get_available_balance(self.user)
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            '/api/withdrawals',
            {'amount': available + 1000, 'wallet_address': '0xtoomuch'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Insufficient balance', response.json().get('error', ''))

    def test_tc06_stage2_requires_stage1_claimed(self):
        """TC-06: Stage 2 blocked until stage 1 is claimed."""
        with self.assertRaises(ClaimError):
            create_claim(self.user, self.purchase, 2)

    def test_tc07_stage2_after_stage1_claim(self):
        """TC-07: Stage 2 can be claimed after stage 1."""
        create_claim(self.user, self.purchase, 1)
        claim2 = create_claim(self.user, self.purchase, 2)
        self.assertEqual(claim2.status, 'approved')
        self.assertEqual(total_claimed_coins(self.user), 75.0)  # 50% + 25% of 100

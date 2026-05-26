from django.conf import settings
from django.db import models


class SponsorEarning(models.Model):
    sponsor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sponsor_earnings_records',
    )
    sponsored_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generated_sponsor_earnings',
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    source_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sponsor_id} <- {self.sponsored_user_id}: {self.amount}"


class SponsorAccessRequest(models.Model):
    """
    ============== One-time sponsor link access request ==============

    User pays a fixed USDT fee (default 5) and admin approves before the
    short referral link becomes active for lifetime.
    """

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_PAID, 'Paid'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sponsor_access_requests',
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default=PAYMENT_PENDING,
        blank=True,
    )
    fee_usdt = models.DecimalField(max_digits=20, decimal_places=8, default=5)
    ref_slug = models.CharField(
        max_length=32,
        db_index=True,
        help_text='Desired short code, e.g. ALEE24',
    )
    payment_txid = models.CharField(max_length=255, blank=True, null=True)
    payment_wallet = models.CharField(max_length=255, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sponsor access request'
        verbose_name_plural = 'Sponsor access requests'
        indexes = [
            models.Index(fields=['user', 'status'], name='sponsor_req_user_st_idx'),
        ]

    def __str__(self):
        return f"SponsorRequest user={self.user_id} slug={self.ref_slug} status={self.status}"


class SponsorRewardClaim(models.Model):
    """
    ============== Multi-level sponsor reward claim ==============

    Ledger row written each time a sponsor claims accumulated reward
    earned across their FULL downline tree (all levels).

    Reward formula (per claim):
        gross_reward_usdt = total_investment_usdt × reward_percentage / 100
        outstanding_usdt  = gross_reward_usdt - sum(prior approved claims)

    The view layer locks the user row (select_for_update) before
    recomputing outstanding so concurrent clicks cannot double-claim.
    """

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='multi_level_reward_claims',
    )

    # Snapshot of the inputs at claim time (audit trail)
    total_investment_usdt = models.DecimalField(max_digits=20, decimal_places=8)
    reward_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    gross_reward_usdt = models.DecimalField(max_digits=20, decimal_places=8)

    # The actual credit applied to the user's wallet at claim time
    amount_usdt = models.DecimalField(max_digits=20, decimal_places=8)
    amount_coins = models.DecimalField(max_digits=20, decimal_places=8)
    coin_rate_at_claim = models.DecimalField(max_digits=20, decimal_places=8)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_APPROVED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='spnreward_user_ct_idx'),
        ]

    def __str__(self):
        return f"SponsorRewardClaim user={self.user_id} amount_usdt={self.amount_usdt} status={self.status}"

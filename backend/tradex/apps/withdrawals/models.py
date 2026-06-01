from decimal import Decimal

from django.conf import settings
from django.db import models


# ============== Staged Withdrawal / Claim Constants ==============
CLAIM_STAGE_PERCENTAGES = (Decimal('50'), Decimal('25'), Decimal('25'))


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    wallet_address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    manual_tx_hash = models.CharField(max_length=255, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    payment_stage = models.IntegerField(default=0)
    stage1_paid_at = models.DateTimeField(null=True, blank=True)
    stage2_paid_at = models.DateTimeField(null=True, blank=True)
    stage3_paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def _normalized_stage_percentages():
        # Use current admin-configured percentages and normalize to 100 if needed.
        from apps.settings_app.models import SystemSettings

        settings_obj = SystemSettings.get_settings()
        stage1_percent = Decimal(str(settings_obj.stage1_percent or 0))
        stage2_percent = Decimal(str(settings_obj.stage2_percent or 0))
        stage3_percent = Decimal(str(settings_obj.stage3_percent or 0))

        total_percent = stage1_percent + stage2_percent + stage3_percent
        if total_percent <= 0:
            return Decimal('50'), Decimal('25'), Decimal('25')

        if total_percent != Decimal('100'):
            scale = Decimal('100') / total_percent
            stage1_percent = (stage1_percent * scale).quantize(Decimal('0.01'))
            stage2_percent = (stage2_percent * scale).quantize(Decimal('0.01'))
            stage3_percent = Decimal('100') - stage1_percent - stage2_percent

        return stage1_percent, stage2_percent, stage3_percent

    @property
    def stage_percentages(self):
        return self._normalized_stage_percentages()

    @property
    def stage_amounts(self):
        """Full withdrawal amount is paid in one release (no partial stages)."""
        amount = Decimal(str(self.amount or 0)).quantize(Decimal('0.00000001'))
        return amount, Decimal('0'), Decimal('0')

    @property
    def paid_amount(self):
        if self.status == 'completed':
            return Decimal(str(self.amount or 0))
        return Decimal('0')

    @property
    def remaining_amount(self):
        remaining = Decimal(str(self.amount or 0)) - self.paid_amount
        return remaining if remaining > 0 else Decimal('0')

    @property
    def next_payout_stage(self):
        if self.status == 'completed':
            return None
        if not self.stage1_paid_at:
            return 1
        if not self.stage2_paid_at:
            return 2
        if not self.stage3_paid_at:
            return 3
        return None

    def __str__(self):
        return f"Withdrawal {self.id} - {self.user.username} - {self.amount}"


class PurchaseClaim(models.Model):
    """
    ============== Per-Purchase Staged Claim ==============

    Each approved purchase has up to 3 claim stages (50% / 25% / 25%).
    Timers are measured from backend timestamps:
        - Stage 1 unlocks 72h after purchase approval (configurable).
        - Stage N (N>1) unlocks `stageN_hours` after Stage N-1 was approved.
    """

    STAGE_CHOICES = (
        (1, 'Stage 1'),
        (2, 'Stage 2'),
        (3, 'Stage 3'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    purchase = models.ForeignKey(
        'purchases.Purchase',
        on_delete=models.CASCADE,
        related_name='claims',
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchase_claims',
        blank=True,
        null=True,
        db_index=True,
    )
    stage = models.PositiveSmallIntegerField(
        choices=STAGE_CHOICES,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        blank=True,
    )
    amount_coins = models.DecimalField(
        max_digits=20, decimal_places=8, blank=True, null=True,
    )
    amount_usdt_snapshot = models.DecimalField(
        max_digits=20, decimal_places=8, blank=True, null=True,
    )
    coin_rate_snapshot = models.DecimalField(
        max_digits=20, decimal_places=8, blank=True, null=True,
    )
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    manual_tx_hash = models.CharField(max_length=255, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase claim'
        verbose_name_plural = 'Purchase claims'
        indexes = [
            models.Index(fields=['purchase', 'stage'], name='claim_purchase_stage_idx'),
            models.Index(fields=['user', 'status'], name='claim_user_status_idx'),
        ]

    def __str__(self):
        return (
            f"PurchaseClaim purchase={self.purchase_id} stage={self.stage} "
            f"status={self.status} amount={self.amount_coins}"
        )

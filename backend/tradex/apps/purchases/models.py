from django.db import models
from django.conf import settings


def generate_transaction_id():
    import random
    num = random.randint(100000, 999999)
    return f"TX24X{num}"


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    REJECTION_REASON_CHOICES = [
        ('transaction_id_mismatch', 'Transaction ID not matching'),
        ('wallet_address_invalid', 'Wallet address invalid or incomplete'),
        ('amount_mismatch', 'Amount does not match'),
        ('screenshot_invalid', 'Screenshot unclear or invalid'),
        ('duplicate_transaction', 'Duplicate transaction detected'),
        ('suspicious_activity', 'Suspicious activity detected'),
        ('incomplete_payment', 'Payment not received or incomplete'),
        ('other', 'Other reason'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    txid = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    screenshot = models.ImageField(upload_to='screenshots/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    rejection_reason_type = models.CharField(max_length=50, choices=REJECTION_REASON_CHOICES, blank=True, null=True)
    rejection_notes = models.TextField(blank=True, null=True, help_text="Additional notes from admin")
    rejection_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    coin_rate_at_approval = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    approved_coin_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    is_coins_assigned = models.BooleanField(default=False)
    coins_assigned_at = models.DateTimeField(null=True, blank=True)
    unlock_stage = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            tid = generate_transaction_id()
            while Purchase.objects.filter(transaction_id=tid).exists():
                tid = generate_transaction_id()
            self.transaction_id = tid
        super().save(*args, **kwargs)

    @property
    def unlocked_amount(self):
        from apps.settings_app.models import SystemSettings
        from django.utils import timezone

        if self.status != 'approved' or not self.approved_at:
            return 0

        settings_obj = SystemSettings.get_settings()
        # Use coin amount for unlocking calculation. If approved_coin_amount is not set,
        # use calculated_coins (conversion from USD amount using stored or current rate).
        calc = self.calculated_coins
        try:
            amount = float(calc)
        except Exception:
            amount = 0.0
        now = timezone.now()
        elapsed = now - self.approved_at
        elapsed_hours = elapsed.total_seconds() / 3600

        stage1_h = settings_obj.stage1_hours
        stage2_h = stage1_h + settings_obj.stage2_hours
        stage3_h = stage2_h + settings_obj.stage3_hours

        unlocked = 0
        if elapsed_hours >= stage3_h:
            unlocked = amount
        elif elapsed_hours >= stage2_h:
            unlocked = amount * (float(settings_obj.stage1_percent) + float(settings_obj.stage2_percent)) / 100
        elif elapsed_hours >= stage1_h:
            unlocked = amount * float(settings_obj.stage1_percent) / 100

        return round(unlocked, 8)

    @property
    def calculated_coins(self):
        from decimal import Decimal
        from apps.settings_app.models import SystemSettings

        if self.approved_coin_amount is not None:
            return self.approved_coin_amount

        settings_obj = SystemSettings.get_settings()
        rate = self.coin_rate_at_approval or settings_obj.coin_rate
        if not rate:
            return Decimal('0')
        return Decimal(self.amount) / Decimal(rate)

    def __str__(self):
        return f"{self.transaction_id} - {self.user.username}"


class PurchaseRejectionDocument(models.Model):
    """Store documents uploaded by users to support rejected purchase requests"""
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='rejection_documents'
    )
    document = models.FileField(upload_to='rejection_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Document for {self.purchase.transaction_id}"

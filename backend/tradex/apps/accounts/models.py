import string
import random
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def generate_sponsor_code():
    chars = string.ascii_uppercase + string.digits
    return '24TX-' + ''.join(random.choices(chars, k=6))


def generate_unique_user_id(model_cls):
    """Generate unique user ID in format 24TX-000123."""
    last_user = model_cls.objects.all().order_by('-id').first()
    next_number = (last_user.id + 1) if last_user else 1
    return f"24TX-{next_number:06d}"


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=False)
    unique_id = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='date joined', db_index=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    sponsor_code = models.CharField(max_length=20, unique=True, blank=True)
    # ============== Sponsor link access (paid + admin-approved) ==============
    SPONSOR_ACCESS_NONE = 'none'
    SPONSOR_ACCESS_PENDING = 'pending'
    SPONSOR_ACCESS_ACTIVE = 'active'
    SPONSOR_ACCESS_REJECTED = 'rejected'
    SPONSOR_ACCESS_CHOICES = [
        (SPONSOR_ACCESS_NONE, 'None'),
        (SPONSOR_ACCESS_PENDING, 'Pending'),
        (SPONSOR_ACCESS_ACTIVE, 'Active'),
        (SPONSOR_ACCESS_REJECTED, 'Rejected'),
    ]
    sponsor_access_status = models.CharField(
        max_length=20,
        choices=SPONSOR_ACCESS_CHOICES,
        default=SPONSOR_ACCESS_NONE,
        db_index=True,
        blank=True,
    )
    sponsor_ref_slug = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text='Short public ref for s24tx.com/ref/SLUG',
    )
    sponsor_activated_at = models.DateTimeField(null=True, blank=True)
    SPONSOR_PAYMENT_NONE = 'none'
    SPONSOR_PAYMENT_PENDING = 'pending'
    SPONSOR_PAYMENT_PAID = 'paid'
    SPONSOR_PAYMENT_CHOICES = [
        (SPONSOR_PAYMENT_NONE, 'None'),
        (SPONSOR_PAYMENT_PENDING, 'Pending'),
        (SPONSOR_PAYMENT_PAID, 'Paid'),
    ]
    sponsor_payment_status = models.CharField(
        max_length=20,
        choices=SPONSOR_PAYMENT_CHOICES,
        default=SPONSOR_PAYMENT_NONE,
        blank=True,
    )
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    is_banned = models.BooleanField(default=False)
    sponsor_earnings = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    wallet_balance = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text='Main in-app wallet (coins), including sponsor rewards after claim.',
    )
    sponsor_reward_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Admin-defined reward % for this sponsor. Falls back to global sponsor_percentage if null.',
    )
    sponsored_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='sponsored_users'
    )

    def save(self, *args, **kwargs):
        if not self.sponsor_code:
            code = generate_sponsor_code()
            while User.objects.filter(sponsor_code=code).exists():
                code = generate_sponsor_code()
            self.sponsor_code = code
        
        if not self.unique_id:
            unique_id = generate_unique_user_id(User)
            while User.objects.filter(unique_id=unique_id).exists():
                next_number = int(unique_id.split('-')[1]) + 1
                unique_id = f"24TX-{next_number:06d}"
            self.unique_id = unique_id
        
        super().save(*args, **kwargs)

    @property
    def has_active_sponsor_access(self):
        return self.sponsor_access_status == self.SPONSOR_ACCESS_ACTIVE

    @property
    def sponsor_public_path(self):
        """Short referral path, e.g. /ref/ALEE24 (only when access is active)."""
        if not self.has_active_sponsor_access or not self.sponsor_ref_slug:
            return None
        return f"/ref/{self.sponsor_ref_slug}"

    @property
    def sponsor_link(self):
        from django.conf import settings
        path = self.sponsor_public_path
        if path:
            base = getattr(settings, 'SPONSOR_REF_BASE_URL', settings.SITE_URL).rstrip('/')
            return f"{base}{path}"
        return f"{settings.SITE_URL}/register?sp={self.sponsor_code}"

    @property
    def sponsored_users_count(self):
        """Count direct sponsored users"""
        return self.sponsored_users.count()
    
    @property
    def total_sponsored_count(self):
        """Count all sponsored users recursively (includes nested)"""
        count = self.sponsored_users.count()
        for child in self.sponsored_users.all():
            count += child.total_sponsored_count
        return count

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            models.Index(fields=['sponsored_by', 'date_joined'], name='accounts_us_sponsor_f4948b_idx'),
        ]


class SignupOtpVerification(models.Model):
    """Pending signup until email OTP is verified."""

    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=64)
    signup_payload = models.JSONField()
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['email', 'verified_at', 'expires_at'],
                name='accounts_otp_email_active_idx',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Signup OTP for {self.email}'


class PasswordResetOtp(models.Model):
    """One-time OTP for forgot-password; invalidated after use or expiry."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_otps',
    )
    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['email', 'used_at', 'expires_at'],
                name='accounts_pwd_reset_active_idx',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Password reset OTP for {self.email}'

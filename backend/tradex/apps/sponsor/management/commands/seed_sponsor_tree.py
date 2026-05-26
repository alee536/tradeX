"""
============== Seed a multi-level sponsor tree for QA ==============

Creates a 4-level sponsor hierarchy with approved purchases so you can
manually verify the Multi-Level Sponsor Reward card on /sponsor.

All seeded users share the email suffix `@tradex.test` so they're easy
to identify and wipe with `--reset`.

Usage:
    python manage.py seed_sponsor_tree
    python manage.py seed_sponsor_tree --reset                  # wipe and reseed
    python manage.py seed_sponsor_tree --password Strong@123    # override common password

After seeding, log in as seed_root@tradex.test (default password Strong@123)
and visit /sponsor to see the ACTIVE Claim button on the new card.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.sponsor.models import SponsorRewardClaim
from apps.settings_app.models import SystemSettings

SEED_EMAIL_SUFFIX = '@tradex.test'

# (email_local, full_name, parent_email_local, self_purchase_usdt)
TREE = [
    ('seed_root',   'Seed Root',      None,         '300'),
    ('seed_l1_a',   'Level 1 A',      'seed_root',  '400'),
    ('seed_l2_a1',  'Level 2 A1',     'seed_l1_a',  '250'),
    ('seed_l3_a1a', 'Level 3 A1a',    'seed_l2_a1', '150'),
    ('seed_l2_a2',  'Level 2 A2',     'seed_l1_a',  '200'),
    ('seed_l1_b',   'Level 1 B',      'seed_root',  '100'),
    ('seed_l2_b1',  'Level 2 B1',     'seed_l1_b',  '50'),
    ('seed_l1_c',   'Level 1 C',      'seed_root',  '600'),
    ('seed_l2_c1',  'Level 2 C1',     'seed_l1_c',  '350'),
]


class Command(BaseCommand):
    help = 'Seed a multi-level sponsor tree (+approved purchases) for QA of the sponsor reward feature.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete previously seeded users (email ends with @tradex.test) before seeding.',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='Strong@123',
            help='Common password for all seeded users (default: Strong@123).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        if options['reset']:
            self._reset()

        self._ensure_settings_defaults()

        created_users: dict[str, User] = {}
        for local, full_name, parent_local, amount in TREE:
            email = f'{local}{SEED_EMAIL_SUFFIX}'
            parent = created_users.get(parent_local) if parent_local else None

            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': local,
                    'full_name': full_name,
                    'sponsored_by': parent,
                },
            )

            # Sync sponsor link on re-runs (without --reset) in case parent changed
            if user.sponsored_by_id != (parent.id if parent else None):
                user.sponsored_by = parent
                user.save(update_fields=['sponsored_by'])

            if was_created or not user.has_usable_password():
                user.set_password(password)
                user.save(update_fields=['password'])

            self._ensure_purchase(user, Decimal(amount))
            created_users[local] = user

            self.stdout.write(
                f'  {"+" if was_created else "·"} {email:<32} '
                f'parent={parent.email if parent else "—":<28} purchase=${amount}'
            )

        self.stdout.write(self.style.SUCCESS('\nSeed complete.'))
        self._print_credentials_summary(password)
        self._print_expected_summary()

    def _reset(self):
        qs = User.objects.filter(email__endswith=SEED_EMAIL_SUFFIX)
        emails = list(qs.values_list('email', flat=True))
        if not emails:
            self.stdout.write('Reset: no previously seeded users found.')
            return
        SponsorRewardClaim.objects.filter(user__in=qs).delete()
        Purchase.objects.filter(user__in=qs).delete()
        qs.delete()
        self.stdout.write(self.style.WARNING(f'Reset: deleted {len(emails)} seeded users + their purchases & claims.'))

    def _ensure_settings_defaults(self):
        s = SystemSettings.get_settings()
        dirty = False
        if not s.coin_rate or Decimal(str(s.coin_rate)) <= 0:
            s.coin_rate = Decimal('1')
            dirty = True
        if not s.sponsor_percentage:
            s.sponsor_percentage = Decimal('5')
            dirty = True
        if not s.sponsor_reward_threshold_usdt:
            s.sponsor_reward_threshold_usdt = Decimal('1000')
            dirty = True
        if dirty:
            s.save()
            self.stdout.write('System settings backfilled with safe defaults for the seed scenario.')

    def _ensure_purchase(self, user: User, amount: Decimal):
        """Idempotent: only create an approved seed purchase if the user has none yet."""
        marker_prefix = 'SEED-'
        existing = Purchase.objects.filter(user=user, transaction_id__startswith=marker_prefix).first()
        if existing:
            if existing.status != 'approved' or existing.amount != amount:
                existing.amount = amount
                existing.status = 'approved'
                existing.approved_at = existing.approved_at or timezone.now()
                existing.save(update_fields=['amount', 'status', 'approved_at'])
            return existing

        return Purchase.objects.create(
            user=user,
            transaction_id=f'{marker_prefix}{user.id}-{int(timezone.now().timestamp())}',
            amount=amount,
            status='approved',
            approved_at=timezone.now(),
        )

    def _print_credentials_summary(self, password: str):
        s = SystemSettings.get_settings()
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Login credentials'))
        self.stdout.write(f'  All seeded users share password: {password}')
        self.stdout.write('  Try logging in as:  seed_root@tradex.test')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Current settings'))
        self.stdout.write(f'  sponsor_percentage             = {s.sponsor_percentage}%')
        self.stdout.write(f'  sponsor_reward_threshold_usdt  = {s.sponsor_reward_threshold_usdt}')
        self.stdout.write(f'  coin_rate                      = {s.coin_rate}')

    def _print_expected_summary(self):
        from apps.accounts.models import User as UserModel  # local import to avoid cycle
        from apps.sponsor.rewards import compute_sponsor_reward_summary

        root = UserModel.objects.filter(email=f'seed_root{SEED_EMAIL_SUFFIX}').first()
        if not root:
            return
        s = SystemSettings.get_settings()
        summary = compute_sponsor_reward_summary(root, s)
        coin_rate = Decimal(str(s.coin_rate or 1))
        expected_coins = (Decimal(str(summary['outstanding_reward_usdt'])) / coin_rate).quantize(Decimal('0.00000001'))

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Live values for seed_root@tradex.test (computed against current DB):'))
        self.stdout.write(f'  Total downline count       = {summary["total_downline_count"]}')
        self.stdout.write(f'  Self investment            = ${summary["self_investment_usdt"]}')
        self.stdout.write(f'  Downline investment        = ${summary["downline_investment_usdt"]}')
        self.stdout.write(f'  Total investment           = ${summary["total_investment_usdt"]}')
        self.stdout.write(f'  Reward percentage          = {summary["reward_percentage"]}%')
        self.stdout.write(f'  Gross reward (USDT)        = ${summary["gross_reward_usdt"]}')
        self.stdout.write(f'  Outstanding reward (USDT)  = ${summary["outstanding_reward_usdt"]}')
        self.stdout.write(f'  Threshold                  = ${summary["threshold_usdt"]}')
        self.stdout.write(f'  Status                     = {summary["status"].upper()}')
        self.stdout.write(f'  Can claim                  = {summary["can_claim"]}')
        self.stdout.write(f'  On claim -> credit         = {expected_coins} coins (= USDT / coin_rate {coin_rate})')

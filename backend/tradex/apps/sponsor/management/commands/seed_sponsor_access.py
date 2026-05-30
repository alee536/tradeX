"""
============== Seed sponsor link access requests for QA ==============

Creates users with pending, approved, and rejected sponsor access requests
so you can test the admin Sponsor Access page and the /sponsor tab flows.

All seeded users share the email suffix `@sponsor-access.test`.

Usage:
    python manage.py seed_sponsor_access
    python manage.py seed_sponsor_access --reset
    python manage.py seed_sponsor_access --password Strong@123
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.sponsor.access import (
    approve_sponsor_access_request,
    create_sponsor_access_request,
    get_sponsor_access_fee,
    reject_sponsor_access_request,
)
from apps.sponsor.models import SponsorAccessRequest

SEED_EMAIL_SUFFIX = '@sponsor-access.test'
SEED_TXID_PREFIX = 'SEED-ACCESS-'
SEED_WALLET = '0x000000000000000000000000000000000000SEED'

# (email_local, full_name, ref_slug, outcome)
# outcome: pending | approved | rejected
ACCESS_SEED = [
    ('seed_access_pending1', 'Pending User One', 'PEND01', 'pending'),
    ('seed_access_pending2', 'Pending User Two', 'PEND02', 'pending'),
    ('seed_access_active1', 'Active User One', 'ACTIVE1', 'approved'),
    ('seed_access_active2', 'Active User Two', 'ACTIVE2', 'approved'),
    ('seed_access_rejected', 'Rejected User', 'REJECT1', 'rejected'),
]


class Command(BaseCommand):
    help = 'Seed sponsor link access requests (pending, approved, rejected) for QA.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete previously seeded sponsor-access users before seeding.',
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

        fee = get_sponsor_access_fee()
        counts = {'pending': 0, 'approved': 0, 'rejected': 0}

        for local, full_name, ref_slug, outcome in ACCESS_SEED:
            email = f'{local}{SEED_EMAIL_SUFFIX}'
            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': local,
                    'full_name': full_name,
                },
            )

            if was_created or not user.has_usable_password():
                user.set_password(password)
                user.save(update_fields=['password'])

            req, action = self._seed_access(user, ref_slug, outcome)
            counts[outcome] += 1

            self.stdout.write(
                f'  {"+" if was_created else "·"} {email:<38} '
                f'slug={ref_slug:<10} status={req.status} ({action})'
            )

        self.stdout.write(self.style.SUCCESS('\nSponsor access seed complete.'))
        self._print_summary(password, fee, counts)

    def _reset(self):
        qs = User.objects.filter(email__endswith=SEED_EMAIL_SUFFIX)
        emails = list(qs.values_list('email', flat=True))
        if not emails:
            self.stdout.write('Reset: no previously seeded sponsor-access users found.')
            return
        SponsorAccessRequest.objects.filter(user__in=qs).delete()
        qs.delete()
        self.stdout.write(
            self.style.WARNING(
                f'Reset: deleted {len(emails)} seeded users and their access requests.'
            )
        )

    def _seed_access(self, user: User, ref_slug: str, outcome: str):
        """Idempotent: skip if the user already matches the desired outcome."""
        target = {
            'pending': SponsorAccessRequest.STATUS_PENDING,
            'approved': SponsorAccessRequest.STATUS_APPROVED,
            'rejected': SponsorAccessRequest.STATUS_REJECTED,
        }[outcome]

        existing = (
            SponsorAccessRequest.objects.filter(user=user, ref_slug__iexact=ref_slug)
            .order_by('-created_at')
            .first()
        )
        if existing and existing.status == target:
            return existing, 'unchanged'

        self._reset_user_access(user)

        txid = f'{SEED_TXID_PREFIX}{user.id}-{ref_slug}'
        req = create_sponsor_access_request(
            user,
            ref_slug=ref_slug,
            payment_txid=txid,
            payment_wallet=SEED_WALLET,
        )

        if outcome == 'approved':
            req = approve_sponsor_access_request(req)
            return req, 'approved'
        if outcome == 'rejected':
            req = reject_sponsor_access_request(req, 'Seed data — rejected for QA.')
            return req, 'rejected'
        return req, 'pending'

    def _reset_user_access(self, user: User):
        user.sponsor_access_status = User.SPONSOR_ACCESS_NONE
        user.sponsor_payment_status = User.SPONSOR_PAYMENT_NONE
        user.sponsor_ref_slug = None
        user.sponsor_activated_at = None
        user.save(
            update_fields=[
                'sponsor_access_status',
                'sponsor_payment_status',
                'sponsor_ref_slug',
                'sponsor_activated_at',
            ]
        )

    def _print_summary(self, password: str, fee, counts: dict):
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Login credentials'))
        self.stdout.write(f'  All seeded users share password: {password}')
        self.stdout.write('  Active sponsor link example: seed_access_active1@sponsor-access.test')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Seeded records'))
        self.stdout.write(f'  Access fee (USDT)  = {fee}')
        self.stdout.write(f'  Pending requests   = {counts["pending"]}')
        self.stdout.write(f'  Approved (active)  = {counts["approved"]}')
        self.stdout.write(f'  Rejected           = {counts["rejected"]}')
        self.stdout.write('')
        self.stdout.write('  Admin dashboard: /admin-dashboard/sponsor-access/')
        self.stdout.write('  User sponsor tab: /sponsor (log in as any seeded user)')

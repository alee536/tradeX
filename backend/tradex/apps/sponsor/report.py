"""
Flat sponsor-wise summary for admin reporting.

Each row represents a user who has at least one direct referral. Metrics include the
full downline (recursive descendants), not only direct children. Child sponsors who
also refer users appear on their own row separately — no tree UI is required.
"""

from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import connection
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.withdrawals.models import Withdrawal

WITHDRAWAL_STATUSES = ('pending', 'approved', 'completed')
MAX_DOWNLINE_DEPTH = 100


def _user_table() -> str:
    return User._meta.db_table


def _purchase_table() -> str:
    return Purchase._meta.db_table


def _withdrawal_table() -> str:
    return Withdrawal._meta.db_table


def _sponsor_base_queryset(search: str | None = None):
    """Users who have sponsored at least one other user (direct)."""
    qs = (
        User.objects.annotate(direct_count=Count('sponsored_users', distinct=True))
        .filter(direct_count__gt=0)
        .only(
            'id',
            'username',
            'full_name',
            'email',
            'unique_id',
            'sponsor_earnings',
            'sponsor_ref_slug',
            'sponsor_access_status',
            'date_joined',
        )
    )
    if search:
        term = search.strip()
        if term:
            qs = qs.filter(
                Q(username__icontains=term)
                | Q(full_name__icontains=term)
                | Q(email__icontains=term)
                | Q(unique_id__icontains=term)
            )
    return qs


def _serialize_row(sponsor: User, metrics: dict[str, Any], default_reward_percentage: float) -> dict[str, Any]:
    display_name = (sponsor.full_name or sponsor.username or '').strip() or sponsor.username
    reward_percentage = float(sponsor.sponsor_reward_percentage or default_reward_percentage)
    return {
        'sponsor_id': sponsor.id,
        'sponsor_name': display_name,
        'sponsor_username': sponsor.username,
        'sponsor_unique_id': sponsor.unique_id,
        'sponsor_email': sponsor.email,
        'sponsored_users_count': metrics['downline_count'],
        'direct_sponsored_count': metrics['direct_count'],
        'total_investment_usdt': metrics['investment_usdt'],
        'total_investment_coins': metrics['investment_coins'],
        'total_earning': metrics['sponsor_earnings'],
        'reward_percentage': reward_percentage,
        'downline_withdrawals_usdt': metrics['withdrawals_usdt'],
        'other_details': {
            'active_downline_users': metrics['active_downline'],
            'sponsor_ref_slug': sponsor.sponsor_ref_slug or '',
            'sponsor_access_status': sponsor.sponsor_access_status,
            'date_joined': sponsor.date_joined.isoformat() if sponsor.date_joined else None,
        },
    }


def _fetch_metrics_postgresql(sponsor_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not sponsor_ids:
        return {}

    user_table = _user_table()
    purchase_table = _purchase_table()
    withdrawal_table = _withdrawal_table()
    placeholders = ','.join(['%s'] * len(sponsor_ids))

    sql = f"""
        WITH RECURSIVE downline AS (
            SELECT
                u.id AS user_id,
                u.sponsored_by_id AS root_id,
                1 AS depth
            FROM {user_table} u
            WHERE u.sponsored_by_id IS NOT NULL

            UNION ALL

            SELECT
                child.id,
                d.root_id,
                d.depth + 1
            FROM {user_table} child
            INNER JOIN downline d ON child.sponsored_by_id = d.user_id
            WHERE d.depth < {MAX_DOWNLINE_DEPTH}
        ),
        roots AS (
            SELECT id AS root_id FROM {user_table} WHERE id IN ({placeholders})
        ),
        scoped AS (
            SELECT d.root_id, d.user_id
            FROM downline d
            INNER JOIN roots r ON r.root_id = d.root_id
        ),
        direct_counts AS (
            SELECT sponsored_by_id AS root_id, COUNT(*) AS direct_count
            FROM {user_table}
            WHERE sponsored_by_id IN ({placeholders})
            GROUP BY sponsored_by_id
        ),
        purchase_stats AS (
            SELECT
                s.root_id,
                COALESCE(SUM(p.amount), 0) AS investment_usdt,
                COALESCE(SUM(
                    COALESCE(
                        p.approved_coin_amount,
                        CASE
                            WHEN COALESCE(p.coin_rate_at_approval, 0) > 0
                            THEN p.amount / p.coin_rate_at_approval
                            ELSE 0
                        END
                    )
                ), 0) AS investment_coins
            FROM scoped s
            LEFT JOIN {purchase_table} p
                ON p.user_id = s.user_id AND p.status = 'approved'
            GROUP BY s.root_id
        ),
        withdrawal_stats AS (
            SELECT
                s.root_id,
                COALESCE(SUM(w.amount), 0) AS withdrawals_usdt
            FROM scoped s
            LEFT JOIN {withdrawal_table} w
                ON w.user_id = s.user_id
                AND w.status IN ('pending', 'approved', 'completed')
            GROUP BY s.root_id
        ),
        active_stats AS (
            SELECT
                s.root_id,
                COUNT(*) FILTER (WHERE u.is_active = TRUE AND u.is_banned = FALSE) AS active_downline
            FROM scoped s
            INNER JOIN {user_table} u ON u.id = s.user_id
            GROUP BY s.root_id
        ),
        downline_counts AS (
            SELECT root_id, COUNT(DISTINCT user_id) AS downline_count
            FROM scoped
            GROUP BY root_id
        )
        SELECT
            r.root_id,
            COALESCE(dc.downline_count, 0) AS downline_count,
            COALESCE(dir.direct_count, 0) AS direct_count,
            COALESCE(ps.investment_usdt, 0) AS investment_usdt,
            COALESCE(ps.investment_coins, 0) AS investment_coins,
            COALESCE(ws.withdrawals_usdt, 0) AS withdrawals_usdt,
            COALESCE(act.active_downline, 0) AS active_downline
        FROM roots r
        LEFT JOIN downline_counts dc ON dc.root_id = r.root_id
        LEFT JOIN direct_counts dir ON dir.root_id = r.root_id
        LEFT JOIN purchase_stats ps ON ps.root_id = r.root_id
        LEFT JOIN withdrawal_stats ws ON ws.root_id = r.root_id
        LEFT JOIN active_stats act ON act.root_id = r.root_id
    """

    params = sponsor_ids + sponsor_ids
    metrics: dict[int, dict[str, Any]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            root_id = int(row[0])
            metrics[root_id] = {
                'downline_count': int(row[1]),
                'direct_count': int(row[2]),
                'investment_usdt': float(row[3]),
                'investment_coins': float(row[4]),
                'withdrawals_usdt': float(row[5]),
                'active_downline': int(row[6]),
            }

    for sponsor_id in sponsor_ids:
        metrics.setdefault(
            sponsor_id,
            {
                'downline_count': 0,
                'direct_count': 0,
                'investment_usdt': 0.0,
                'investment_coins': 0.0,
                'withdrawals_usdt': 0.0,
                'active_downline': 0,
            },
        )
    return metrics


def _build_children_map() -> dict[int, list[int]]:
    children: dict[int, list[int]] = defaultdict(list)
    for user_id, parent_id in User.objects.exclude(sponsored_by_id=None).values_list('id', 'sponsored_by_id'):
        if parent_id:
            children[parent_id].append(user_id)
    return children


def _collect_downline_sets(sponsor_ids: list[int], children: dict[int, list[int]]) -> dict[int, set[int]]:
    downline_by_root: dict[int, set[int]] = {}
    for root_id in sponsor_ids:
        seen: set[int] = set()
        queue = deque(children.get(root_id, []))
        while queue:
            uid = queue.popleft()
            if uid in seen:
                continue
            seen.add(uid)
            queue.extend(children.get(uid, []))
            if len(seen) > 50000:
                break
        downline_by_root[root_id] = seen
    return downline_by_root


def _fetch_metrics_python(sponsor_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not sponsor_ids:
        return {}

    children = _build_children_map()
    downline_by_root = _collect_downline_sets(sponsor_ids, children)

    user_to_roots: dict[int, list[int]] = defaultdict(list)
    all_downline_ids: set[int] = set()
    for root_id, downline in downline_by_root.items():
        for uid in downline:
            user_to_roots[uid].append(root_id)
            all_downline_ids.add(uid)

    metrics = {
        sid: {
            'downline_count': len(downline_by_root.get(sid, set())),
            'direct_count': len(children.get(sid, [])),
            'investment_usdt': 0.0,
            'investment_coins': 0.0,
            'withdrawals_usdt': 0.0,
            'active_downline': 0,
        }
        for sid in sponsor_ids
    }

    if all_downline_ids:
        active_ids = set(
            User.objects.filter(
                id__in=all_downline_ids,
                is_active=True,
                is_banned=False,
            ).values_list('id', flat=True)
        )
        for root_id, downline in downline_by_root.items():
            metrics[root_id]['active_downline'] = sum(1 for uid in downline if uid in active_ids)

        purchases = Purchase.objects.filter(
            user_id__in=all_downline_ids,
            status='approved',
        ).only('user_id', 'amount', 'approved_coin_amount', 'coin_rate_at_approval')

        for purchase in purchases:
            roots = user_to_roots.get(purchase.user_id, [])
            if not roots:
                continue
            usdt = float(purchase.amount)
            coins = float(
                purchase.approved_coin_amount
                if purchase.approved_coin_amount is not None
                else purchase.calculated_coins
            )
            for root_id in roots:
                metrics[root_id]['investment_usdt'] += usdt
                metrics[root_id]['investment_coins'] += coins

        withdrawal_rows = (
            Withdrawal.objects.filter(
                user_id__in=all_downline_ids,
                status__in=WITHDRAWAL_STATUSES,
            )
            .values('user_id')
            .annotate(total=Coalesce(Sum('amount'), Decimal('0')))
        )
        for row in withdrawal_rows:
            for root_id in user_to_roots.get(row['user_id'], []):
                metrics[root_id]['withdrawals_usdt'] += float(row['total'])

    return metrics


def _fetch_downline_metrics(sponsor_ids: list[int]) -> dict[int, dict[str, Any]]:
    engine = settings.DATABASES['default']['ENGINE']
    if 'postgresql' in engine:
        try:
            return _fetch_metrics_postgresql(sponsor_ids)
        except Exception:
            pass
    return _fetch_metrics_python(sponsor_ids)


def get_sponsor_report_rows(
    *,
    search: str | None = None,
    order_by: str = '-total_investment_usdt',
    min_investment_usdt: float | None = None,
    min_reward_percentage: float | None = None,
) -> list[dict[str, Any]]:
    """
    Build flat sponsor report rows for admin dashboards and APIs.

    order_by: one of total_investment_usdt, -total_investment_usdt, sponsored_users_count,
              -sponsored_users_count, total_earning, -total_earning, sponsor_name, -sponsor_name
    """
    sponsors = list(_sponsor_base_queryset(search))
    if not sponsors:
        return []

    sponsor_ids = [s.id for s in sponsors]
    metrics_map = _fetch_downline_metrics(sponsor_ids)

    settings_obj = SystemSettings.get_settings()
    default_reward_percentage = float(settings_obj.sponsor_percentage or 0)

    rows: list[dict[str, Any]] = []
    for sponsor in sponsors:
        base = metrics_map.get(sponsor.id, {})
        base['sponsor_earnings'] = float(sponsor.sponsor_earnings or 0)
        rows.append(_serialize_row(sponsor, base, default_reward_percentage))

    if min_investment_usdt is not None:
        rows = [row for row in rows if row['total_investment_usdt'] >= min_investment_usdt]
    if min_reward_percentage is not None:
        rows = [row for row in rows if row['reward_percentage'] >= min_reward_percentage]

    reverse = order_by.startswith('-')
    key_name = order_by.lstrip('-')
    key_map = {
        'total_investment_usdt': lambda r: r['total_investment_usdt'],
        'sponsored_users_count': lambda r: r['sponsored_users_count'],
        'total_earning': lambda r: r['total_earning'],
        'sponsor_name': lambda r: (r['sponsor_name'] or '').lower(),
    }
    sort_key = key_map.get(key_name, key_map['total_investment_usdt'])
    rows.sort(key=sort_key, reverse=reverse)
    return rows

"""One-off claim diagnostic — run: .venv\\Scripts\\python.exe manage.py shell < scripts/check_claim_status.py"""
import os
import sys
from pathlib import Path

# Allow running via: python scripts/check_claim_status.py from backend/
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir / 'tradex'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tradex.settings')

import django

django.setup()

from apps.accounts.models import User
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from apps.withdrawals.claims import create_claim, get_user_claim_schedule

EMAIL = 'rzxgraphics@gmail.com'

print('=' * 60)
print('CLAIM DIAGNOSTIC FOR:', EMAIL)
print('=' * 60)

try:
    u = User.objects.get(email=EMAIL)
except User.DoesNotExist:
    print('ERROR: User not found')
    sys.exit(1)

print(f'User id={u.id} username={u.username} staff={u.is_staff}')
print()

print('--- All purchases ---')
purchases = list(Purchase.objects.filter(user=u).order_by('-id'))
if not purchases:
    print('(none)')
else:
    for p in purchases:
        print(
            f'  id={p.id} {p.transaction_id} status={p.status} '
            f'assigned={p.is_coins_assigned} amount={p.amount} '
            f'assigned_at={p.coins_assigned_at}'
        )

p = Purchase.objects.filter(user=u, status='approved').order_by('-id').first()
print()

s = SystemSettings.get_settings()
print('--- System settings ---')
print(f'  stage1_hours={s.stage1_hours} stage2_hours={s.stage2_hours} stage3_hours={s.stage3_hours}')
print(f'  profit_enabled={s.profit_enabled} profit_percentage={s.profit_percentage}')
print()

if p is None:
    print('RESULT: No approved purchase — admin must approve first.')
    sys.exit(0)

if not p.is_coins_assigned:
    print('RESULT: Purchase approved but coins NOT assigned.')
    print('  ACTION: Admin panel -> Purchases -> Assign coins')
    sys.exit(0)

sched = get_user_claim_schedule(u)
if not sched:
    print('RESULT: No claim schedule (unexpected if assigned=True)')
    sys.exit(0)

item = sched[0]
print('--- Claim schedule (latest purchase) ---')
print(f'  TX: {item["transaction_id"]}')
print(f'  base_usdt={item["base_usdt"]} profit%={item.get("profit_percentage")} total_usdt={item["total_usdt"]}')
print()

for st in item['stages']:
    print(
        f'  Stage {st["stage"]}: state={st["state"]} can_request={st["can_request"]} '
        f'coins={st["amount_coins"]} seconds_until_unlock={st["seconds_until_unlock"]}'
    )

st1 = item['stages'][0]
print()
if st1['can_request']:
    print('RESULT: Stage 1 is READY — Claim button should work on Withdraw page.')
    try:
        claim = create_claim(u, p, 1, '0xDIAGNOSTIC_TEST_WALLET')
        print(f'  SHELL TEST CLAIM OK: status={claim.status} amount_coins={claim.amount_coins}')
    except Exception as exc:
        print(f'  SHELL TEST CLAIM FAILED: {exc}')
else:
    hours_left = (st1['seconds_until_unlock'] or 0) / 3600
    print(f'RESULT: Stage 1 LOCKED — wait ~{hours_left:.1f} hours OR set stage hours to 0 in admin.')
    print('  ACTION: Admin -> Coin Settings -> Stage 1/2/3 hours = 0 for instant testing')

print('=' * 60)

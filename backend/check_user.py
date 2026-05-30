from apps.accounts.models import User

u = User.objects.filter(username='alikhan').first()
if u:
    print(f'Found: True')
    print(f'Email: {u.email}')
    print(f'is_active: {u.is_active}')
    print(f'is_banned: {u.is_banned}')
    print(f'has_usable_password: {u.has_usable_password()}')
    print(f'check_password User123!: {u.check_password("User123!")}')
else:
    print('User alikhan NOT FOUND')

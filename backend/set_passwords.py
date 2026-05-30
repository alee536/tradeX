from django.contrib.auth import get_user_model

def set_passwords():
    User = get_user_model()
    users = User.objects.filter(is_superuser=False)
    for u in users:
        u.set_password('User123!')
        u.save()
    print("Passwords updated!")

set_passwords()

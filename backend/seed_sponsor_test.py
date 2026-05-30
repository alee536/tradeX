from django.contrib.auth import get_user_model
from apps.purchases.models import Purchase
from apps.settings_app.models import SystemSettings
from decimal import Decimal

def seed():
    User = get_user_model()
    # Setup SystemSettings
    settings = SystemSettings.get_settings()
    settings.sponsor_reward_threshold_usdt = Decimal('1000.00')
    settings.sponsor_percentage = Decimal('5.00')
    settings.save()

    data = [
        {"name": "Ali Khan", "username": "alikhan", "count": 5, "sales": 1000, "pct": 5.0},
        {"name": "Ahmed Raza", "username": "ahmedraza", "count": 3, "sales": 750, "pct": 5.0},
        {"name": "Usman Ali", "username": "usmanali", "count": 8, "sales": 2500, "pct": 10.0},
        {"name": "Hassan Malik", "username": "hassanmalik", "count": 2, "sales": 400, "pct": 10.0},
    ]

    for item in data:
        # Create Parent
        parent, _ = User.objects.get_or_create(username=item['username'], defaults={
            'full_name': item['name'],
            'email': f"{item['username']}@test.com",
            'sponsor_reward_percentage': Decimal(str(item['pct'])),
            'is_active': True,
        })
        parent.sponsor_reward_percentage = Decimal(str(item['pct']))
        parent.save()

        sales_per_child = Decimal(str(item['sales'])) / Decimal(str(item['count']))

        # Create Children and Purchases
        for i in range(item['count']):
            child_username = f"child_{item['username']}_{i}"
            child, _ = User.objects.get_or_create(username=child_username, defaults={
                'full_name': f"Child {i} of {item['name']}",
                'email': f"{child_username}@test.com",
                'sponsored_by': parent,
                'is_active': True,
            })
            child.sponsored_by = parent
            child.save()

            # Create Purchase for child
            Purchase.objects.filter(user=child).delete()
            Purchase.objects.create(
                user=child,
                amount=sales_per_child,
                status='approved'
            )
        
        # Create a grandchild to prove they aren't counted
        gc_username = f"grandchild_{item['username']}"
        first_child = User.objects.get(username=f"child_{item['username']}_0")
        gc, _ = User.objects.get_or_create(username=gc_username, defaults={
            'full_name': f"Grandchild of {item['name']}",
            'email': f"{gc_username}@test.com",
            'sponsored_by': first_child,
            'is_active': True,
        })
        gc.sponsored_by = first_child
        gc.save()
        Purchase.objects.filter(user=gc).delete()
        Purchase.objects.create(
            user=gc,
            amount=Decimal('5000.00'), # Huge amount to make it obvious if it was counted
            status='approved'
        )

    print("Test data seeded successfully!")

seed()

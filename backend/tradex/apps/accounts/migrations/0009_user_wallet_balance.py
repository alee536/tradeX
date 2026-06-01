from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_user_sponsor_reward_percentage'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='wallet_balance',
            field=models.DecimalField(
                decimal_places=8,
                default=0,
                help_text='Main in-app wallet balance (coins), including transferred sponsor rewards.',
                max_digits=20,
            ),
        ),
    ]

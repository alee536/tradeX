from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0003_systemsettings_sold_coins_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='profit_enabled',
            field=models.BooleanField(default=False, help_text='Enable profit display and reward cycle for users'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='profit_percentage',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Profit percentage applied to assigned purchase USDT, e.g. 10 = 10%',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='profit_cycle_hours',
            field=models.IntegerField(
                default=72,
                help_text='Hours after coin assignment before each profit reward cycle',
            ),
        ),
    ]

from decimal import Decimal

from django.db import migrations, models


def set_default_min_claim(apps, schema_editor):
    SystemSettings = apps.get_model('settings_app', 'SystemSettings')
    SystemSettings.objects.filter(pk=1).update(sponsor_min_claim_amount_usd=Decimal('100'))


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0008_multilevel_sponsor_reward'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='sponsor_min_claim_amount_usd',
            field=models.DecimalField(
                decimal_places=8,
                default=Decimal('100'),
                help_text='Minimum USD value of accumulated sponsor reward coins before Claim Reward is enabled.',
                max_digits=20,
            ),
        ),
        migrations.RunPython(set_default_min_claim, migrations.RunPython.noop),
    ]

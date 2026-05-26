from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_password_reset_otp'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='sponsor_reward_percentage',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Admin-defined reward % for this sponsor. Falls back to global sponsor_percentage if null.',
                max_digits=5,
                null=True,
            ),
        ),
    ]

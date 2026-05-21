import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('settings_app', '0004_systemsettings_profit_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfitClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_usdt', models.DecimalField(decimal_places=8, max_digits=20)),
                ('amount_coins', models.DecimalField(decimal_places=8, max_digits=20)),
                ('profit_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('profit_cycle_hours', models.PositiveIntegerField()),
                ('base_usdt_snapshot', models.DecimalField(decimal_places=8, max_digits=20)),
                ('claimed_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='profit_claims',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Profit claim',
                'verbose_name_plural': 'Profit claims',
                'ordering': ['-claimed_at'],
            },
        ),
    ]

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0006_signup_otp_verification'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordResetOtp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('otp_hash', models.CharField(max_length=64)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_sent_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_otps', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='passwordresetotp',
            index=models.Index(fields=['email', 'used_at', 'expires_at'], name='accounts_pwd_reset_active_idx'),
        ),
    ]

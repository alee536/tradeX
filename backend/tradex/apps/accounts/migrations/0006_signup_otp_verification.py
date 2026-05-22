from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_sponsor_access'),
    ]

    operations = [
        migrations.CreateModel(
            name='SignupOtpVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('otp_hash', models.CharField(max_length=64)),
                ('signup_payload', models.JSONField()),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_sent_at', models.DateTimeField()),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='signupotpverification',
            index=models.Index(
                fields=['email', 'verified_at', 'expires_at'],
                name='accounts_otp_email_active_idx',
            ),
        ),
    ]

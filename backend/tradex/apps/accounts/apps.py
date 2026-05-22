from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        # Startup email config (Docker logs) — helps debug OTP delivery
        from django.conf import settings

        backend = getattr(settings, 'EMAIL_BACKEND', '')
        print('[OTP EMAIL DEBUG] Django started — email settings:', flush=True)
        print(f'[OTP EMAIL DEBUG]   EMAIL_BACKEND={backend}', flush=True)
        print(f'[OTP EMAIL DEBUG]   EMAIL_HOST={getattr(settings, "EMAIL_HOST", "")}', flush=True)
        print(
            f'[OTP EMAIL DEBUG]   EMAIL_HOST_USER={getattr(settings, "EMAIL_HOST_USER", "")!r}',
            flush=True,
        )
        print(
            f'[OTP EMAIL DEBUG]   password set={bool(getattr(settings, "EMAIL_HOST_PASSWORD", ""))}',
            flush=True,
        )
        if 'console' in backend:
            print(
                '[OTP EMAIL DEBUG]   WARNING: console backend — emails go to logs only, '
                'not inbox. Use smtp + backend/.env for real delivery.',
                flush=True,
            )

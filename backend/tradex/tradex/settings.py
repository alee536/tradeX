import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT.parent / 'frontend'
FRONTEND_DIST_DIR = FRONTEND_DIR / 'dist'

load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-24tradex-dev-secret-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get(
        'ALLOWED_HOSTS',
        's24tx.com,www.s24tx.com,.onrender.com,localhost,127.0.0.1',
    ).split(',') if h.strip()
]

INSTALLED_APPS = [
    'apps.admin_dashboard',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'apps.accounts',
    'apps.purchases',
    'apps.withdrawals',
    'apps.sponsor',
    'apps.notifications',
    'apps.settings_app',
    'apps.dashboard',
    'apps.admin_api',
    'apps.transactions',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tradex.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(PROJECT_ROOT / 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tradex.wsgi.application'

def _writable_path(requested: str, fallback: Path) -> Path:
    """Use requested path if its parent can be created; otherwise fall back (e.g. Render Free /var/data)."""
    if not requested:
        return fallback
    path = Path(requested)
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return fallback


def _resolve_sqlite_path() -> Path:
    """SQLite path: DATABASE_PATH on persistent disk, else backend/tradex/db.sqlite3."""
    default = BASE_DIR / os.environ.get('DB_NAME', 'db.sqlite3')
    database_path = os.environ.get('DATABASE_PATH', '').strip()
    return _writable_path(database_path, default)


DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': (
            _resolve_sqlite_path()
            if DB_ENGINE == 'django.db.backends.sqlite3'
            else os.environ.get('DB_NAME', '')
        ),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = PROJECT_ROOT / 'staticfiles'
STATICFILES_DIRS = [PROJECT_ROOT / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
_media_root = os.environ.get('MEDIA_ROOT', '').strip()
MEDIA_ROOT = _writable_path(_media_root, PROJECT_ROOT / 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'apps.accounts.authentication.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'apps.accounts.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

CORS_ALLOW_CREDENTIALS = True
_cors_allowed = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
if _cors_allowed:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_allowed.split(',') if o.strip()]
else:
    CORS_ALLOW_ALL_ORIGINS = os.environ.get('CORS_ALLOW_ALL_ORIGINS', 'True') == 'True'

JWT_SECRET = os.environ.get('JWT_SECRET', SECRET_KEY)
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', str(24 * 7)))

SITE_URL = os.environ.get('SITE_URL', 'https://24tradex.com')

# Production security (Render terminates SSL — trust X-Forwarded-Proto)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True') == 'True'
    _hsts = os.environ.get('SECURE_HSTS_SECONDS', '31536000')
    SECURE_HSTS_SECONDS = int(_hsts) if _hsts else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

_csrf_trusted = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
if _csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_trusted.split(',') if o.strip()]

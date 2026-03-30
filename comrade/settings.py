"""
Django settings for comrade project.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
# In production, SECRET_KEY MUST be set via environment variable.
_secret = os.getenv('SECRET_KEY', '')
if not _secret:
    import warnings
    warnings.warn('SECRET_KEY not set! Using insecure fallback for local dev only.', stacklevel=1)
    _secret = 'django-insecure-LOCAL-DEV-ONLY-c+%9#v0&z&-av-84em1*d3aazv4$'
SECRET_KEY = _secret

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.sites',
    
    # Custom Apps
    'Authentication',
    'rest_framework',
    'django_filters',
    'UserManagement',
    'Rooms',
    'Announcements',
    'Events',
    'Resources',
    'Specialization',
    'Organisation',
    'Institution',
    'Task',
    'Payment',
    'Research',
    'Opinions',  # Social opinions feature
    'Notifications',  # Notification system
    'Messages',  # Direct messaging system
    'Verification',  # New verification system
    'Articles',  # Articles/Blog system
    'QomAI',  # AI Assistant
    'Funding',  # Business Funding Hub
    'Careers',  # Gigs & Career Opportunities
    
    # Authentication Support Apps
    'DeviceManagement',
    'ActivityLog',
    
    # JWT and Social Auth
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.twitter_oauth2',
    'allauth.socialaccount.providers.apple',

]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'Authentication.middleware.ActiveUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
    'ActivityLog.tracking_middleware.ActivityTrackingMiddleware',
]

# ALLOWED_HOSTS: read from env, with sensible defaults
_allowed = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()] or [
    "localhost", "127.0.0.1", "[::1]", "qomrade.onrender.com",
]

# CORS settings - FIX THESE
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
# ]

_cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()] or [
    "http://localhost:3000", "http://localhost:5173",
    "https://comrade-frontend-ochre.vercel.app",
]

# CRITICAL: This must be True for cookies/session auth
# CORS_ALLOW_CREDENTIALS = True


# CSRF settings - CRITICAL for POST requests
_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(",") if o.strip()] or [
    "https://comrade-frontend-ochre.vercel.app",
    "https://qomrade.onrender.com",
]

# Additional CORS headers needed
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'access-control-allow-credentials',  # Add this
]

# Add these settings for better CORS handling
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://localhost:8000$",
    r"^https?://localhost:8080$",
    r"^https?://localhost:5173$",
    r"^https?://localhost:3000$",
    r"^https://comrade-frontend-ochre\.vercel\.app$",
    r"^https://qomrade\.onrender\.com$",
]

# ── Security settings ───────────────────────────────────────────────────────
# SSL / HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HSTS — instruct browsers to only connect via HTTPS
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000  # 1 year in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Prevent MIME-type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# Request body size limits (prevent oversized uploads / DoS)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024    # 10 MB

CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True") == "True"



# Twilio configuration
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
COUNTRY_CODE = os.getenv('COUNTRY_CODE', '')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Email configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

ROOT_URLCONF = 'comrade.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'comrade.wsgi.application'

# ── Database ────────────────────────────────────────────────────────────────
# Production: set DATABASE_URL env var (PostgreSQL on Render)
# Local dev:  leave DATABASE_URL unset → falls back to SQLite
_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=0,  # 0 is recommended for Supabase connection poolers (port 6543)
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('RATE_LIMIT_ANON', '100/hour'),
        'user': os.getenv('RATE_LIMIT_USER', '1000/hour'),
        'login': os.getenv('RATE_LIMIT_LOGIN', '5/minute'),
        'otp': os.getenv('RATE_LIMIT_OTP', '3/hour'),
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

AUTH_USER_MODEL = 'Authentication.CustomUser'
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# PAYMENT PROVIDER CONFIGURATION
# ============================================================================

# Stripe
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# PayPal
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')  # 'sandbox' or 'live'
PAYPAL_API_URL = 'https://api-m.sandbox.paypal.com' if PAYPAL_MODE == 'sandbox' else 'https://api-m.paypal.com'

# M-Pesa (Safaricom)
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_BUSINESS_SHORTCODE = os.getenv('MPESA_BUSINESS_SHORTCODE', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_API_URL = os.getenv('MPESA_API_URL', 'https://sandbox.safaricom.co.ke')
MPESA_STK_PUSH_URL = os.getenv('MPESA_STK_PUSH_URL', f'{MPESA_API_URL}/mpesa/stkpush/v1/processrequest')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')

# Equity Bank (Jenga API)
EQUITY_API_KEY = os.getenv('EQUITY_API_KEY', '')
EQUITY_MERCHANT_CODE = os.getenv('EQUITY_MERCHANT_CODE', '')
EQUITY_API_URL = os.getenv('EQUITY_API_URL', 'https://uat.jengahq.io')  # UAT for testing
EQUITY_CONSUMER_SECRET = os.getenv('EQUITY_CONSUMER_SECRET', '')

# Default payment destination (where platform earnings are routed)
PAYMENT_DESTINATION = os.getenv('PAYMENT_DESTINATION', 'stripe')  # stripe, paypal, mpesa, equity

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'consent'},
    },
    "twitter_oauth2": {
        'APP': {
            'client_id': os.getenv('TWITTER_CLIENT_ID', ''),
            'secret': os.getenv('TWITTER_CLIENT_SECRET', ''),
            'key': ''
        },
        "SCOPE": [
            "tweet.read",
            "users.read",
            "offline.access",
        ],
        "AUTH_PARAMS": {
            "access_type": "offline",
        },
        "OAUTH_PKCE_ENABLED": True,
    },
    'apple': {
        'APP': {
            'client_id': os.getenv('APPLE_CLIENT_ID', ''),
            'secret': os.getenv('APPLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'name'],
        'AUTH_PARAMS': {'response_mode': 'form_post'},
    },
}

# Account adapter for custom user model
ACCOUNT_ADAPTER = 'Authentication.adapters.MyAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'Authentication.adapters.MySocialAccountAdapter'

# Email-only authentication (NO USERNAME) - Updated for allauth v0.50+
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {'email'}  # New v0.50+ syntax
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']  # New v0.50+ syntax
ACCOUNT_EMAIL_VERIFICATION = 'optional' if DEBUG else 'mandatory'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Qomrade] '

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Trust OAuth providers
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = True

# Redirect URLs - Point to frontend
# NOTE: Frontend runs on port 3000 by default, ensure FRONTEND_URL has trailing slash
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173/')

# Dashboard is at root '/' in frontend
FRONTEND_DASHBOARD = FRONTEND_URL  # Frontend dashboard is at '/'
LOGIN_REDIRECT_URL = FRONTEND_DASHBOARD
ACCOUNT_LOGIN_REDIRECT_URL = FRONTEND_DASHBOARD
ACCOUNT_SIGNUP_REDIRECT_URL = FRONTEND_DASHBOARD
SOCIALACCOUNT_LOGIN_REDIRECT_URL = FRONTEND_DASHBOARD
LOGOUT_REDIRECT_URL = f"{FRONTEND_URL}login"



# Django AllAuth settings for development
SITE_ID = 1

# Allow HTTP in dev, HTTPS in production
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http' if DEBUG else 'https'

# These settings help with cross-origin requests
# ACCOUNT_EMAIL_VERIFICATION already set above (optional in dev, mandatory in prod)
ACCOUNT_SESSION_REMEMBER = True

# Cookie SameSite policy — required for cross-origin httpOnly JWT cookies
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False   # Allow JS to read CSRF token
SESSION_COOKIE_HTTPONLY = True  # Session cookie is httpOnly

